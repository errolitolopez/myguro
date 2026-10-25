"""Attendance rules that need no database: the statuses and checking the day and the marks."""

from datetime import date

from myguro.errors import ValidationError

STATUSES = ("present", "late", "absent", "excused")


def clean_day(value, today):
    """The day as "YYYY-MM-DD". Today if empty; a day that has not come yet is refused."""
    if value in (None, ""):
        return today.isoformat()
    try:
        day = date.fromisoformat(value) if isinstance(value, str) and len(value) == 10 else None
    except ValueError:
        day = None
    if day is None:
        raise ValidationError("Choose a valid date.")
    if day > today:
        raise ValidationError("You can't take attendance for a day that has not come yet.")
    return day.isoformat()


def clean_marks(marks):
    """{student id: status, or None to clear} with the ids as numbers. Refuses anything else."""
    if not isinstance(marks, dict):
        raise ValidationError("Send the attendance as a list of students.")
    cleaned = {}
    for key, status in marks.items():
        if not str(key).isdigit() or (status is not None and status not in STATUSES):
            raise ValidationError("Each student must be present, late, absent or excused.")
        cleaned[int(key)] = status
    return cleaned
