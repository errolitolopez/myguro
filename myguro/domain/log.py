"""Rules of the activity log that need no database: its categories, and day bounds in school time."""

from datetime import datetime, timedelta, timezone

from myguro.errors import ValidationError

CATEGORIES = ("sign-in", "accounts", "classes", "activities", "giving", "checking", "students", "settings")
LOG_ROLES = ("admin", "teacher", "student", "supervisor")
MAX_SUMMARY_LENGTH = 300  # a summary is one short sentence; longer text is cut


def day_bounds(day, timezone_info):
    """("2026-10-01 00:00:00", "2026-10-02 00:00:00"): the UTC start of a school-time day and the
    start of the next one, as stored in the log (compare with at >= start AND at < end)."""
    try:
        start = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone_info)
    except ValueError:
        raise ValidationError("Choose a valid date.") from None
    end = start + timedelta(days=1)
    as_utc = lambda moment: moment.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")  # noqa: E731
    return as_utc(start), as_utc(end)


def clean_summary(text):
    """One line for people to read, cut to MAX_SUMMARY_LENGTH."""
    text = " ".join(str(text).split())
    return text if len(text) <= MAX_SUMMARY_LENGTH else text[:MAX_SUMMARY_LENGTH - 1] + "…"
