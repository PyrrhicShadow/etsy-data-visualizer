#!/usr/bin/env python3
"""
salesToTrendsGen.py - Pyrrhic Silva Shop

Reads the raw sales export (one row per line item) and produces a trends CSV
in the same layout as the hand-tallied PyrrhicSilvaShopTrends.csv:
one row per day of sales, one column per bead type / finding / design, plus
a Total row at the bottom.

USAGE:
    python3 salesToTrendsGen.py

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
  - NK / "Chain (inches)": count of necklace items, and the summed chain
    length (0 for a NK0 "charm on a bail" listing).
  - BRAC / BRAC-e / "BRAC (inches)": count of chain vs. elastic bracelets,
    and their summed length in inches (both types share one inches column,
    matching the sample file).
  - "CH (phone charm)": count of "-CH" phone charm findings. 
  - Pride-flag / design columns (RAIN6, LESBO5, PAN, etc.): count of items
    carrying that design, regardless of bead style or finding. 
  - AETHER / SEASONS / CC (Candy-Cane): each also fills a second, more
    specific column (element, season, or color pattern).
  - USA, KRIS, HOWLS, KYO-Red, KYO-Black, "10-13-STAR": direct name/SKU
    matches, no further sub-columns.

Columns that exist in skuParser.py's flag list but do NOT have a column
in the trends format are not silently dropped: if one is ever sold, a
warning is generated and it still counts it toward "items sold" and the
bead-type column, but the specific design won't appear anywhere else in
the CSV until a column is added for it.

GUI NOTE: every warning path in this module now returns warnings as data
instead of print()-ing them, including the "design has no trends column"
case inside build_day_rows() (previously a bare print() buried in the
row-building loop) and the "couldn't parse reference date" case inside
load_reference_trends() (same problem). compute_trend_diffs() replaces
the old compare_trends() -- it returns a structured list of per-date diff
records instead of printing; render_diffs_cli() is the CLI-only renderer
for that output. generate_trends_report() is the one-stop compute entry
point: it loads the sales file, builds the day rows, and (if a reference
trends file exists) computes the diff report, bundling every warning
from every stage into one list. main() only handles input()/print() and
calls generate_trends_report() -- it does no parsing or aggregation
itself anymore. The module-level trend-column cross-check still runs at
import time (a genuinely missing column is a real bug that should fail
loudly), but it stores its result in UNREFERENCED_TREND_COLUMNS rather
than printing, so importing this module never writes to stdout on its
own.
"""

import csv
import os
import shopFormatting
from collections import defaultdict
from datetime import datetime
from cliPrompts import QuitRequested, prompt_yes_no

# ---------------------------------------------------------------------
# STEP 1: Trend sheet's exact column order (copied from the sample file)
# ---------------------------------------------------------------------
TREND_COLUMNS = [
    'date', 'items sold', '4B', '4C', '6P', '8R', 'CHD',
    'BRAC (chain bracelets & chokers)', 'BRAC-e (elastic bracelets)', 'BRAC (inches)',
    'NK (necklace)', 'Chain (inches)', 'CH (phone charm)', 'LV (lever back earrings)',
    'WR (fish hook earrings)', 'BP (4mm ball post studs)',
    'RAIN7', 'RAIN6', 'RAIN8', 'PHILLY', 'PROG', 'TRANS3', 'TRANS5', 'LESBO5', 'GAY5',
    'BI3', 'BI5', 'PAN', 'GQUEER', 'GFLUID', 'ENBY', 'INTSEX', 'AROACE', 'ORAROACE', 
    'ARO', 'ACE4', 'ACE6', 'CETERO4', 'CETERO5', 'MAV', 'AGEND', 'ANGY', 'GNEUT', 'TROIS', 
    'OMNIS', 'MULTIG', 'MULTIS', 'POLYG', 'POLYS', 'BIGEND', 'ABRO', 'ANDRO', 'GYNE', 
    'BERRI', 'ALMD', 'QPR', 'GAYBO', 'GFLUX', 'QUEER', 
    'USA', 'TART', 'HOWLS', '10-13-STAR',
    'SEASONS', 'spring', 'summer', 'fall', 'winter',
    'CC (Candy-Cane)', 'RW', 'RWG', 'RG', 'KYO-Red', 'KYO-Black', 'KRIS', 'FRISK',
    'AETHER', 'ANEMO', 'GEO', 'ELECTRO', 'DENDRO', 'HYDRO', 'PYRO', 'CRYO', 'NONE', 'ALL',
]

