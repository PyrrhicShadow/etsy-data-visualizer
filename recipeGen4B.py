#!/usr/bin/env python3
"""
Recipe Generator for Pyrrhic Silva Shop
Translates 4B pride flag recipes to 6P and 8R equivalents
"""

import csv

# == COLOR MAPPING ==
# 4B ID -> (6P pearl ID, 8R jelly ID, 4C cube ID)
COLOR_MAP = {
    '1101': ('1401', '1201', '1601'),  # red
    '1102': ('1402', '1202', '1602'),  # orange
    '1103': ('1403', '1203', '1603'),  # yellow
    '1104': ('1404', '1204', '1604'),  # green
    '1105': ('1405', '1205', '1605'),  # cyan / sky blue
    '1106': ('1406', '1206', '1606'),  # blue
    '1107': ('1407', '1207', '1607'),  # purple
    '1108': ('1408', '1208', '1608'),  # white
    '1109': ('1409', '1209', '1609'),  # gray
    '1110': ('1410', '1210', '1610'),  # black
    '1111': ('1411', '1211', '1611'),  # pink
    '1112': ('1412', '1212', '1612'),  # magenta
    '1113': ('1413', '1213', '1613'),  # light green
    '1114': ('1414', '1214', '1614'),  # light purple
    '1115': ('1415', '1215', '1615'),  # brown
}

# Charm replacements per bead type
CHARM_MAP = {
    '6p': {'0500': '0500'},  # Keep star
    '8r': {'0500': '0503'},  # Hollow star
    '4c': {'0500': '0507'},  # Heart charm
}

# Materials that carry over unchanged (pins, findings, packaging, etc.)
PRESERVE_IDS = {
    '0000', '0001',
    '0100', '0101',
    '0200', '0201', '0202', '0203', '0204', '0205', '0206', '0207',
    '0300', '0301',
    '0500', '0501', '0502', '0503', '0504', '0505', '0506',
    '0507', '0508', '0509', '0510', '0511', '0512', '0513',
    '0900', '0901', '0902', '0903',
    '1001', '1002', '1003', '1004', '1005', '1006',
    '1500', '1501', '1502', '1503',
}

def load_inventory(filename):
    """Load inventory data from CSV."""
    inventory = {}
    with open(filename, 'r', encoding='utf-8-sig') as f:  # utf-8-sig strips BOM
        reader = csv.DictReader(f)
        for row in reader:
            mat_id = row['material id'].strip()
            inventory[mat_id] = {
                'name': row['material name'].strip(),
                'price': float(row['price']),
                'total_units': float(row['total units']),
                'specific_units': float(row['specific units']),
            }
    return inventory

def load_recipes(filename):
    """Load recipes from CSV, handling variable-length rows."""
    recipes = {}
    with open(filename, 'r', encoding='utf-8-sig') as f:
        for line in f:
            # ... rest stays the same
            parts = line.strip().split(',')
            if len(parts) < 2:
                continue
            
            sku = parts[0].strip()
            materials = {}
            
            for cell in parts[1:]:
                cell = cell.strip()
                if cell and '*' in cell:
                    mat_id, qty = cell.split('*')
                    mat_id = mat_id.strip()
                    qty = int(qty.strip())
                    if mat_id.isdigit():
                        materials[mat_id] = qty
                # Non-numeric entries (like "cat charm") are silently skipped
            
            recipes[sku] = materials
    
    return recipes

def translate_recipe(recipe, target_type, color_map, charm_map):
    """Translate a 4B recipe to 6P, 8R, or 4C."""
    translated = {}
    target_index = {'6p': 0, '8r': 1, '4c': 2}
    idx = target_index[target_type]
    
    for mat_id, qty in recipe.items():
        if mat_id.startswith('11') and mat_id in color_map:
            new_id = color_map[mat_id][idx]
            
            if new_id is None:
                print(f"  ⚠️ No {target_type.upper()} equivalent for color {mat_id}")
                continue
            
            if new_id in translated:
                translated[new_id] += qty
            else:
                translated[new_id] = qty
        
        elif mat_id in charm_map.get(target_type, {}):
            new_charm = charm_map[target_type][mat_id]
            translated[new_charm] = qty
        
        elif mat_id in PRESERVE_IDS:
            translated[mat_id] = qty
        
        else:
            print(f"  ⚠️ Unknown material {mat_id} in recipe, passing through")
            translated[mat_id] = qty
    
    return translated

