#!/usr/bin/env python3
"""
addSale.py - Pyrrhic Silva Shop

Interactive tool to add a new order's line items to PyrrhicSilvaShopSales.csv,
computing every fee/earnings/profit column the same way the hand-tallied
rows in that file already do.

SCOPE (read this before trusting the output on anything unusual):
  - Built and verified against POSITIVE-quantity, forward/new-sale rows.
    Quantity CAN be entered as negative and the sign-based formula terms
    below will compute arithmetically, but a real refund/cancel row in
    your existing sheet reuses the ORIGINAL order's payment/shipping fee
    dollar amounts rather than recomputing them fresh -- that lookback
    isn't implemented here. Treat negative-quantity support as untested,
    not as a refund-entry feature.
  - customer name and customer ID are now collected (one prompt each,
    right after order number) and written to every row for that order,
    matching how the existing sales CSV repeats them per line.
  - shipping label ID, ship date, arrival date, transit days, and notes
    are still NOT collected by this script and are written as blank
    cells, to be filled in by hand later (consistent with how many of
    your own historical rows leave these blank at time of sale).

INPUT CONVENTIONS:
  - Sale date is entered as mm/dd/yyyy. It's parsed with
    datetime.strptime and converted to this project's stored date-string
    format ('Tuesday, April 22, 2025'). A date that doesn't parse
    (typo) re-prompts instead of crashing -- it does NOT quit the
    program, since a bad date is assumed to be a typo, not a bail-out.
  - Typing 'quit', 'exit', or 'q' at ANY prompt during order/SKU entry
    aborts the whole order with nothing written -- no partial CSV rows,
    no traceback. This matches skuParser.py's and skuCostLookup.py's
    interactive loop convention. It does not apply to the final
    y/n confirmation or output-path prompt in main(), which already
    have their own abort path ("Aborted -- nothing written.").
  - Integer fields (number of unique SKUs, quantity per SKU), numeric
    fields (discount percent and every currency field), and the
    Share & Save y/n prompt all loop via _prompt_int()/_prompt_float()/
    _prompt_yes_no() until a valid value is entered -- same as
    _prompt_order_number()'s existing loop for order numbers. Each of
    these calls _input() first on every attempt, so the quit check
    always happens before the field-specific format check, not after.
    Share & Save now re-prompts on anything outside y/yes/true/n/no/false
    instead of silently treating a typo as "no".

FORMULAS (per Julien, confirmed against multiple historical rows,
including a refund row with a negative quantity):
  price_after_discount = qty * item_price * (1 - discount_pct/100)
  transaction_fee      = 6.5% of abs(price_after_discount)   <- stored
                          UNSIGNED; the sign only gets applied down in
                          the earnings formula via sign(qty). Confirmed
                          against order 3681-597-318 (qty -1): stored
                          fee is positive ($0.33) even though price after
                          discount is negative ($(5.00)).
  payment_fee   = 3% of order's total payment amount + $0.25   (ORDER-level)
  shipping_fee  = 6.5% of order's "shipping price" value       (ORDER-level)
  envelope_cost = calculate_envelope_cost() from skuCostLookup  (ORDER-level)

  earnings = price_after_discount
             - (qty * listing_fee)
             - (sign(qty) * payment_fee)
             - (sign(qty) * transaction_fee)
             + share_and_save_refund
             - (sign(qty) * shipping_fee)

  profit = earnings
           - (qty * charm_cost)
           - (qty * finding_cost)
           - (qty * finding_packaging_cost)
           - envelope_cost

ORDER-LEVEL vs LINE-LEVEL, matching the existing CSV's own convention:
  Stored ONLY on the first-entered SKU's row (zero/blank on every other
  row of the same order): payment_fee, shipping_fee, share_and_save_refund,
  envelope_cost, payment_amount, sales_tax, shipping_price.
  Stored on EVERY row: listing_fee (flat $0.20, not pre-multiplied by
  quantity -- Julien wants the multiplication to happen in the earnings
  calculation, not baked into the stored cell), charm_cost, finding_cost,
  finding_packaging_cost, transaction_fee (each per-unit / per-line, not
  pre-multiplied by quantity either), and customer_name / customer_id
  (repeated per line, matching how the existing CSV stores them).

SHIPPING PRICE ASSUMPTION: the single "shipping price" input serves double
duty per EtsyFeesRules.md -- for a free-shipping listing it's the real
label cost the shop paid, for a customer-paid-shipping listing it's what
the customer paid for shipping. Either way shipping_fee = 6.5% of that one
number. This script does not ask which case applies; it just fees 6.5% of
whatever's entered. It does not attempt the historical "reshipment cost
added on top" special case mentioned in EtsyFeesRules.md.

BRAC / BRAC-E: skuCostLookup.calculate_cost() returns not_implemented=True
for these categories rather than costing them. This script still writes
the row (so the order isn't silently dropped) with charm/finding/finding-
packaging costs zeroed out, and surfaces a warning so you know to hand-fill
those cells once BRAC/BRAC-E costing is built out.

GUI NOTE: following this project's established pattern, compute_sale_rows()
is a pure function (no printing/input) that returns (rows, warnings).
main() handles all input()/print() and hands off to write_sales_csv_rows()
for the file-writing step.
"""

