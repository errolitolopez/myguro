"""Taking a complete, consistent copy of the database while the app may be writing to it."""

import os
import sqlite3
import tempfile
from datetime import datetime

from myguro.config import SCHOOL_TIMEZONE

BACKUP_PREFIX = "myguro-"
BACKUP_SUFFIX = ".db"


def backup_to(source_path, target_path):
    """Copy the database at `source_path` to `target_path` with SQLite's own online backup. Unlike copying
    the file, it is a valid database even if the app writes at the same moment."""
    source = sqlite3.connect(source_path)
    target = sqlite3.connect(target_path)
    try:
        with target:
            source.backup(target)
    finally:
        target.close()
        source.close()


def backup_bytes(source_path):
    """The same copy, as bytes (for a download). The temporary file is removed at once."""
    handle, temp_path = tempfile.mkstemp(suffix=BACKUP_SUFFIX)
    os.close(handle)
    try:
        backup_to(source_path, temp_path)
        with open(temp_path, "rb") as copy:
            return copy.read()
    finally:
        os.remove(temp_path)


def backup_name(now=None):
    """"myguro-2026-10-16-103000-123456.db": the time at the school down to the microsecond, so names sort by
    date and two backups taken in the same second never share a name."""
    now = now or datetime.now(SCHOOL_TIMEZONE)
    return f"{BACKUP_PREFIX}{now:%Y-%m-%d-%H%M%S-%f}{BACKUP_SUFFIX}"


def prune(folder, keep):
    """Delete the oldest backups in `folder`, keeping the newest `keep`. Only files named like a backup are
    touched. Returns the names removed."""
    names = sorted(name for name in os.listdir(folder)
                   if name.startswith(BACKUP_PREFIX) and name.endswith(BACKUP_SUFFIX))
    removed = names[:-keep] if keep < len(names) else []
    for name in removed:
        os.remove(os.path.join(folder, name))
    return removed
