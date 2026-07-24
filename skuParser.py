#!/usr/bin/env python3
"""
SKU Parser - Pyrrhic Silva Shop (Unified)

parse_sku(sku) is the single source of truth for decomposing a SKU string.
It returns a plain dict describing the SKU's structure -- prefix, design,
suffix category/length, and (crucially for costing) 'base_sku', the exact
lowercased substring that is used as a literal key into RecipesData.csv.

readable_description(sku_or_parsed) builds a human-readable sentence on
top of parse_sku()'s output. It exists purely for the CLI / human-facing
side of things; it does not re-parse anything.

skuCostLookup.py and salesToTrendsGen.py both call parse_sku() and use
only the pieces they need -- neither re-implements SKU parsing itself.
"""

import re
from skuVocab import (
    BEAD_PREFIXES, STANDALONE_PREFIXES, DESIGNS,
    SEASON_NAMES, AETHER_ELEMENTS, CC_COLORS, KYO_COLORS,
    FINDINGS, FINDINGS_LEN, TART_INFO,
)

# ---------------------------------------------------------------------
# Prefix matching: longest-first so no prefix can accidentally be a
# substring-match of a longer one (none currently collide, but this is
# free insurance).
# ---------------------------------------------------------------------
_ALL_PREFIXES = sorted(set(BEAD_PREFIXES) | set(STANDALONE_PREFIXES),
                       key=len, reverse=True)


def _design_map_for_prefix(prefix):
    """Which vocab dict holds the valid design tokens for this prefix."""
    if prefix == 'AETHER':
        return AETHER_ELEMENTS
    if prefix == 'SEASONS':
        return SEASON_NAMES
    if prefix == 'CC':
        return CC_COLORS
    if prefix == 'KYO':
        return KYO_COLORS
    if prefix in BEAD_PREFIXES:
        return DESIGNS
    return None


# ---------------------------------------------------------------------
# Suffix detection -- data-driven for findings (LV/WR/BP/DK/CH, straight
# from skuVocab.FINDINGS, so a new finding type needs zero changes here).
# NK/BRAC/BRAC-e stay as explicit regexes: the trailing number is not a
# vocabulary code, it's a length the customer/you choose per listing.
# ---------------------------------------------------------------------
def _finding_patterns():
    patterns = []
    for code in FINDINGS:
        if code == 'CH':
            patterns.append((code, re.compile(r'-ch(?:-[a-z]+)?$')))
        else:
            patterns.append((code, re.compile(rf'-{code.lower()}$')))
    return patterns


_FINDING_PATTERNS = _finding_patterns()
_BRAC_E_PATTERN = re.compile(r'-brac-e(\d+(?:\.\d+)?)$')
_BRAC_PATTERN = re.compile(r'-brac(\d+(?:\.\d+)?)$')
_NK_PATTERN = re.compile(r'-nk(\d+)$')


def _match_suffix(sku_lower):
    """Find the trailing suffix on a lowercased SKU string.
    Returns {'category', 'length', 'start'} or None if there's no suffix
    (e.g. a bare master-recipe key like '4b-rain6')."""
    for code, pattern in _FINDING_PATTERNS:
        m = pattern.search(sku_lower)
        if m:
            return {'category': code, 'length': None, 'start': m.start()}

    m = _BRAC_E_PATTERN.search(sku_lower)
    if m:
        raw = m.group(1)
        return {'category': 'BRAC-E',
                'length': float(raw) if '.' in raw else int(raw),
                'start': m.start()}

    m = _BRAC_PATTERN.search(sku_lower)
    if m:
        raw = m.group(1)
        return {'category': 'BRAC',
                'length': float(raw) if '.' in raw else int(raw),
                'start': m.start()}

    m = _NK_PATTERN.search(sku_lower)
    if m:
        return {'category': 'NK', 'length': int(m.group(1)), 'start': m.start()}

    return None


