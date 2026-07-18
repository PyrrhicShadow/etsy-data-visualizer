#!/usr/bin/env python3
"""
Recipe Generator for Pyrrhic Silva Shop
Translates 4B pride flag recipes to 6P and 8R equivalents
"""

import csv
import json

# == COLOR MAPPING ==
# 4B ID -> (6P pearl ID, 8R jelly ID)
# 6P IDs follow same numbering as 4B but in 14XX range
# 8R IDs follow same numbering in 12XX range
COLOR_MAP = {
    '1101': ('1401', '1201'),  # red
    '1102': ('1402', '1202'),  # orange
    '1103': ('1403', '1203'),  # yellow
    '1104': ('1404', '1204'),  # green
    '1105': ('1405', '1205'),  # cyan / sky blue
    '1106': ('1406', '1206'),  # blue
    '1107': ('1407', '1207'),  # purple
    '1108': ('1408', '1208'),  # white
    '1109': ('1409', '1209'),  # gray
    '1110': ('1410', '1210'),  # black
    '1111': ('1411', '1211'),  # pink (1411 already exists!)
    '1112': ('1412', '1212'),  # magenta
    '1113': ('1413', '1213'),  # light green
    '1114': ('1414', '1214'),  # light purple
    '1115': ('1415', '1215'),  # brown
}

# Charm replacements per bead type
# 4B uses 0500 (8mm star), 8R uses 0503 (13mm hollow star)
# 6P keeps 0500 for now — adjust manually if needed
CHARM_MAP = {
    '6p': {'0500': '0500'},  # Keep star (manual override later if needed)
    '8r': {'0500': '0503'},  # Hollow star
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
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mat_id = row['material id'].strip()
            inventory[mat_id] = {
                'name': row['material name'].strip(),
                'price': float(row['price']),
                'total_units': int(row['total units']),
                'specific_units': int(row['specific units']),
            }
    return inventory

def load_recipes(filename):
    """Load recipes from CSV, handling variable-length rows."""
    recipes = {}
    with open(filename, 'r') as f:
        for line in f:
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
    """Translate a 4B recipe to 6P or 8R."""
    translated = {}
    
    for mat_id, qty in recipe.items():
        # Color beads: translate from 11XX to 14XX or 12XX
        if mat_id.startswith('11') and mat_id in color_map:
            idx = 0 if target_type == '6p' else 1
            new_id = color_map[mat_id][idx]
            
            if new_id is None:
                print(f"  ⚠️ No {target_type.upper()} equivalent for color {mat_id}")
                continue
            
            # Aggregate if same ID already exists
            if new_id in translated:
                translated[new_id] += qty
            else:
                translated[new_id] = qty
        
        # Charm replacements
        elif mat_id in charm_map.get(target_type, {}):
            new_charm = charm_map[target_type][mat_id]
            translated[new_charm] = qty
        
        # Preserve everything else
        elif mat_id in PRESERVE_IDS:
            translated[mat_id] = qty
        
        # Unknown material — pass through with warning
        else:
            print(f"  ⚠️ Unknown material {mat_id} in recipe, passing through")
            translated[mat_id] = qty
    
    return translated

def generate_recipes(recipes):
    """Generate 6P and 8R recipes from 4B pride flag recipes."""
    output = {}
    warnings = []
    
    # Find all 4B pride flag recipes (sku starts with "4b-" and has a flag name)
    pride_skus = [sku for sku in recipes if sku.startswith('4b-')]
    
    for sku in pride_skus:
        recipe = recipes[sku]
        flag_name = sku[3:]  # Strip "4b-" prefix
        
        for target in ['6p', '8r']:
            new_sku = f"{target}-{flag_name}"
            translated = translate_recipe(recipe, target, COLOR_MAP, CHARM_MAP)
            output[new_sku] = translated
            
            if not translated:
                warnings.append(f"{new_sku}: empty recipe")
    
    # Copy through all non-4B recipes (aether, seasons, howls, etc.)
    for sku, recipe in recipes.items():
        if not sku.startswith('4b-'):
            output[sku] = recipe
    
    return output, warnings

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
    print("\nGenerating 6P and 8R recipes...")
    all_recipes, warnings = generate_recipes(recipes)
    
    new_count = len(all_recipes) - len(recipes)
    print(f"  ✓ {new_count} new recipes generated")
    
    # Show summary
    print("\n" + "-" * 40)
    for target in ['6p', '8r']:
        count = len([r for r in all_recipes if r.startswith(f'{target}-')])
        print(f"  {target.upper()}: {count} recipes")
    
    # Warnings
    if warnings:
        print(f"\n⚠️ {len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")
    
    # Check for 8R colors that don't exist in inventory yet
    missing_8r = ['1201', '1212', '1214', '1215']
    missing_6p = ['1401', '1402', '1403', '1404', '1405', '1406', 
                   '1407', '1408', '1409', '1410', '1412', '1413', '1414', '1415']
    
    print("\n📋 Materials to add to InventoryData.csv:")
    print("  6P pearl colors (point to box price for now):")
    for mid in missing_6p:
        if mid not in inventory:
            print(f"    {mid}: 6mm [color] pearl glass beads (from box 1420)")
    print("  8R jelly colors:")
    for mid in missing_8r:
        if mid not in inventory:
            print(f"    {mid}: 8mm [color] round jelly glass beads")
    
    # Save output
    output = {
        'inventory': inventory,
        'recipes': all_recipes,
    }
    
    output_file = 'RecipesComplete.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2, sort_keys=True)
    
    print(f"\n✓ Saved to {output_file}")
    print(f"  Total recipes: {len(all_recipes)}")

if __name__ == '__main__':
    main()