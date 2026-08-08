#!/usr/bin/env python3
"""
Cost Calculator - Pyrrhic Silva Shop (v2)
Uses specific_units for all calculations.

Suffix parsing returns a normalized (category, length) pair instead of a
re-parsed string, so there's a single source of truth for what a SKU's
ending means -- no separate dictionaries that have to agree on casing.

GUI NOTE: calculate_cost() already returned a plain result dict (that
part of the original design was right). What it didn't do was collect
its own warnings -- material-lookup helpers used to print() directly,
which a GUI has no way to intercept. Those helpers now return warnings
as a list, calculate_cost() collects them into result['warnings'], and
format_output() (CLI-only) is the one place that turns everything,
warnings included, into printable text.

ADDED FOR addSale.py: calculate_envelope_cost() -- material 0900 is a
per-ORDER packaging cost (one envelope per order, regardless of how many
unique SKUs or units are in it), unlike every other packaging rule in
this module, which is per-SKU-line. It's kept as its own small function
rather than folded into calculate_packaging_cost() because that function
resolves packaging through a RECIPE key ('ear-card', 'bag', etc.), while
the envelope is a direct, fixed material lookup with no recipe involved.
"""

from skuVocab import FINDINGS, FINDINGS_LEN, DEFAULT_PACKAGING, TART_INFO
from skuParser import parse_sku
from shopIO import load_inventory, load_recipes
from cliPrompts import prompt_input, QuitRequested
import difflib
import shopFormatting

PACKAGING_RULES = {
    **{code: info['packaging'] for code, info in FINDINGS.items()},
    'TART': TART_INFO['packaging'],
    None: DEFAULT_PACKAGING,
}

SUFFIX_MULTIPLIERS = {
    **{code: {'charm': info['charm_mult'], 'finding': info['finding_mult']}
       for code, info in FINDINGS.items()},
    'NK': {'charm': 1, 'finding': 1},
    'TART': {'charm': 2, 'finding': 0},
    None: {'charm': 1, 'finding': 0},
}

NOT_IMPLEMENTED_CATEGORIES = {'BRAC', 'BRAC-E'}

ENVELOPE_MATERIAL_ID = '0900'


def calculate_material_cost(material_id, quantity, inventory):
    """Returns (cost, mat, warning). warning is None on success, or a
    plain string describing the problem -- never printed here."""
    if material_id not in inventory:
        return 0.0, None, f"Material {material_id} not found in inventory"

    mat = inventory[material_id]
    divisor = mat['specific_units']

    if divisor <= 0:
        return 0.0, mat, f"Zero units for material {material_id}"

    cost_per_unit = mat['price'] / divisor
    return cost_per_unit * quantity, mat, None


