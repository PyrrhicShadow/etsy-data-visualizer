#!/usr/bin/env python3
"""
Cost Calculator - Pyrrhic Silva Shop (v2)
Uses specific_units for all calculations.

Suffix parsing returns a normalized (category, length) pair instead of a
re-parsed string, so there's a single source of truth for what a SKU's
ending means -- no separate dictionaries that have to agree on casing.
"""

from skuVocab import FINDINGS, FINDINGS_LEN, TART_INFO
from skuParser import parse_sku
from shopIO import load_inventory, load_recipes
import difflib

PACKAGING_RULES = {
    **{code: info['packaging'] for code, info in FINDINGS.items()},
    'TART': TART_INFO['packaging'],
    None: ('bag', 1),
}

SUFFIX_MULTIPLIERS = {
    **{code: {'charm': info['charm_mult'], 'finding': info['finding_mult']}
       for code, info in FINDINGS.items()},
    'NK': {'charm': FINDINGS_LEN['NK']['charm_mult'], 'finding': FINDINGS_LEN['NK']['finding_mult']},
    'TART': {'charm': 2, 'finding': 0},
    None: {'charm': 1, 'finding': 0},
}

NOT_IMPLEMENTED_CATEGORIES = {'BRAC', 'BRAC-E'}

def calculate_material_cost(material_id, quantity, inventory):
    if material_id not in inventory:
        print(f"  \u26a0\ufe0f Warning: Material {material_id} not found in inventory")
        return 0.0, None

    mat = inventory[material_id]
    divisor = mat['specific_units']

    if divisor <= 0:
        print(f"  \u26a0\ufe0f Warning: Zero units for material {material_id}")
        return 0.0, mat

    cost_per_unit = mat['price'] / divisor
    return cost_per_unit * quantity, mat


def calculate_chain_cost(length_inches, inventory):
    """Cost of `length_inches` of necklace chain (material 0300), which is
    sold as a single spool rather than discrete countable pieces -- so this
    bypasses calculate_material_cost's price/specific_units*qty formula and
    prices the chain purely by length instead."""
    if '0300' not in inventory:
        return 0.0, None

    chain_mat = inventory['0300']
    spool_feet = chain_mat['specific_units']
    total_inches = spool_feet * 12

    if total_inches <= 0:
        return 0.0, chain_mat

    cost_per_inch = chain_mat['price'] / total_inches
    return cost_per_inch * length_inches, chain_mat


def suggest_recipe_keys(base_sku, recipes, n=5):
    return difflib.get_close_matches(base_sku, recipes.keys(), n=n, cutoff=0.5)


def material_label(material_id, mat):
    """Human-readable 'ID (name)' label for breakdown lines, falling back
    gracefully if the material isn't in inventory."""
    if mat and mat.get('name'):
        return f"{material_id} ({mat['name']})"
    return f"{material_id} (unknown material)"


def calculate_packaging_cost(pkg_key, pkg_qty, inventory, recipes):
    """Packaging labels ('ear-card', 'chain-card', 'bag') are recipe keys,
    not material IDs -- e.g. 'ear-card' resolves to 1x material 0901 via
    RecipesData.csv. Resolve through the recipe, then price the actual
    material(s), same as charms and findings."""
    if pkg_key not in recipes:
        print(f"  \u26a0\ufe0f Warning: Packaging recipe '{pkg_key}' not found")
        return 0.0, []

    total = 0.0
    items = []
    for mat_id, base_qty in recipes[pkg_key].items():
        cost, mat = calculate_material_cost(mat_id, base_qty * pkg_qty, inventory)
        total += cost
        items.append({
            'category': 'packaging', 'material_id': mat_id,
            'material_label': material_label(mat_id, mat),
            'quantity': base_qty * pkg_qty, 'cost': round(cost, 4),
        })
    return total, items


