#!/usr/bin/env python3
"""
generateTrends.py - Pyrrhic Silva Shop

Reads the raw sales export (one row per line item) and produces a trends CSV
in the same layout as the hand-tallied PyrrhicSilvaShopTrends.csv:
one row per day of sales, one column per bead type / finding / design, plus
a Total row at the bottom.

USAGE:
    python3 generateTrends.py

You'll be prompted for the sales CSV path and an output path.

--------------------------------------------------------------------------
HOW ORDERS ARE GROUPED (same rule as countOrdersDayOfWeek.py /
countOrdersSubMonths.py already in this project):
  - Line items are grouped by "order number".
  - An order's date is the EARLIEST date that appears among its line items
    (a cancellation or refund line sometimes carries a later date than the
    original purchase).
  - Rows with item quantity < 1 (cancellations, refunds) are dropped before
    the earliest date is computed, and don't contribute to any count.
  - Known non-product rows are dropped outright: "custom", "cancel",
    "refund", "package bounced", and anything starting with "usps".
  - Every remaining line item is then bucketed into the trend day that
    matches its order's earliest date, and the trend row for that day is
    a sum across every order that landed there (a single day can, and
    regularly does, combine several unrelated orders).

HOW EACH COLUMN IS FILLED (reverse-engineered from RecipesData.csv,
skuKey.txt and skuParser.py, then checked against the sample trends file):
  - "items sold": total quantity of every counted line item that day.
  - 4B/4C/6P/8R/CHD: total quantity of items with that bead-style prefix.
  - LV/WR/BP: total quantity of items with that earring finding suffix.
    NOTE: this is applied uniformly, including to CHD ("kids' bracelet
    kit") SKUs that carry an earring suffix. The sample trends file
    excluded CHD from these finding counts in at least one case - see the
    note printed at the end of this run.
  - NK / "Chain (inches)": count of necklace items, and the summed chain
    length (0 for a NK0 "charm on a bail" listing).
  - BRAC / BRAC-e / "BRAC (inches)": count of chain vs. elastic bracelets,
    and their summed length in inches (both types share one inches column,
    matching the sample file).
  - "CH (phone charm)": count of "-CH" phone charm findings. The shipped
    skuParser.py does not recognize this suffix at all (SUFFIX_FINDINGS
    only has LV/WR/BP/DK) - this script adds that recognition.
  - Pride-flag / design columns (RAIN6, LESBO5, PAN, etc.): count of items
    carrying that design, regardless of bead style or finding. Column
    names now match skuParser.py's spelling directly (GQUEER, CETERO4,
    CETERO5, RWG) after the trends header typos were corrected.
  - AETHER / SEASONS / CC (Candy-Cane): each also fills a second, more
    specific column (element, season, or color pattern).
  - TART: NOT a simple item count. The sample file stores the number
    encoded in the SKU itself (TART-1 -> 1, TART-2 -> 2, i.e. single vs.
    pair), multiplied by quantity - not the count of orders.
  - USA, KRIS, HOWLS, KYO-Red, KYO-Black, "10-13-STAR": direct name/SKU
    matches, no further sub-columns.

Known gaps in the shipped skuParser.py that this script fixes:
  1. SUFFIX_PATTERNS is unpacked as a 3-tuple in a loop but defined with
     4 elements - `for pattern, brace_val, chain_val in SUFFIX_PATTERNS`
     raises ValueError immediately. That means the shared skuParser.py
     currently cannot parse ANY necklace or bracelet SKU. Fixed here.
  2. No recognition of the "-CH" phone charm finding. Added here.

Columns that exist in skuParser.py's flag list but do NOT have a column
in the trends format (PROG, MULTG, BIGEND, BERRI, ALMD, ABRO, QPR, GAYBO,
GFLUX, ANDRO, GYNE) are not silently dropped: if one is ever sold, this
script prints a warning and still counts it toward "items sold" and the
bead-type column, but the specific design won't appear anywhere else in
the CSV until a column is added for it.
"""

import csv
import os
import re
from collections import defaultdict
from datetime import datetime

