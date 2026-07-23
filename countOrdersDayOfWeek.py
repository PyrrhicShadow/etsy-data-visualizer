from collections import defaultdict
from shopIO import load_valid_sales_rows, earliest_dates_by_order

def analyze_sales_by_day_of_week():
    sales_path = input("Enter path to sales CSV (or Enter for PyrrhicSilvaShopSales.csv): ").strip()
    if not sales_path:
        sales_path = 'PyrrhicSilvaShopSales.csv'

    DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    try:
        rows = load_valid_sales_rows(sales_path)
    except FileNotFoundError:
        print(f"Error: File not found at '{sales_path}'")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    order_to_date = earliest_dates_by_order(rows)
    
    # Count orders by day of week
    day_counts = defaultdict(int)
    for order_num, date_obj in order_to_date.items():
        day_of_week = date_obj.weekday()  # 0 = Monday, 6 = Sunday
        day_counts[DAY_NAMES[day_of_week]] += 1
    
    # Calculate totals
    total_orders = sum(day_counts.values())
    
    # Sort by day order (Mon-Sun)
    sorted_days = [(day, day_counts.get(day, 0)) for day in DAY_NAMES]
    
    # Display results
    print("\n=== Sales by Day of Week ===\n")
    print(f"{'Day':<15} {'Unique Orders':>12} {'Percentage':>12}")
    print("-" * 39)
    
    max_orders = max(count for _, count in sorted_days) if sorted_days else 0
    
    for day, count in sorted_days:
        percentage = (count / total_orders * 100) if total_orders > 0 else 0
        bar = "█" * int(count / max_orders * 20) if max_orders > 0 else ""
        print(f"{day:<15} {count:>12} {percentage:>10.1f}% {bar}")
    
    print("-" * 39)
    print(f"{'TOTAL':<15} {total_orders:>12} {100:>10.1f}%")
    
    # Find busiest and slowest days
    if sorted_days:
        busiest = max(sorted_days, key=lambda x: x[1])
        slowest = min(sorted_days, key=lambda x: x[1])
        
        print(f"\nBusiest day:  {busiest[0]} ({busiest[1]} orders)")
        print(f"Slowest day:   {slowest[0]} ({slowest[1]} orders)")
        
        # Recommend trip planning
        if busiest[1] > slowest[1] * 1.5:
            print(f"\nTip: {slowest[0]} is {busiest[1]/slowest[1]:.1f}x slower than {busiest[0]}.")
            print(f"   Good day to schedule errands or day trips!")
        else:
            print("\nTip: Sales are fairly consistent across weekdays.")
    
    return dict(day_counts)

if __name__ == "__main__":
    analyze_sales_by_day_of_week()