# ---------------------------------------------------------------------
# STEP 2: SKU vocabulary (from skuParser.py / skuKey.txt), with the
# renames needed to land on the trends sheet's exact header spelling.
#
# Every one of these is built as code -> trend_column, uniformly, even
# where code and column currently happen to match (e.g. '4B' -> '4B').
# Never assume they'll stay identical -- skuVocab.py's own data model
# (code -> (desc, col)) explicitly allows them to diverge, the same way
# 'BI' -> 'BI3' already diverges in DESIGNS.
# ---------------------------------------------------------------------
import skuVocab as vocab

BEAD_PREFIX_COLUMN = {code: col for code, (_desc, col) in vocab.BEAD_PREFIXES.items()}
DESIGN_COLUMN = {code: col for code, (_desc, col) in vocab.PRIDE_DESIGNS.items()}
# append non-pride DESIGNS to DESIGN_COLUMN
DESIGN_COLUMN.update({code: col for code, (_desc, col) in vocab.DESIGNS.items()})
STANDALONE_COLUMN = {code: col for code, (_desc, col) in vocab.STANDALONE_PREFIXES.items()}
AETHER_COLUMN = {code: col for code, (_desc, col) in vocab.AETHER_ELEMENTS.items()}
SEASON_COLUMN = {code: col for code, (_desc, col) in vocab.SEASON_NAMES.items()}
CC_COLUMN = {code: col for code, (_desc, col) in vocab.CC_COLORS.items()}
KYO_COLUMN = {code: col for code, (_desc, col) in vocab.KYO_COLORS.items()}

# ---------------------------------------------------------------------
# VALIDATION -- call this against the live TREND_COLUMNS list so a typo
# or renamed column fails loudly at import time instead of silently
# undercounting a design in the generated trends CSV.
# ---------------------------------------------------------------------
def all_expected_trend_columns():
    cols = set()

    for code_map in (BEAD_PREFIX_COLUMN, STANDALONE_COLUMN, DESIGN_COLUMN,
                      SEASON_COLUMN, AETHER_COLUMN, CC_COLUMN, KYO_COLUMN):
        for col in code_map.values():
            if col is not None:
                cols.add(col)

    for entry in vocab.FINDINGS.values():
        if entry['trend_column'] is not None:
            cols.add(entry['trend_column'])

    for _code, info in vocab.FINDINGS_LEN.items():
        if info.get('trend_column'):
            cols.add(info['trend_column'])
        if info.get('length_trend_column'):
            cols.add(info['length_trend_column'])

    cols.add(vocab.TART_INFO['trend_column'])

    return cols


def validate_against_trend_columns(trend_columns, raise_on_error=False):
    """
    Compare this vocabulary against a live TREND_COLUMNS list.

    Returns (missing, unreferenced):
      - missing: columns this vocabulary expects but that AREN'T in
        trend_columns (typo, renamed column, or column that got deleted --
        this is the dangerous direction, since it means a design will
        silently stop being counted anywhere but 'items sold').
      - unreferenced: columns that exist in trend_columns but that no
        vocabulary code points to (informational only -- some of these
        are structural, e.g. 'date', 'items sold', 'SEASONS-charm', so
        this list will never be empty and that's fine).

    If raise_on_error is True, raises ValueError when `missing` is
    non-empty. salesToTrendsGen.py should call this at startup with
    raise_on_error=True so a bad mapping stops the run instead of quietly
    producing a wrong trends file.
    """
    expected = all_expected_trend_columns()
    trend_set = set(trend_columns)

    missing = sorted(expected - trend_set)
    unreferenced = sorted(trend_set - expected)

    if missing and raise_on_error:
        raise ValueError(
            "sku_vocabulary.py expects these trend columns, but they're "
            f"missing from TREND_COLUMNS: {missing}. Either the column was "
            "renamed/removed, or a vocabulary entry has a typo'd "
            "trend_column value."
        )

    return missing, unreferenced