def calculate_cost(sku, inventory, recipes):
    sku_original = sku.strip()

    result = {
        'sku': sku_original, 'category': None, 'length': None,
        'charm_cost': 0.0, 'finding_cost': 0.0, 'combined_finding_cost': 0.0,
        'packaging_cost': 0.0, 'total_cost': 0.0, 'breakdown': [],
    }

    parsed = parse_sku(sku_original)
    if parsed.get('error'):
        result['error'] = parsed['error']
        return result

    category = parsed['category']
    length = parsed['length']
    base_sku = parsed['base_sku']
    result['category'] = category
    result['length'] = length

    if category == 'TART':
        tart_n = parsed['tart_n']
        if 'tart' not in recipes:
            result['error'] = "No recipe found for 'tart'"
            return result
        materials = recipes['tart']
        charm_mult = SUFFIX_MULTIPLIERS['TART']['charm']
        total = 0.0
        for mat_id, qty in materials.items():
            qty_mult = qty * charm_mult if tart_n == 2 else qty
            cost, mat = calculate_material_cost(mat_id, qty_mult, inventory)
            total += cost
            result['breakdown'].append({
                'category': 'charm', 'material_id': mat_id,
                'material_label': material_label(mat_id, mat),
                'quantity': qty_mult, 'cost': round(cost, 4),
            })
        pkg_key, pkg_qty = PACKAGING_RULES['TART']
        pkg_cost, pkg_items = calculate_packaging_cost(pkg_key, pkg_qty, inventory, recipes)
        total += pkg_cost
        result['breakdown'].extend(pkg_items)
        result['charm_cost'] = round(total - pkg_cost, 4)
        result['packaging_cost'] = round(pkg_cost, 4)
        result['total_cost'] = round(total, 4)
        return result

    if category is None:
        if parsed.get('is_standalone'):
            if base_sku not in recipes:
                result['error'] = f"No recipe found for '{base_sku}'"
                return result
            total = 0.0
            for mat_id, qty in recipes[base_sku].items():
                cost, mat = calculate_material_cost(mat_id, qty, inventory)
                total += cost
                result['breakdown'].append({
                    'category': 'charm', 'material_id': mat_id,
                    'material_label': material_label(mat_id, mat),
                    'quantity': qty, 'cost': round(cost, 4),
                })
            pkg_key, pkg_qty = PACKAGING_RULES[None]
            pkg_cost, pkg_items = calculate_packaging_cost(pkg_key, pkg_qty, inventory, recipes)
            total += pkg_cost
            result['breakdown'].extend(pkg_items)
            result['charm_cost'] = round(total - pkg_cost, 4)
            result['packaging_cost'] = round(pkg_cost, 4)
            result['total_cost'] = round(total, 4)
            return result
        result['error'] = (
            f"Could not recognize a suffix on '{sku_original}'. Expected one of: "
            f"{', '.join(FINDINGS.keys())}, NK[n], BRAC[n], BRAC-e[n], or TART-1/TART-2."
        )
        return result

    if category in NOT_IMPLEMENTED_CATEGORIES:
        result['not_implemented'] = True
        result['message'] = (
            f"Bracelet costing ({category}) isn't implemented yet -- "
            f"'{sku_original}' was not calculated."
        )
        return result

    if base_sku not in recipes:
        suggestions = suggest_recipe_keys(base_sku, recipes)
        result['error'] = f"No recipe found for base SKU: {base_sku}"
        if suggestions:
            result['error'] += f" (closest matches: {', '.join(suggestions)})"
        return result

    charm_recipe = recipes[base_sku]
    multipliers = SUFFIX_MULTIPLIERS.get(category, SUFFIX_MULTIPLIERS[None])
    if parsed['prefix'] == 'AETHER':
        multipliers = {'charm': 1, 'finding': 1}

    charm_multiplier = multipliers['charm']
    finding_multiplier = multipliers['finding']

    for mat_id, qty in charm_recipe.items():
        cost, mat = calculate_material_cost(mat_id, qty * charm_multiplier, inventory)
        result['charm_cost'] += cost
        result['breakdown'].append({
            'category': 'charm', 'material_id': mat_id,
            'material_label': material_label(mat_id, mat),
            'quantity': qty * charm_multiplier, 'cost': round(cost, 4),
        })

    finding_total = 0.0
    chain_cost = 0.0

    if category == 'NK':
        if 'nk0' in recipes:
            for mat_id, qty in recipes['nk0'].items():
                cost, mat = calculate_material_cost(mat_id, qty * finding_multiplier, inventory)
                finding_total += cost
                result['breakdown'].append({
                    'category': 'finding', 'material_id': mat_id,
                    'material_label': material_label(mat_id, mat),
                    'quantity': qty * finding_multiplier, 'cost': round(cost, 4),
                })
        if length and length > 0:
            if 'nk[n]' in recipes:
                for mat_id, qty in recipes['nk[n]'].items():
                    cost, mat = calculate_material_cost(mat_id, qty * finding_multiplier, inventory)
                    finding_total += cost
                    result['breakdown'].append({
                        'category': 'finding', 'material_id': mat_id,
                        'material_label': material_label(mat_id, mat),
                        'quantity': qty * finding_multiplier, 'cost': round(cost, 4),
                    })
            chain_cost, chain_mat = calculate_chain_cost(length, inventory)
            if chain_mat:
                result['breakdown'].append({
                    'category': 'finding', 'material_id': '0300',
                    'material_label': material_label('0300', chain_mat),
                    'quantity': f"{length} in", 'cost': round(chain_cost, 4),
                    'note': f'{length}-inch chain',
                })
        packaging_rule = FINDINGS_LEN['NK']['packaging']['nonzero'] if length else FINDINGS_LEN['NK']['packaging']['zero']
    else:
        finding_recipe_key = category.lower()
        if finding_recipe_key in recipes:
            for mat_id, qty in recipes[finding_recipe_key].items():
                cost, mat = calculate_material_cost(mat_id, qty * finding_multiplier, inventory)
                finding_total += cost
                result['breakdown'].append({
                    'category': 'finding', 'material_id': mat_id,
                    'material_label': material_label(mat_id, mat),
                    'quantity': qty * finding_multiplier, 'cost': round(cost, 4),
                })
        packaging_rule = PACKAGING_RULES.get(category, PACKAGING_RULES[None])

    result['finding_cost'] = round(finding_total, 4)
    result['combined_finding_cost'] = round(finding_total + chain_cost, 4)

    pkg_key, pkg_qty = packaging_rule
    pkg_cost, pkg_items = calculate_packaging_cost(pkg_key, pkg_qty, inventory, recipes)
    result['packaging_cost'] = round(pkg_cost, 4)
    result['breakdown'].extend(pkg_items)

    result['charm_cost'] = round(result['charm_cost'], 4)
    result['total_cost'] = round(
        result['charm_cost'] + result['combined_finding_cost'] + result['packaging_cost'], 4
    )
    return result


def format_output(result):
    if 'error' in result:
        return f"\n\u274c Error: {result['error']}\n"

    if result.get('not_implemented'):
        return f"\n\u26a0\ufe0f {result['message']}\n"

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
        label = item.get('material_label', item['material_id'])
        cost = item['cost']
        note = f"  [{item.get('note', '')}]" if item.get('note') else ""
        lines.append(f"  \u2022 {label}: {qty_str} @ ${cost:.4f}{note}")

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

    print("\nLoading inventory...")
    inventory = load_inventory(inv_path)
    print(f"  \u2713 {len(inventory)} materials loaded")

    print("Loading recipes...")
    recipes = load_recipes(rec_path)
    print(f"  \u2713 {len(recipes)} recipes loaded")

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