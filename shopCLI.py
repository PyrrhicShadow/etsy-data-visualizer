#!/usr/bin/env python3
"""
shopCLI.py - Pyrrhic Silva Crafts unified dispatcher

Single entry point for every read-only reporting/lookup script in this
project. Pick a context from the menu, it runs, and you're dropped back
at the menu -- no re-launching a different .py file, no re-typing CSV
paths every time you hop back in mid-workflow.

DESIGN
------
This script owns NO business logic. Every context function below is a
thin adapter that:
  1. pulls already-loaded data from a shared ShopData cache,
  2. calls that module's existing pure compute function (unchanged),
  3. calls that module's existing render_report_cli() (unchanged) to
     print the result.

That's only possible because countOrdersDayOfWeek.py, countOrdersSubMonths.py,
checkNewFlags.py, recipeGen4B.py, and skuCostLookup.py already separate
"compute" from "render" per their own GUI notes. This dispatcher is the
first real consumer of that separation -- see the "KNOWN GAPS" section
at the bottom for the any modules that AREN'T actually ready yet, even if
its docstring claims it is.

Two kinds of context:
  - ONE-SHOT  (auto_exit=True):  runs once, prints its report, returns
    to the main menu automatically. checkNewFlags, recipeGen4B,
    day-of-week, sub-months all fall here -- there's nothing to "stay
    inside" between runs.
  - INTERACTIVE (auto_exit=False): loops on its own sub-prompt (SKU
    lookups, SKU parsing) until you type 'menu' or 'exit', then returns
    to the main menu. Also supports 'reload' inside the loop, since your
    workflow edits CSVs in Excel between CLI visits -- typing a SKU
    twice in a row should not require leaving and re-entering the
    context just to pick up a hand-added recipe row.

DATA CACHING
------------
ShopData lazily loads InventoryData.csv / RecipesData.csv / the sales
export and caches them for the session. Every context forces a fresh
reload on entry (force_reload=True) since the whole point of this tool
is "edit CSV in Excel, hop back to CLI" -- a stale cache would silently
show you yesterday's data. Interactive contexts also expose a manual
'reload' command for edits made without leaving the context.
"""

import sys

from shopIO import load_inventory, load_recipes, load_valid_sales_rows
from cliPrompts import QuitRequested, prompt_yes_no, prompt_input

import checkNewFlags
import recipeGen4B
import skuCostLookup
import skuParser
import countOrdersDayOfWeek
import countOrdersSubMonths
import salesToTrendsGen
import addSale
import trendsParser


MENU_COMMANDS = ('menu', 'exit', 'quit', 'q')


class ReturnToMenu(Exception):
    """Raised by prompt_loop_input() when the user types a menu-return
    command (MENU_COMMANDS) inside one of shopCLI's interactive
    sub-loops. Distinct from cliPrompts.QuitRequested, which aborts a
    single in-progress order/entry -- this unwinds the whole sub-loop
    back to the main dispatcher menu instead. Single consumer (this
    file, three call sites) -- if a second script ever needs the same
    idiom, promote it to cliPrompts.py then, not before."""
    pass


def prompt_loop_input(prompt):
    """input() wrapper for shopCLI's interactive sub-loops (SKU Cost
    Lookup, SKU Parser, Add Sale). Raises ReturnToMenu on any of
    MENU_COMMANDS instead of making every call site hand-check the same
    tuple. Returns the raw, stripped (but NOT lowercased) value
    otherwise -- callers still own their own '' / 'reload' handling,
    since that differs per context (ctx_add_sale folds its reload check
    into a differently-worded prompt than the other two)."""
    value = input(prompt).strip()
    if value.lower() in MENU_COMMANDS:
        raise ReturnToMenu()
    return value

from datetime import datetime

def prompt_optional_date(prompt):
    """Local wrapper around cliPrompts.prompt_date()'s validation loop,
    for trendsParser's start/end date bounds -- unlike every other date
    prompt in this project, either bound here is legitimately optional
    (open-ended range), so blank input returns None instead of re-
    prompting. Kept local to shopCLI.py, not promoted to cliPrompts.py --
    single consumer.

    Returns a raw datetime, not a formatted string: trendsParser.
    filter_records_by_date() compares directly against each record's
    datetime, it doesn't write these to CSV, so there's no CSV-format
    step to apply here the way prompt_date()'s callers need.
    """
    while True:
        raw = prompt_input(prompt)
        if not raw:
            return None
        try:
            return datetime.strptime(raw, "%m/%d/%Y")
        except ValueError:
            print(f"  Could not parse '{raw}' as mm/dd/yyyy -- try again, or leave blank to skip.")

