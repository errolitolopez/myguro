"""Philippine holidays: the national ones worked out from the year, and the rules for a local holiday."""

from datetime import date, timedelta

from myguro.errors import ValidationError

MAX_NAME_LENGTH = 100
MIN_YEAR = 2000  # the calendar page and the API stay inside a sane range
MAX_YEAR = 2100

# What kind of day it is. "local" holidays are the ones the admin adds.
REGULAR = "regular"  # regular holiday: no classes
SPECIAL = "special"  # special non-working day: no classes
SPECIAL_WORKING = "special-working"  # a special day, but school goes on
LOCAL = "local"
KINDS = (REGULAR, SPECIAL, SPECIAL_WORKING, LOCAL)

# Fixed dates: (month, day, name, kind).
FIXED = [
    (1, 1, "New Year's Day", REGULAR),
    (2, 25, "EDSA People Power Revolution Anniversary", SPECIAL_WORKING),
    (4, 9, "Araw ng Kagitingan", REGULAR),
    (5, 1, "Labor Day", REGULAR),
    (6, 12, "Independence Day", REGULAR),
    (8, 21, "Ninoy Aquino Day", SPECIAL),
    (11, 1, "All Saints' Day", SPECIAL),
    (11, 30, "Bonifacio Day", REGULAR),
    (12, 8, "Feast of the Immaculate Conception", SPECIAL),
    (12, 24, "Christmas Eve", SPECIAL),
    (12, 25, "Christmas Day", REGULAR),
    (12, 30, "Rizal Day", REGULAR),
    (12, 31, "New Year's Eve", SPECIAL),
]


def easter_sunday(year):
    """Easter Sunday of a year (the usual Gregorian calendar calculation)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def last_monday(year, month):
    """The last Monday of a month (National Heroes Day is the last Monday of August)."""
    last = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    return last - timedelta(days=last.weekday())


def national_holidays(year):
    """The national holidays of a year as [{"day": "2026-04-03", "name": ..., "kind": ...}], by date.
    Days set by a yearly proclamation (Eid'l Fitr, Eid'l Adha, Chinese New Year, one-off days) are not here:
    the admin adds those as local holidays."""
    found = [(date(year, month, day), name, kind) for month, day, name, kind in FIXED]
    easter = easter_sunday(year)
    found += [(easter - timedelta(days=3), "Maundy Thursday", REGULAR),
              (easter - timedelta(days=2), "Good Friday", REGULAR),
              (easter - timedelta(days=1), "Black Saturday", SPECIAL),
              (last_monday(year, 8), "National Heroes Day", REGULAR)]
    return [{"day": day.isoformat(), "name": name, "kind": kind} for day, name, kind in sorted(found)]


def check_year(value):
    """The year to show, as a number between MIN_YEAR and MAX_YEAR."""
    try:
        year = int(value)
    except (TypeError, ValueError):
        raise ValidationError("Choose a valid year.") from None
    if not MIN_YEAR <= year <= MAX_YEAR:
        raise ValidationError("Choose a valid year.")
    return year


def check_holiday(data):
    """(day, name) of a local holiday from the request. Raises ValidationError with a short message."""
    day = data.get("day")
    try:
        parsed = date.fromisoformat(day) if isinstance(day, str) and len(day) == 10 else None
    except ValueError:
        parsed = None
    if parsed is None or not MIN_YEAR <= parsed.year <= MAX_YEAR:
        raise ValidationError("Choose a valid date.")
    name = " ".join(data.get("name").split()) if isinstance(data.get("name"), str) else ""
    if not name:
        raise ValidationError("Type the name of the holiday.")
    if len(name) > MAX_NAME_LENGTH:
        raise ValidationError(f"The name can be at most {MAX_NAME_LENGTH} characters.")
    return parsed.isoformat(), name