def calculate_envelope_cost(inventory):
    """Cost of ONE envelope (material 0900), charged once per ORDER
    regardless of unique SKU count or quantities sold within that order --
    this is the one packaging cost in the shop that is order-level rather
    than line-level. Callers (e.g. addSale.py) should call this exactly
    once per order and apply the result only to that order's first
    written row, matching the existing sales CSV's convention for other
    order-level fields (payment fee, transaction... no, shipping fee,
    sales tax, payment amount).

    Returns (cost, warning) -- same shape as calculate_material_cost()
    minus the `mat` dict, since callers here don't need material details,
    just the dollar amount and whether something went wrong.
    """
    cost, _mat, warning = calculate_material_cost(ENVELOPE_MATERIAL_ID, 1, inventory)
    return cost, warning


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
    material(s), same as charms and findings.

    Returns (total_cost, items, warnings)."""
    if pkg_key not in recipes:
        return 0.0, [], [f"Packaging recipe '{pkg_key}' not found"]

    total = 0.0
    items = []
    warnings = []
    for mat_id, base_qty in recipes[pkg_key].items():
        cost, mat, warning = calculate_material_cost(mat_id, base_qty * pkg_qty, inventory)
        total += cost
        if warning:
            warnings.append(warning)
        items.append({
            'category': 'packaging', 'material_id': mat_id,
            'material_label': material_label(mat_id, mat),
            'quantity': base_qty * pkg_qty, 'cost': round(cost, 4),
        })
    return total, items, warnings


def calculate_cost(sku, inventory, recipes):
    sku_original = sku.strip()

    result = {
        'sku': sku_original, 'canonical_sku': sku_original, 'category': None, 'length': None,
        'charm_cost': 0.0, 'finding_cost': 0.0, 'combined_finding_cost': 0.0,
        'packaging_cost': 0.0, 'total_cost': 0.0, 'breakdown': [], 'warnings': [],
    }

    parsed = parse_sku(sku_original)
    if parsed.get('error'):
        result['error'] = parsed['error']
        return result

    result['canonical_sku'] = parsed.get('canonical_sku', sku_original)

    if parsed.get('resolved_alias'):
        orig = parsed['resolved_alias']['original']
        canon = parsed['resolved_alias']['canonical']
        result['warnings'].append(
            f"'{orig}' is an alias; resolved to canonical design '{canon}'."
        )

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
            cost, mat, warning = calculate_material_cost(mat_id, qty_mult, inventory)
            total += cost
            if warning:
                result['warnings'].append(warning)
            result['breakdown'].append({
                'category': 'charm', 'material_id': mat_id,
                'material_label': material_label(mat_id, mat),
                'quantity': qty_mult, 'cost': round(cost, 4),
            })
        pkg_key, pkg_qty = PACKAGING_RULES['TART']
        pkg_cost, pkg_items, pkg_warnings = calculate_packaging_cost(pkg_key, pkg_qty, inventory, recipes)
        total += pkg_cost
        result['breakdown'].extend(pkg_items)
        result['warnings'].extend(pkg_warnings)
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
                cost, mat, warning = calculate_material_cost(mat_id, qty, inventory)
                total += cost
                if warning:
                    result['warnings'].append(warning)
                result['breakdown'].append({
                    'category': 'charm', 'material_id': mat_id,
                    'material_label': material_label(mat_id, mat),
                    'quantity': qty, 'cost': round(cost, 4),
                })
            pkg_key, pkg_qty = PACKAGING_RULES[None]
            pkg_cost, pkg_items, pkg_warnings = calculate_packaging_cost(pkg_key, pkg_qty, inventory, recipes)
            total += pkg_cost
            result['breakdown'].extend(pkg_items)
            result['warnings'].extend(pkg_warnings)
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
        cost, mat, warning = calculate_material_cost(mat_id, qty * charm_multiplier, inventory)
        result['charm_cost'] += cost
        if warning:
            result['warnings'].append(warning)
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
                cost, mat, warning = calculate_material_cost(mat_id, qty * finding_multiplier, inventory)
                finding_total += cost
                if warning:
                    result['warnings'].append(warning)
                result['breakdown'].append({
                    'category': 'finding', 'material_id': mat_id,
                    'material_label': material_label(mat_id, mat),
                    'quantity': qty * finding_multiplier, 'cost': round(cost, 4),
                })
        if length and length > 0:
            if 'nk[n]' in recipes:
                for mat_id, qty in recipes['nk[n]'].items():
                    cost, mat, warning = calculate_material_cost(mat_id, qty * finding_multiplier, inventory)
                    finding_total += cost
                    if warning:
                        result['warnings'].append(warning)
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
                cost, mat, warning = calculate_material_cost(mat_id, qty * finding_multiplier, inventory)
                finding_total += cost
                if warning:
                    result['warnings'].append(warning)
                result['breakdown'].append({
                    'category': 'finding', 'material_id': mat_id,
                    'material_label': material_label(mat_id, mat),
                    'quantity': qty * finding_multiplier, 'cost': round(cost, 4),
                })
        packaging_rule = PACKAGING_RULES.get(category, PACKAGING_RULES[None])

    result['finding_cost'] = round(finding_total, 4)
    result['combined_finding_cost'] = round(finding_total + chain_cost, 4)

    pkg_key, pkg_qty = packaging_rule
    pkg_cost, pkg_items, pkg_warnings = calculate_packaging_cost(pkg_key, pkg_qty, inventory, recipes)
    result['packaging_cost'] = round(pkg_cost, 4)
    result['breakdown'].extend(pkg_items)
    result['warnings'].extend(pkg_warnings)

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
        f"Charm Cost:         {shopFormatting.currencyFormatUI(result['charm_cost'])}",
        f"Finding/Chain Cost: {shopFormatting.currencyFormatUI(result['combined_finding_cost'])}",
        f"Packaging Cost:     {shopFormatting.currencyFormatUI(result['packaging_cost'])}",
        "-" * 40,
        f"TOTAL COST:         {shopFormatting.currencyFormatUI(result['total_cost'])}",
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

    if result.get('warnings'):
        lines.append("")
        lines.append("Warnings:")
        for w in result['warnings']:
            lines.append(f"  \u26a0\ufe0f {w}")

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
        try:
            user_input = prompt_input(">>> ")
        except QuitRequested:
            print("\nGoodbye!\n")
            break
        if not user_input:
            continue

        result = calculate_cost(user_input, inventory, recipes)
        print(format_output(result))


if __name__ == '__main__':
    main()