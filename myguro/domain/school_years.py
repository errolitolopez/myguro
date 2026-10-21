"""School year names."""

import re

from myguro.errors import ValidationError

# "2026-2027": two years in a row, so the list sorts and reads the same everywhere.
NAME_PATTERN = re.compile(r"^(\d{4})-(\d{4})$")


def check_year_name(value):
    """The school year name, like "2026-2027" (the second year is the one after the first)."""
    name = (value or "").strip() if isinstance(value, str) else ""
    match = NAME_PATTERN.match(name)
    if not match or int(match.group(2)) != int(match.group(1)) + 1:
        raise ValidationError('Write the school year like "2026-2027".')
    return name
