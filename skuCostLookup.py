#!/usr/bin/env python3
"""
Cost Calculator - Pyrrhic Silva Shop (v2)
Uses specific_units for all calculations.

Suffix parsing returns a normalized (category, length) pair instead of a
re-parsed string, so there's a single source of truth for what a SKU's
ending means -- no separate dictionaries that have to agree on casing.
"""

import csv
import re
import difflib

# Packaging by suffix category. NK is split into "charm on a bail" (length 0)
# and "actual chain" (length > 0) further down, since they ship differently.
PACKAGING_RULES = {
    'LV': ('ear-card', 1),
    'WR': ('ear-card', 1),
    'BP': ('ear-card', 1),
    'DK': ('ear-card', 1),
    'CH': ('bag', 1),
    'NK': ('chain-card', 1),
    'NK0': ('bag', 1),
    'TART': ('ear-card', 1),
    None: ('bag', 1),
}

# charm/finding quantity multipliers by suffix category.
# LV/WR/BP produce a pair of earrings, so charm+finding materials double.
# DK (Aether-style) and everything else is sold as a single piece.
SUFFIX_MULTIPLIERS = {
    'LV': {'charm': 2, 'finding': 2},
    'WR': {'charm': 2, 'finding': 2},
    'BP': {'charm': 2, 'finding': 2},
    'DK': {'charm': 1, 'finding': 1},
    'CH': {'charm': 1, 'finding': 1},
    'NK': {'charm': 1, 'finding': 1},
    'NK0': {'charm': 1, 'finding': 1},
    'TART': {'charm': 2, 'finding': 0},
    None: {'charm': 1, 'finding': 0},
}

# Suffix patterns, checked in order, against the lowercased SKU.
# BRAC-E must be checked before BRAC so "-brac-e6.5" doesn't get eaten by
# the plainer "-brac" pattern.
SUFFIX_PATTERNS = [
    ('LV', r'-lv$'),
    ('WR', r'-wr$'),
    ('BP', r'-bp$'),
    ('DK', r'-dk$'),
    ('CH', r'-ch(?:-[a-z]+)?$'),
    ('BRAC-E', r'-brac-e(\d+(?:\.\d+)?)$'),
    ('BRAC', r'-brac(\d+(?:\.\d+)?)$'),
    ('NK', r'-nk(\d+(?:\.\d+)?)$'),
]

NOT_IMPLEMENTED_CATEGORIES = {'BRAC', 'BRAC-E'}


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

            sku = parts[0].strip().lower()
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
    """Return {'category': str, 'length': float|int|None, 'start': int} or
    None if no known suffix pattern matches. 'start' is where the suffix
    begins in sku_lower, so the caller can slice off the base SKU."""
    if sku_lower.startswith('tart-'):
        return {'category': 'TART', 'length': None, 'start': 0}

    for category, pattern in SUFFIX_PATTERNS:
        match = re.search(pattern, sku_lower)
        if match:
            length = None
            if match.groups():
                raw = match.group(1)
                length = float(raw) if '.' in raw else int(raw)
            return {'category': category, 'length': length, 'start': match.start()}

    return None


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
        cost, _ = calculate_material_cost(mat_id, base_qty * pkg_qty, inventory)
        total += cost
        items.append({
            'category': 'packaging', 'material_id': mat_id,
            'quantity': base_qty * pkg_qty, 'cost': round(cost, 4),
        })
    return total, items


