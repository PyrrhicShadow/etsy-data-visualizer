#!/usr/bin/env python3
"""
shopIO.py - Pyrrhic Silva Shop

SINGLE SOURCE OF TRUTH for reading the shop's three recurring CSV shapes:
InventoryData.csv, RecipesData.csv, and the sales export. Every script
that used to hand-roll its own copy of these loaders should import from
here instead.

This module owns FILE I/O and ROW VALIDATION only. It does not know about
SKU parsing, pride-flag vocabulary, or trend columns -- that's skuVocab.py
and each script's own aggregation logic. Keeping these separate means a
change to "how do we read a CSV row" doesn't require touching "what do we
do with that row."
"""

import csv
from datetime import datetime


def clean_field(value):
    """Strip whitespace and stray leading/trailing quote characters that
    Excel/Etsy exports sometimes leave on a field."""
    return (value or '').strip().strip('"').strip("'")


def load_inventory(filename):
    """Load InventoryData.csv into {material_id: {name, price, total_units,
    specific_units}}. Callers that only need a subset of these fields
    (e.g. skuCostLookup.py, which never used total_units) just ignore the
    keys they don't need -- that's cheaper than maintaining a second
    loader that reads three columns instead of four.
    """
    inventory = {}
    with open(filename, 'r', encoding='utf-8-sig') as f:
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
    """Load RecipesData.csv into {sku: {material_id: qty}}.

    Uses a manual comma-split rather than csv.DictReader because rows are
    variable-length (materials columns padded with trailing empty cells).
    SKUs are lowercased for consistent lookup keys, since every consumer
    (recipeGen4B.py, skuCostLookup.py, checkNewFlags.py) either already
    lowercases or works against data that's already all-lowercase in the
    source file. The header row ('sku,materials,,,...') is explicitly
    skipped so it doesn't silently produce a bogus recipes['sku'] = {}
    entry, which the pre-consolidation version of this function in
    recipeGen4B.py did not guard against.
    """
    recipes = {}
    with open(filename, 'r', encoding='utf-8-sig') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) < 2:
                continue

            sku = parts[0].strip().lower()
            if sku == 'sku':
                continue

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


def load_valid_sales_rows(filename, date_format="%A, %B %d, %Y"):
    """Read the sales export and return a list of cleaned, validated row
    dicts: {'order_number', 'date' (datetime), 'quantity' (int), 'sku',
    'row' (the raw DictReader row, for any script-specific field access)}.

    A row is dropped (with a printed warning where the data itself looks
    malformed, silently where it's just structurally empty) if:
      - date or order number is blank
      - item quantity doesn't parse as an int, or is < 1 (cancellations
        and refunds carry negative or zero quantities)
      - the date doesn't match date_format

    This is the ONE place the "is this row a real, countable order line"
    rule lives. Anything beyond that -- SKU parsing, non-product-token
    filtering, per-order aggregation, earliest-vs-all dates -- is left to
    the caller, since that varies by script.
    """
    rows = []
    with open(filename, 'r', newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            date_str = clean_field(row.get('date'))
            order_num = clean_field(row.get('order number'))
            quantity_str = clean_field(row.get('item quantity'))
            sku = clean_field(row.get('item sku'))

            if not date_str or not order_num:
                continue

            try:
                quantity = int(quantity_str)
            except ValueError:
                print(f"Warning: Invalid quantity '{quantity_str}', skipping...")
                continue
            if quantity < 1:
                continue  # cancellations / refunds

            try:
                parsed_date = datetime.strptime(date_str, date_format)
            except ValueError:
                print(f"Warning: Could not parse date '{date_str}', skipping...")
                continue

            rows.append({
                'order_number': order_num,
                'date': parsed_date,
                'quantity': quantity,
                'sku': sku,
                'row': row,
            })
    return rows


def earliest_dates_by_order(rows):
    """Given rows from load_valid_sales_rows(), return
    {order_number: earliest datetime}. Two of the three current
    consumers want exactly this; the third (countOrdersSubMonths.py)
    wants every date per order, so it builds its own dict directly from
    rows instead of calling this.
    """
    earliest = {}
    for r in rows:
        onum = r['order_number']
        if onum not in earliest or r['date'] < earliest[onum]:
            earliest[onum] = r['date']
    return earliest