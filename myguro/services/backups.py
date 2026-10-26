"""Backup use cases: remember when a backup was taken, and say how old the last one is."""

from datetime import datetime, timezone

from flask import current_app

from myguro import backup
from myguro.services.base import Service

LAST_BACKUP_KEY = "last_backup_at"
STALE_AFTER_DAYS = 7


def _now_text():
    """The current time as the database writes it: "2026-10-16 02:30:00" (UTC)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class BackupService(Service):
    def record(self):
        """Remember that a backup was just taken (no commit)."""
        self.settings.set(LAST_BACKUP_KEY, _now_text())

    def download(self):
        """A complete copy of the database as bytes, and a note that a backup was taken."""
        data = backup.backup_bytes(current_app.config["DATABASE"])
        self.record()
        # The file holds every account (with password hashes), so the log says who took it
        self.log("backup.downloaded", "settings", "Downloaded a backup of the database.")
        self.commit()
        return data

    def status(self):
        """{"last", "days", "stale"}: when the last backup was (UTC text), how many days ago, and whether the
        admin should be reminded (never, or more than STALE_AFTER_DAYS days ago)."""
        text = self.settings.get(LAST_BACKUP_KEY)
        if text is None:
            return {"last": None, "days": None, "stale": True}
        taken = datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - taken).days
        return {"last": text, "days": days, "stale": days > STALE_AFTER_DAYS}