# --- run the cross-check immediately after TREND_COLUMNS is defined ---
# raise_on_error=True still applies here: a MISSING column is a real bug
# (a design would silently stop being counted), so that case should keep
# failing loudly at import time. An UNREFERENCED column is informational
# only, so it's stored for a caller to inspect/display instead of printed
# -- importing this module should never write to stdout on its own.
_missing, UNREFERENCED_TREND_COLUMNS = validate_against_trend_columns(
    TREND_COLUMNS, raise_on_error=True
)

NON_PRODUCT_TOKENS = {
    'custom', 'cancel', 'refund', 'package bounced',
}

from skuParser import parse_sku as _shared_parse_sku
from skuVocab import FINDINGS

_FINDING_CODES = set(FINDINGS.keys())


def parse_sku_row(sku_original):
    """Adapter: same return shape build_day_rows() already expects,
    but the actual parsing is delegated to skuParser.parse_sku().

    Returns (parsed_or_None, warning_or_None) instead of printing --
    parsed is None for rows that aren't a real product line (non-product
    tokens, USPS rows, blank SKUs) and {'error': True} for SKUs that
    couldn't be parsed at all, same as before."""
    sku = sku_original.strip()
    if not sku:
        return None, None
    if sku.lower() in NON_PRODUCT_TOKENS or sku.lower().startswith('usps'):
        return None, None

    parsed = _shared_parse_sku(sku)

    if parsed.get('error'):
        return {'error': True}, f"Could not recognize SKU '{sku_original}', skipping."

    if parsed['category'] == 'TART':
        return {'kind': 'tart', 'tart_n': parsed['tart_n']}, None

    if parsed.get('is_standalone'):
        return {'kind': 'ten_thirteen_star'}, None

    warning = None
    if parsed.get('unmatched_design_token'):
        warning = (f"Design token '{parsed['unmatched_design_token']}' on SKU "
                   f"'{sku_original}' isn't recognized in skuVocab.py yet.")

    category = parsed['category']
    result = {
        'kind': 'standard',
        'prefix': parsed['prefix'],
        'flag': parsed['design'],
        'finding': category if category in _FINDING_CODES else None,
        'chain_length': parsed['length'] if category == 'NK' else None,
        'brace_length': parsed['length'] if category in ('BRAC', 'BRAC-E') else None,
        'brace_type': 'chain' if category == 'BRAC' else 'elastic' if category == 'BRAC-E' else None,
    }
    return result, warning

from shopIO import load_valid_sales_rows

def load_valid_line_items(sales_path):
    """Returns (order_items, order_date, warnings). warnings combines
    row-loading warnings from shopIO (bad quantity/date) and SKU-parsing
    warnings from parse_sku_row (unrecognized SKU, unmatched design
    token) -- all as plain strings, none printed here."""
    order_items = defaultdict(list)
    order_date = {}
    warnings = []

    rows, row_warnings = load_valid_sales_rows(sales_path)
    warnings.extend(row_warnings)

    for r in rows:
        parsed, warning = parse_sku_row(r['sku'])
        if warning:
            warnings.append(warning)
        if parsed is None or parsed.get('error'):
            continue

        order_items[r['order_number']].append((parsed, r['quantity']))
        onum = r['order_number']
        if onum not in order_date or r['date'] < order_date[onum]:
            order_date[onum] = r['date']

    return order_items, order_date, warnings


