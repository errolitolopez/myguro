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


def clean_range(start, end):
    """(first day, last day) as "YYYY-MM-DD" or None for "no limit". Both days are included."""
    days = []
    for value in (start, end):
        if value in (None, ""):
            days.append(None)
            continue
        try:
            days.append(date.fromisoformat(value).isoformat() if isinstance(value, str) and len(value) == 10 else None)
        except ValueError:
            days.append(None)
        if days[-1] is None:
            raise ValidationError("Choose a valid date.")
    if days[0] and days[1] and days[0] > days[1]:
        raise ValidationError("The first day must not be after the last day.")
    return tuple(days)


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
