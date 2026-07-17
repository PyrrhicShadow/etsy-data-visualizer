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
                    day_of_month = parsed_date.day
                    
                    if 1 <= day_of_month <= 10:
                        ranges['1-10'].add(order_num)
                    elif 11 <= day_of_month <= 20:
                        ranges['11-20'].add(order_num)
                    elif 21 <= day_of_month <= 31:
                        ranges['21-end'].add(order_num)
                except ValueError as e:
                    print(f"Warning: Could not parse date '{date_str}', skipping...")
                    continue
    
    except FileNotFoundError:
        print(f"Error: File not found at '{file_path}'")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
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
        print(f"\n WARNING: {sum_of_ranges - total_unique} order(s) appear in multiple date ranges!")
    
    return ranges

if __name__ == "__main__":
    analyze_order_numbers()