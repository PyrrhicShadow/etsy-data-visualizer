#!/usr/bin/env python3
"""
etsyReconcile.py - Pyrrhic Silva Crafts

Compares your official Etsy "Sold Orders" export against ShopSales.csv
and surfaces orders that exist in the Etsy report but NOT in your own
records -- one direction only, per Julien's instructions: this never
flags an order that's in ShopSales.csv but missing from Etsy (that's
not what this tool is for).

For each missing order, it pre-fills whatever Etsy's export reliably
provides and prompts for everything it can't -- then hands off to
addSale.py's existing compute_sale_rows() / verify_payment_amount() /
write_sales_csv_rows() so the fee/earnings/profit math has exactly one
implementation in this project, not two.

WHY THIS IS ITS OWN SCRIPT, NOT A shopCLI CONTEXT (Julien's call):
Julien is planning an eventual move off the centralized shopCLI
dispatcher toward a GUI. This script imports addSale directly and owns
its own reconciliation-specific logic (the Etsy-vs-entered sanity
checks below), rather than living as another thin shopCLI adapter.

WHAT ETSY'S EXPORT CAN AND CAN'T BE TRUSTED FOR (verified against
Julien's real historical ShopSales.csv rows before writing any of this
-- see chat history, not re-derived here):
  - Order Total  -> matches 'payment amount (customer)' exactly, every
    order checked. Pre-filled with confirm/override.
  - Shipping     -> matches 'shipping price' exactly WHEN the customer
    paid for shipping. When shipping was free, this field is 0.00 and
    tells you nothing about the real postage cost paid -- confirmed
    against orders where Julien manually recorded real shipping cost
    elsewhere (e.g. a "USPS real shipping" line item). So: Shipping > 0
    pre-fills with confirm/override and implies customer_paid_shipping
    unless overridden (Julien's call); Shipping == 0.00 gets a blank
    prompt for the real cost, plus an explicit customer-paid-shipping
    question, since there's no signal either way.
  - Sales Tax    -> NOT the same thing as what Julien records. Etsy's
    Sales Tax field logs what Julien paid (always $0 so far); Julien
    records what the BUYER paid. Never read, always a fresh prompt.
  - Discount Amount / Order Value -> Discount Amount/Order Value*100
    matches Julien's recorded discount% exactly on every order checked.
    Per Julien: prompt for discount% fresh (do NOT pre-fill), then
    compare against this derived value as a post-hoc sanity check.
  - Number of Items -> total UNIT count across the whole order, not a
    count of unique SKU lines (Etsy repeats a SKU per unit rather than
    using a quantity field for multi-unit-same-SKU orders). Used only
    as a sanity-check total against sum(entered quantities), never to
    pre-fill num_skus.
  - SKU field -> IGNORED ENTIRELY per Julien's explicit instruction.
    Not every listing variation has an accurate SKU attached on Etsy's
    side, so this is shown for reference only, never parsed or trusted.

ORDER-ID NORMALIZATION: Etsy's Order ID is a bare 10-digit integer.
ShopSales.csv currently mixes formats -- older hand-entered rows are
dashed ('3934-784-543'), but addSale.py's own docstring says newly-
written rows are raw digits, no dashes. normalize_order_number() strips
everything but digits on BOTH sides before comparing, so this doesn't
produce false "missing" hits. This is comparison-only; nothing here
ever rewrites an existing order number's stored format.

WHAT COUNTS AS "ALREADY RECORDED": uses shopIO.load_valid_sales_rows()
same as every other report in this project, which drops rows with
quantity < 1 (cancellations/refunds/insurance payouts). Per Julien:
by design, a cancel/refund row always follows a real order row with
qty >= 1 for the same order number, so that order number stays in the
known set regardless. Watch for exceptions here -- if an order was
recorded ONLY as a cancellation with no qty>=1 row ever entered, it
would correctly show up as "missing", as the original qty >= 1 row 
would actually be missing in such cases.

QUIT SCOPING (two-tier, deliberately different from a single flat
convention): 'quit'/'exit'/'q' typed at the top-level "Enter this order
now?" prompt (before any per-order data entry starts) stops the WHOLE
reconciliation run -- anything not yet entered is still "missing" and
will show up again next run, so nothing is lost. The same words typed
DURING one order's data entry (order_info / SKU lines) only abort that
ONE order and move to the next missing order -- this matches
addSale.py's own established per-order abort convention exactly. Both
paths use the same QuitRequested exception; which one fires depends on
which prompt tier it's raised from, not a second mechanism.

NOT touching shopIO.py: the Etsy CSV loader below is local to this
file. Per this project's "no speculative extraction" rule, a shared
loader gets promoted to shopIO.py only once a second script needs one --
this is currently the only consumer.

GUI NOTE: every function above the CLI-rendering section is pure (no
print()/input()) except where explicitly a *_cli prompt/render helper.
main() is the only place with the interactive orchestration.
"""