import csv
import os
from cliPrompts import QuitRequested, prompt_input, prompt_date, prompt_float, prompt_int, prompt_yes_no

from shopIO import load_inventory, load_recipes
from skuCostLookup import calculate_cost, calculate_envelope_cost


SALES_CSV_HEADER = [
    'date', 'order number', 'item sku', 'item quantity', 'customer name', 'customer ID',
    ' charm cost ', ' finding cost ', ' finding packaging cost ', ' envelope cost ',
    ' item price ', 'order discount', ' price after discounts ', ' listing fee ',
    ' payment processing fee ', ' transaction fee ', ' Share & Save refund ',
    ' shipping cost ', 'earnings (etsy payout)', ' profit (including all costs) ',
    ' payment amount (customer) ', ' sales tax paid ', ' shipping price ',
    ' shipping label ID ', 'ship date', 'arrival date', ' transit days (approx) ', ' notes ',
]

LISTING_FEE = 0.20
PAYMENT_PROCESSING_RATE = 0.03
PAYMENT_PROCESSING_FIXED = 0.25
TRANSACTION_FEE_RATE = 0.065
SHIPPING_FEE_RATE = 0.065


def _fmt_money(value):
    """Format a numeric value to match the existing sales CSV's style:
    ' X.XX ' for nonzero values, '0' for exactly zero"""
    if abs(value) < 0.0001:
        return ' 0 '
    return f' {value:.2f} '

def _prompt_order_number():
    """Prompt for an order number and re-prompt until it's exactly 10
    digits (no dashes, no letters) once leading/trailing whitespace is
    stripped -- anything else is assumed to be a typo, not a new format,
    so it loops rather than accepting it. Does not reformat into the 
    exisiting XXXX-XXX-XXX format for ease of import from temp CSV to 
    the master XLXS."""
    while True:
        raw = prompt_input("Order number (10 digits, no dashes): ")
        if raw.isdigit() and len(raw) == 10:
            return raw
        print("  \u274c Order number must be exactly 10 digits, no dashes or letters. Try again.")

def prompt_order_info():
    """Collect the per-order fields (asked once per order). Returns a
    plain dict. This is the ONLY place input() is called for order-level
    fields -- kept separate from per-SKU prompting and from
    compute_sale_rows().

    Every prompt goes through _input()/prompt_date(), so typing
    'quit'/'exit'/'q' at any point here raises QuitRequested and aborts
    order entry -- no partial order is ever written.
    """
    print("\n--- Order details ---")
    date_str = prompt_date()
    order_number = _prompt_order_number()
    customer_name = prompt_input("Customer name: ")
    customer_id = prompt_input("Customer ID: ")
    num_skus = prompt_int("Number of unique SKUs in this order: ")
    discount_pct = prompt_float("Discount percent applied at checkout (e.g. 25 for 25%, 0 for none): ")

    share_and_save = prompt_yes_no("Was this a Share & Save order? (y/n): ")
    share_save_refund = 0.0
    if share_and_save:
        share_save_refund = prompt_float("Exact Share & Save refund dollar amount for this order: $")

    payment_amount = prompt_float("Total order payment amount (customer): $")
    sales_tax = prompt_float("Sales tax paid by customer: $")
    shipping_price = prompt_float(
        "Shipping price (real label cost you paid if free shipping, "
        "or amount customer paid for shipping otherwise): $"
    )
    customer_paid_shipping = prompt_yes_no(
        "Did the customer pay for shipping (vs. free shipping you covered)? (y/n): "
    )

    return {
        'date_str': date_str,
        'order_number': order_number,
        'customer_name': customer_name,
        'customer_id': customer_id,
        'num_skus': num_skus,
        'discount_pct': discount_pct,
        'share_and_save': share_and_save,
        'share_save_refund': share_save_refund,
        'payment_amount': payment_amount,
        'sales_tax': sales_tax,
        'shipping_price': shipping_price,
        'customer_paid_shipping': customer_paid_shipping,
    }


