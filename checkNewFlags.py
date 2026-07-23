#!/usr/bin/env python3
"""
checkNewFlags.py - Pyrrhic Silva Shop

Scans RecipesData.csv for 4b-[flag] entries and compares the flag codes
against skuVocab.DESIGNS. Run this BEFORE recipeGen4B.py when starting the
"add new recipes" workflow, so you know up front whether skuVocab.py (and
skuKey.txt) need a new entry before you generate 4C/6P/8R equivalents.

WHY THIS IS A SEPARATE SCRIPT (not folded into recipeGen4B.py):
recipeGen4B.py's job is translating an EXISTING 4b-[flag] recipe into its
4C/6P/8R equivalents. This script's job is validating that the flag code
even exists in the vocabulary before you get that far. Different concern,
different script -- same reasoning as why skuVocab.py's own
validate_against_trend_columns() is a separate function rather than being
folded into salesToTrendsGen.py's main().

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
    print()


if __name__ == "__main__":
    main()