#!/usr/bin/env python3
"""
trendsParser.py - Pyrrhic Silva Shop

Ranks sales by jewelry type (aggregate, plus breakdown by earring
finding / necklace length / bracelet type) and by design (Pride flag
designs vs. everything else), most-to-least popular.

SOURCE FILE NOTE (read before assuming this reads the trends CSV just
because of the module name): this reads PyrrhicSilvaShopSales.csv, NOT
PyrrhicSilvaShopTrends.csv. The trends CSV only stores one NK count and
one summed Chain(inches) value per day -- it has no per-length totals,
so a necklace-length ranking cannot be built from it. It also has no
column at all for DK earrings (skuVocab.FINDINGS['DK']['trend_column']
is None, by design), so DK sales are invisible in that file. Reading
raw sales line items and re-deriving everything through skuParser.py
and skuVocab.py fixes both problems and is the only way to get the
granularity this script was asked for.

DESIGN CATEGORIZATION: uses skuVocab.resolve_design_category()'s `kind`
field to split designs into groups, rather than a hardcoded
Pride/non-Pride check. Today that field only ever returns 'pride' or
'misc', so the CLI report shows exactly two sections ("Pride Flag
Designs" and "Non-Pride Flag Designs"). If resolve_design_category() is
ever extended to return additional kind values, they show up here
automatically -- compute_design_report() groups by whatever kinds are
actually present in the data, and render_report_cli() lumps every
non-'pride' kind under one "Non-Pride Flag Designs" heading (with a
sub-heading per kind if more than one shows up).

FINE VS. COARSE DESIGN GRANULARITY: AETHER, SEASONS, and CC each have a
bare trend column (AETHER, SEASONS, CC (Candy-Cane)) plus more specific
sub-columns (AETHER-ANEMO, etc.). KYO does NOT have a bare column --
skuVocab.STANDALONE_PREFIXES intentionally gives KYO a None trend
column, so only KYO-Red/KYO-Black exist. compute_design_report()'s
fine_grained bool controls this for AETHER/SEASONS/CC; KYO always shows
fine-grained (KYO-Red vs. KYO-Black) regardless of that flag, because
there is no coarser option to fall back to. This is a structural
asymmetry in the data, not a bug in this script.

REUSE, NOT REIMPLEMENTATION: SKU-row parsing and the non-product-token
filter ('cancel', 'refund', 'custom', 'package bounced', anything
starting with 'usps') are NOT duplicated here. This module imports and
calls salesToTrendsGen.parse_sku_row(), which already does exactly that
filtering on top of skuParser.parse_sku(). This is a second real
consumer of that function (the first being salesToTrendsGen.py itself),
so reusing it directly satisfies this project's "no speculative
extraction" rule without needing to move it anywhere first.

DATE RANGE: build_trends_report() already accepts optional start_date /
end_date bounds and filters records before aggregating. main() does NOT
yet prompt for them -- the CLI currently only produces an all-time
report. Wiring an interactive start/end date prompt is a follow-up
task, not done here.

GUI NOTE: every compute function in this module is pure (no print(),
no input()) and returns plain data. render_report_cli() is the only
function that prints anything; a GUI should call build_trends_report()
directly and render the result however it wants.
"""

from collections import defaultdict

from shopIO import load_valid_sales_rows
from salesToTrendsGen import parse_sku_row
from skuVocab import resolve_design_category, FINDINGS, TART_INFO


# ---------------------------------------------------------------------
# Which FINDINGS codes belong to which jewelry_type. Built from
# skuVocab.FINDINGS at import time rather than hardcoded, so a future
# finding type with jewelry_type='earrings' (or 'phone_charm') is picked
# up here automatically with no changes to this file.
# ---------------------------------------------------------------------
_EARRING_FINDING_CODES = {code for code, info in FINDINGS.items()
                           if info['jewelry_type'] == 'earrings'}
_PHONE_CHARM_FINDING_CODES = {code for code, info in FINDINGS.items()
                               if info['jewelry_type'] == 'phone_charm'}


def classify_jewelry(parsed):
    """Given one salesToTrendsGen.parse_sku_row() result (already
    checked for None/error by the caller), return (jewelry_type,
    jewelry_subtype).

    jewelry_type mirrors skuVocab's own 'jewelry_type' field:
        'earrings' | 'necklace' | 'bracelet' | 'phone_charm'
    jewelry_subtype is the breakdown label WITHIN that jewelry_type:
        earrings    -> finding code (LV/WR/BP/DK) or 'TART'
        necklace    -> chain length (int, 0 = charm-on-bail-only)
        bracelet    -> 'BRAC' (chain) or 'BRAC-E' (elastic)
        phone_charm -> finding code (CH)

    Returns (None, None) if the parsed item doesn't match any known
    jewelry_type -- this is a real gap worth a warning (see
    build_line_item_records()), not silently dropped.
    """
    if parsed['kind'] == 'tart':
        return TART_INFO['jewelry_type'], 'TART'

    finding = parsed.get('finding')
    if finding in _EARRING_FINDING_CODES:
        return 'earrings', finding
    if finding in _PHONE_CHARM_FINDING_CODES:
        return 'phone_charm', finding
    if parsed.get('chain_length') is not None:
        return 'necklace', parsed['chain_length']
    if parsed.get('brace_type') == 'chain':
        return 'bracelet', 'BRAC'
    if parsed.get('brace_type') == 'elastic':
        return 'bracelet', 'BRAC-E'

    return None, None


