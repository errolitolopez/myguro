"""School events on the calendar: everyone reads them, the admin changes them."""

from myguro.domain.school_events import check_event
from myguro.errors import NotFoundError, ValidationError
from myguro.repositories import SchoolEventRepository
from myguro.services.base import Service


class SchoolEventService(Service):
    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.events = SchoolEventRepository(db)

    def add(self, data):
        """Admin: add an event. Returns its id."""
        start_day, end_day, name = check_event(data)
        if self.events.exists(start_day, end_day, name):
            raise ValidationError("This event is already on the calendar.")
        event_id = self.events.create(start_day, end_day, name)
        self.log("event.added", "settings", f"Added the school event {name} on {start_day}.", ("event", event_id, name))
        self.commit()
        return event_id

    def update(self, event_id, data):
        """Admin: change an event's days or name."""
        row = self.event_or_404(event_id)
        start_day, end_day, name = check_event(data)
        unchanged = (start_day, end_day, name.lower()) == (row["start_day"], row["end_day"], row["name"].lower())
        if not unchanged and self.events.exists(start_day, end_day, name):
            raise ValidationError("This event is already on the calendar.")
        self.events.update(event_id, start_day, end_day, name)
        self.log("event.updated", "settings", f"Changed the school event {row['name']} to {name} on {start_day}.",
                 ("event", event_id, name))
        self.commit()

    def delete(self, event_id):
        """Admin: remove an event."""
        row = self.event_or_404(event_id)
        self.events.delete(event_id)
        self.log("event.deleted", "settings", f"Removed the school event {row['name']} on {row['start_day']}.",
                 ("event", event_id, row["name"]))
        self.commit()

    def event_or_404(self, event_id):
        row = self.events.get(event_id)
        if row is None:
            raise NotFoundError("Event not found.")
        return row
