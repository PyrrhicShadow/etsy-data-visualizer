import csv
from datetime import datetime
from collections import defaultdict

def analyze_sales_by_day_of_week():
    file_path = input("Enter the file path: ").strip()
    
    # Map day numbers to names (0 = Monday, 6 = Sunday)
    DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Store order_number -> earliest date
    order_to_date = {}
    
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
                    
                    # Keep only the earliest date for each order
                    if order_num not in order_to_date or parsed_date < order_to_date[order_num]:
                        order_to_date[order_num] = parsed_date
                    
                except ValueError as e:
                    print(f"Warning: Could not parse date '{date_str}', skipping...")
                    continue
    
    except FileNotFoundError:
        print(f"Error: File not found at '{file_path}'")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
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