# ---------------------------------------------------------------------
# Shared, lazily-loaded CSV data
# ---------------------------------------------------------------------
class ShopData:
    def __init__(self):
        self.inventory_path = 'InventoryData.csv'
        self.recipes_path = 'RecipesData.csv'
        self.sales_path = 'ShopSales.csv'
        self.trends_path = 'ShopTrends.csv'
        self._inventory = None
        self._recipes = None
        self._sales_rows = None
        self._sales_warnings = None

    def inventory(self, force_reload=False):
        if self._inventory is None or force_reload:
            self._inventory = load_inventory(self.inventory_path)
        return self._inventory

    def recipes(self, force_reload=False):
        if self._recipes is None or force_reload:
            self._recipes = load_recipes(self.recipes_path)
        return self._recipes

    def sales_rows(self, force_reload=False):
        if self._sales_rows is None or force_reload:
            self._sales_rows, self._sales_warnings = load_valid_sales_rows(self.sales_path)
        return self._sales_rows, self._sales_warnings

    def configure_paths(self):
        """Lets the person repoint at different CSVs mid-session instead
        of only at startup. Blank input keeps the current path."""
        print(f"\nCurrent paths (blank = keep current):")
        inv = input(f"  Inventory CSV [{self.inventory_path}]: ").strip()
        rec = input(f"  Recipes CSV   [{self.recipes_path}]: ").strip()
        sal = input(f"  Sales CSV     [{self.sales_path}]: ").strip()
        trn = input(f"  Trends CSV    [{self.trends_path}] (reference file, optional): ").strip()
        if inv:
            self.inventory_path = inv
        if rec:
            self.recipes_path = rec
        if sal:
            self.sales_path = sal
        if trn:
            self.trends_path = trn
        print("  \u2713 paths updated (will load fresh next time a context needs them)")


def _print_warnings(warnings):
    if warnings:
        print(f"\n\u26a0\ufe0f  {len(warnings)} warning(s) while loading data:")
        for w in warnings:
            print(f"  - {w}")


def _safe_load(label, fn):
    """Every context loads data on entry; a missing/broken CSV shouldn't
    crash the whole CLI session, just that one context. Returns the
    loaded value or None on failure."""
    try:
        return fn()
    except FileNotFoundError as e:
        print(f"\n\u274c Could not load {label}: {e}")
        print("   Check the path (main menu -> 'p' to reconfigure paths).")
        return None
    except Exception as e:
        print(f"\n\u274c Error loading {label}: {e}")
        return None


# ---------------------------------------------------------------------
# ONE-SHOT contexts
# ---------------------------------------------------------------------
def ctx_check_new_flags(data):
    recipes = _safe_load('RecipesData.csv', lambda: data.recipes(force_reload=True))
    if recipes is None:
        return
    skus = list(recipes.keys())
    report = checkNewFlags.run_checks(skus)
    checkNewFlags.render_report_cli(report)


def ctx_recipe_gen_4b(data):
    inventory = _safe_load('InventoryData.csv', lambda: data.inventory(force_reload=True))
    recipes = _safe_load('RecipesData.csv', lambda: data.recipes(force_reload=True))
    if inventory is None or recipes is None:
        return

    report = recipeGen4B.build_generation_report(inventory, recipes)
    recipeGen4B.render_report_cli(report)

    if not report['recipes']:
        print("\n(No new recipes generated -- nothing to save.)")
        return

    try:
        save = prompt_yes_no("\nSave these to a file? (y/n): ")
    except QuitRequested:
        print("\nCancelled -- nothing saved.")
        return

    if not save:
        print("Not saved. Re-run this context after adding more 4B recipes to try again.")
        return

    output_path = input("Output path (or Enter for Local/TempMissingRecipes.csv): ").strip()
    if not output_path:
        output_path = 'Local/TempMissingRecipes.csv'
    recipeGen4B.write_recipes_csv(report['recipes'], output_path)
    print(f"\n\u2713 Saved to {output_path}. Copy/paste the rows you want into RecipesData.csv,")
    print("  then run 'Check New Flags' again to confirm the conversion is complete.")


def ctx_day_of_week(data):
    if _safe_load('ShopSales.csv', lambda: True) is None:
        return
    rows, warnings = data.sales_rows(force_reload=True)
    _print_warnings(warnings)
    result = countOrdersDayOfWeek.compute_day_of_week_counts(rows)
    countOrdersDayOfWeek.render_report_cli(result)


def ctx_sub_months(data):
    if _safe_load('ShopSales.csv', lambda: True) is None:
        return
    rows, warnings = data.sales_rows(force_reload=True)
    _print_warnings(warnings)
    result = countOrdersSubMonths.compute_order_ranges(rows)
    countOrdersSubMonths.render_report_cli(result)