def build_line_item_records(rows):
    """Parse and classify every valid sales row into a flat list of
    per-line-item records ready for ranking.

    Returns (records, warnings). Each record:
        {'date', 'quantity', 'jewelry_type', 'jewelry_subtype',
         'design_kind', 'design_identity', 'design_coarse_identity'}
    Any field can be None if that record didn't resolve on that axis
    (jewelry classification and design classification are independent
    -- a record failing one doesn't exclude it from the other).

    warnings covers: SKU parse failures, non-product-token skips (both
    surfaced by parse_sku_row() itself), unresolved design tokens (from
    resolve_design_category()), and items that matched no known
    jewelry_type. Nothing here is raised as an error -- consistent with
    this project's warnings-as-data convention.
    """
    records = []
    warnings = []

    for r in rows:
        parsed, warning = parse_sku_row(r['sku'])
        if warning:
            warnings.append(warning)
        if parsed is None or parsed.get('error'):
            continue

        jewelry_type, jewelry_subtype = classify_jewelry(parsed)
        if jewelry_type is None:
            warnings.append(
                f"'{r['sku']}' (order {r['order_number']}) didn't match any "
                f"known jewelry_type; excluded from the jewelry-type breakdown."
            )

        if parsed['kind'] == 'tart':
            design_info, design_warning = resolve_design_category(None, None, type='TART')
        else:
            design_info, design_warning = resolve_design_category(parsed['prefix'], parsed['flag'])
        if design_warning:
            warnings.append(f"'{r['sku']}' (order {r['order_number']}): {design_warning}")

        records.append({
            'date': r['date'],
            'quantity': r['quantity'],
            'jewelry_type': jewelry_type,
            'jewelry_subtype': jewelry_subtype,
            'design_kind': design_info['kind'] if design_info else None,
            'design_identity': design_info['identity'] if design_info else None,
            'design_coarse_identity': design_info['coarse_identity'] if design_info else None,
        })

    return records, warnings


def filter_records_by_date(records, start_date=None, end_date=None):
    """Inclusive date filter on already-built records. Either bound may
    be None for an open-ended range. Not currently called by main() --
    see DATE RANGE note at the top of this module -- but build_trends_
    report() already threads these params through so wiring an
    interactive prompt later doesn't touch this function."""
    if start_date is None and end_date is None:
        return records
    filtered = []
    for rec in records:
        d = rec['date']
        if start_date is not None and d < start_date:
            continue
        if end_date is not None and d > end_date:
            continue
        filtered.append(rec)
    return filtered


def rank_by(records, key_fn, filter_fn=None):
    """Generic ranking helper: sum quantity grouped by key_fn(record),
    sorted descending by total. filter_fn(record) -> bool restricts
    which records are considered at all (e.g. jewelry_type ==
    'earrings'). Records where key_fn(record) is None are excluded --
    that's the "didn't resolve on this axis" case, already warned about
    elsewhere; it shouldn't reappear here as a fake 'None' ranked line.

    Returns a list of (key, total_quantity) tuples, most-to-least
    popular. Ties are not given a defined secondary order.
    """
    totals = defaultdict(int)
    for rec in records:
        if filter_fn and not filter_fn(rec):
            continue
        key = key_fn(rec)
        if key is None:
            continue
        totals[key] += rec['quantity']
    return sorted(totals.items(), key=lambda kv: kv[1], reverse=True)


def compute_jewelry_type_report(records):
    """Aggregate jewelry-type ranking plus the three sub-breakdowns.
    Pure function of `records` (build_line_item_records() output)."""
    return {
        'aggregate': rank_by(records, key_fn=lambda r: r['jewelry_type']),
        'earrings': rank_by(
            records, key_fn=lambda r: r['jewelry_subtype'],
            filter_fn=lambda r: r['jewelry_type'] == 'earrings',
        ),
        'necklaces': rank_by(
            records, key_fn=lambda r: r['jewelry_subtype'],
            filter_fn=lambda r: r['jewelry_type'] == 'necklace',
        ),
        'bracelets': rank_by(
            records, key_fn=lambda r: r['jewelry_subtype'],
            filter_fn=lambda r: r['jewelry_type'] == 'bracelet',
        ),
    }


