"""The rules for a school event on the calendar: one day or a range of days."""

from myguro.domain.holidays import check_day
from myguro.errors import ValidationError

MAX_NAME_LENGTH = 150  # longer than a holiday's: DepEd's activity names are long


def check_event(data):
    """(start_day, end_day, name) of an event from the request; no end day means one day.
    Raises ValidationError with a short message."""
    start_day = check_day(data.get("start_day"))
    end_day = check_day(data.get("end_day")) if data.get("end_day") else start_day
    if end_day < start_day:  # ISO days sort like dates
        raise ValidationError("The end date cannot be before the start date.")
    name = " ".join(data.get("name").split()) if isinstance(data.get("name"), str) else ""
    if not name:
        raise ValidationError("Type the name of the event.")
    if len(name) > MAX_NAME_LENGTH:
        raise ValidationError(f"The name can be at most {MAX_NAME_LENGTH} characters.")
    return start_day, end_day, name
