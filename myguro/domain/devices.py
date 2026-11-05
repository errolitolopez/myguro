"""Telling devices apart: the browser keeps a random id in a cookie, and the server keeps only a short hash of it
(no database, no Flask). Two accounts that signed in with the same id used the same browser, so the same phone or
computer. It is not proof of anything (a private tab or cleared cookies is a new device), only a pointer."""

import hashlib
import re
import secrets

COOKIE = "myguro-device"
COOKIE_MAX_AGE = 2 * 365 * 24 * 3600  # two years, in seconds
ID_LENGTH = 32  # hex characters
KEY_LENGTH = 8  # characters of the hash that are kept and shown
SHARED_AT_LEAST = 2  # accounts on one device before it is listed
MAX_SHARED_DEVICES = 100  # at most this many devices are listed


def new_device_id():
    """A random id for a browser that has none yet."""
    return secrets.token_hex(ID_LENGTH // 2)


def clean_device_id(value):
    """The id from the cookie when it has the right shape, else None (anything else is ignored, never trusted)."""
    return value if isinstance(value, str) and re.fullmatch(rf"[0-9a-f]{{{ID_LENGTH}}}", value) else None


def device_key(device_id):
    """What is kept and shown for a device: the first characters of the id's hash, in capitals ("3F9A2C10")."""
    return hashlib.sha256(device_id.encode()).hexdigest()[:KEY_LENGTH].upper()
