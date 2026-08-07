#!/usr/bin/env python3
"""
cliPrompts.py - Pyrrhic Silva Shop

SINGLE SOURCE OF TRUTH for interactive input() prompt mechanics shared
across this project's CLI scripts: the quit-command convention, and
loop-until-valid wrappers for integers, floats, yes/no answers, and
this project's mm/dd/yyyy sale-date format.

SCOPE: this module owns PROMPT MECHANICS only -- how to ask, validate,
and re-ask. It does not own business logic (what an order needs, what a
SKU means, what a valid discount percent range is) and it does not touch
files. That's the same boundary shopIO.py draws around file I/O and row
validation; this is the equivalent boundary for stdin/stdout interaction.
Anything script-specific (order-level field prompts, SKU-line prompts)
stays in that script, built ON TOP of these primitives -- see
addSale.py's prompt_order_info() / prompt_sku_lines() for the pattern.

Extracted from addSale.py, which was the first (and until this pass,
only) consumer. shopCLI.py's ad hoc y/n confirms in ctx_recipe_gen_4b()
and ctx_sales_to_trends() are the second demonstrated consumer -- see
Julien's "no speculative extraction" rule: two or more real consumers,
not preemptive infrastructure.

QUIT CONVENTION: every function here goes through _input() (directly or
via prompt_date()'s own _input() calls), so typing 'quit', 'exit', or
'q' at ANY prompt built on these primitives raises QuitRequested. A
calling script's own order/session loop is expected to catch that and
abort cleanly -- no partial writes, no traceback. The quit check always
happens before any format-specific parsing (int/float/date), never after.

NOT included here (deliberately):
  - _prompt_order_number() (addSale.py) -- the 10-digit-to-dashed-format
    reformatting is a sales-CSV-specific rule, not a generic prompt shape.
  - Any GUI equivalent -- this module is CLI-only by design, same as
    every render_report_cli() in this project. A GUI does its own input
    validation on whatever widget it uses; it does not call these.
"""

from datetime import datetime

QUIT_COMMANDS = ('quit', 'exit', 'q')
YES_VALUES = ('y', 'yes', 'true')
NO_VALUES = ('n', 'no', 'false')


class QuitRequested(Exception):
    """Raised when the user types a quit command at any input() prompt
    built on _input(), so the calling script's own loop can abort
    cleanly -- no file writes, no traceback."""
    pass


def prompt_input(prompt):
    """input() wrapper that raises QuitRequested if the user types a quit
    command, instead of returning it as a normal value to be parsed as a
    date/number/answer. Every prompt in this module goes through this
    first, so bailing out is possible at every step."""
    value = input(prompt).strip()
    if value.lower() in QUIT_COMMANDS:
        raise QuitRequested()
    return value


def prompt_int(prompt):
    """Loop on `prompt` until the input parses as an integer. Goes
    through _input() first on every attempt, so a quit command still
    aborts at any point -- the quit check always happens before the
    int() parse is even attempted."""
    while True:
        raw = prompt_input(prompt)
        try:
            return int(raw)
        except ValueError:
            print(f"  \u274c '{raw}' isn't a whole number. Try again.")


def prompt_float(prompt):
    """Loop on `prompt` until the input parses as a number (decimals
    fine). Same _input()-first ordering as prompt_int()."""
    while True:
        raw = prompt_input(prompt)
        try:
            return float(raw)
        except ValueError:
            print(f"  \u274c '{raw}' isn't a valid number. Try again.")


def prompt_yes_no(prompt):
    """Loop on `prompt` until the input is one of YES_VALUES or
    NO_VALUES (case-insensitive), returning True/False. This is the fix
    for the bug that motivated this module's extraction: a typo like
    'ys' must re-prompt, not silently fall through as 'no'."""
    while True:
        raw = prompt_input(prompt).lower()
        if raw in YES_VALUES:
            return True
        if raw in NO_VALUES:
            return False
        print("  \u274c Please answer y/yes/true or n/no/false. Try again.")


def prompt_date(prompt="Sale date (mm/dd/yyyy): "):
    """Prompt for a date in mm/dd/yyyy format, re-prompting on a
    bad/unparseable date instead of crashing (assumed to be a typo, not
    a quit request). Returns the date converted to Excel's expected
    date-string format ('8/12/2025'), matching day/month/year
    construction for import into master XLSX (day/month is NOT 
    zero-padded -- '5/4/2025', not '05/04/2025').

    `prompt` is overridable since not every future caller is necessarily
    asking about a "sale" date specifically, even though every current
    consumer is.
    """
    while True:
        raw = prompt_input(prompt)
        try:
            date_obj = datetime.strptime(raw, "%m/%d/%Y")
        except ValueError:
            print(f"  Could not parse '{raw}' as mm/dd/yyyy -- please try again.")
            continue
        return f"{date_obj.month}/{date_obj.day}/{date_obj.year}"