# ---------------------------------------------------------------------
# STEP 1: Trend sheet's exact column order (copied from the sample file)
# ---------------------------------------------------------------------
TREND_COLUMNS = [
    'date', 'items sold', '4B', '4C', '6P', '8R', 'CHD',
    'BRAC (chain bracelets & chokers)', 'BRAC-e (elastic bracelets)', 'BRAC (inches)',
    'NK (necklace)', 'Chain (inches)', 'CH (phone charm)',
    'LV (lever back earrings', 'WR (fish hook earrings', 'BP (4mm ball post studs)',
    'RAIN7', 'RAIN6', 'RAIN8', 'PHILLY', 'TRANS3', 'TRANS5', 'LESBO5', 'GAY5',
    'BI3', 'BI5', 'PAN', 'GQUEER', 'GFLUID', 'ENBY', 'INTSEX', 'AROACE', 'ARO',
    'ACE4', 'ACE6', 'CETERO4', 'CETERO5', 'MAV', 'AGEND', 'ANGY', 'GNEUT', 'TROIS', 'OMNIS',
    'MULTS', 'POLYG', 'POLYS', 'USA', 'TART', 'HOWLS', '10-13-STAR',
    'SEASONS', 'SEASONS-charm', 'spring', 'summer', 'fall', 'winter',
    'CC (Candy-Cane)', 'RW', 'RWG', 'RG', 'KYO-Red', 'KYO-Black', 'KRIS', 'FRISK',
    'AETHER', 'ANEMO', 'GEO', 'ELECTRO', 'DENDRO', 'HYDRO', 'PYRO', 'CRYO', 'NONE', 'ALL',
]

# ---------------------------------------------------------------------
# STEP 2: SKU vocabulary (from skuParser.py / skuKey.txt), with the
# renames needed to land on the trends sheet's exact header spelling.
# ---------------------------------------------------------------------
BEAD_PREFIXES = {'4B', '4C', '6P', '8R', 'CHD'}
STANDALONE_PREFIXES = {'AETHER', 'CC', 'HOWLS', 'SEASONS', 'KYO'}

FLAG_RENAME = {
    # No renames needed anymore - the trends header now spells GQUEER and
    # CETERO4/CETERO5 correctly, matching skuParser.py directly.
}
# Everything else maps to a column of the identical name, IF one exists.
GENERIC_FLAGS = {
    'RAIN6', 'RAIN7', 'RAIN8', 'PHILLY', 'TRANS3', 'TRANS5', 'LESBO5', 'GAY5',
    'BI3', 'BI5', 'PAN', 'GQUEER', 'GFLUID', 'ENBY', 'INTSEX', 'AROACE', 'ARO',
    'ACE4', 'ACE6', 'CETERO4', 'CETERO5', 'MAV', 'AGEND', 'ANGY', 'GNEUT',
    'TROIS', 'OMNIS', 'MULTS', 'POLYG', 'POLYS', 'USA', 'KRIS', 'FRISK',
    # known-unmapped (no column exists yet) - kept here just so we can warn
    'PROG', 'MULTG', 'BIGEND', 'BERRI', 'ALMD', 'ABRO', 'QPR', 'GAYBO',
    'GFLUX', 'ANDRO', 'GYNE',
}

AETHER_ELEMENTS = {'ANEMO', 'GEO', 'ELECTRO', 'DENDRO', 'HYDRO', 'PYRO', 'CRYO', 'NONE', 'ALL'}
SEASON_NAMES = {'WINTER': 'winter', 'SPRING': 'spring', 'SUMMER': 'summer', 'FALL': 'fall'}
CC_COLORS = {'RW': 'RW', 'RWG': 'RWG', 'RG': 'RG'}
KYO_COLORS = {'RED': 'KYO-Red', 'BLACK': 'KYO-Black'}

NON_PRODUCT_TOKENS = {
    'custom', 'cancel', 'refund', 'package bounced',
}

SUFFIX_FINDINGS = {'LV', 'WR', 'BP', 'DK', 'CH'}  # CH added - see module docstring


