#!/usr/bin/env python3
"""
Cost Calculator - Pyrrhic Silva Shop
Input SKU → Output total/charm/finding/packaging cost breakdown
Uses specific_units for all material cost calculations.
"""

import csv
import re
from collections import defaultdict

# == PACKAGING RULES ==
# Each suffix maps to ONE packaging type (card OR bag), not both
PACKAGING_RULES = {
    'LV': ('earcard', 1),   # Leverback earrings
    'WR': ('earcard', 1),   # Fish hook earrings
    'BP': ('earcard', 1),   # Ball post studs
    'DK': ('earcard', 1),   # Disk stud (Aether)
    'NK': ('chaincard', 1), # Necklace with chain
    'NK0': ('bag', 1),       # Charm only, no chain
    'BRAC': ('chaincard', 1), # Chain bracelet/choker
    'BRAC-e': ('chaincard', 1), # Elastic bracelet
    'CH': ('bag', 1),        # Phone charm
    'TART': ('earcard', 1), # TART-1 or TART-2
    None: ('bag', 1),        # Default fallback
}

# == SUFFIX MULTIPLIERS ==
# Charm and finding quantities per suffix type
SUFFIX_MULTIPLIERS = {
    'LV': {'charm': 2, 'finding': 2},
    'WR': {'charm': 2, 'finding': 2},
    'BP': {'charm': 2, 'finding': 2},
    'DK': {'charm': 1, 'finding': 1},  # Aether single earring
    'NK': {'charm': 1, 'finding': 1},
    'NK0': {'charm': 1, 'finding': 1},
    'BRAC': {'charm': 1, 'finding': 1},
    'BRAC-e': {'charm': 1, 'finding': 1},
    'CH': {'charm': 1, 'finding': 1},
    'TART': {'charm': 2, 'finding': 0},  # TART-2 is pair, TART-1 handled separately
    None: {'charm': 1, 'finding': 0},
}