def compute_design_report(records, fine_grained=False):
    """Rank designs by kind (whatever kind values resolve_design_
    category() actually produced -- see module docstring), most-to-
    least popular within each kind.

    fine_grained=False groups by coarse_identity (e.g. bare 'AETHER'
    total across all elements); True groups by identity (e.g.
    'AETHER-ANEMO' split out from 'AETHER-HYDRO'). KYO items fall back
    to identity regardless of this flag, since KYO has no coarse
    identity to group by (see module docstring). Pride designs are
    unaffected either way -- identity == coarse_identity for every
    PRIDE_DESIGNS entry, so the toggle is a no-op there.

    Returns {kind: [(identity, total_qty), ...]}, one entry per kind
    actually present in `records` -- not a hardcoded ('pride', 'misc')
    tuple.
    """
    key_field = 'design_identity' if fine_grained else 'design_coarse_identity'

    def key_fn(rec):
        return rec[key_field] if rec[key_field] is not None else rec['design_identity']

    kinds_present = {rec['design_kind'] for rec in records if rec['design_kind'] is not None}

    return {
        kind: rank_by(records, key_fn=key_fn, filter_fn=lambda r, k=kind: r['design_kind'] == k)
        for kind in sorted(kinds_present)
    }


def build_trends_report(rows, start_date=None, end_date=None, fine_grained_designs=False):
    """One-stop compute entry point. `rows` is shopIO.load_valid_sales_
    rows()'s first return value. No printing, no input() -- this is
    what a GUI should call.

    Returns:
        {
          'records_count': int,
          'warnings': [...],
          'jewelry': {...},   # compute_jewelry_type_report() output
          'designs': {...},   # compute_design_report() output
        }
    """
    records, warnings = build_line_item_records(rows)
    records = filter_records_by_date(records, start_date, end_date)

    return {
        'records_count': len(records),
        'warnings': warnings,
        'jewelry': compute_jewelry_type_report(records),
        'designs': compute_design_report(records, fine_grained=fine_grained_designs),
    }


# ---------------------------------------------------------------------
# CLI-only rendering below. Nothing above this line prints anything.
# ---------------------------------------------------------------------
def _print_ranking(ranking, top_n=None):
    if not ranking:
        print("  (no sales in this category)")
        return
    total = sum(qty for _, qty in ranking)
    display = ranking[:top_n] if top_n else ranking
    for label, qty in display:
        pct = (qty / total * 100) if total else 0
        print(f"  {str(label):<20} {qty:>6}  ({pct:4.1f}%)")
    if top_n and len(ranking) > top_n:
        print(f"  ... and {len(ranking) - top_n} more")


def render_report_cli(report, top_n=None):
    """CLI-only text renderer for build_trends_report()'s output. The
    only function in this module that prints anything. top_n caps how
    many rows are shown per ranking (None = show all, sorted most-to-
    least popular)."""
    print(f"\n{report['records_count']} line item(s) included in this report.")

    print("\n=== JEWELRY TYPE POPULARITY (aggregate) ===\n")
    _print_ranking(report['jewelry']['aggregate'], top_n)

    print("\n--- Earrings, by finding ---")
    _print_ranking(report['jewelry']['earrings'], top_n)

    print("\n--- Necklaces, by chain length (inches; 0 = charm on bail only) ---")
    _print_ranking(report['jewelry']['necklaces'], top_n)

    print("\n--- Bracelets, by type (BRAC = chain, BRAC-E = elastic) ---")
    _print_ranking(report['jewelry']['bracelets'], top_n)

    designs = report['designs']
    if 'pride' in designs:
        print("\n=== PRIDE FLAG DESIGNS ===\n")
        _print_ranking(designs['pride'], top_n)

    non_pride_kinds = sorted(k for k in designs if k != 'pride')
    if non_pride_kinds:
        print("\n=== NON-PRIDE FLAG DESIGNS ===")
        for kind in non_pride_kinds:
            if len(non_pride_kinds) > 1:
                print(f"\n-- {kind} --")
            else:
                print()
            _print_ranking(designs[kind], top_n)

    if report['warnings']:
        print(f"\n\u26a0\ufe0f  {len(report['warnings'])} warning(s):")
        for w in report['warnings']:
            print(f"  - {w}")


def main():
    print("=" * 60)
    print("TRENDS PARSER - Pyrrhic Silva Shop")
    print("(reads the raw sales CSV, not PyrrhicSilvaShopTrends.csv --")
    print(" see this module's docstring for why)")
    print("=" * 60)

    sales_path = input("\nEnter path to sales CSV (or Enter for PyrrhicSilvaShopSales.csv): ").strip()
    if not sales_path:
        sales_path = 'PyrrhicSilvaShopSales.csv'

    try:
        rows, load_warnings = load_valid_sales_rows(sales_path)
    except FileNotFoundError:
        print(f"Error: File not found at '{sales_path}'")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    for w in load_warnings:
        print(f"Warning: {w}")

    fine_raw = input("\nShow fine-grained AETHER/SEASONS/CC sub-designs? (y/N): ").strip().lower()
    fine_grained = fine_raw in ('y', 'yes')

    top_raw = input("How many top entries per ranking? (Enter for all): ").strip()
    top_n = int(top_raw) if top_raw.isdigit() else None

    report = build_trends_report(rows, fine_grained_designs=fine_grained)
    render_report_cli(report, top_n=top_n)
    return report


if __name__ == '__main__':
    main()