def ctx_sales_to_trends(data):
    """salesToTrendsGen.py builds its own line-item view of the sales
    CSV rather than consuming ShopData.sales_rows() -- it needs quantity
    per SKU per order, not the same shape the day-of-week/sub-months
    reports use -- so this calls generate_trends_report() directly on
    the configured paths instead of going through the shared cache.
    Reference-file comparison is optional: if data.trends_path doesn't
    exist on disk, this just generates and offers to save."""
    import os as _os
    if not _os.path.isfile(data.sales_path):
        print(f"\n\u274c Could not find sales CSV at '{data.sales_path}'.")
        print("   Check the path (main menu -> 'p' to reconfigure paths).")
        return

    report = salesToTrendsGen.generate_trends_report(data.sales_path, data.trends_path)

    print(f"  \u2713 {report['order_count']} orders with valid line items")
    print(f"  \u2713 {len(report['days'])} distinct sale days")
    _print_warnings(report['warnings'])

    if report['reference_days'] is None:
        print(f"\n  (no reference file found at '{data.trends_path}' -- skipping comparison)")
    else:
        print(f"\n  \u2713 compared against {len(report['reference_days'])} dated rows in '{data.trends_path}'")
        print("\n" + "-" * 60)
        salesToTrendsGen.render_diffs_cli(report['diffs'])

    if len(report['diffs']) > 0: 
        try:
            save = prompt_yes_no("\nSave generated trends to a file? (y/n): ")
        except QuitRequested:
            print("\nCancelled -- nothing saved.")
            return

        if not save:
            return
        output_path = input("Output path (or Enter for Local/TempTrendsGenerated.csv): ").strip()
        if not output_path:
            output_path = 'Local/TempTrendsGenerated.csv'
        salesToTrendsGen.write_trends_csv(report['days'], output_path)
        print(f"\n\u2713 Saved to {output_path}")


def ctx_trends_parser(data):
    if _safe_load('ShopSales.csv', lambda: True) is None:
        return
    rows, warnings = data.sales_rows(force_reload=True)
    _print_warnings(warnings)

    try:
        use_range = prompt_yes_no("\nFilter by date range? (y/n): ")
        start_date = end_date = None
        if use_range:
            start_date = prompt_optional_date("  Start date (mm/dd/yyyy, blank = no lower bound): ")
            end_date = prompt_optional_date("  End date (mm/dd/yyyy, blank = no upper bound): ")

        fine_grained = prompt_yes_no("Show fine-grained AETHER/SEASONS/CC sub-designs? (y/n): ")
    except QuitRequested:
        print("\nCancelled.")
        return

    top_raw = input("How many top entries per ranking? (Enter for all): ").strip()
    top_n = int(top_raw) if top_raw.isdigit() else None

    report = trendsParser.build_trends_report(
        rows, start_date=start_date, end_date=end_date, fine_grained_designs=fine_grained
    )
    trendsParser.render_report_cli(report, top_n=top_n)

# ---------------------------------------------------------------------
# INTERACTIVE contexts (own sub-loop; 'menu'/'exit' returns to main menu)
# ---------------------------------------------------------------------
def ctx_sku_cost_lookup(data):
    inventory = _safe_load('InventoryData.csv', lambda: data.inventory(force_reload=True))
    recipes = _safe_load('RecipesData.csv', lambda: data.recipes(force_reload=True))
    if inventory is None or recipes is None:
        return

    print("\nSKU Cost Lookup -- enter a SKU, 'reload' to re-read the CSVs, or 'menu'/'exit' to leave.")
    while True:
        try:
            user_input = prompt_loop_input("cost>>> ")
        except ReturnToMenu:
            return
        if not user_input:
            continue
        if user_input.lower() == 'reload':
            inventory = data.inventory(force_reload=True)
            recipes = data.recipes(force_reload=True)
            print("  \u2713 reloaded InventoryData.csv and RecipesData.csv")
            continue
        result = skuCostLookup.calculate_cost(user_input, inventory, recipes)
        print(skuCostLookup.format_output(result))


def ctx_sku_parser(data):
    print("\nSKU Parser -- enter a SKU, or 'menu'/'exit' to leave. (No CSV data needed.)")
    while True:
        try:
            user_input = prompt_loop_input("parse>>> ")
        except ReturnToMenu:
            return
        if not user_input:
            continue

        parsed = skuParser.parse_sku(user_input)
        if parsed.get('error'):
            print(f"\u274c {parsed['error']}")
        else:
            print(f"\u2705 {skuParser.readable_description(parsed)}")