import csv
import os
from datetime import datetime

import addSale
import shopFormatting
from cliPrompts import QuitRequested, prompt_input, prompt_float, prompt_int, prompt_yes_no
from shopIO import load_valid_sales_rows, load_inventory, load_recipes

ETSY_FILENAME_TEMPLATE = "Local/EtsySoldOrders{year}.csv"
ETSY_DATE_FORMAT = "%m/%d/%y"  # Etsy's own export format, e.g. '12/29/25'


# ---------------------------------------------------------------------
# Order-number normalization / comparison
# ---------------------------------------------------------------------
def normalize_order_number(raw):
    """Digits-only normalization so Etsy's bare '3934784543' and
    ShopSales.csv's dashed '3934-784-543' (or addSale.py's own
    undashed new rows) compare equal. Comparison-only."""
    return ''.join(ch for ch in str(raw) if ch.isdigit())


def known_order_numbers_from_sales(sales_rows):
    """sales_rows: shopIO.load_valid_sales_rows() output. Returns the
    set of normalized order numbers already present in ShopSales.csv."""
    return {normalize_order_number(r['order_number']) for r in sales_rows}


# ---------------------------------------------------------------------
# Etsy CSV loading (local to this file -- see module docstring)
# ---------------------------------------------------------------------
def load_etsy_csv(path):
    """Load one Etsy 'Sold Orders' export. Returns (rows, warnings).

    Each row is the raw DictReader dict PLUS two derived keys:
      'order_number' -- normalize_order_number()'d Order ID
      'sale_date'    -- parsed datetime (from Etsy's own mm/dd/yy format)

    A row with a blank Order ID or an unparseable Sale Date is dropped
    with a warning rather than crashing the whole load -- same
    warnings-as-data convention as shopIO.load_valid_sales_rows().
    """
    rows = []
    warnings = []
    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for raw_row in reader:
            order_id = (raw_row.get('Order ID') or '').strip()
            if not order_id:
                continue

            date_str = (raw_row.get('Sale Date') or '').strip()
            try:
                sale_date = datetime.strptime(date_str, ETSY_DATE_FORMAT)
            except ValueError:
                warnings.append(
                    f"Could not parse Etsy sale date '{date_str}' for order {order_id}, skipping."
                )
                continue

            row = dict(raw_row)
            row['order_number'] = normalize_order_number(order_id)
            row['sale_date'] = sale_date
            rows.append(row)
    return rows, warnings


def find_missing_orders(etsy_rows, known_order_numbers):
    """Etsy rows whose order_number isn't in known_order_numbers,
    oldest first (natural order to work through them in)."""
    missing = [r for r in etsy_rows if r['order_number'] not in known_order_numbers]
    return sorted(missing, key=lambda r: r['sale_date'])


# ---------------------------------------------------------------------
# Etsy-derived sanity-check values
# ---------------------------------------------------------------------
def _safe_float(row, key):
    try:
        return float(row.get(key) or 0)
    except ValueError:
        return None


def etsy_derived_discount_pct(row):
    """Discount% implied by Etsy's own Discount Amount / Order Value.
    None if Order Value is missing/zero -- nothing to divide by."""
    order_value = _safe_float(row, 'Order Value')
    discount_amount = _safe_float(row, 'Discount Amount')
    if order_value is None or discount_amount is None or order_value <= 0:
        return None
    return discount_amount / order_value * 100


