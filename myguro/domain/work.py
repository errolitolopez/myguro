"""Rules for assignments and students' work: due dates, late, tries, paper scores."""

from datetime import date

from myguro.domain.text import clean_name, whole_number
from myguro.errors import ValidationError

MAX_NOTE_LENGTH = 200


def clean_due_date(value, class_label):
    """"2026-10-15", or None for no due date."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError:
        raise ValidationError(f"{class_label}: the due date is not valid.") from None


def is_late(due_date, today):
    return bool(due_date and today.isoformat() > due_date)


def can_try_again(submission, max_attempts):
    """After submitting this attempt: may the student start another one by themselves?
    Not after a paper score: only the teacher can reopen it (Give another try)."""
    if submission["paper"]:
        return False
    return max_attempts is None or submission["attempt"] < max_attempts


def clean_paper_score(data, possible):
    """(score, late, note) for a paper score typed by the teacher."""
    score = data.get("score")
    if not whole_number(score, 0, possible):
        raise ValidationError(f"The score must be a whole number from 0 to {possible}.")
    note = clean_name(data.get("note"))
    if len(note) > MAX_NOTE_LENGTH:
        raise ValidationError(f"The note can be at most {MAX_NOTE_LENGTH} characters.")
    return score, bool(data.get("late")), note
