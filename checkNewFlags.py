#!/usr/bin/env python3
"""
checkNewFlags.py - Pyrrhic Silva Shop

Scans RecipesData.csv for 4b-[flag] entries and compares the flag codes
against skuVocab.DESIGNS, in BOTH directions:

  1. Recipe -> vocab: flag codes used in RecipesData.csv that aren't in
     skuVocab.DESIGNS at all (NEW), or that are recognized only as a
     non-canonical alias/misspelling (e.g. 'BI' instead of 'BI3').
     Run this BEFORE recipeGen4B.py when starting the "add new recipes"
     workflow, so you know up front whether skuVocab.py (and skuKey.txt)
     need a new entry before you generate 4C/6P/8R equivalents.

  2. Vocab -> recipe: designs already in skuVocab.DESIGNS that have no
     4b-[flag] recipe yet under any of their known code spellings. This
     is the more common direction in practice, since skuVocab.py is
     where new designs tend to get added first. Not an error -- just a
     checklist of what still needs a recipe.

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

USAGE:
    python3 checkNewFlags.py

You'll be prompted for the RecipesData.csv path.
"""

import csv
from skuVocab import DESIGNS


def load_recipe_skus(filename):
    """Load just the SKU column from RecipesData.csv.

    Uses the same manual comma-split as recipeGen4B.py's load_recipes(),
    rather than csv.DictReader, because these rows are variable-length
    (materials columns are padded with trailing empty cells and csv's
    dialect handling isn't needed here -- we only want column 0).
    """
    skus = []
    with open(filename, 'r', encoding='utf-8-sig') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) < 2:
                continue
            sku = parts[0].strip()
            if sku.lower() == 'sku':  # header row
                continue
            skus.append(sku)
    return skus


def extract_4b_flags(skus):
    """Return dict flag_code (uppercase) -> list of original SKUs that used it.

    Mirrors recipeGen4B.py's own parsing: sku[3:] after stripping the
    '4b-' prefix. This is safe ONLY because 4b- recipe rows in
    RecipesData.csv are charm-only recipes with no finding/length suffix
    baked in (findings like -lv, -nk18 are separate recipe rows, per
    skuCostLookup.py's parse_suffix / base_sku split). If that ever
    changes, this slicing logic needs to change too.
    """
    flags = {}
    for sku in skus:
        if sku.lower().startswith('4b-'):
            flag = sku[3:].strip().upper()
            if not flag:
                print(f"  \u26a0\ufe0f  Warning: '{sku}' has no flag after the 4b- prefix, skipping.")
                continue
            flags.setdefault(flag, []).append(sku)
    return flags


def group_designs_by_trend_column(designs):
    """Group DESIGNS entries by trend_column (the actual design identity),
    since multiple codes can point at the same design (e.g. BI/BI3 both
    -> BI3, TRANS/TRANS3/TRANS5 -> TRANS3/TRANS5 respectively).

    Returns dict trend_column -> {'codes': set of all codes for it,
    'canonical': the code where code == trend_column (or None if somehow
    absent), 'description': description text from the canonical code, or
    from whichever code is available if no canonical one exists}.
    """
    groups = {}
    for code, (desc, trend_col) in designs.items():
        group = groups.setdefault(trend_col, {'codes': set(), 'canonical': None, 'description': None})
        group['codes'].add(code)
        if code.upper() == trend_col.upper():
            group['canonical'] = code
            group['description'] = desc
        elif group['description'] is None:
            group['description'] = desc
    return groups


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
        skus = load_recipe_skus(rec_path)
    except FileNotFoundError:
        print(f"Error: File not found at '{rec_path}'")
        return

    found_flags = extract_4b_flags(skus)
    print(f"\n  \u2713 {len(found_flags)} distinct 4b- flag code(s) found in {rec_path}")

    new, non_canonical, canonical = classify_flags(found_flags, DESIGNS)

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
    unused = find_unused_designs(found_flags, DESIGNS)
    if unused:
        print(f"\n\U0001F4CB IN skuVocab.py BUT NO 4b- RECIPE YET ({len(unused)}):")
        for trend_col in sorted(unused):
            group = unused[trend_col]
            label = group['canonical'] or trend_col
            other_codes = group['codes'] - {label}
            alias_note = f"  (aliases: {', '.join(sorted(other_codes))})" if other_codes else ""
            print(f"  \u2022 {label} - {group['description']}{alias_note}")
        print("\n  This is normal if you just haven't gotten to these yet -- it's")
        print("  not an error. Useful as a checklist of designs still needing a")
        print("  4b-[flag] recipe added to RecipesData.csv.")
    else:
        print("\n\u2705 Every design in skuVocab.py already has at least one 4b- recipe.")

    print()


if __name__ == "__main__":
    main()