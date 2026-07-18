#!/usr/bin/env python3
"""
Inventory Gap Filler - Pyrrhic Silva Shop
Scans InventoryData.csv for missing bead color IDs and appends blank-price rows.
"""

import csv

# == COLOR DEFINITIONS ==
# Pulled from 4B inventory entries (11XX series)
COLORS = [
    ('1101', '1401', '1201', '1601', 'red'),
    ('1102', '1402', '1202', '1602', 'orange'),
    ('1103', '1403', '1203', '1603', 'yellow'),
    ('1104', '1404', '1204', '1604', 'green'),
    ('1105', '1405', '1205', '1605', 'cyan'),
    ('1106', '1406', '1206', '1606', 'blue'),
    ('1107', '1407', '1207', '1607', 'purple'),
    ('1108', '1408', '1208', '1608', 'white'),
    ('1109', '1409', '1209', '1609', 'gray'),
    ('1110', '1410', '1210', '1610', 'black'),
    ('1111', '1411', '1211', '1611', 'pink'),
    ('1112', '1412', '1212', '1612', 'magenta'),
    ('1113', '1413', '1213', '1613', 'light green'),
    ('1114', '1414', '1214', '1614', 'light purple'),
    ('1115', '1415', '1215', '1615', 'brown'),
]

# Naming templates per series
NAME_TEMPLATES = {
    '4b': '4mm {color} faceted bicone glass beads',
    '6p': '6mm {color} round plastic pearl beads',
    '8r': '8mm {color} round jelly glass beads',
    '4c': '4mm {color} faceted cube glass beads',
}

# ID mappings per series
SERIES_IDS = {
    '4b': lambda c: c[0],
    '6p': lambda c: c[1],
    '8r': lambda c: c[2],
    '4c': lambda c: c[3],
}


def load_existing_ids(filename):
    """Load existing material IDs from inventory CSV."""
    ids = set()
    with open(filename, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ids.add(row['material id'].strip())
    return ids


def generate_missing_entries(existing_ids):
    """Generate rows for any missing color IDs across all four series."""
    new_rows = []
    
    for color_entry in COLORS:
        color_name = color_entry[4]
        
        for series in ['4b', '6p', '8r', '4c']:
            mat_id = SERIES_IDS[series](color_entry)
            
            if mat_id not in existing_ids:
                name = NAME_TEMPLATES[series].format(color=color_name)
                new_rows.append({
                    'material id': mat_id,
                    'material name': name,
                    'price': '',
                    'total units': '',
                    'specific units': '',
                })
    
    return new_rows


def main():
    print("=" * 60)
    print("INVENTORY GAP FILLER - Pyrrhic Silva Shop")
    print("=" * 60)
    
    input_path = input("\nEnter path to InventoryData CSV (or Enter for InventoryData.csv): ").strip()
    if not input_path:
        input_path = 'InventoryData.csv'
    
    print(f"\nLoading existing inventory...")
    existing_ids = load_existing_ids(input_path)
    print(f"  ✓ {len(existing_ids)} materials found")
    
    new_rows = generate_missing_entries(existing_ids)
    
    if not new_rows:
        print("\n✓ All color entries already exist. No gaps to fill.")
        return
    
    # Group by series for display
    from collections import defaultdict
    by_series = defaultdict(list)
    for row in new_rows:
        mid = row['material id']
        if mid.startswith('14'):
            by_series['6P'].append(row)
        elif mid.startswith('12'):
            by_series['8R'].append(row)
        elif mid.startswith('16'):
            by_series['4C'].append(row)
    
    print(f"\n📋 Missing entries to add:")
    for series in ['6P', '8R', '4C']:
        if by_series[series]:
            print(f"\n  {series}:")
            for row in by_series[series]:
                print(f"    {row['material id']}  {row['material name']}")
    
    # Write to a new file
    default_output = 'InventoryData_Gaps.csv'
    output_path = input(f"\nEnter output path (or Enter for {default_output}): ").strip()
    if not output_path:
        output_path = default_output
    
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['material id', 'material name', 'price', 'total units', 'specific units'])
        writer.writeheader()
        for row in new_rows:
            writer.writerow(row)
    
    print(f"\n✓ Written {len(new_rows)} entries to {output_path}")
    print("  Review in Excel, fill in prices/units, then merge into InventoryData.csv manually.")


if __name__ == '__main__':
    main()