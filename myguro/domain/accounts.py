"""Rules for accounts: names, usernames, passwords, grades and sections."""

import re
import secrets

from myguro.domain.text import clean_name
from myguro.errors import ValidationError

ROLES = ("admin", "teacher", "student")
ACCOUNT_ROLES = ("teacher", "student")  # the ones the admin manages

USERNAME_PATTERN = re.compile(r"[a-z0-9._-]{3,30}")
MIN_PASSWORD_LENGTH = 8
MAX_NAME_LENGTH = 100
MAX_SECTION_LENGTH = 50
# Grade levels a student can have (or none). Shown as a dropdown so the values stay the same.
GRADES = ["Kinder"] + [f"Grade {number}" for number in range(1, 13)]
# Temporary passwords leave out letters and digits that look alike (l, 1, o, 0).
TEMP_PASSWORD_LETTERS = "abcdefghjkmnpqrstuvwxyz23456789"


def make_temp_password():
    return "".join(secrets.choice(TEMP_PASSWORD_LETTERS) for _ in range(10))


def check_name(name, label="Name"):
    """A cleaned name, or ValidationError."""
    if not name:
        raise ValidationError(f"{label} is required.")
    if len(name) > MAX_NAME_LENGTH:
        raise ValidationError(f"{label} can be at most {MAX_NAME_LENGTH} characters.")
    return name


def clean_username(value):
    username = str(value or "").strip().lower()
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValidationError("Username must be 3 to 30 letters, numbers, dots, dashes or underscores, "
                              "with no spaces.")
    return username


def check_new_account_password(password):
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    return password


def check_password_change(username, current_password, new_password):
    """Rules for a new password chosen by the user (the current one is already checked)."""
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"New password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if new_password == current_password:
        raise ValidationError("New password must be different from the current one.")
    if new_password.lower() == username.lower():
        raise ValidationError("New password can't be the same as your username.")


def clean_grade_section(data):
    """(grade, section) from posted data: both optional (irregular students may have none)."""
    grade = clean_name(data.get("grade"))
    section = clean_name(data.get("section"))
    if grade and grade not in GRADES:
        raise ValidationError("Choose a grade from the list.")
    if len(section) > MAX_SECTION_LENGTH:
        raise ValidationError(f"Section can be at most {MAX_SECTION_LENGTH} characters.")
    return grade, section
