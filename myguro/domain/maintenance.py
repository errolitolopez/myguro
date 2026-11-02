"""Maintenance mode: the admin closes MyGuro to everyone else for a while. The rules here have no database or Flask."""

from myguro.domain.text import clean_name
from myguro.errors import ValidationError

MAX_MESSAGE_LENGTH = 200
DEFAULT_MESSAGE = "MyGuro is down for maintenance. Please try again in a little while."

# The only people who can still use MyGuro while it is on. Everyone else sees the maintenance page.
ALLOWED_ROLES = ("admin",)


def clean_message(value):
    """The admin's note for the maintenance page as one short line, or "" for none (the default text is used then).
    Raises ValidationError when it is too long."""
    message = clean_name(value)
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValidationError(f"The message is too long (at most {MAX_MESSAGE_LENGTH} characters).")
    return message


def blocks(role):
    """True when this role is kept out during maintenance. A person who is not logged in has no role ("")."""
    return role not in ALLOWED_ROLES
