"""Recovery code rules: how a code looks, how it is made and how a typed one is cleaned (no database, no Flask).

A recovery code lets a person who forgot their password choose a new one without the admin. It has to be
impossible to guess, so it is long and random, like the recovery keys of Microsoft or a crypto exchange:
25 characters in 5 groups of 5, about 124 bits. Only a hash of it is stored.
"""

import secrets

from myguro.errors import ValidationError

# Letters and digits without the ones that look alike (0 O, 1 I L), so a code can be read from a phone
# screen and typed by hand. 31 characters.
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
GROUPS = 5
GROUP_SIZE = 5
CODE_LENGTH = GROUPS * GROUP_SIZE


def make_code():
    """A new random code written in groups: "K7M2P-9XQ4T-W3HNB-E6RYC-5ZD8J"."""
    characters = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
    return format_code(characters)


def format_code(characters):
    """"K7M2P9XQ4T..." -> "K7M2P-9XQ4T-...": the groups people read and copy."""
    return "-".join(characters[start:start + GROUP_SIZE] for start in range(0, CODE_LENGTH, GROUP_SIZE))


def clean_code(text):
    """The code as stored and compared: capitals only, with no dashes, spaces or other marks, so
    "k7m2p 9xq4t-..." and the code as shown are the same. Raises ValidationError if it cannot be a code."""
    characters = "".join(char for char in str(text or "").upper() if char.isalnum())
    if len(characters) != CODE_LENGTH or any(char not in ALPHABET for char in characters):
        raise ValidationError("The recovery code is not right.")
    return characters