def compute_reconciliation_warnings(etsy_row, order_info, sku_lines):
    """Sanity checks unique to reconciling against Etsy's own numbers --
    distinct from addSale.verify_payment_amount(), which only checks
    that the entered fields are internally arithmetically consistent
    with each other. These checks catch entries that are internally
    consistent but don't match what Etsy actually reported. Pure
    function; returns a list of warning strings, never printed here."""
    warnings = []

    derived_pct = etsy_derived_discount_pct(etsy_row)
    entered_pct = order_info['discount_pct']
    if derived_pct is not None and abs(entered_pct - derived_pct) > 0.5:
        warnings.append(
            f"Entered discount {entered_pct:g}% differs from Etsy-derived "
            f"{derived_pct:.1f}% (Discount Amount / Order Value). Double-check."
        )

    try:
        etsy_num_items = int(etsy_row.get('Number of Items') or 0)
    except ValueError:
        etsy_num_items = None
    total_qty = sum(line['quantity'] for line in sku_lines)
    if etsy_num_items is not None and etsy_num_items != total_qty:
        warnings.append(
            f"Entered SKU quantities total {total_qty}, but Etsy's 'Number of Items' "
            f"for this order is {etsy_num_items}. Double-check you didn't miss a line."
        )

    etsy_order_value = _safe_float(etsy_row, 'Order Value')
    entered_pre_discount = sum(line['quantity'] * line['item_price'] for line in sku_lines)
    if etsy_order_value is not None and abs(entered_pre_discount - etsy_order_value) > 0.02:
        warnings.append(
            f"Entered item prices sum to ${entered_pre_discount:.2f} before discount, but "
            f"Etsy's Order Value is ${etsy_order_value:.2f}. Double-check your listing prices."
        )

    return warnings


# ---------------------------------------------------------------------
# Interactive prompting -- pre-fill/confirm helper local to this file
# (single consumer; promote to cliPrompts.py only if a second script
# ever needs the same "accept or override" shape).
# ---------------------------------------------------------------------
def prompt_confirm_value(prompt, default_value, default_display=None, parser=str):
    """Ask the user to accept a pre-filled value (blank input) or type
    an override, parsed with `parser`. Returns (value, was_overridden).
    Goes through prompt_input() first, so 'quit'/'exit'/'q' raises
    QuitRequested same as every other prompt in this project."""
    if default_display is None:
        default_display = str(default_value)
    while True:
        raw = prompt_input(f"{prompt} [{default_display}] (Enter to accept, or type a new value): ")
        if not raw:
            return default_value, False
        try:
            return parser(raw), True
        except ValueError:
            print(f"  \u274c Could not parse '{raw}'. Try again.")


def prompt_etsy_report():
    """Prompt for a year, try ETSY_FILENAME_TEMPLATE for it, and if
    that's not found, loop asking for a path until a real, readable
    file is given -- catches typos/naming drift in future downloads
    without hardcoding every possible filename. Returns
    (rows, path_used, warnings)."""
    year = prompt_input("Etsy report year (e.g. 2026): ")
    path = ETSY_FILENAME_TEMPLATE.format(year=year)
    while True:
        if os.path.isfile(path):
            try:
                rows, warnings = load_etsy_csv(path)
                return rows, path, warnings
            except Exception as e:
                print(f"  \u274c Error reading '{path}': {e}")
        else:
            print(f"  \u274c Could not find '{path}'.")
        path = prompt_input("Enter a path to the Etsy report CSV: ")


