import csv
from datetime import datetime
from collections import defaultdict

def analyze_order_numbers():
    file_path = input("Enter the file path: ").strip()
    
    ranges = {
        '1-10': set(),
        '11-20': set(),
        '21-end': set()
    }
    
    # Store order_number -> list of dates
    order_dates = defaultdict(list)
    
    try:
        with open(file_path, 'r', newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                date_str = row.get('date', '').strip().strip('"').strip("'")
                order_num = row.get('order number', '').strip().strip('"').strip("'")
                quantity_str = row.get('item quantity', '').strip().strip('"').strip("'")
                
                # Skip rows without valid data
                if not date_str or not order_num:
                    continue
                
                # Filter: Only process actual orders (quantity >= 1)
                try:
                    quantity = int(quantity_str)
                    if quantity < 1:
                        continue  # Skip cancellations/refunds
                except ValueError:
                    print(f"Warning: Invalid quantity '{quantity_str}', skipping...")
                    continue
                
                try:
                    parsed_date = datetime.strptime(date_str, "%A, %B %d, %Y")
                    order_dates[order_num].append((parsed_date, parsed_date.date()))
                except ValueError as e:
                    print(f"Warning: Could not parse date '{date_str}', skipping...")
                    continue
    
    except FileNotFoundError:
        print(f"Error: File not found at '{file_path}'")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Now process: for each order, find earliest date and categorize
    duplicates_found = []
    for order_num, date_list in order_dates.items():
        if len(date_list) > 1:
            duplicates_found.append(order_num)
        
        # Get the earliest date for this order
        earliest_date = min(date_list, key=lambda x: x[0])[1]
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
        print(f"\n WARNING: {sum_of_ranges - total_unique} order(s) still appear in multiple date ranges!")
    else:
        print("\n✓ All counts add up correctly!")
    
    if duplicates_found:
        print(f"\n{len(duplicates_found)} order(s) had multiple dates (kept earliest):")
        for order_num in duplicates_found:
            dates = [d[0].strftime('%Y-%m-%d') for d in order_dates[order_num]]
            print(f"  • {order_num}: {dates} → kept {min(dates)}")
    
    return ranges

if __name__ == "__main__":
    analyze_order_numbers()