def parse_sku(sku_original):
    """
    Parse one SKU into a small dict describing what it is.
    Returns None for rows that aren't real product SKUs.
    Returns {'error': ...} (and prints a warning) for anything that looks
    like a product SKU but doesn't match a known pattern, so nothing is
    silently dropped.
    """
    sku = sku_original.strip().upper()
    if not sku:
        return None
    if sku.lower() in NON_PRODUCT_TOKENS or sku.lower().startswith('usps'):
        return None

    # --- TART-1 / TART-2 (earring pair count, standalone) ---
    m = re.match(r'^TART-(\d+)$', sku)
    if m:
        return {'kind': 'tart', 'tart_n': int(m.group(1))}

    # --- 10-13-star (standalone SKU, no bead prefix) ---
    if sku == '10-13-STAR':
        return {'kind': 'ten_thirteen_star'}

    # --- find bead prefix or standalone prefix ---
    matched_prefix = None
    remainder = None
    for prefix in sorted(BEAD_PREFIXES | STANDALONE_PREFIXES, key=len, reverse=True):
        if sku == prefix or sku.startswith(prefix + '-'):
            matched_prefix = prefix
            remainder = sku[len(prefix):].strip('-')
            break

    if not matched_prefix:
        print(f"  \u26a0\ufe0f  Warning: could not recognize SKU '{sku_original}', skipping.")
        return {'error': True}

    result = {
        'kind': 'standard',
        'prefix': matched_prefix,
        'flag': None,
        'finding': None,
        'chain_length': None,
        'brace_length': None,
        'brace_type': None,
    }

    # --- middle design token (pride flag, season, aether element, kyo color, cc color) ---
    tokens = remainder.split('-') if remainder else []
    # first token is the "design"; remaining token(s) are the finding/spec
    if tokens:
        design_token = tokens[0]
        rest = '-'.join(tokens[1:])

        if matched_prefix == 'AETHER' and design_token in AETHER_ELEMENTS:
            result['flag'] = design_token
            remainder = rest
        elif matched_prefix == 'SEASONS' and design_token in SEASON_NAMES:
            result['flag'] = design_token
            remainder = rest
        elif matched_prefix == 'CC' and design_token in CC_COLORS:
            result['flag'] = design_token
            remainder = rest
        elif matched_prefix == 'KYO' and design_token in KYO_COLORS:
            result['flag'] = design_token
            remainder = rest
        elif matched_prefix in BEAD_PREFIXES and design_token in GENERIC_FLAGS:
            result['flag'] = design_token
            remainder = rest
        else:
            remainder = '-'.join(tokens)  # leave untouched; may just be a finding

    # --- suffix: finding, chain, or bracelet spec ---
    if remainder:
        if remainder in SUFFIX_FINDINGS:
            result['finding'] = remainder
        else:
            m = re.match(r'^BRAC[-]?E[-]?(\d+(?:\.\d+)?)$', remainder)
            if m:
                result['brace_type'] = 'elastic'
                result['brace_length'] = float(m.group(1))
            else:
                m = re.match(r'^BRAC(\d+(?:\.\d+)?)$', remainder)
                if m:
                    result['brace_type'] = 'chain'
                    result['brace_length'] = float(m.group(1))
                else:
                    m = re.match(r'^NK(\d+)$', remainder)
                    if m:
                        result['chain_length'] = int(m.group(1))
                    else:
                        print(f"  \u26a0\ufe0f  Warning: unrecognized suffix "
                              f"'{remainder}' on SKU '{sku_original}'.")

    return result


