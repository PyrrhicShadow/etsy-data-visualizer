#!/usr/bin/env python3
"""
Cost Calculator - Pyrrhic Silva Shop (Fixed Version)
Uses specific_units for all calculations.
"""

import csv
import re
from collections import defaultdict

PACKAGING_RULES = {
    'LV': ('ear-card', 1),
    'WR': ('ear-card', 1),
    'BP': ('ear-card', 1),
    'DK': ('ear-card', 1),
    'NK': ('chain-card', 1),
    'NK0': ('bag', 1),
    'BRAC': ('chain-card', 1),
    'BRAC-e': ('chain-card', 1),
    'CH': ('bag', 1),
    'TART': ('ear-card', 1),
    None: ('bag', 1),
}

SUFFIX_MULTIPLIERS = {
    'LV': {'charm': 2, 'finding': 2},
    'WR': {'charm': 2, 'finding': 2},
    'BP': {'charm': 2, 'finding': 2},
    'DK': {'charm': 1, 'finding': 1},
    'NK': {'charm': 1, 'finding': 1},
    'NK0': {'charm': 1, 'finding': 1},
    'BRAC': {'charm': 1, 'finding': 1},
    'BRAC-e': {'charm': 1, 'finding': 1},
    'CH': {'charm': 1, 'finding': 1},
    'TART': {'charm': 2, 'finding': 0},
    None: {'charm': 1, 'finding': 0},
}

def load_inventory(filename):
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
    recipes = {}
    with open(filename, 'r', encoding='utf-8-sig') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) < 2:
                continue
            
            sku = parts[0].strip().lower()  # Lowercase recipes
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

def parse_suffix(sku_lower):
    """Extract suffix from SKU."""
    # Handle TART specially
    if sku_lower.startswith('tart-'):
        return 'TART'
    
    # Match known suffix patterns at the end of the SKU
    patterns = [
        r'-LV$',
        r'-WR$',
        r'-BP$',
        r'-DK$',
        r'-BK$',  # backup
        r'-NK(\d+)$',
        r'-NK0$',
        r'-BRAC-e(\d+(?:\.\d+)?)$',
        r'-BRAC(\d+(?:\.\d+)?)$',
        r'-CH$',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, sku_lower)
        if match:
            if pattern == r'-NK(\d+)$':
                length = match.group(1)
                if length == '0':
                    return 'NK0'
                return f'NK{length}'
            elif pattern == r'-BRAC-e(\d+(?:\.\d+)?)$':
                return 'BRAC-e'
            elif pattern == r'-BRAC(\d+(?:\.\d+)?)$':
                return 'BRAC'
            else:
                return match.group(0).strip('-')
    
    return None

def strip_suffix(sku_lower, suffix):
    """Remove suffix from SKU to get base recipe key."""
    if suffix == 'TART':
        return 'tart'  # TART recipe key is just 'tart'
    
    # Remove the suffix part from the end
    patterns = {
        'LV': r'-LV$',
        'WR': r'-WR$',
        'BP': r'-BP$',
        'DK': r'-DK$',
        'NK': r'-NK\d+$',
        'NK0': r'-NK0$',
        'BRAC': r'-BRAC\d+(?:\.\d+)?$',
        'BRAC-e': r'-BRAC-e\d+(?:\.\d+)?$',
        'CH': r'-CH$',
    }
    
    pattern = patterns.get(suffix, r'$')
    base = re.sub(pattern, '', sku_lower)
    return base

def calculate_material_cost(material_id, quantity, inventory):
    if material_id not in inventory:
        print(f"  ⚠️ Warning: Material {material_id} not found in inventory")
        return 0.0, None
    
    mat = inventory[material_id]
    divisor = mat['specific_units']
    
    if divisor <= 0:
        print(f"  ⚠️ Warning: Zero units for material {material_id}")
        return 0.0, mat
    
    cost_per_unit = mat['price'] / divisor
    return cost_per_unit * quantity, mat

def calculate_chain_cost(length_inches, inventory):
    if '0300' not in inventory:
        return 0.0, None
    
    chain_mat = inventory['0300']
    total_inches = 36 * 12  # 432 inches
    divisor = chain_mat['specific_units']
    
    if divisor <= 0:
        return 0.0, chain_mat
    
    cost_per_inch = (chain_mat['price'] / divisor) / total_inches
    return cost_per_inch * length_inches, chain_mat

