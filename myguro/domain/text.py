"""Cleaning typed text."""


def clean_name(value):
    """One line: trimmed, with runs of spaces made single ("  Maria   Santos " -> "Maria Santos")."""
    return " ".join(str(value or "").split())


def clean_description(value):
    """Several lines: keeps the line breaks and blank lines; only trims the ends
    (Windows line breaks become \\n)."""
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def normalize(text):
    """For checking typed answers: capital letters and extra spaces don't matter."""
    return " ".join(str(text).split()).casefold()


def like_pattern(text):
    """Search text -> a LIKE pattern that finds it anywhere. % and _ are wildcards in LIKE, so they
    are escaped: searching "50%" finds "50%". Use with: ... LIKE ? ESCAPE '\\'"""
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def whole_number(value, low, high):
    """True when value is an int (not True/False) from low to high."""
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high
