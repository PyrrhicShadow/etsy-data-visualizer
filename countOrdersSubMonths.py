from collections import defaultdict
from shopIO import load_valid_sales_rows

def analyze_order_numbers():
    sales_path = input("Enter path to sales CSV (or Enter for PyrrhicSilvaShopSales.csv): ").strip()
    if not sales_path:
        sales_path = 'PyrrhicSilvaShopSales.csv'

    ranges = {'1-10': set(), '11-20': set(), '21-end': set()}
    order_dates = defaultdict(list)

    try:
        rows = load_valid_sales_rows(sales_path)
    except FileNotFoundError:
        print(f"Error: File not found at '{sales_path}'")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    for r in rows:
        order_dates[r['order_number']].append(r['date'].date())
    
    # Now process: for each order, find earliest date and categorize
    duplicates_found = []
    for order_num, date_list in order_dates.items():
        # Check if there are ACTUALLY DIFFERENT date values (not just multiple rows)
        unique_dates = set(date_list)
        if len(unique_dates) > 1:
            duplicates_found.append(order_num)
        
        # Get the earliest date for this order
        earliest_date = min(date_list)
        day_of_month = earliest_date.day
        
        # Categorize by date range
        if 1 <= day_of_month <= 10:
            ranges['1-10'].add(order_num)
        elif 11 <= day_of_month <= 20:
            ranges['11-20'].add(order_num)
        elif 21 <= day_of_month <= 31:
            ranges['21-end'].add(order_num)
    
    # Calculate totals
    total_unique = len(ranges['1-10'] | ranges['11-20'] | ranges['21-end'])
    sum_of_ranges = len(ranges['1-10']) + len(ranges['11-20']) + len(ranges['21-end'])
    
    # Display results
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
    
    if duplicates_found:
        print(f"\n{len(duplicates_found)} order(s) had DIFFERENT dates (kept earliest):")
        for order_num in duplicates_found:
            unique_dates = sorted(set(order_dates[order_num]))
            print(f"  • {order_num}: {[d.strftime('%Y-%m-%d') for d in unique_dates]} → kept {min(unique_dates).strftime('%Y-%m-%d')}")
    
    return ranges

if __name__ == "__main__":
    analyze_order_numbers()