"""The "Support MyGuro" link shown to admin and teachers (never to students), and the teacher pop-up."""

import re
from urllib.parse import urlparse

from myguro.domain.text import clean_name
from myguro.errors import ValidationError

MAX_MESSAGE_LENGTH = 200
MAX_LABEL_LENGTH = 30
MAX_URL_LENGTH = 300
MAX_GCASH_NAME_LENGTH = 60

DEFAULT_MESSAGE = "Enjoying MyGuro? Help keep it running."
DEFAULT_LABEL = "Support MyGuro"

# When the support window opens by itself for a teacher: never, once per login, once a day
# (while logged in), or on every page.
POPUP_MODES = ("off", "login", "daily", "always")
DEFAULT_POPUP = "off"


def popup_due(mode, last_shown_day, today):
    """True if the support window should open now. last_shown_day is the ISO day it last opened
    in this login (None if not yet); today is the ISO day now."""
    if mode == "always":
        return True
    if mode == "login":
        return last_shown_day is None
    if mode == "daily":
        return last_shown_day != today
    return False


def clean_gcash_number(value):
    """A Philippine mobile number as 09XXXXXXXXX, from "0917 123 4567", "+63 917 123 4567",
    "0917-123-4567" or "". Raises ValidationError for anything else."""
    text = re.sub(r"[\s\-()]", "", str(value or ""))
    if not text:
        return ""
    if text.startswith("+63"):
        text = "0" + text[3:]
    elif text.startswith("63") and len(text) == 12:
        text = "0" + text[2:]
    if not re.fullmatch(r"09\d{9}", text):
        raise ValidationError("GCash number must be a mobile number like 0917 123 4567.")
    return text


def format_gcash_number(number):
    """09171234567 -> "0917 123 4567" (empty stays empty)."""
    return f"{number[:4]} {number[4:7]} {number[7:]}" if len(number) == 11 else number


def clean_support(data):
    """(enabled, message, label, url, gcash_number, gcash_name, popup) from posted data. An empty
    message or label uses the default text, a missing popup is off. To turn it on there must be a link (a web address,
    http or https) or a GCash number."""
    enabled = data.get("enabled")
    if not isinstance(enabled, bool):
        raise ValidationError("Choose whether to show the support link.")
    message = clean_name(data.get("message")) or DEFAULT_MESSAGE
    label = clean_name(data.get("label")) or DEFAULT_LABEL
    url = clean_name(data.get("url"))
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValidationError(f"Message can be at most {MAX_MESSAGE_LENGTH} characters.")
    if len(label) > MAX_LABEL_LENGTH:
        raise ValidationError(f"Button text can be at most {MAX_LABEL_LENGTH} characters.")
    if url:
        parsed = urlparse(url)
        if len(url) > MAX_URL_LENGTH or parsed.scheme not in ("http", "https") or not parsed.netloc or " " in url:
            raise ValidationError("Link must be a web address starting with http:// or https://.")
    gcash_number = clean_gcash_number(data.get("gcash_number"))
    gcash_name = clean_name(data.get("gcash_name"))
    if len(gcash_name) > MAX_GCASH_NAME_LENGTH:
        raise ValidationError(f"GCash name can be at most {MAX_GCASH_NAME_LENGTH} characters.")
    popup = data.get("popup", DEFAULT_POPUP)
    if popup not in POPUP_MODES:
        raise ValidationError("Choose when to show the pop-up from the list.")
    if enabled and not url and not gcash_number:
        raise ValidationError("Add a link or a GCash number before turning the support link on.")
    return enabled, message, label, url, gcash_number, gcash_name, popup
