"""
countOrdersDayOfWeek.py - Pyrrhic Silva Shop

GUI NOTE: compute_day_of_week_counts() returns plain data (a dict plus a
couple of derived summary values) with zero printing. render_report()
is the CLI-only text renderer, including the ASCII bar chart -- a GUI
would replace render_report() with an actual chart widget fed the same
`counts` dict.
"""

from collections import defaultdict
from shopIO import load_valid_sales_rows, earliest_dates_by_order

DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def compute_day_of_week_counts(rows):
    """Count unique orders by day of week. Returns:
        counts: {day_name: count} for all 7 days, in DAY_NAMES order
        total_orders: int
        busiest: (day_name, count)
        slowest: (day_name, count)
    Pure function of `rows` (as returned by shopIO.load_valid_sales_rows)
    -- no printing, no input.
    """
    order_to_date = earliest_dates_by_order(rows)

    raw_counts = defaultdict(int)
    for order_num, date_obj in order_to_date.items():
        raw_counts[DAY_NAMES[date_obj.weekday()]] += 1

    counts = {day: raw_counts.get(day, 0) for day in DAY_NAMES}
    total_orders = sum(counts.values())

    busiest = max(counts.items(), key=lambda x: x[1]) if counts else (None, 0)
    slowest = min(counts.items(), key=lambda x: x[1]) if counts else (None, 0)

    return {
        'counts': counts,
        'total_orders': total_orders,
        'busiest': busiest,
        'slowest': slowest,
    }


def render_report_cli(result):
    """CLI-only text renderer for compute_day_of_week_counts()'s output."""
    counts = result['counts']
    total_orders = result['total_orders']
    busiest = result['busiest']
    slowest = result['slowest']

    print("\n=== Sales by Day of Week ===\n")
    print(f"{'Day':<15} {'Unique Orders':>12} {'Percentage':>12}")
    print("-" * 39)

    max_orders = max(counts.values()) if counts else 0

    for day in DAY_NAMES:
        count = counts[day]
        percentage = (count / total_orders * 100) if total_orders > 0 else 0
        bar = "\u2588" * int(count / max_orders * 20) if max_orders > 0 else ""
        print(f"{day:<15} {count:>12} {percentage:>10.1f}% {bar}")

    print("-" * 39)
    print(f"{'TOTAL':<15} {total_orders:>12} {100:>10.1f}%")

    if total_orders > 0:
        print(f"\nBusiest day:  {busiest[0]} ({busiest[1]} orders)")
        print(f"Slowest day:   {slowest[0]} ({slowest[1]} orders)")

        if slowest[1] > 0 and busiest[1] > slowest[1] * 1.5:
            print(f"\nTip: {slowest[0]} is {busiest[1] / slowest[1]:.1f}x slower than {busiest[0]}.")
            print(f"   Good day to schedule errands or day trips!")
        else:
            print("\nTip: Sales are fairly consistent across weekdays.")


def main():
    sales_path = input("Enter path to sales CSV (or Enter for PyrrhicSilvaShopSales.csv): ").strip()
    if not sales_path:
        sales_path = 'PyrrhicSilvaShopSales.csv'

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

    result = compute_day_of_week_counts(rows)
    render_report_cli(result)
    return result['counts']


if __name__ == "__main__":
    main()