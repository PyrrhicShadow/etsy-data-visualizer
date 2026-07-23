#!/usr/bin/env python3
"""
checkNewFlags.py - Pyrrhic Silva Shop

Scans RecipesData.csv for 4B/4C/6P/8R-[flag] entries and compares the
flag codes against skuVocab.DESIGNS, across THREE checks:

  1. Recipe -> vocab: flag codes used ANYWHERE in RecipesData.csv (any of
     the four bead types) that aren't in skuVocab.DESIGNS at all (NEW),
     or that are recognized only as a non-canonical alias/misspelling
     (e.g. 'BI' instead of 'BI3'). Run this BEFORE recipeGen4B.py when
     starting the "add new recipes" workflow, so you know up front
     whether skuVocab.py (and skuKey.txt) need a new entry.

  2. Vocab -> master recipe: designs already in skuVocab.DESIGNS that
     have no master 4B recipe yet under any of their known code
     spellings. This is the more common direction in practice, since
     skuVocab.py is where new designs tend to get added first. Not an
     error -- just a checklist of what still needs a 4B recipe.

  3. Conversion completeness: designs that have a recipe under SOME but
     not ALL of 4B/4C/6P/8R -- i.e. recipeGen4B.py has been run (or the
     recipe was hand-added) for some bead types but not others. This is
     the "where did I leave off converting" check.

HOW "NEW" VS "NON-CANONICAL" IS DETERMINED:
skuVocab.DESIGNS maps code -> (description, trend_column). For canonical
codes the trend_column equals the code itself (e.g. 'LESBO5' -> 'LESBO5').
For old aliases and known Etsy misspellings, it doesn't (e.g. 'BI' ->
'BI3', 'MULTG' -> 'MULTIG'). There's no separate "is this an alias" flag
in the data -- only a source comment, which a script can't read reliably.
So this script uses that code-vs-column mismatch as the structural signal
for "non-canonical, but not necessarily new." Flags that don't appear as
a DESIGNS key at all -- under any spelling -- are reported as genuinely
NEW.

The same alias-awareness applies to the conversion-completeness check
(#3): if a design was converted as 4b-bi but 6p-bi3 (inconsistent code
across bead types), it's still recognized as ONE design with 4B and 6P
done, not two unrelated half-finished conversions.

USAGE:
    python3 checkNewFlags.py

You'll be prompted for the RecipesData.csv path.
"""

import csv
from skuVocab import DESIGNS, group_designs_by_trend_column, flag_identity
from shopIO import load_recipes

CONVERSION_PREFIXES = ('4B', '4C', '6P', '8R')  # matches recipeGen4B.py's translation targets


def extract_flags_by_prefix(skus, prefixes=CONVERSION_PREFIXES):
    """Return dict prefix -> {flag_code (uppercase): [original SKUs]} for
    each of the given bead-type prefixes.

    Mirrors recipeGen4B.py's own parsing for the 4B case (sku[len(prefix)+1:]
    after stripping 'prefix-'). Safe for the same reason as before: these
    recipe rows are charm-only, with no finding/length suffix baked in
    (findings like -lv, -nk18 are separate recipe rows, per
    skuCostLookup.py's parse_suffix / base_sku split). If that ever
    changes, this slicing logic needs to change too.
    """
    result = {p: {} for p in prefixes}
    for sku in skus:
        sku_lower = sku.lower()
        for p in prefixes:
            token = p.lower() + '-'
            if sku_lower.startswith(token):
                flag = sku[len(token):].strip().upper()
                if not flag:
                    print(f"  \u26a0\ufe0f  Warning: '{sku}' has no flag after the "
                          f"{p}- prefix, skipping.")
                    continue
                result[p].setdefault(flag, []).append(sku)
                break  # a SKU can only match one prefix
    return result


def find_unused_designs(found_flags, designs):
    """Return dict trend_column -> group info (codes/canonical/description)
    for every design in skuVocab.DESIGNS that has NO 4b- recipe yet under
    ANY of its known code spellings.

    found_flags is the same dict extract_4b_flags() returns: flag_code
    (already uppercase) -> list of source SKUs. Only the keys matter here.
    """
    found_set = set(found_flags.keys())
    groups = group_designs_by_trend_column(designs)

    unused = {}
    for trend_col, group in groups.items():
        if not (group['codes'] & found_set):
            unused[trend_col] = group
    return unused


def check_conversion_completeness(flags_by_prefix, designs, prefixes=CONVERSION_PREFIXES):
    """For every design that has a recipe under AT LEAST ONE of the given
    bead-type prefixes, but NOT ALL of them, report which prefixes are
    done and which are still missing.

    Grouping is by flag_identity() rather than literal code, so a design
    converted inconsistently (e.g. 4b-bi but 6p-bi3) is still recognized
    as one design with 4B/6P done and 4C/8R missing -- not misread as two
    unrelated half-finished conversions.

    Returns dict identity -> {'present': {prefix: flag_code_used},
    'missing': set of prefixes}. Designs with recipes under every prefix,
    or under none of them, are excluded -- the former needs no action,
    and the latter is find_unused_designs()'s job to report.
    """
    by_identity = {}
    for p in prefixes:
        for flag in flags_by_prefix[p]:
            identity = flag_identity(flag, designs)
            by_identity.setdefault(identity, {})[p] = flag

    incomplete = {}
    for identity, present_map in by_identity.items():
        missing = set(prefixes) - set(present_map.keys())
        if missing:
            incomplete[identity] = {'present': present_map, 'missing': missing}
    return incomplete