def calculate_cost(sku, inventory, recipes):
    sku_original = sku.strip()
    sku_lower = sku_original.lower()
    
    result = {
        'sku': sku_original,
        'suffix': None,
        'charm_cost': 0.0,
        'finding_cost': 0.0,
        'combined_finding_cost': 0.0,  # finding + chain
        'packaging_cost': 0.0,
        'total_cost': 0.0,
        'breakdown': [],
    }
    
    # 1. Parse suffix
    suffix = parse_suffix(sku_lower)
    result['suffix'] = suffix
    result['packaging_rule'] = PACKAGING_RULES.get(suffix, PACKAGING_RULES[None])
    result['multipliers'] = SUFFIX_MULTIPLIERS.get(suffix, SUFFIX_MULTIPLIERS[None])
    
    # 2. Handle TART specially
    if suffix == 'TART':
        tart_num = 2 if '-2' in sku_lower else 1
        result['tart_single_pair'] = 'single' if tart_num == 1 else 'pair'
        recipe_key = 'tart'
        
        if recipe_key not in recipes:
            result['error'] = f"No recipe found for {recipe_key}"
            return result
        
        materials = recipes[recipe_key]
        charm_mult = result['multipliers']['charm']
        total = 0
        
        for mat_id, qty in materials.items():
            qty_multiplied = qty * charm_mult if tart_num == 2 else qty
            cost, mat = calculate_material_cost(mat_id, qty_multiplied, inventory)
            total += cost
            result['breakdown'].append({
                'category': 'charm',
                'material_id': mat_id,
                'quantity': qty_multiplied,
                'cost': round(cost, 4),
            })
        
        # Packaging
        pkg_id, pkg_qty = result['packaging_rule']
        pkg_cost, _ = calculate_material_cost(pkg_id, pkg_qty, inventory)
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
        result['combined_finding_cost'] = 0.0
        return result
    
    # 3. Strip suffix to get base recipe key
    base_sku = strip_suffix(sku_lower, suffix)
    
    if base_sku not in recipes:
        result['error'] = f"No recipe found for base SKU: {base_sku}. Tried: {base_sku}"
        result['available_base_skus'] = [r for r in recipes.keys() if not any(re.search(p, r) for p in ['-lv$', '-wr$', '-bp$', '-dk$', '-nk', '-brac', '-ch$'])]
        return result
    
    charm_recipe = recipes[base_sku]
    charm_multiplier = result['multipliers']['charm']
    
    # 4. Calculate charm cost
    for mat_id, qty in charm_recipe.items():
        cost, _ = calculate_material_cost(mat_id, qty * charm_multiplier, inventory)
        result['charm_cost'] += cost
        result['breakdown'].append({
            'category': 'charm',
            'material_id': mat_id,
            'quantity': qty * charm_multiplier,
            'cost': round(cost, 4),
        })
    
    # 5. Calculate chain cost (for necklaces with chain > 0)
    chain_cost = 0.0
    if suffix and suffix.startswith('NK'):
        try:
            length = int(suffix[2:])
            if length > 0:
                chain_cost, chain_mat = calculate_chain_cost(length, inventory)
                
                if chain_mat:
                    total_inches = 36 * 12
                    effective_qty = length / total_inches
                    result['breakdown'].append({
                        'category': 'finding',
                        'material_id': '0300',
                        'quantity': f"{effective_qty:.4f}",
                        'cost': round(chain_cost, 4),
                        'note': f'{length}-inch chain from 36ft spool',
                    })
        except ValueError:
            pass
    
    # 6. Add finding recipe cost (bail, jump rings, closures)
    finding_recipe_key = suffix.lower() if suffix else None
    finding_total = 0.0
    
    if finding_recipe_key and finding_recipe_key in recipes:
        finding_recipe = recipes[finding_recipe_key]
        finding_multiplier = result['multipliers']['finding']
        
        for mat_id, qty in finding_recipe.items():
            cost, _ = calculate_material_cost(mat_id, qty * finding_multiplier, inventory)
            finding_total += cost
            result['breakdown'].append({
                'category': 'finding',
                'material_id': mat_id,
                'quantity': qty * finding_multiplier,
                'cost': round(cost, 4),
            })
    
    result['finding_cost'] = finding_total
    result['combined_finding_cost'] = finding_total + chain_cost
    
    # 7. Packaging
    pkg_id, pkg_qty = result['packaging_rule']
    pkg_cost, _ = calculate_material_cost(pkg_id, pkg_qty, inventory)
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
        result['combined_finding_cost'] +
        result['packaging_cost']
    )
    
    # Round
    for k in ['charm_cost', 'finding_cost', 'combined_finding_cost', 'packaging_cost', 'total_cost']:
        result[k] = round(result[k], 4)
    
    return result

def format_output(result):
    if 'error' in result:
        msg = f"\n❌ Error: {result['error']}\n"
        if 'available_base_skus' in result:
            msg += f"Available base recipes: {', '.join(sorted(result['available_base_skus'])[:10])}\n"
        return msg
    
    lines = [
        "=" * 60,
        f"SKU: {result['sku']}",
        "-" * 40,
        f"Charm Cost:         ${result['charm_cost']:.4f}",
        f"Finding/Chain Cost: ${result['combined_finding_cost']:.4f}",
        f"Packaging Cost:     ${result['packaging_cost']:.4f}",
        "-" * 40,
        f"TOTAL COST:         ${result['total_cost']:.4f}",
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