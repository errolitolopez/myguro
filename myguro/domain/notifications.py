"""The bell: which events make a note, and the sentence for each (no database, no Flask)."""

MAX_PER_USER = 50  # older notes of a person are deleted when a new one is added
LIST_LIMIT = 20  # how many the bell shows

# kind -> the English sentence ({title} = the activity). The Taglish is in i18n/tl.py.
MESSAGES = {
    "opened": "{title} is now open. You can answer it.",
    "closed": "{title} is closed. You can still read it, but not answer it.",
    "reopened": "{title} is open again. You can continue answering it.",
    "released": "Your score for {title} is ready.",
}


def link_for(assignment_id):
    """link_for(7) -> "/my-activities/7", or "" when the note is not about an activity."""
    return f"/my-activities/{assignment_id}" if assignment_id else ""