def load_valid_line_items(sales_path):
    """
    Returns: dict order_number -> list of (parsed_item, qty)
             dict order_number -> earliest datetime
    Mirrors the earliest-date logic in countOrdersDayOfWeek.py.
    """
    order_items = defaultdict(list)
    order_date = {}

    with open(sales_path, 'r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = (row.get('date') or '').strip().strip('"').strip("'")
            order_num = (row.get('order number') or '').strip().strip('"').strip("'")
            sku = (row.get('item sku') or '').strip()
            qty_str = (row.get('item quantity') or '').strip()

            if not date_str or not order_num:
                continue
            try:
                qty = int(qty_str)
            except ValueError:
                continue
            if qty < 1:
                continue  # cancellations / refunds

            try:
                parsed_date = datetime.strptime(date_str, "%A, %B %d, %Y")
            except ValueError:
                print(f"  \u26a0\ufe0f  Warning: could not parse date '{date_str}', skipping row.")
                continue

            parsed = parse_sku(sku)
            if parsed is None or parsed.get('error'):
                continue

            order_items[order_num].append((parsed, qty))
            if order_num not in order_date or parsed_date < order_date[order_num]:
                order_date[order_num] = parsed_date

    return order_items, order_date


def build_day_rows(order_items, order_date):
    """Returns dict date(datetime) -> row dict (column name -> numeric total)."""
    days = defaultdict(lambda: defaultdict(int))

    for order_num, items in order_items.items():
        day = order_date[order_num]
        row = days[day]

        for parsed, qty in items:
            row['items sold'] += qty

            if parsed['kind'] == 'tart':
                row['TART'] += parsed['tart_n'] * qty
                continue

            if parsed['kind'] == 'ten_thirteen_star':
                row['10-13-STAR'] += qty
                continue

            prefix = parsed['prefix']

            if prefix in BEAD_PREFIXES:
                row[prefix] += qty
            elif prefix == 'HOWLS':
                row['HOWLS'] += qty
            elif prefix == 'AETHER':
                row['AETHER'] += qty
                if parsed['flag']:
                    row[parsed['flag']] += qty  # ANEMO/GEO/... match column name directly
            elif prefix == 'SEASONS':
                row['SEASONS'] += qty
                if parsed['flag']:
                    row[SEASON_NAMES[parsed['flag']]] += qty
            elif prefix == 'CC':
                row['CC (Candy-Cane)'] += qty
                if parsed['flag']:
                    row[CC_COLORS[parsed['flag']]] += qty
            elif prefix == 'KYO':
                if parsed['flag']:
                    row[KYO_COLORS[parsed['flag']]] += qty

            # design flag (pride flags etc.) for bead-prefixed items
            if parsed['flag'] and prefix in BEAD_PREFIXES:
                col = FLAG_RENAME.get(parsed['flag'], parsed['flag'])
                if col in TREND_COLUMNS:
                    row[col] += qty
                else:
                    print(f"  \u26a0\ufe0f  Warning: design '{parsed['flag']}' has no trends "
                          f"column yet (order dated {day:%A, %B %d, %Y}); counted in "
                          f"'items sold' and '{prefix}' only.")

            # finding
            finding = parsed['finding']
            if finding == 'LV':
                row['LV (lever back earrings'] += qty
            elif finding == 'WR':
                row['WR (fish hook earrings'] += qty
            elif finding == 'BP':
                row['BP (4mm ball post studs)'] += qty
            elif finding == 'CH':
                row['CH (phone charm)'] += qty
            # DK (Aether earrings) intentionally has no trends column

            # necklace
            if parsed['chain_length'] is not None:
                row['NK (necklace)'] += qty
                row['Chain (inches)'] += parsed['chain_length'] * qty

            # bracelet
            if parsed['brace_type'] == 'chain':
                row['BRAC (chain bracelets & chokers)'] += qty
                row['BRAC (inches)'] += parsed['brace_length'] * qty
            elif parsed['brace_type'] == 'elastic':
                row['BRAC-e (elastic bracelets)'] += qty
                row['BRAC (inches)'] += parsed['brace_length'] * qty

    return days


def write_trends_csv(days, output_path):
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(TREND_COLUMNS)

        totals = defaultdict(float)
        for day in sorted(days.keys()):
            row = days[day]
            out_row = []
            for col in TREND_COLUMNS:
                if col == 'date':
                    out_row.append(f"{day.strftime('%A, %B')} {day.day}, {day.year}")
                    continue
                val = row.get(col, 0)
                totals[col] += val
                out_row.append('' if val == 0 else _fmt(val))
            writer.writerow(out_row)

        total_row = ['Total']
        for col in TREND_COLUMNS[1:]:
            total_row.append(_fmt(totals[col]))
        writer.writerow(total_row)


def _fmt(val):
    if isinstance(val, float) and val.is_integer():
        return int(val)
    return val


def _parse_reference_date(date_str):
    """Try a few date formats, since a hand-edited spreadsheet may have
    been reformatted by Excel/Sheets at some point. Returns None (and lets
    the caller warn) if nothing matches."""
    date_str = date_str.strip().strip('"').strip("'")
    for fmt in ("%A, %B %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def load_reference_trends(path):
    """
    Load an existing (hand-tallied or previously generated) trends CSV into
    the same shape build_day_rows() produces: dict date -> {column: value}.
    Matches columns by NAME (from the file's own header row), not position,
    so minor column reordering won't silently misalign values. Blank cells
    are treated as 0. The trailing "Total" row and any blank rows are
    skipped.
    """
    days = {}
    with open(path, 'r', newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if not row or not row[0].strip() or row[0].strip() == 'Total':
                continue
            day = _parse_reference_date(row[0])
            if day is None:
                print(f"  \u26a0\ufe0f  Warning: could not parse reference date "
                      f"'{row[0]}', skipping that row.")
                continue
            row_dict = {}
            for col, val in zip(header[1:], row[1:]):
                val = (val or '').strip()
                if val == '':
                    row_dict[col] = 0
                    continue
                try:
                    num = float(val)
                    row_dict[col] = int(num) if num.is_integer() else num
                except ValueError:
                    row_dict[col] = val  # leave as-is; will just show as a mismatch
            days[day] = row_dict
    return days


def compare_trends(generated_days, reference_days):
    """
    Print per-date discrepancies between the freshly generated trends and
    an existing reference file (hand-tallied or a prior run), so they can
    be manually checked against the Etsy dashboard.

    A date only in one side is flagged as such. For dates in both, only
    columns whose values actually differ are printed - matching columns
    are not noise here.
    """
    all_dates = sorted(set(generated_days) | set(reference_days))
    discrepancy_count = 0

    for day in all_dates:
        label = f"{day.strftime('%A, %B')} {day.day}, {day.year}"
        mine = generated_days.get(day)
        theirs = reference_days.get(day)

        if mine is not None and theirs is None:
            print(f"{label}  -- only in generated output (missing from reference file)")
            discrepancy_count += 1
            continue
        if mine is None and theirs is not None:
            print(f"{label}  -- only in reference file (missing from generated output)")
            discrepancy_count += 1
            continue

        # present in both - compare column by column (skip 'date' itself)
        diffs = []
        columns = [c for c in TREND_COLUMNS if c != 'date']
        for col in columns:
            a = mine.get(col, 0)
            b = theirs.get(col, 0)
            a_num = a if isinstance(a, (int, float)) else 0
            b_num = b if isinstance(b, (int, float)) else 0
            if a_num != b_num:
                diffs.append((col, a, b))

        if diffs:
            print(f"{label}")
            for col, a, b in diffs:
                a_disp = _fmt(a) if isinstance(a, (int, float)) else a
                b_disp = _fmt(b) if isinstance(b, (int, float)) else b
                print(f"    {col:35s} generated={a_disp!s:<10s} reference={b_disp!s}")
            discrepancy_count += 1

    if discrepancy_count == 0:
        print("No discrepancies found - generated output matches the reference file exactly.")
    else:
        print(f"\n{discrepancy_count} date(s) with discrepancies (see above).")


def main():
    sales_path = input("Enter path to sales CSV (or Enter for PyrrhicSilvaShopSales.csv): ").strip()
    if not sales_path:
        sales_path = 'PyrrhicSilvaShopSales.csv'

    output_path = input("Enter output path (or Enter for TrendsGenerated.csv): ").strip()
    if not output_path:
        output_path = 'TrendsGenerated.csv'

    print(f"\nReading {sales_path} ...")
    order_items, order_date = load_valid_line_items(sales_path)
    print(f"  \u2713 {len(order_items)} orders with valid line items")

    days = build_day_rows(order_items, order_date)
    print(f"  \u2713 {len(days)} distinct sale days")

    write_trends_csv(days, output_path)
    print(f"\n\u2713 Saved to {output_path}")

    # Compare against an existing hand-tallied (or previously generated)
    # trends CSV in the same folder as the sales export, so discrepancies
    # can be checked manually against the Etsy dashboard.
    reference_path = os.path.join(
        os.path.dirname(os.path.abspath(sales_path)), 'PyrrhicSilvaShopTrends.csv'
    )
    print(f"\nLooking for reference file at {reference_path} ...")
    if not os.path.isfile(reference_path):
        print("  (not found - skipping comparison)")
        return

    reference_days = load_reference_trends(reference_path)
    print(f"  \u2713 loaded {len(reference_days)} dated rows from reference file")

    print("\n" + "=" * 60)
    print("DISCREPANCIES vs PyrrhicSilvaShopTrends.csv")
    print("=" * 60 + "\n")
    compare_trends(days, reference_days)


if __name__ == '__main__':
    main()