def load_inventory(filename):
    """Load inventory with specific_units."""
    inventory = {}
    with open(filename, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mat_id = row['material id'].strip()
            inventory[mat_id] = {
                'name': row['material name'].strip(),
                'price': float(row['price']),
                'specific_units': int(row['specific units']),
            }
    return inventory

def load_recipes(filename):
    """Load recipes from CSV."""
    recipes = {}
    with open(filename, 'r', encoding='utf-8-sig') as f:
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
            
            recipes[sku] = materials
    
    return recipes

def parse_suffix(sku_upper):
    """Extract suffix from SKU for packaging/multiplier lookup."""
    # Find patterns: LV, WR, BP, DK, NK[n], NK0, BRAC[n], BRAC-e[n], CH, TART
    patterns = [
        (r'^[^-]+-[^-]+-(LV|WR|BP|DK)$', lambda m: m.group(1)),
        (r'^([^-]+-[^-]+-)NK(\d+)$', lambda m: f'NK{m.group(2)}'),
        (r'^[^-]+-[^-]+-(NK0)$', lambda m: m.group(1)),
        (r'^[^-]+-[^-]+-BRAC-e(\d+(?:\.\d+)?)$', lambda m: 'BRAC-e'),
        (r'^[^-]+-[^-]+-BRAC(\d+(?:\.\d+)?)$', lambda m: 'BRAC'),
        (r'^[^-]+-[^-]+-(CH)$', lambda m: m.group(1)),
        (r'^TART-[12]$', lambda m: 'TART'),
    ]
    
    for pattern, extractor in patterns:
        match = re.search(pattern, sku_upper)
        if match:
            result = extractor(match)
            return result
    return None

def calculate_material_cost(material_id, quantity, inventory, unit_type='specific'):
    """Calculate cost for a single material."""
    if material_id not in inventory:
        print(f"  ⚠️ Warning: Material {material_id} not found in inventory")
        return 0.0
    
    mat = inventory[material_id]
    divisor = mat['specific_units'] if unit_type == 'specific' else mat['total_units']
    
    if divisor <= 0:
        print(f"  ⚠️ Warning: Zero units for material {material_id}")
        return 0.0
    
    cost_per_unit = mat['price'] / divisor
    return cost_per_unit * quantity

def calculate_chain_cost(length_inches, inventory, unit_type='specific'):
    """Calculate chain cost prorated by length.
    Chain material 0300 is 36 feet = 432 inches at full price."""
    if '0300' not in inventory:
        return 0.0
    
    chain_mat = inventory['0300']
    total_inches = 36 * 12  # 432 inches
    divisor = chain_mat['specific_units'] if unit_type == 'specific' else chain_mat['total_units']
    
    if divisor <= 0:
        return 0.0
    
    # Cost per inch = (price / specific_units) / total_inches
    cost_per_inch = (chain_mat['price'] / divisor) / total_inches
    return cost_per_inch * length_inches

def calculate_cost(sku, inventory, recipes):
    """Calculate complete cost breakdown for an SKU."""
    sku_upper = sku.strip().upper()
    
    result = {
        'sku': sku,
        'suffix': None,
        'charm_cost': 0.0,
        'finding_cost': 0.0,
        'chain_cost': 0.0,
        'packaging_cost': 0.0,
        'total_cost': 0.0,
        'breakdown': [],
    }
    
    # 1. Parse suffix for packaging/multiplier rules
    suffix = parse_suffix(sku_upper)
    result['suffix'] = suffix
    result['packaging_rule'] = PACKAGING_RULES.get(suffix, PACKAGING_RULES[None])
    result['multipliers'] = SUFFIX_MULTIPLIERS.get(suffix, SUFFIX_MULTIPLIERS[None])
    
    # 2. Handle TART specially (has its own recipe)
    if suffix == 'TART':
        tart_num = 2 if '-2' in sku_upper else 1
        result['tarts_single_pair'] = 'single' if tart_num == 1 else 'pair'
        recipe_key = 'tart'
        
        if recipe_key not in recipes:
            result['error'] = f"No recipe found for {recipe_key}"
            return result
        
        materials = recipes[recipe_key]
        total = 0
        for mat_id, qty in materials.items():
            # For pair, double all materials
            qty_multiplied = qty * result['multipliers']['charm'] if tart_num == 2 else qty
            cost = calculate_material_cost(mat_id, qty_multiplied, inventory)
            total += cost
            result['breakdown'].append({
                'category': 'charm',
                'material_id': mat_id,
                'quantity': qty_multiplied,
                'cost': round(cost, 4),
            })
        
        # Packaging for TART
        pkg_id, pkg_qty = result['packaging_rule']
        pkg_cost = calculate_material_cost(pkg_id, pkg_qty, inventory)
        total += pkg_cost
        result['breakdown'].append({
            'category': 'packaging',
            'material_id': pkg_id,
            'quantity': pkg_qty,
            'cost': round(pkg_cost, 4),
        })
        
        result['charm_cost'] = total - pkg_cost
        result['packaging_cost'] = pkg_cost
        result['total_cost'] = total
        return result
    
    # 3. For regular SKUs, extract charm recipe from the main portion
    # Find matching recipe (remove suffix to get base charm recipe)
    base_sku = sku_upper
    for suffix_pattern in ['-LV', '-WR', '-BP', '-DK', '-NK', '-NK0', '-BRAC', '-BRAC-e', '-CH']:
        if base_sku.endswith(suffix_pattern):
            base_sku = base_sku[:-len(suffix_pattern)].rstrip('-')
            break
    
    # Handle NK[n] patterns
    nk_match = re.match(r'^(.+-[^-]+)-NK(\d+)$', base_sku)
    if nk_match:
        base_sku = nk_match.group(1)
    
    if base_sku not in recipes:
        result['error'] = f"No recipe found for base SKU: {base_sku}"
        return result
    
    charm_recipe = recipes[base_sku]
    
    # 4. Calculate charm cost (apply multiplier for earrings)
    charm_multiplier = result['multipliers']['charm']
    for mat_id, qty in charm_recipe.items():
        cost = calculate_material_cost(mat_id, qty * charm_multiplier, inventory)
        result['charm_cost'] += cost
        result['breakdown'].append({
            'category': 'charm',
            'material_id': mat_id,
            'quantity': qty * charm_multiplier,
            'cost': round(cost, 4),
        })
    
    # 5. Add chain cost for necklaces (NK[n] where n > 0)
    if suffix and suffix.startswith('NK'):
        try:
            length = int(suffix[2:])
            if length > 0:
                chain_cost = calculate_chain_cost(length, inventory)
                
                # Add chain to breakdown
                chain_mat_id = '0300'
                chain_mat = inventory.get(chain_mat_id)
                if chain_mat:
                    total_inches = 36 * 12  # 432 inches
                    cost_per_inch = (chain_mat['price'] / chain_mat['specific_units']) / total_inches
                    effective_qty = length / total_inches
                    
                    result['chain_cost'] = chain_cost
                    result['breakdown'].append({
                        'category': 'finding',
                        'material_id': chain_mat_id,
                        'quantity': f"{effective_qty:.4f} of spool",
                        'cost': round(chain_cost, 4),
                        'note': f'{length}-inch chain from 36ft spool',
                    })
        except ValueError:
            pass  # NK0 has no chain
    
    # 6. Calculate finding cost (jump rings, bails, closures)
    finding_recipe_key = suffix.lower() if suffix else None
    if finding_recipe_key and finding_recipe_key in recipes:
        finding_recipe = recipes[finding_recipe_key]
        finding_multiplier = result['multipliers']['finding']
        
        for mat_id, qty in finding_recipe.items():
            cost = calculate_material_cost(mat_id, qty * finding_multiplier, inventory)
            result['finding_cost'] += cost
            result['breakdown'].append({
                'category': 'finding',
                'material_id': mat_id,
                'quantity': qty * finding_multiplier,
                'cost': round(cost, 4),
            })
    
    # 7. Calculate packaging cost
    pkg_id, pkg_qty = result['packaging_rule']
    pkg_cost = calculate_material_cost(pkg_id, pkg_qty, inventory)
    result['packaging_cost'] = pkg_cost
    result['breakdown'].append({
        'category': 'packaging',
        'material_id': pkg_id,
        'quantity': pkg_qty,
        'cost': round(pkg_cost, 4),
    })
    
    # 8. Sum totals
    result['total_cost'] = (
        result['charm_cost'] +
        result['finding_cost'] +
        result['chain_cost'] +
        result['packaging_cost']
    )
    
    # Round all costs to 4 decimals
    result['charm_cost'] = round(result['charm_cost'], 4)
    result['finding_cost'] = round(result['finding_cost'], 4)
    result['chain_cost'] = round(result['chain_cost'], 4)
    result['packaging_cost'] = round(result['packaging_cost'], 4)
    result['total_cost'] = round(result['total_cost'], 4)
    
    return result

def format_output(result):
    """Format cost breakdown for display."""
    if 'error' in result:
        return f"\n❌ Error: {result['error']}\n"
    
    lines = [
        "=" * 60,
        f"SKU: {result['sku']}",
        "-" * 40,
        f"Charm Cost:       ${result['charm_cost']:.4f}",
        f"Finding Cost:     ${result['finding_cost']:.4f}",
        f"Chain Cost:       ${result['chain_cost']:.4f}",
        f"Packaging Cost:   ${result['packaging_cost']:.4f}",
        "-" * 40,
        f"TOTAL COST:       ${result['total_cost']:.4f}",
        "=" * 60,
        "",
        "Breakdown:",
    ]
    
    for item in result['breakdown']:
        qty_str = str(item['quantity'])
        mat_id = item['material_id']
        cost = item['cost']
        note = f"  [{item.get('note', '')}]" if item.get('note') else ""
        lines.append(f"  • {mat_id}: {qty_str} @ ${cost:.4f}{note}")
    
    lines.append("")
    return "\n".join(lines)

def main():
    print("=" * 60)
    print("COST CALCULATOR - Pyrrhic Silva Shop")
    print("(Uses specific_units for all calculations)")
    print("=" * 60)
    
    # Load data
    inv_path = input("\nEnter path to InventoryData CSV (or Enter for InventoryData.csv): ").strip()
    if not inv_path:
        inv_path = 'InventoryData.csv'
    
    rec_path = input("Enter path to RecipesData CSV (or Enter for RecipesData.csv): ").strip()
    if not rec_path:
        rec_path = 'RecipesData.csv'
    
    print(f"\nLoading inventory...")
    inventory = load_inventory(inv_path)
    print(f"  ✓ {len(inventory)} materials loaded")
    
    print("Loading recipes...")
    recipes = load_recipes(rec_path)
    print(f"  ✓ {len(recipes)} recipes loaded")
    
    # Interactive mode
    print("\nEnter a SKU (or 'quit' to exit):\n")
    
    while True:
        user_input = input(">>> ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\nGoodbye!\n")
            break
        
        if not user_input:
            continue
        
        result = calculate_cost(user_input, inventory, recipes)
        print(format_output(result))

if __name__ == '__main__':
    main()