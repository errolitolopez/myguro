"""The language setting: which language a request wants, and filling a sentence with its values."""

import re
from functools import lru_cache

LANGUAGES = ("en", "tl")  # English, and Taglish (Tagalog with the everyday English words kept)
DEFAULT_LANGUAGE = "en"
LANGUAGE_COOKIE = "myguro-lang"

PLACEHOLDER = re.compile(r"\{(\w+)\}")
# Values of these placeholders are words and places the server wrote ("Section 2, question 3", "Last name"), so they
# are translated too; every other value (a title, a name, a number) is kept exactly as it is.
TRANSLATED_VALUES = ("where", "label", "class_label", "DIRECT_CLASS_NAME", "verb")


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


@lru_cache(maxsize=None)
def message_pattern(key):
    """A key with {name} placeholders as a regex that matches a whole message and captures each value.
    The same name twice must match the same text."""
    parts = PLACEHOLDER.split(key)  # [text, name, text, name, ..., text]
    seen = set()
    regex = ""
    for index, part in enumerate(parts):
        if index % 2 == 0:
            regex += re.escape(part)
        elif part in seen:
            regex += f"(?P={part})"
        else:
            seen.add(part)
            regex += f"(?P<{part}>.+?)"
    return re.compile(r"\A" + regex + r"\Z", re.DOTALL)


def translate_message(text, dictionary):
    """A message the server wrote (an error answer) in the dictionary's language. The exact sentence first;
    else the key with {placeholders} that fits the whole message and has the most fixed text (so "Title can be at
    most {MAX_TITLE_LENGTH} characters." wins over "{label} can be at most {limit} characters."), so a message
    with a value in it ("Password must be at least 6 characters.") is found without the raise site changing, and
    the value is kept exactly. No match: the English text."""
    if text in dictionary:
        return translate(text, dictionary)
    best = None
    for key in dictionary:
        if "{" not in key:
            continue
        match = message_pattern(key).match(text)
        if match:
            fixed = len(PLACEHOLDER.sub("", key))
            if best is None or fixed > best[0]:
                best = (fixed, key, match)
    if best is None:
        return text
    _, key, match = best
    values = {name: translate_message(value, dictionary) if name in TRANSLATED_VALUES else value
              for name, value in match.groupdict().items()}
    return translate(key, dictionary, values)
