"""The password a teacher puts on a downloaded answer key (PDF or Word)."""

from myguro.domain.accounts import MIN_PASSWORD_LENGTH
from myguro.errors import ValidationError

MAX_FILE_PASSWORD_LENGTH = 100


def clean_file_password(password):
    """The password as typed, or ValidationError when it is missing, too short or too long."""
    password = password if isinstance(password, str) else ""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Type a password of at least {MIN_PASSWORD_LENGTH} characters for the file.")
    if len(password) > MAX_FILE_PASSWORD_LENGTH:
        raise ValidationError(f"The file password can have at most {MAX_FILE_PASSWORD_LENGTH} characters.")
    return password