def build_day_rows(order_items, order_date):
    """Returns (days, warnings).

    days: dict date(datetime) -> row dict (column name -> numeric total)
    warnings: list of plain strings, one per line item whose design flag
    is a recognized code but has no trends column mapped to it yet (it's
    still counted in 'items sold' and the bead-type column, but nowhere
    else). This used to be a bare print() buried inside the row-building
    loop; it's now returned like every other warning in this module so a
    GUI (or CLI) can decide how/whether to surface it.
    """
    days = defaultdict(lambda: defaultdict(int))
    warnings = []

    for order_num, items in order_items.items():
        day = order_date[order_num]
        row = days[day]

        for parsed, qty in items:
            row['items sold'] += qty

            if parsed['kind'] == 'tart':
                row['TART'] += qty
                continue

            if parsed['kind'] == 'ten_thirteen_star':
                row['10-13-STAR'] += qty
                continue

            prefix = parsed['prefix']

            if prefix in BEAD_PREFIX_COLUMN:
                row[BEAD_PREFIX_COLUMN[prefix]] += qty
            elif prefix == 'HOWLS':
                row['HOWLS'] += qty
            elif prefix == 'AETHER':
                row['AETHER'] += qty
                if parsed['flag']:
                    row[AETHER_COLUMN[parsed['flag']]] += qty
            elif prefix == 'SEASONS':
                row['SEASONS'] += qty
                if parsed['flag']:
                    row[SEASON_COLUMN[parsed['flag']]] += qty
            elif prefix == 'CC':
                row['CC (Candy-Cane)'] += qty
                if parsed['flag']:
                    row[CC_COLUMN[parsed['flag']]] += qty
            elif prefix == 'KYO':
                if parsed['flag']:
                    row[KYO_COLUMN[parsed['flag']]] += qty

            # design flag (pride flags etc.) for bead-prefixed items
            if parsed['flag'] and prefix in BEAD_PREFIX_COLUMN:
                col = DESIGN_COLUMN.get(parsed['flag'])
                if col:
                    row[col] += qty
                else:
                    warnings.append(
                        f"Design '{parsed['flag']}' has no trends column yet "
                        f"(order dated {shopFormatting.dateFormatUI(day)}); counted in 'items sold' and "
                        f"'{prefix}' only."
                    )

            # finding
            finding = parsed['finding']
            if finding and finding in FINDINGS:
                trend_col = FINDINGS[finding]['trend_column']
                if trend_col:
                    row[trend_col] += qty
            # DK intentionally has no trends column (trend_column is None)

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

    return days, warnings