def calculate_cost(sku, inventory, recipes):
    sku_original = sku.strip()
    sku_lower = sku_original.lower()

    result = {
        'sku': sku_original,
        'category': None,
        'length': None,
        'charm_cost': 0.0,
        'finding_cost': 0.0,
        'combined_finding_cost': 0.0,  # finding + chain
        'packaging_cost': 0.0,
        'total_cost': 0.0,
        'breakdown': [],
    }

    parsed = parse_suffix(sku_lower)

    if parsed is None:
        result['error'] = (
            f"Could not recognize a suffix on '{sku_original}'. "
            "Expected one of: LV, WR, BP, DK, CH, NK[n], BRAC[n], "
            "BRAC-e[n], or TART-1/TART-2."
        )
        return result

    category = parsed['category']
    length = parsed['length']
    result['category'] = category
    result['length'] = length

    # -- TART is a fully separate recipe shape (single vs. pair), unrelated
    #    to the charm-recipe-lookup flow everything else uses.
    if category == 'TART':
        tart_num = 2 if sku_lower.endswith('-2') else 1
        recipe_key = 'tart'

        if recipe_key not in recipes:
            result['error'] = f"No recipe found for '{recipe_key}'"
            return result

        materials = recipes[recipe_key]
        charm_mult = SUFFIX_MULTIPLIERS['TART']['charm']
        total = 0.0

        for mat_id, qty in materials.items():
            qty_multiplied = qty * charm_mult if tart_num == 2 else qty
            cost, _ = calculate_material_cost(mat_id, qty_multiplied, inventory)
            total += cost
            result['breakdown'].append({
                'category': 'charm', 'material_id': mat_id,
                'quantity': qty_multiplied, 'cost': round(cost, 4),
            })

        pkg_key, pkg_qty = PACKAGING_RULES['TART']
        pkg_cost, pkg_items = calculate_packaging_cost(pkg_key, pkg_qty, inventory, recipes)
        total += pkg_cost
        result['breakdown'].extend(pkg_items)

        result['charm_cost'] = round(total - pkg_cost, 4)
        result['packaging_cost'] = round(pkg_cost, 4)
        result['total_cost'] = round(total, 4)
        return result

    # -- Bracelets: acknowledged as not yet implemented rather than
    #    silently returning $0.
    if category in NOT_IMPLEMENTED_CATEGORIES:
        result['not_implemented'] = True
        result['message'] = (
            f"Bracelet costing ({category}) isn't implemented yet -- "
            f"'{sku_original}' was not calculated."
        )
        return result

    # -- Everything else: strip the suffix off to find the base charm recipe.
    base_sku = sku_lower[:parsed['start']]

    if base_sku not in recipes:
        suggestions = suggest_recipe_keys(base_sku, recipes)
        result['error'] = f"No recipe found for base SKU: {base_sku}"
        if suggestions:
            result['error'] += f" (closest matches: {', '.join(suggestions)})"
        return result

    charm_recipe = recipes[base_sku]
    multipliers = SUFFIX_MULTIPLIERS.get(category, SUFFIX_MULTIPLIERS[None])
    charm_multiplier = multipliers['charm']
    finding_multiplier = multipliers['finding']

    for mat_id, qty in charm_recipe.items():
        cost, _ = calculate_material_cost(mat_id, qty * charm_multiplier, inventory)
        result['charm_cost'] += cost
        result['breakdown'].append({
            'category': 'charm', 'material_id': mat_id,
            'quantity': qty * charm_multiplier, 'cost': round(cost, 4),
        })

    finding_total = 0.0
    chain_cost = 0.0

    if category == 'NK':
        # Every necklace -- charm-on-a-bail or full chain -- uses the bail
        # from the 'nk0' recipe.
        if 'nk0' in recipes:
            for mat_id, qty in recipes['nk0'].items():
                cost, _ = calculate_material_cost(mat_id, qty * finding_multiplier, inventory)
                finding_total += cost
                result['breakdown'].append({
                    'category': 'finding', 'material_id': mat_id,
                    'quantity': qty * finding_multiplier, 'cost': round(cost, 4),
                })

        # A real chain length additionally needs the jump rings + clasp
        # ('nk[n]' recipe, a template -- not looked up by literal length)
        # and the physical chain cost.
        if length and length > 0:
            if 'nk[n]' in recipes:
                for mat_id, qty in recipes['nk[n]'].items():
                    cost, _ = calculate_material_cost(mat_id, qty * finding_multiplier, inventory)
                    finding_total += cost
                    result['breakdown'].append({
                        'category': 'finding', 'material_id': mat_id,
                        'quantity': qty * finding_multiplier, 'cost': round(cost, 4),
                    })

            chain_cost, chain_mat = calculate_chain_cost(length, inventory)
            if chain_mat:
                result['breakdown'].append({
                    'category': 'finding', 'material_id': '0300',
                    'quantity': f"{length} in", 'cost': round(chain_cost, 4),
                    'note': f'{length}-inch chain',
                })

        packaging_rule = PACKAGING_RULES['NK'] if length else PACKAGING_RULES['NK0']

    else:
        # LV, WR, BP, DK, CH: finding recipe is keyed by the lowercase
        # category itself.
        finding_recipe_key = category.lower()
        if finding_recipe_key in recipes:
            for mat_id, qty in recipes[finding_recipe_key].items():
                cost, _ = calculate_material_cost(mat_id, qty * finding_multiplier, inventory)
                finding_total += cost
                result['breakdown'].append({
                    'category': 'finding', 'material_id': mat_id,
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
        mat_id = item['material_id']
        cost = item['cost']
        note = f"  [{item.get('note', '')}]" if item.get('note') else ""
        lines.append(f"  \u2022 {mat_id}: {qty_str} @ ${cost:.4f}{note}")

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
