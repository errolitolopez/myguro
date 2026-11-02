"""Time in / time out for teachers: the rules, with no database and no Flask."""

from datetime import datetime, timedelta

# A time in with no time out for longer than this is taken as forgotten: it stays on the record without a time out
# and no longer stops the teacher from timing in again.
MAX_OPEN_HOURS = 16
MAX_RANGE_DAYS = 62  # the longest span of days the admin can look at
HISTORY_DAYS = 14  # how many days back a teacher sees
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def to_text(moment):
    """to_text(aware UTC datetime) -> "2026-11-02 07:30:00" (the way SQLite and the rest of the app keep UTC)."""
    return moment.strftime(TIME_FORMAT)


def from_text(text):
    return datetime.strptime(text, TIME_FORMAT)


def is_open(time_in_text, now):
    """True when a time in (UTC text) is recent enough to still be waiting for its time out."""
    return now.replace(tzinfo=None) - from_text(time_in_text) < timedelta(hours=MAX_OPEN_HOURS)


def seconds_between(time_in_text, time_out_text):
    """seconds_between("2026-11-02 00:00:00", "2026-11-02 01:30:00") -> 5400"""
    return int((from_text(time_out_text) - from_text(time_in_text)).total_seconds())


def day_total(sessions):
    """Seconds worked in these sessions ({time_in, time_out}); a session without a time out adds nothing."""
    return sum(seconds_between(s["time_in"], s["time_out"]) for s in sessions if s["time_out"])