def generate_recipes(recipes):
    """Generate 4C, 6P, and 8R recipes from 4B recipes.
    Only generates recipes that don't already exist in the data."""
    output = {}
    warnings = []
    skipped = 0
    
    pride_skus = [sku for sku in recipes if sku.startswith('4b-')]
    
    for sku in pride_skus:
        recipe = recipes[sku]
        flag_name = sku[3:]  # Strip "4b-" prefix
        
        for target in ['4c', '6p', '8r']:
            new_sku = f"{target}-{flag_name}"
            
            if new_sku in recipes:
                skipped += 1
                continue
            
            translated = translate_recipe(recipe, target, COLOR_MAP, CHARM_MAP)
            output[new_sku] = translated
            
            if not translated:
                warnings.append(f"{new_sku}: empty recipe")
    
    return output, warnings, skipped

def write_recipes_csv(recipes, filename):
    """Write recipes to CSV in the same format as RecipesData.csv.
    
    Format: sku,matID*qty,matID*qty,...,padding to 10 columns
    """
    # Sort: original recipes first (alphabetical), then new ones grouped by type
    def sort_key(sku):
        # Group by prefix, then alphabetically
        if '-' in sku:
            prefix, rest = sku.split('-', 1)
            return (prefix, rest)
        return (sku, '')
    
    sorted_skus = sorted(recipes.keys(), key=sort_key)
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header: sku + 10 material columns
        header = ['sku', 'materials'] + [''] * 8
        writer.writerow(header)
        
        for sku in sorted_skus:
            materials = recipes[sku]
            cells = [sku]
            
            # Convert dict to matID*qty strings
            for mat_id, qty in materials.items():
                cells.append(f"{mat_id}*{qty}")
            
            # Pad to 10 columns (matching original format)
            while len(cells) < 10:
                cells.append('')
            
            writer.writerow(cells)

def main():
    print("=" * 60)
    print("RECIPE GENERATOR - Pyrrhic Silva Shop")
    print("=" * 60)
    
    # Load data
    print("\nLoading inventory...")
    inventory = load_inventory('InventoryData.csv')
    print(f"  ✓ {len(inventory)} materials loaded")
    
    print("Loading recipes...")
    recipes = load_recipes('RecipesData.csv')
    print(f"  ✓ {len(recipes)} recipes loaded")
    
    # Generate
    print("\nGenerating missing 4C, 6P, and 8R recipes...")
    all_recipes, warnings, skipped = generate_recipes(recipes)
    
    print(f"  ✓ {len(all_recipes)} new recipes generated")
    print(f"  ⊘ {skipped} recipes already existed (skipped)")
    
    # Show summary
    print("\n" + "-" * 40)
    for target in ['4c', '6p', '8r']:
        count = len([r for r in all_recipes if r.startswith(f'{target}-')])
        print(f"  {target.upper()}: {count} recipes")
    
    # Warnings
    if warnings:
        print(f"\n⚠️ {len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")
    
    # Check for missing inventory entries
    missing_8r = ['1201', '1212', '1214', '1215']
    missing_6p = ['1401', '1402', '1403', '1404', '1405', '1406', 
                   '1407', '1408', '1409', '1410', '1412', '1413', '1414', '1415']
    missing_4c = ['1601', '1602', '1603', '1604', '1605', '1606', 
                   '1607', '1608', '1609', '1610', '1611', '1612', '1613', '1614', '1615']
    
    print("\n📋 Materials to add to InventoryData.csv:")
    print("  6P pearl colors:")
    for mid in missing_6p:
        if mid not in inventory:
            print(f"    {mid}: 6mm [color] pearl glass beads (from box 1420)")
    print("  8R jelly colors:")
    for mid in missing_8r:
        if mid not in inventory:
            print(f"    {mid}: 8mm [color] round jelly glass beads")
    print("  4C cube colors:")
    for mid in missing_4c: 
        if mid not in inventory: 
            print(f"    {mid}: 6mm [color] round plastic pearl beads")
    
    # Save output as CSV
    output_path = input("\nEnter output path (or press Enter for RecipesComplete.csv): ").strip()
    if not output_path:
        output_path = 'RecipesComplete.csv'
    
    write_recipes_csv(all_recipes, output_path)
    
    print(f"\n✓ Saved to {output_path}")
    print(f"  Total recipes: {len(all_recipes)}")

if __name__ == '__main__':
    main()