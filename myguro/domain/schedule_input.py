"""Cleaning what the admin types for the schedule generator (no database, no Flask)."""

from myguro.domain.schedule import DAYS, PERIOD_TIMES
from myguro.domain.text import clean_name
from myguro.errors import ValidationError

MAX_NAME_LENGTH = 100
MAX_SHORT_LENGTH = 30
MAX_PER_WEEK = DAYS * len(PERIOD_TIMES)


def _short(value, label, limit=MAX_SHORT_LENGTH, required=False):
    text = clean_name(value)
    if required and not text:
        raise ValidationError(f"{label} is required.")
    if len(text) > limit:
        raise ValidationError(f"{label} can be at most {limit} characters.")
    return text


def clean_whole(value, label, low, high, required=True):
    if value in (None, ""):
        if required:
            raise ValidationError(f"{label} is required.")
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValidationError(f"{label} must be a whole number from {low} to {high}.")
    return value


def clean_section(data):
    """(name, grade, room, adviser)."""
    return (_short(data.get("name"), "Section name", MAX_NAME_LENGTH, required=True),
            _short(data.get("grade"), "Grade"), _short(data.get("room"), "Room"),
            _short(data.get("adviser"), "Adviser", MAX_NAME_LENGTH))


def clean_teacher(data):
    """(name, user id or None, max gap or None, max per day or None, sorted [(day, period)] they cannot teach)."""
    blocked = set()
    for item in data.get("blocked") or []:
        if not (isinstance(item, (list, tuple)) and len(item) == 2):
            raise ValidationError("Choose the unavailable periods again.")
        day = clean_whole(item[0], "Day", 0, DAYS - 1)
        period = clean_whole(item[1], "Period", 0, len(PERIOD_TIMES) - 1)
        blocked.add((day, period))
    return (_short(data.get("name"), "Teacher name", MAX_NAME_LENGTH, required=True),
            clean_whole(data.get("user_id"), "Account", 1, 10**9, required=False),
            clean_whole(data.get("max_gap"), "Longest gap", 0, len(PERIOD_TIMES), required=False),
            clean_whole(data.get("max_per_day"), "Most periods a day", 1, len(PERIOD_TIMES), required=False),
            sorted(blocked))


def clean_assignment(data):
    """(section id, subject, teacher id, periods a week). The subject is kept in capitals ("philo" -> "PHILO")."""
    return (clean_whole(data.get("section_id"), "Section", 1, 10**9),
            _short(data.get("subject"), "Subject", required=True).upper(),
            clean_whole(data.get("teacher_id"), "Teacher", 1, 10**9),
            clean_whole(data.get("per_week"), "Periods a week", 1, MAX_PER_WEEK))