def ctx_add_sale(data):
    inventory = _safe_load('InventoryData.csv', lambda: data.inventory(force_reload=True))
    recipes = _safe_load('RecipesData.csv', lambda: data.recipes(force_reload=True))
    if inventory is None or recipes is None:
        return

    print("\nAdd Sale -- enter orders one at a time.")
    print("At any prompt DURING an order, 'quit'/'exit'/'q' aborts just that order (nothing written).")
    print("At the prompt BELOW, 'menu'/'exit'/'quit'/'q' leaves this context entirely.")

    while True:
        try:
            start = prompt_loop_input(
                "\nPress Enter to start a new order "
                "('reload' to re-read CSVs, 'menu' to leave): "
            )
        except ReturnToMenu:
            return
        if start.lower() == 'reload':
            inventory = data.inventory(force_reload=True)
            recipes = data.recipes(force_reload=True)
            print("  \u2713 reloaded InventoryData.csv and RecipesData.csv")
            continue

        try:
            order_info = addSale.prompt_order_info()
            sku_lines = addSale.prompt_sku_lines(order_info['num_skus'])
        except addSale.QuitRequested:
            print("\nOrder aborted -- nothing written.")
            continue

        rows, warnings = addSale.compute_sale_rows(order_info, sku_lines, inventory, recipes)
        verification = addSale.verify_payment_amount(rows, order_info)

        addSale.render_preview_cli(rows)
        addSale.render_warnings_cli(warnings)
        addSale.render_verification_cli(verification)

        try:
            if not verification['is_valid']:
                proceed = prompt_yes_no("\nMismatch found above. Write anyway? (y/n): ")
                if not proceed:
                    print("Aborted -- nothing written. Re-run to re-enter the order.")
                    continue

            confirm = prompt_yes_no("\nWrite these rows to the sales CSV? (y/n): ")
        except QuitRequested:
            print("\nOrder aborted -- nothing written.")
            continue

        if not confirm:
            print("Not written. Order discarded.")
            continue

        output_path = input("Output path (or Enter for Local/TempNewSales.csv): ").strip()
        if not output_path:
            output_path = 'Local/TempNewSales.csv'
        addSale.write_sales_csv_rows(rows, output_path)
        print(f"\n\u2713 Appended {len(rows)} row(s) to {output_path}")

# ---------------------------------------------------------------------
# Menu registry: (key, label, run_fn, auto_exit)
# ---------------------------------------------------------------------
CONTEXTS = [
    ('1', 'SKU Parser             (interactive, readable descriptions)', ctx_sku_parser,     False),
    ('2', 'SKU Cost Lookup        (interactive)',                      ctx_sku_cost_lookup, False),
    ('3', 'Check New Flags        (recipe vs. skuVocab audit)',        ctx_check_new_flags, True),
    ('4', 'Recipe Gen 4B          (generate 4C/6P/8R from 4B)',        ctx_recipe_gen_4b,   True),
    ('5', 'Add Sale               (interactive, one order at a time)', ctx_add_sale,        False),
    ('6', 'Sales -> Trends Generator (vs. reference file, if present)', ctx_sales_to_trends, True),
    ('7', 'Trends Parser          (design/jewelry-type rankings, date filter)', ctx_trends_parser, True),
    ('8', 'Orders by Day of Week',                                     ctx_day_of_week,     True),
    ('9', 'Orders by Month Third',                                     ctx_sub_months,      True),
]


def print_menu(data):
    print("\n" + "=" * 60)
    print("PYRRHIC SILVA CRAFTS - unified CLI")
    print("=" * 60)
    for key, label, _fn, auto_exit in CONTEXTS:
        tag = '' if auto_exit else '  [interactive]'
        print(f"  {key}) {label}{tag}")
    print(f"  p) Reconfigure CSV paths")
    print(f"  q) Quit")
    print(f"\n  Inventory: {data.inventory_path}   Recipes: {data.recipes_path}")
    print(f"  Sales: {data.sales_path}   Trends (reference): {data.trends_path}")


def main():
    data = ShopData()
    context_map = {key: (fn, auto_exit) for key, _label, fn, auto_exit in CONTEXTS}

    while True:
        print_menu(data)
        choice = input("\nSelect an option: ").strip().lower()

        if choice in ('q', 'quit', 'exit'):
            print("\nHave a nice day!\n")
            return

        if choice == 'p':
            data.configure_paths()
            continue

        if choice not in context_map:
            print(f"\nUnrecognized option '{choice}'.")
            continue

        fn, auto_exit = context_map[choice]
        try:
            fn(data)
        except KeyboardInterrupt:
            print("\n\n(Interrupted -- returning to main menu.)")
        except Exception as e:
            print(f"\n\u274c Unexpected error in this context: {e}")
            print("   Returning to main menu. This is worth investigating -- it means")
            print("   something threw instead of returning an error/warning as data.")

        # auto_exit contexts fall through to here immediately after one run;
        # interactive contexts only reach here once their own loop returns.
        input("\n(Press Enter to return to the main menu.)")


if __name__ == '__main__':
    main()