def prompt_order_info_from_etsy(etsy_row):
    """Same return shape as addSale.prompt_order_info(), pre-filling
    every field Etsy's export reliably provides (with confirm/override)
    and freshly prompting for everything it can't -- see module
    docstring for the evidence behind each choice. Raises
    QuitRequested to abort just THIS order (caller moves on to the
    next missing order, per the two-tier quit scoping in the module
    docstring)."""
    order_number = etsy_row['order_number']  # normalized digits-only; matches addSale.py's own no-dash convention for new rows

    date_val, _ = prompt_confirm_value(
        "Sale date (mm/dd/yyyy)", etsy_row['sale_date'],
        default_display=shopFormatting.dateFormatCSV(etsy_row['sale_date']),
        parser=lambda s: datetime.strptime(s, "%m/%d/%Y"),
    )
    date_str = shopFormatting.dateFormatCSV(date_val)

    customer_name, _ = prompt_confirm_value("Customer name", etsy_row.get('Full Name', ''))
    customer_id, _ = prompt_confirm_value("Customer ID", etsy_row.get('Buyer User ID', ''))

    num_skus = prompt_int("Number of unique SKUs in this order: ")
    discount_pct = prompt_float(
        "Discount percent applied at checkout (e.g. 25 for 25%, 0 for none) "
    )

    share_and_save = prompt_yes_no("Was this a Share & Save order? (y/n): ")
    share_save_refund = 0.0
    if share_and_save:
        share_save_refund = prompt_float("Exact Share & Save refund dollar amount for this order: $")

    etsy_payment_amount = _safe_float(etsy_row, 'Order Total') or 0.0
    payment_amount, _ = prompt_confirm_value(
        "Total order payment amount (customer)", etsy_payment_amount,
        default_display=f"${etsy_payment_amount:.2f}", parser=float,
    )

    sales_tax = prompt_float(
        "Sales tax paid by customer (not seller): $"
    )

    etsy_shipping = _safe_float(etsy_row, 'Shipping') or 0.0
    if etsy_shipping > 0:
        shipping_price, shipping_overridden = prompt_confirm_value(
            "Shipping price", etsy_shipping,
            default_display=f"${etsy_shipping:.2f}", parser=float,
        )
        if shipping_overridden:
            customer_paid_shipping = prompt_yes_no(
                "You changed the pre-filled shipping value -- did the customer pay for "
                "shipping (vs. free shipping you covered)? (y/n): "
            )
        else:
            customer_paid_shipping = True
    else:
        shipping_price = prompt_float(
            "Shipping price (Etsy reported $0 -- usually free shipping; enter your real "
            "label cost paid, or what the customer paid if this wasn't actually free): $"
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


# ---------------------------------------------------------------------
# CLI-only rendering below. Nothing above this line prints anything
# except the prompt helpers, which are interactive by nature.
# ---------------------------------------------------------------------
def render_etsy_summary_cli(row):
    print("\n" + "-" * 60)
    print(f"  Date:          {shopFormatting.dateFormatUI(row['sale_date'])}")
    print(f"  Order ID:      {row.get('Order ID', '')}")
    print(f"  Buyer:         {row.get('Full Name', '')}  (ID: {row.get('Buyer User ID', '')})")
    print(f"  Order Value:   ${row.get('Order Value', '')}   Discount Amount: ${row.get('Discount Amount', '')}")
    derived_pct = etsy_derived_discount_pct(row)
    if derived_pct is not None:
        print(f"  Etsy-derived discount %: {derived_pct:.1f}%  (sanity check only)")
    print(f"  Order Total (payment amount): ${row.get('Order Total', '')}")
    print(f"  Shipping (Etsy):   ${row.get('Shipping', '')} (amt paid by customer)")
    print(f"  Sales Tax (Etsy):  ${row.get('Sales Tax', '')}  (amt paid by seller)")
    print(f"  Number of Items:   {row.get('Number of Items', '')}")
    sku_field = (row.get('SKU') or '').strip()
    if sku_field:
        print(f"  Etsy SKU field (reference only): {sku_field}")


def render_reconciliation_warnings_cli(warnings):
    if not warnings:
        return
    print(f"\n\u26a0\ufe0f  {len(warnings)} Etsy-reconciliation check(s) flagged something:")
    for w in warnings:
        print(f"  - {w}")


def main():
    print("=" * 60)
    print("ETSY RECONCILE - Pyrrhic Silva Crafts")
    print("Finds orders in your Etsy sold orders report missing from ShopSales.csv")
    print("and walks you through entering each one.")
    print("=" * 60)

    try:
        etsy_rows, etsy_path, load_warnings = prompt_etsy_report()
    except QuitRequested:
        print("\nCancelled.\n")
        return

    for w in load_warnings:
        print(f"Warning: {w}")

    if not etsy_rows:
        print("\nNo usable rows found in that Etsy report.\n")
        return

    oldest = min(r['sale_date'] for r in etsy_rows)
    newest = max(r['sale_date'] for r in etsy_rows)
    print(f"\n  \u2713 Loaded {len(etsy_rows)} order(s) from '{etsy_path}'")
    print(f"  Report covers {shopFormatting.dateFormatUI(oldest)} through {shopFormatting.dateFormatUI(newest)}.")
    print("  (Only as current as your last Etsy download -- re-download for anything more recent.)")

    sales_path = input("\nPath to ShopSales.csv (or Enter for ShopSales.csv): ").strip() or 'ShopSales.csv'
    try:
        sales_rows, sales_warnings = load_valid_sales_rows(sales_path)
    except FileNotFoundError as e:
        print(f"\n\u274c Could not load '{sales_path}': {e}")
        return
    for w in sales_warnings:
        print(f"Warning: {w}")

    known = known_order_numbers_from_sales(sales_rows)
    missing = find_missing_orders(etsy_rows, known)

    print(f"\n  \u2713 {len(missing)} order(s) in the Etsy report not found in '{sales_path}'.")
    if not missing:
        print("  Nothing to enter.\n")
        return

    inv_path = input("Path to InventoryData CSV (or Enter for InventoryData.csv): ").strip() or 'InventoryData.csv'
    rec_path = input("Path to RecipesData CSV (or Enter for RecipesData.csv): ").strip() or 'RecipesData.csv'
    try:
        inventory = load_inventory(inv_path)
        recipes = load_recipes(rec_path)
    except FileNotFoundError as e:
        print(f"\n\u274c {e}")
        return

    output_path = input("\nOutput path for new rows this session (or Enter for Local/TempNewSales.csv): ").strip()
    if not output_path:
        output_path = 'Local/TempNewSales.csv'

    written_count = 0
    for etsy_row in missing:
        render_etsy_summary_cli(etsy_row)
        try:
            proceed = prompt_yes_no("\nEnter this order now? (y/n): ")
        except QuitRequested:
            print("\nStopping here -- remaining orders are still 'missing' and will show up again next run.")
            break
        if not proceed:
            print("  Skipped -- will show up again next run.")
            continue

        try:
            order_info = prompt_order_info_from_etsy(etsy_row)
            sku_lines = addSale.prompt_sku_lines(order_info['num_skus'])
        except QuitRequested:
            print("\n  Order aborted -- nothing written. Moving to next missing order.")
            continue

        rows, warnings = addSale.compute_sale_rows(order_info, sku_lines, inventory, recipes)
        verification = addSale.verify_payment_amount(rows, order_info)
        reconciliation_warnings = compute_reconciliation_warnings(etsy_row, order_info, sku_lines)

        addSale.render_preview_cli(rows)
        addSale.render_warnings_cli(warnings)
        render_reconciliation_warnings_cli(reconciliation_warnings)
        addSale.render_verification_cli(verification)

        try:
            if not verification['is_valid'] or reconciliation_warnings:
                proceed_anyway = prompt_yes_no("\nDiscrepancy found above. Write anyway? (y/n): ")
                if not proceed_anyway:
                    print("  Not written -- will show up again next run.")
                    continue
            confirm = prompt_yes_no("\nWrite these rows to the sales CSV? (y/n): ")
        except QuitRequested:
            print("\n  Order aborted -- nothing written. Moving to next missing order.")
            continue

        if not confirm:
            print("  Not written -- will show up again next run.")
            continue

        addSale.write_sales_csv_rows(rows, output_path)
        written_count += len(rows)
        print(f"  \u2713 Appended {len(rows)} row(s) to {output_path}")

    print(f"\nDone. {written_count} row(s) written this session to {output_path}.")


if __name__ == '__main__':
    main()