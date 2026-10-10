"""Rules for accounts: names, usernames, passwords, grades and sections."""

import re
import secrets
import unicodedata

from myguro.domain.text import clean_name
from myguro.errors import ValidationError

ROLES = ("admin", "teacher", "student")
ACCOUNT_ROLES = ("teacher", "student")  # the ones the admin manages

USERNAME_PATTERN = re.compile(r"[a-z0-9._-]{3,30}")
MIN_PASSWORD_LENGTH = 6
MAX_NAME_LENGTH = 100
MAX_SECTION_LENGTH = 50
# Grade levels a student can have (or none). Shown as a dropdown so the values stay the same.
GRADES = ["Kinder"] + [f"Grade {number}" for number in range(1, 13)]
# Temporary passwords leave out letters and digits that look alike (l, 1, o, 0).
TEMP_PASSWORD_LETTERS = "abcdefghjkmnpqrstuvwxyz23456789"


def make_temp_password():
    return "".join(secrets.choice(TEMP_PASSWORD_LETTERS) for _ in range(10))


# --- Person names: Last name, First name, Middle initial (optional) ------------------------

MAX_NAME_PART_LENGTH = 50
NAME_FORMAT_HELP = "Write the name as Last name, First name (e.g. Altamerano, Rian Joshua)."


def display_name(last_name, first_name, middle_initial=""):
    """"Altamerano, Rian Joshua J." — how a person's name is shown and sorted (by last name)."""
    return f"{last_name}, {first_name}" + (f" {middle_initial}." if middle_initial else "")


def clean_middle_initial(value):
    """"m", "M." or a whole middle name "Mendoza" -> "M". Empty when there is none."""
    text = clean_name(value).replace(".", "").strip()
    if not text:
        return ""
    if not text[0].isalpha():
        raise ValidationError("The middle initial must be a letter.")
    return text[0].upper()


def clean_person_name(last_name, first_name, middle_initial=""):
    """(last name, first name, middle initial), cleaned and checked."""
    parts = []
    for label, value in (("Last name", last_name), ("First name", first_name)):
        value = clean_name(value)
        if not value:
            raise ValidationError(f"{label} is required.")
        if len(value) > MAX_NAME_PART_LENGTH:
            raise ValidationError(f"{label} can be at most {MAX_NAME_PART_LENGTH} characters.")
        parts.append(value)
    return parts[0], parts[1], clean_middle_initial(middle_initial)


def split_full_name(text):
    """One text "Last, First" or "Last, First, M" or "Last, First M." -> (last, first, middle).
    The comma is required: "Juan Dela Cruz" can't be split safely."""
    text = clean_name(text)
    parts = [part.strip() for part in text.split(",")]
    if len(parts) < 2 or len(parts) > 3:
        raise ValidationError(NAME_FORMAT_HELP)
    last, first = parts[0], parts[1]
    middle = parts[2] if len(parts) == 3 else ""
    words = first.split()
    # "Santos, Maria Clara M." : a single letter at the end of the first name is the middle initial
    if not middle and len(words) > 1 and len(words[-1].rstrip(".")) == 1 and words[-1][0].isalpha():
        middle, first = words[-1], " ".join(words[:-1])
    return clean_person_name(last, first, middle)


def guess_name_parts(name):
    """For names saved before the Last, First format: split at commas if there are any,
    otherwise the last word is the last name ("Juan Dela Cruz" -> Cruz, Juan Dela)."""
    try:
        return split_full_name(name)
    except ValidationError:
        words = clean_name(name).split()
        if len(words) < 2:
            return clean_name(name) or "?", "?", ""
        return words[-1], " ".join(words[:-1]), ""


def name_from_request(data, current=None):
    """(last, first, middle) from posted data: last_name / first_name / middle_initial, or one
    "name" text with commas. current = the person's name parts now (for changing only some)."""
    if any(key in data for key in ("last_name", "first_name", "middle_initial")):
        last, first, middle = current or ("", "", "")
        return clean_person_name(data.get("last_name", last), data.get("first_name", first),
                                 data.get("middle_initial", middle))
    if "name" in data:
        return split_full_name(data["name"])
    if current:
        return current
    raise ValidationError("Last name is required.")


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


def suggest_username(first_name, last_name):
    """"Rian Joshua" + "Altamerano" -> "raltamerano" (first letter of the first name + the
    last name, without spaces), the same as the add-account form suggests. ñ -> n, é -> e."""
    def plain(text):
        text = unicodedata.normalize("NFD", text)
        text = "".join(char for char in text if not unicodedata.combining(char)).lower()
        return "".join(char for char in text if char.isascii() and char.isalnum())
    first, last = plain(first_name), plain(last_name)
    return ((first[:1] + last) or first)[:30]


def grade_from_text(value):
    """A grade as people type it in a spreadsheet: "Grade 9", "grade 9", "9", 9, "Kinder", "K".
    Returns the grade as stored ("Grade 9", "Kinder", "" for none), or ValidationError."""
    text = clean_name(value).lower()
    if not text:
        return ""
    if text in ("k", "kinder", "kindergarten"):
        return "Kinder"
    number = text.removeprefix("grade").strip()
    grade = f"Grade {int(number)}" if number.isdigit() else None
    if grade not in GRADES:
        raise ValidationError("Choose a grade from the list.")
    return grade