def write_trends_csv(days, output_path):
    """Writes the generated trend rows to a CSV file. This is a file
    output action (like recipeGen4B.py's write_recipes_csv), not console
    presentation -- it stays separate from render_diffs_cli()/main()'s
    print() calls."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(TREND_COLUMNS)

        totals = defaultdict(float)
        for day in sorted(days.keys()):
            row = days[day]
            out_row = []
            for col in TREND_COLUMNS:
                if col == 'date':
                    out_row.append(f"{shopFormatting.dateFormatCSV(day)}")
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

    Returns (days, warnings). warnings holds one plain string per
    reference row whose date couldn't be parsed under any known format
    (that row is skipped, not counted). Previously printed directly here;
    now returned like everything else in this module.
    """
    days = {}
    warnings = []
    with open(path, 'r', newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if not row or not row[0].strip() or row[0].strip() == 'Total':
                continue
            day = _parse_reference_date(row[0])
            if day is None:
                warnings.append(f"Could not parse reference date '{row[0]}', skipping that row.")
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
    return days, warnings


def compute_trend_diffs(generated_days, reference_days):
    """
    Compare freshly generated trends against an existing reference file
    (hand-tallied or a prior run) and return the discrepancies as data,
    so they can be checked against the Etsy dashboard however the caller
    wants (CLI text, a GUI diff view, etc.).

    A date only on one side gets a record with no diffs list. For dates
    on both sides, only columns whose values actually differ are
    included -- matching columns are not noise here.

    Returns a list of dicts, one per date with any discrepancy:
        {'label': 'Tuesday, April 22, 2025',
         'status': 'only_generated' | 'only_reference' | 'diffs',
         'diffs': [(col, generated_val, reference_val), ...]}  # [] for only_* statuses

    Pure function -- no printing. render_diffs_cli() is the CLI-only
    renderer for this output.
    """
    all_dates = sorted(set(generated_days) | set(reference_days))
    diffs_report = []

    for day in all_dates:
        label = f"{shopFormatting.dateFormatUI(day)}"
        mine = generated_days.get(day)
        theirs = reference_days.get(day)

        if mine is not None and theirs is None:
            diffs_report.append({'label': label, 'status': 'only_generated', 'diffs': []})
            continue
        if mine is None and theirs is not None:
            diffs_report.append({'label': label, 'status': 'only_reference', 'diffs': []})
            continue

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
            diffs_report.append({'label': label, 'status': 'diffs', 'diffs': diffs})

    return diffs_report


def render_diffs_cli(diffs_report):
    """CLI-only text renderer for compute_trend_diffs()'s output. The
    only function in this module concerned with discrepancy display."""
    if not diffs_report:
        print("No discrepancies found - generated output matches the reference file exactly.")
        return

    for entry in diffs_report:
        label = entry['label']
        if entry['status'] == 'only_generated':
            print(f"{label}  -- only in generated output (missing from reference file)")
        elif entry['status'] == 'only_reference':
            print(f"{label}  -- only in reference file (missing from generated output)")
        else:
            print(label)
            for col, a, b in entry['diffs']:
                a_disp = _fmt(a) if isinstance(a, (int, float)) else a
                b_disp = _fmt(b) if isinstance(b, (int, float)) else b
                print(f"    {col:35s} generated={a_disp!s:<10s} reference={b_disp!s}")

    print(f"\n{len(diffs_report)} date(s) with discrepancies (see above).")


def generate_trends_report(sales_path, reference_path=None):
    """One-stop compute entry point: reads the sales CSV, builds the
    trend day rows, and -- if reference_path is given and exists --
    loads that reference file and computes the diff report against it.
    Bundles every warning from every stage (row loading, SKU parsing,
    day-row building, reference loading) into a single list.

    No printing, no input() -- this is what a GUI should call. main()
    is reduced to input()/print() around this and write_trends_csv().

    Returns:
        {
          'order_count': int,
          'days': {date: {col: val}},
          'warnings': [...],
          'reference_days': {date: {col: val}} or None,
          'diffs': [...] or None,   # compute_trend_diffs() output, None if no reference
        }
    """
    order_items, order_date, warnings = load_valid_line_items(sales_path)
    days, day_row_warnings = build_day_rows(order_items, order_date)
    warnings = list(warnings) + day_row_warnings

    reference_days = None
    diffs = None
    if reference_path and os.path.isfile(reference_path):
        reference_days, ref_warnings = load_reference_trends(reference_path)
        warnings.extend(ref_warnings)
        diffs = compute_trend_diffs(days, reference_days)

    return {
        'order_count': len(order_items),
        'days': days,
        'warnings': warnings,
        'reference_days': reference_days,
        'diffs': diffs,
    }


def main():
    sales_path = input("Enter path to sales CSV (or Enter for PyrrhicSilvaShopSales.csv): ").strip()
    if not sales_path:
        sales_path = 'PyrrhicSilvaShopSales.csv'

    # Reference file is looked for alongside the sales CSV, same as before.
    reference_path = os.path.join(
        os.path.dirname(os.path.abspath(sales_path)), 'PyrrhicSilvaShopTrends.csv'
    )

    print(f"\nReading {sales_path} ...")
    report = generate_trends_report(sales_path, reference_path)

    print(f"  \u2713 {report['order_count']} orders with valid line items")
    print(f"  \u2713 {len(report['days'])} distinct sale days")

    if report['warnings']:
        print(f"\n\u26a0\ufe0f  {len(report['warnings'])} warning(s):")
        for w in report['warnings']:
            print(f"  - {w}")

    print(f"\nLooking for reference file at {sales_path} ...")

    if report['reference_days'] is None:
        print(f"\n  (no reference file found at '{sales_path}' -- skipping comparison)")
    else:
        print(f"\n  \u2713 compared against {len(report['reference_days'])} dated rows in '{sales_path}'")
        print("\n" + "-" * 60)
        render_diffs_cli(report['diffs'])

    if len(report['diffs']) > 0: 
        try:
            save = prompt_yes_no("\nSave generated trends to a file? (y/n): ")
        except QuitRequested:
            print("\nCancelled -- nothing saved.")
            return

        if save:
            output_path = input("Output path (or Enter for TempTrendsGenerated.csv): ").strip()
            if not output_path:
                output_path = 'TempTrendsGenerated.csv'
            write_trends_csv(report['days'], output_path)
            print(f"\n\u2713 Saved to {output_path}")


if __name__ == '__main__':
    main()