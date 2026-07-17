import csv
from datetime import datetime
from collections import defaultdict

def analyze_order_numbers():
    # Ask for file location
    file_path = input("Enter the file path: ").strip()
    
    # Initialize counters for each date range
    ranges = {
        '1-10': set(),
        '11-20': set(),
        '21-end': set()
    }
    
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                # Get the date and order number fields
                date_str = row.get('date', '').strip()
                order_num = row.get('order number', '').strip()
                
                # Skip rows without valid data
                if not date_str or not order_num:
                    continue
                
                try:
                    # Parse the date (format: "Tuesday, April 22, 2025")
                    parsed_date = datetime.strptime(date_str, "%A, %B %d, %Y")
                    day_of_month = parsed_date.day
                    
                    # Categorize by date range
                    if 1 <= day_of_month <= 10:
                        ranges['1-10'].add(order_num)
                    elif 11 <= day_of_month <= 20:
                        ranges['11-20'].add(order_num)
                    elif 21 <= day_of_month <= 31:
                        ranges['21-end'].add(order_num)
                except ValueError:
                    print(f"Warning: Could not parse date '{date_str}', skipping...")
                    continue
    
    except FileNotFoundError:
        print(f"Error: File not found at '{file_path}'")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Display results
    print("\n=== Unique Order Numbers by Date Range ===\n")
    print(f"Days 1-10:      {len(ranges['1-10'])} unique orders")
    print(f"Days 11-20:     {len(ranges['11-20'])} unique orders")
    print(f"Days 21-End:    {len(ranges['21-end'])} unique orders")
    print(f"\nTotal unique:   {len(ranges['1-10'] | ranges['11-20'] | ranges['21-end'])} orders")
    
    return ranges

if __name__ == "__main__":
    analyze_order_numbers()