def prompt_sku_lines(num_skus):
    """Collect SKU, quantity, and listing item price for each unique SKU
    in the order. The FIRST one entered here is treated as the "first
    unique SKU" for every order-level field's placement rule. Returns a
    list of dicts: {'sku', 'quantity', 'item_price'}.

    Same quit convention as prompt_order_info(): typing 'quit'/'exit'/'q'
    at any of these prompts raises QuitRequested and aborts the whole
    order, not just the current SKU line."""
    lines = []
    for i in range(num_skus):
        print(f"\n-- SKU {i + 1} of {num_skus} --")
        sku = prompt_input("SKU: ")
        quantity = prompt_int(f"Quantity of '{sku}' sold: ")
        item_price = prompt_float(f"Listing item price for '{sku}': $")
        lines.append({'sku': sku, 'quantity': quantity, 'item_price': item_price})
    return lines


def compute_sale_rows(order_info, sku_lines, inventory, recipes):
    """Pure compute function: no printing, no input. Returns (rows, warnings).

    rows: list of dicts, one per SKU line, with every value
    write_sales_csv_rows() needs.
    warnings: list of plain strings (unparseable SKU, BRAC/BRAC-E not
    costed, envelope material missing, etc.) -- caller decides how to
    surface them.
    """
    warnings = []
    rows = []

    discount_mult = 1 - (order_info['discount_pct'] / 100)

    payment_fee = round(order_info['payment_amount'] * PAYMENT_PROCESSING_RATE + PAYMENT_PROCESSING_FIXED, 4)
    shipping_fee = round(order_info['shipping_price'] * SHIPPING_FEE_RATE, 4)

    envelope_cost, envelope_warning = calculate_envelope_cost(inventory)
    if envelope_warning:
        warnings.append(envelope_warning)

    for idx, line in enumerate(sku_lines):
        is_first = (idx == 0)
        sku = line['sku']
        qty = line['quantity']
        sign = 1 if qty >= 0 else -1
        item_price = line['item_price']

        price_after_discount = round(qty * item_price * discount_mult, 4)

        # Transaction fee is stored UNSIGNED -- confirmed against a
        # historical refund row where price_after_discount was negative
        # but the stored transaction fee cell was still positive.
        transaction_fee = round(abs(price_after_discount) * TRANSACTION_FEE_RATE, 4)

        cost_result = calculate_cost(sku, inventory, recipes)

        charm_cost = 0.0
        finding_cost = 0.0
        finding_pkg_cost = 0.0

        if cost_result.get('error'):
            warnings.append(f"'{sku}': {cost_result['error']} -- costs zeroed out for this row.")
        elif cost_result.get('not_implemented'):
            warnings.append(f"'{sku}': {cost_result['message']} Costs zeroed out -- fill in by hand.")
        else:
            charm_cost = cost_result['charm_cost']
            finding_cost = cost_result['finding_cost']
            finding_pkg_cost = cost_result['packaging_cost']
            warnings.extend(cost_result.get('warnings', []))

        # Order-level fields: real value on the first row, zero (which
        # renders as the file's own "$-" blank-cost convention) elsewhere.
        line_payment_fee = payment_fee if is_first else 0.0
        line_shipping_fee = shipping_fee if is_first else 0.0
        line_share_save = order_info['share_save_refund'] if is_first else 0.0
        line_envelope = envelope_cost if is_first else 0.0
        line_payment_amount = order_info['payment_amount'] if is_first else 0.0
        line_sales_tax = order_info['sales_tax'] if is_first else 0.0
        line_shipping_price = order_info['shipping_price'] if is_first else 0.0

        earnings = round((
            price_after_discount
            - (qty * LISTING_FEE)
            - (sign * line_payment_fee)
            - (sign * transaction_fee)
            + line_share_save
            - (sign * line_shipping_fee)
        ), 4)

        profit = round((
            earnings
            - (qty * charm_cost)
            - (qty * finding_cost)
            - (qty * finding_pkg_cost)
            - line_envelope
        ), 4)

        rows.append({
            'date': order_info['date_str'],
            'order_number': order_info['order_number'],
            'customer_name': order_info['customer_name'],
            'customer_id': order_info['customer_id'],
            'sku': cost_result.get('canonical_sku', sku),
            'quantity': qty,
            'charm_cost': charm_cost,
            'finding_cost': finding_cost,
            'finding_pkg_cost': finding_pkg_cost,
            'envelope_cost': line_envelope,
            'item_price': item_price,
            'discount_pct': order_info['discount_pct'],
            'price_after_discount': price_after_discount,
            'listing_fee': LISTING_FEE,
            'payment_fee': line_payment_fee,
            'transaction_fee': transaction_fee,
            'share_save_refund': line_share_save,
            'shipping_fee': line_shipping_fee,
            'earnings': earnings,
            'profit': profit,
            'payment_amount': line_payment_amount,
            'sales_tax': line_sales_tax,
            'shipping_price': line_shipping_price,
        })

    return rows, warnings

