"""The language setting: which language a request wants, and filling a sentence with its values."""

import re

LANGUAGES = ("en", "tl")  # English, and Taglish (Tagalog with the everyday English words kept)
DEFAULT_LANGUAGE = "en"
LANGUAGE_COOKIE = "myguro-lang"

PLACEHOLDER = re.compile(r"\{(\w+)\}")


def language_from_cookie(value):
    """"tl" only when the cookie says exactly "tl"; anything else (none, empty, a wrong value) is English."""
    return value if value in LANGUAGES else DEFAULT_LANGUAGE


def translate(text, dictionary, values=None):
    """The dictionary's text for this English sentence, or the English sentence itself when it has none.
    Each {name} is then replaced with values["name"]; a name with no value is left as written.
    A regex, not str.format, so a stray brace in a sentence can never raise."""
    text = dictionary.get(text, text)
    values = values or {}
    return PLACEHOLDER.sub(lambda match: str(values.get(match.group(1), match.group(0))), text)
