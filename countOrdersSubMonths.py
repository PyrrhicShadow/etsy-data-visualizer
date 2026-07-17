import csv
from datetime import datetime

def analyze_order_numbers():
    file_path = input("Enter the file path: ").strip()
    
    ranges = {
        '1-10': set(),
        '11-20': set(),
        '21-end': set()
    }
    
    processed_rows = 0
    skipped_rows = 0
    failed_dates = 0
    
    try:
        with open(file_path, 'r', newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Debug: Print column names to verify
            print(f"Available columns: {list(reader.fieldnames)}\n")
            
            for i, row in enumerate(reader):
                # Show first 5 rows for debugging
                if i < 5:
                    print(f"Row {i}: date='{row.get('date', 'MISSING')}' | order='{row.get('order number', 'MISSING')}'")
                
                date_str = row.get('date', '').strip().strip('"').strip("'")
                order_num = row.get('order number', '').strip().strip('"').strip("'")
                
                if not date_str or not order_num or order_num == '-1':
                    skipped_rows += 1
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
                    
                    processed_rows += 1
                except ValueError as e:
                    failed_dates += 1
                    if i < 10:
                        print(f"  Failed to parse: '{date_str}' ({e})")
                    continue
    
    except FileNotFoundError:
        print(f"Error: File not found at '{file_path}'")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    print(f"\n{'='*50}")
    print(f"Processed rows: {processed_rows}")
    print(f"Skipped rows: {skipped_rows}")
    print(f"Failed date parses: {failed_dates}\n")
    
    print(f"Days 1-10:      {len(ranges['1-10'])} unique orders")
    print(f"Days 11-20:     {len(ranges['11-20'])} unique orders")  
    print(f"Days 21-End:    {len(ranges['21-end'])} unique orders")
    print(f"Total unique:   {len(ranges['1-10'] | ranges['11-20'] | ranges['21-end'])} orders")

if __name__ == "__main__":
    analyze_order_numbers()