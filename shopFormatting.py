"""
shopFormatting.py - Pyrrhic Silva Shop

SINGLE SOURCE OF TRUTH for the currency, date, and order-ID display/
export string formats used across this project.

Every function here validates its input and RAISES on bad input rather
than returning a sentinel or silently coercing -- unlike the rest of
this project's compute functions (skuCostLookup, shopIO, etc.), which
return (value, warning) so a caller can surface problems without a
crash. Formatting is different: there is no sensible "partial" or
"best-effort" currency string for a non-numeric value, and a bad order
ID or unparseable date is virtually always an upstream bug (a caller
passing the wrong field) rather than something a human needs to be
warned about and continue past. Consumers wrap calls in their own
try/except and decide whether to re-prompt (interactive input) or show
an error (batch/GUI processing) -- this module never makes that
decision for them.
"""

from datetime import date as _date, datetime as _datetime


def currencyFormatCSV(num):
    """'X.XX' formatting for currency exported to CSV. Plain fixed-point
    string -- no currency symbol, no sign styling. Raises TypeError if
    `num` isn't an int or float (bool excluded, since True/False aren't
    meaningfully currency)."""
    if isinstance(num, bool) or not isinstance(num, (int, float)):
        raise TypeError(f"currencyFormatCSV expected a number, got {type(num).__name__}: {num!r}")
    return f"{num:.2f}"


def currencyFormatUI(num):
    """'$X.XX' for num >= 0, '$(X.XX)' for num < 0, for UI display.
    Same input validation as currencyFormatCSV."""
    if isinstance(num, bool) or not isinstance(num, (int, float)):
        raise TypeError(f"currencyFormatUI expected a number, got {type(num).__name__}: {num!r}")
    if num < 0:
        return f"$({abs(num):.2f})"
    return f"${num:.2f}"


def dateFormatCSV(date):
    """'{month}/{day}/{year}' formatting for dates exported to CSV
    (no zero-padding). Raises ValueError if `date` isn't a
    datetime.date or datetime.datetime instance."""
    if not isinstance(date, (_date, _datetime)):
        raise ValueError(f"dateFormatCSV expected a date/datetime object, got {type(date).__name__}: {date!r}")
    return f"{date.month}/{date.day}/{date.year}"


def dateFormatUI(date):
    """'{Weekday, Month} {day}, {year}' formatting for dates displayed
    to UI. Same input validation as dateFormatCSV."""
    if not isinstance(date, (_date, _datetime)):
        raise ValueError(f"dateFormatUI expected a date/datetime object, got {type(date).__name__}: {date!r}")
    return f"{date.strftime('%A, %B')} {date.day}, {date.year}"


def orderIDFormatUI(orderID):
    """'XXXX-XXX-XXX' formatting for order numbers displayed to UI.
    Raises ValueError unless the input is exactly 10 characters, all
    digits, once whitespace is stripped -- matches the same 10-digit
    rule addSale.py's _prompt_order_number() already enforces at entry."""
    s = str(orderID).strip()
    if len(s) != 10 or not s.isdigit():
        raise ValueError(f"orderIDFormatUI expected exactly 10 digits, got {orderID!r}")
    return f"{s[:4]}-{s[4:7]}-{s[7:10]}"