def format_completeness_line(identity, info, prefixes=CONVERSION_PREFIXES):
    """'IDENTITY - have: 4B, 6P(as BI)   missing: 4C, 8R' -- noting the
    actual code used wherever it differs from the display identity, since
    that's a detail worth knowing (see flag_identity())."""
    have_parts = []
    for p in prefixes:
        if p in info['present']:
            used = info['present'][p]
            have_parts.append(p if used == identity else f"{p}(as {used})")
    have_str = ', '.join(have_parts)
    missing_str = ', '.join(p for p in prefixes if p in info['missing'])
    return f"  \u2022 {identity} - have: {have_str}   missing: {missing_str}"


def classify_flags(found_flags, designs):
    """Split found flag codes into three buckets:
      - new: code isn't a DESIGNS key under any spelling
      - non_canonical: code IS a DESIGNS key, but its trend_column differs
        from the code itself (old alias or known misspelling)
      - canonical: code is a DESIGNS key and matches its own trend_column
    Returns three dicts, each flag_code -> list of source SKUs.
    """
    new, non_canonical, canonical = {}, {}, {}

    for flag, skus in found_flags.items():
        if flag not in designs:
            new[flag] = skus
        else:
            _desc, trend_col = designs[flag]
            if trend_col.upper() == flag.upper():
                canonical[flag] = skus
            else:
                non_canonical[flag] = skus

    return new, non_canonical, canonical


def main():
    print("=" * 60)
    print("CHECK NEW FLAGS - Pyrrhic Silva Shop")
    print("=" * 60)

    rec_path = input("\nEnter path to RecipesData CSV (or Enter for RecipesData.csv): ").strip()
    if not rec_path:
        rec_path = 'RecipesData.csv'

    try:
        skus = list(load_recipes(rec_path).keys())
    except FileNotFoundError:
        print(f"Error: File not found at '{rec_path}'")
        return

    flags_by_prefix = extract_flags_by_prefix(skus)
    counts_str = ', '.join(f"{p}={len(flags_by_prefix[p])}" for p in CONVERSION_PREFIXES)
    print(f"\n  \u2713 Distinct flag codes found by bead type: {counts_str}")

    # Union across all four bead types -- a flag introduced via 6p-newflag
    # before any 4b-newflag exists should still be caught here.
    combined_flags = {}
    for p in CONVERSION_PREFIXES:
        for flag, flag_skus in flags_by_prefix[p].items():
            combined_flags.setdefault(flag, []).extend(flag_skus)

    new, non_canonical, canonical = classify_flags(combined_flags, DESIGNS)

    print("\n" + "-" * 60)
    if new:
        print(f"\n\U0001F195 NEW - not in skuVocab.DESIGNS at all ({len(new)}):")
        for flag in sorted(new):
            skus_str = ', '.join(new[flag])
            print(f"  \u2022 {flag}   (from: {skus_str})")
        print("\n  Add these to skuVocab.py's DESIGNS dict (and skuKey.txt by hand)")
        print("  before running recipeGen4B.py, or the translated 6P/8R/4C recipes")
        print("  will pass the flag through unrecognized.")
    else:
        print("\n\u2705 No brand-new flag codes found.")

    if non_canonical:
        print(f"\n\u26a0\ufe0f  NON-CANONICAL - recognized, but not the canonical spelling ({len(non_canonical)}):")
        for flag in sorted(non_canonical):
            _desc, trend_col = DESIGNS[flag]
            skus_str = ', '.join(non_canonical[flag])
            print(f"  \u2022 {flag} -> canonical is {trend_col}   (from: {skus_str})")
        print("\n  These will still work (skuVocab.py maps them), but consider")
        print("  using the canonical code for new recipes going forward.")

    print(f"\n\u2713 {len(canonical)} flag(s) already canonical, no action needed.")

    print("\n" + "-" * 60)
    unused = find_unused_designs(flags_by_prefix['4B'], DESIGNS)
    if unused:
        print(f"\n\U0001F4CB IN skuVocab.py BUT NO 4B RECIPE YET ({len(unused)}):")
        for trend_col in sorted(unused):
            group = unused[trend_col]
            label = group['canonical'] or trend_col
            other_codes = group['codes'] - {label}
            alias_note = f"  (aliases: {', '.join(sorted(other_codes))})" if other_codes else ""
            print(f"  \u2022 {label} - {group['description']}{alias_note}")
        print("\n  This is normal if you just haven't gotten to these yet -- it's")
        print("  not an error. Useful as a checklist of designs still needing a")
        print("  master 4B recipe added to RecipesData.csv.")
    else:
        print("\n\u2705 Every design in skuVocab.py already has at least one 4B recipe.")

    print("\n" + "-" * 60)
    incomplete = check_conversion_completeness(flags_by_prefix, DESIGNS)
    if incomplete:
        print(f"\n\U0001F504 CONVERSION IN PROGRESS - some bead types still missing ({len(incomplete)}):")
        for identity in sorted(incomplete):
            print(format_completeness_line(identity, incomplete[identity]))
        print("\n  These have a recipe for at least one bead type but not all four.")
        print("  Run recipeGen4B.py on these (it skips ones that already exist) and")
        print("  paste the missing bead-type recipes back into RecipesData.csv.")
    else:
        print("\n\u2705 Every design with a recipe has all four bead types (4B/4C/6P/8R).")

    print()


if __name__ == "__main__":
    main()