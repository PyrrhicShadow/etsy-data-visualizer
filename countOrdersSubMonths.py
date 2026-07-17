import csv
from datetime import datetime
from collections import defaultdict

def analyze_order_numbers():
    file_path = input("Enter the file path: ").strip()
    
    # Track order number -> dates mapping
    order_to_dates = defaultdict(list)
    
    try:
        with open(file_path, 'r', newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                date_str = row.get('date', '').strip().strip('"').strip("'")
                order_num = row.get('order number', '').strip().strip('"').strip("'")
                
                if not date_str or not order_num or order_num == '-1':
                    continue
                
                try:
                    parsed_date = datetime.strptime(date_str, "%A, %B %d, %Y")
                    order_to_dates[order_num].append(parsed_date.date())
                except ValueError:
                    continue
    
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # Find order numbers with multiple different dates
    print(f"\n{'='*60}")
    print("ORDERS WITH MULTIPLE DATES (causing count discrepancy):")
    print('='*60)
    
    duplicates = {k: list(set(v)) for k, v in order_to_dates.items() if len(set(v)) > 1}
    
    if duplicates:
        for order_num, dates in sorted(duplicates.items()):
            print(f"\nOrder: {order_num}")
            for d in sorted(dates):
                print(f"  → {d}")
        
        print(f"\n{'='*60}")
        print(f"Found {len(duplicates)} order(s) with multiple dates")
    else:
        print("\nNo duplicate orders found.")
    
    return duplicates

if __name__ == "__main__":
    analyze_order_numbers()