def verify_payment_amount(rows, order_info, tolerance=0.02):
    """Pure check: sums price_after_discount across all SKU lines in this
    order (quantity is already baked into that value -- see
    compute_sale_rows(), no re-multiplying it here) plus sales tax, plus
    shipping_price ONLY if the customer paid for it
    (order_info['customer_paid_shipping']), and compares the result to
    the order-level payment_amount the user entered.

    This exists to catch INPUT typos (e.g. '123' for sales tax instead
    of '1.23', or the wrong item price on one SKU line) -- it is NOT a
    validator for historical/edited rows, which can legitimately have
    partial refunds or manual overrides this won't account for.

    Returns a dict, never printed here:
        {'is_valid': bool, 'computed_total': float, 'expected': float,
         'difference': float}
    |difference| within `tolerance` (default 2 cents, to absorb per-line
    round(..., 4) rounding across multiple SKU lines) counts as valid.
    """
    computed_total = sum(r['price_after_discount'] for r in rows)
    computed_total += order_info['sales_tax']
    if order_info.get('customer_paid_shipping'):
        computed_total += order_info['shipping_price']
    computed_total = round(computed_total, 4)

    expected = order_info['payment_amount']
    difference = round(computed_total - expected, 4)

    return {
        'is_valid': abs(difference) <= tolerance,
        'computed_total': computed_total,
        'expected': expected,
        'difference': difference,
    }

