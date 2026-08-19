"""
countOrdersSubMonths.py - Pyrrhic Silva Crafts

GUI NOTE: compute_order_ranges() is the reusable piece -- it takes rows
already loaded by shopIO.load_valid_sales_rows() and returns a plain
dict of results, no printing or input() involved. render_report() is
the CLI-only piece that turns that dict into console text. A GUI should
call compute_order_ranges() directly and render the result however it
wants (a table widget, a chart, whatever) instead of going through
render_report() at all.
"""

from collections import defaultdict
from shopIO import load_valid_sales_rows
import shopFormatting

def compute_order_ranges(rows):
    """Categorize orders by which third of the month their earliest date
    falls in. Returns a dict:
        ranges: {'1-10': set, '11-20': set, '21-end': set} of order numbers
        total_unique: int
        sum_of_ranges: int
        duplicates: {order_num: [sorted unique dates]} for orders whose
            line items disagreed on date (kept the earliest)
    No printing, no input -- pure function of `rows` (as returned by
    shopIO.load_valid_sales_rows).
    """
    ranges = {'1-10': set(), '11-20': set(), '21-end': set()}
    order_dates = defaultdict(list)

    for r in rows:
        order_dates[r['order_number']].append(r['date'].date())

    duplicates = {}
    for order_num, date_list in order_dates.items():
        unique_dates = sorted(set(date_list))
        if len(unique_dates) > 1:
            duplicates[order_num] = unique_dates

        earliest_date = min(date_list)
        day_of_month = earliest_date.day

        if 1 <= day_of_month <= 10:
            ranges['1-10'].add(order_num)
        elif 11 <= day_of_month <= 20:
            ranges['11-20'].add(order_num)
        else:
            ranges['21-end'].add(order_num)

    total_unique = len(ranges['1-10'] | ranges['11-20'] | ranges['21-end'])
    sum_of_ranges = sum(len(v) for v in ranges.values())

    return {
        'ranges': ranges,
        'total_unique': total_unique,
        'sum_of_ranges': sum_of_ranges,
        'duplicates': duplicates,
    }


def render_report_cli(result):
    """Turn compute_order_ranges()'s result dict into CLI text. This is
    the ONLY function in this module that prints anything."""
    ranges = result['ranges']
    total_unique = result['total_unique']
    sum_of_ranges = result['sum_of_ranges']
    duplicates = result['duplicates']

    print("\n=== Unique Order Numbers by Date Range ===\n")
    print(f"Days 1-10:      {len(ranges['1-10'])} unique orders")
    print(f"Days 11-20:     {len(ranges['11-20'])} unique orders")
    print(f"Days 21-End:    {len(ranges['21-end'])} unique orders")
    print(f"\nSum of ranges:  {sum_of_ranges}")
    print(f"Total unique:   {total_unique} orders")

    if sum_of_ranges != total_unique:
        print(f"\nWARNING: {sum_of_ranges - total_unique} order(s) still appear in multiple date ranges!")
    else:
        print("\nAll counts add up correctly!")

    if duplicates:
        print(f"\n{len(duplicates)} order(s) had DIFFERENT dates (kept earliest):")
        for order_num, unique_dates in duplicates.items():
            dates_str = [shopFormatting.dateFormatCSV(d) for d in unique_dates]
            print(f"  \u2022 {order_num}: {dates_str} \u2192 kept {shopFormatting.dateFormatCSV(unique_dates[0])}")


def main():
    sales_path = input("Enter path to sales CSV (or Enter for ShopSales.csv): ").strip()
    if not sales_path:
        sales_path = 'ShopSales.csv'

    try:
        rows, warnings = load_valid_sales_rows(sales_path)
    except FileNotFoundError:
        print(f"Error: File not found at '{sales_path}'")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    for w in warnings:
        print(f"Warning: {w}")

    result = compute_order_ranges(rows)
    render_report_cli(result)
    return result


if __name__ == "__main__":
    main()