def parse_sku(sku_input):
    """Parse a SKU string into its structural components.

    Returns a dict:
      sku, error (None or message)
      base_sku      -- the exact lowercased recipe-key substring
      prefix        -- e.g. '4B', 'AETHER', 'KYO' (or None)
      design        -- e.g. 'RAIN6', 'ANEMO', 'RED' (or None)
      category      -- 'LV'/'WR'/'BP'/'DK'/'CH'/'NK'/'BRAC'/'BRAC-E'/'TART'/None
      length        -- numeric length for NK/BRAC/BRAC-E (or None)
      tart_n        -- 1 or 2 for TART items (or None)
      is_standalone -- True for items with no prefix scheme
      unmatched_design_token -- a design-looking token that wasn't found in
                                 skuVocab (worth adding there), or None
    """
    sku_original = sku_input.strip()
    if not sku_original:
        return {'sku': sku_original, 'error': 'Empty SKU.'}

    sku_upper = sku_original.upper()
    sku_lower = sku_original.lower()

    # -- TART-1 / TART-2: standalone, no prefix/design/finding scheme --
    m = re.match(r'^TART-(\d+)$', sku_upper)
    if m:
        return {
            'sku': sku_original, 'error': None,
            'base_sku': 'tart', 'prefix': None, 'design': None,
            'category': 'TART', 'length': None, 'tart_n': int(m.group(1)),
            'is_standalone': False, 'unmatched_design_token': None,
        }

    # -- bead-style or standalone prefix --
    matched_prefix = None
    for prefix in _ALL_PREFIXES:
        if sku_upper == prefix or sku_upper.startswith(prefix + '-'):
            matched_prefix = prefix
            break

    if not matched_prefix:
        return {'sku': sku_original,
                'error': f"Could not parse SKU: no known prefix found in '{sku_original}'."}

    # -- suffix: matched against the FULL string, independent of the
    #    prefix/design step below, so an unrecognized design token can
    #    never break finding detection. --
    suffix = _match_suffix(sku_lower)
    if suffix:
        base_sku = sku_lower[:suffix['start']]
        category = suffix['category']
        length = suffix['length']
        suffix_start_in_upper = suffix['start']
    else:
        base_sku = sku_lower
        category = None
        length = None
        suffix_start_in_upper = len(sku_upper)

    # -- design token: exact match against the prefix-appropriate vocab
    #    dict, so 'ACE4' can never be misread as its alias 'ACE'. --
    middle = sku_upper[len(matched_prefix):suffix_start_in_upper].strip('-')
    design = None
    unmatched_design_token = None
    if middle:
        design_map = _design_map_for_prefix(matched_prefix)
        first_token = middle.split('-')[0]
        if design_map and first_token in design_map:
            design = first_token
        else:
            unmatched_design_token = first_token

    return {
        'sku': sku_original, 'error': None,
        'base_sku': base_sku, 'prefix': matched_prefix, 'design': design,
        'category': category, 'length': length, 'tart_n': None,
        'is_standalone': False, 'unmatched_design_token': unmatched_design_token,
    }


# ---------------------------------------------------------------------
# Human-readable description -- built entirely from parse_sku()'s output.
# ---------------------------------------------------------------------
def _prefix_description(prefix):
    if prefix in BEAD_PREFIXES:
        return BEAD_PREFIXES[prefix][0]
    if prefix in STANDALONE_PREFIXES:
        return STANDALONE_PREFIXES[prefix][0]
    return prefix.lower() if prefix else ''


def _design_description(prefix, design_code):
    design_map = _design_map_for_prefix(prefix)
    if design_map and design_code in design_map:
        return design_map[design_code][0]
    return design_code


def readable_description(sku_or_parsed):
    """Accepts either a raw SKU string or an already-parsed dict from
    parse_sku(), so callers who already have the parsed structure (e.g.
    skuCostLookup) don't have to parse twice."""
    parsed = parse_sku(sku_or_parsed) if isinstance(sku_or_parsed, str) else sku_or_parsed

    if parsed.get('error'):
        return f"Error: {parsed['error']}"

    if parsed['category'] == 'TART':
        n = parsed['tart_n']
        if n == 1:
            return TART_INFO['description_single']
        if n == 2:
            return TART_INFO['description_pair']
        return f"Tartaglia cosplay earrings (unrecognized count: {n})"

    if parsed.get('is_standalone'):
        return f"{parsed['base_sku']} (standalone item; no description template defined yet)"

    prefix = parsed['prefix']
    desc_parts = [_prefix_description(prefix)]

    if parsed['design']:
        variation_desc = _design_description(prefix, parsed['design'])
        if prefix == 'AETHER':
            desc_parts[-1] += f' ({variation_desc}) cosplay'
        elif prefix == 'SEASONS':
            desc_parts.append(f"{variation_desc} themed cottage-core")
        elif prefix in ('KYO', 'CC'):
            desc_parts.append(f"({variation_desc})")
        else:
            desc_parts.append(variation_desc)

    category = parsed['category']
    if category in FINDINGS:
        desc_parts.append(FINDINGS[category]['description'])
        if prefix != 'AETHER' and category != 'CH':
            desc_parts[-1] += 's'
    elif category == 'NK':
        length = parsed['length']
        desc = FINDINGS_LEN['NK']['description']['nonzero' if length else 'zero']
        desc_parts.append(desc.format(length=length))
    elif category in ('BRAC', 'BRAC-E'):
        desc_parts.append(FINDINGS_LEN[category]['description'].format(length=parsed['length']))

    if parsed.get('unmatched_design_token'):
        desc_parts.append(f"[unrecognized design token: {parsed['unmatched_design_token']}]")

    return ' '.join(desc_parts)


def main():
    print("=" * 60)
    print("SKU PARSER - Pyrrhic Silva Shop")
    print("=" * 60)
    print("\nEnter a SKU (or 'quit' to exit):\n")

    while True:
        user_input = input(">>> ").strip()
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\nGoodbye!\n")
            break
        if not user_input:
            continue

        parsed = parse_sku(user_input)
        if parsed.get('error'):
            print(f"\n❌ {parsed['error']}\n")
        else:
            print(f"\n✅ SKU: {parsed['sku']}")
            print(f"   {readable_description(parsed)}\n")


if __name__ == "__main__":
    main()