def write_sales_csv_rows(rows, output_path):
    """Append (or create) rows in PyrrhicSilvaShopSales.csv's existing
    format: ' $X.XX ' / '25%' style discount strings, and blank cells 
    for fields this script doesn't collect (shipping label ID, ship / 
    arrival dates, transit days, notes).

    This is a dedicated writer local to addSale.py rather than an
    addition to shopIO.py -- per this project's design, shopIO.py owns
    file I/O in general, but the sales CSV's specific currency-string/
    quoting format is specific enough to this one file that duplicating
    it here keeps shopIO.py from needing to know about display formatting
    at all. (Per Julien: revisit if a second script ever needs to write
    this same format.)
    """
    file_exists = os.path.isfile(output_path)

    with open(output_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(SALES_CSV_HEADER)

        for r in rows:
            discount_str = f"{r['discount_pct']:g}%"
            out_row = [
                r['date'],
                r['order_number'],
                r['sku'],
                r['quantity'],
                r['customer_name'],
                r['customer_id'],
                _fmt_money(r['charm_cost']),
                _fmt_money(r['finding_cost']),
                _fmt_money(r['finding_pkg_cost']),
                _fmt_money(r['envelope_cost']),
                _fmt_money(r['item_price']),
                discount_str,
                _fmt_money(r['price_after_discount']),
                _fmt_money(r['listing_fee']),
                _fmt_money(r['payment_fee']),
                _fmt_money(r['transaction_fee']),
                _fmt_money(r['share_save_refund']),
                _fmt_money(r['shipping_fee']),
                _fmt_money(r['earnings']),
                _fmt_money(r['profit']),
                _fmt_money(r['payment_amount']),
                _fmt_money(r['sales_tax']),
                _fmt_money(r['shipping_price']),
                '',  # shipping label ID -- not collected
                '',  # ship date -- not collected
                '',  # arrival date -- not collected
                '',  # transit days -- not collected
                '',  # notes -- not collected
            ]
            writer.writerow(out_row)


def render_warnings_cli(warnings):
    if not warnings:
        print("\n\u2713 No warnings.")
        return
    print(f"\n\u26a0\ufe0f  {len(warnings)} warning(s):")
    for w in warnings:
        print(f"  - {w}")

def render_verification_cli(verification):
    """CLI-only renderer for verify_payment_amount()'s output."""
    if verification['is_valid']:
        print(
            f"\n\u2713 Payment amount checks out (computed "
            f"${verification['computed_total']:.2f} vs. entered "
            f"${verification['expected']:.2f})."
        )
        return
    print(
        f"\n\u26a0\ufe0f  Payment amount mismatch: computed total is "
        f"${verification['computed_total']:.2f} but you entered "
        f"${verification['expected']:.2f} (difference: "
        f"${verification['difference']:+.2f})."
    )
    print("   Likely a typo in sales tax, shipping price, an item price,")
    print("   the discount percent, or payment amount itself.")


def render_preview_cli(rows):
    print("\n" + "-" * 60)
    print("PREVIEW")
    print("-" * 60)
    for r in rows:
        print(
            f"  {r['sku']:<20} qty={r['quantity']:>3}  "
            f"earnings=${r['earnings']:>7.2f}  profit=${r['profit']:>7.2f}"
        )
    print("-" * 60)


def main():
    print("=" * 60)
    print("ADD SALE - Pyrrhic Silva Shop")
    print("=" * 60)

    inv_path = input("\nEnter path to InventoryData CSV (or Enter for InventoryData.csv): ").strip()
    if not inv_path:
        inv_path = 'InventoryData.csv'
    rec_path = input("Enter path to RecipesData CSV (or Enter for RecipesData.csv): ").strip()
    if not rec_path:
        rec_path = 'RecipesData.csv'

    try:
        inventory = load_inventory(inv_path)
        recipes = load_recipes(rec_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    print(f"  \u2713 {len(inventory)} materials, {len(recipes)} recipes loaded")
    print("  (Type 'quit', 'exit', or 'q' at any prompt below to bail out --")
    print("   nothing is written until you confirm at the very end.)")

    try:
        order_info = prompt_order_info()
        sku_lines = prompt_sku_lines(order_info['num_skus'])
    except QuitRequested:
        print("\nAborted -- nothing written.")
        return

    rows, warnings = compute_sale_rows(order_info, sku_lines, inventory, recipes)
    verification = verify_payment_amount(rows, order_info)

    render_preview_cli(rows)
    render_warnings_cli(warnings)
    render_verification_cli(verification)

    try:
        if not verification['is_valid']:
            proceed = prompt_yes_no("\nMismatch found above. Write anyway? (y/n): ")
            if not proceed:
                print("Aborted -- nothing written. Re-run to re-enter the order.")
                return

        confirm = prompt_yes_no("\nWrite these rows to the sales CSV? (y/n): ")
    except QuitRequested:
        print("\nAborted -- nothing written.")
        return

    if not confirm:
        print("Aborted -- nothing written.")
        return

    output_path = input("Enter output path (or Enter for TempNewSales.csv): ").strip()
    if not output_path:
        output_path = 'TempNewSales.csv'

    write_sales_csv_rows(rows, output_path)
    print(f"\n\u2713 Appended {len(rows)} row(s) to {output_path}")


if __name__ == '__main__':
    main()