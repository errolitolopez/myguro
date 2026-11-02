"""School events on the calendar."""

from myguro.repositories.base import Repository


class SchoolEventRepository(Repository):
    """Events run over one day or many, unlike holidays, so a lookup asks which ones touch a range of days."""

    def in_year(self, year):
        """The events with at least one day in a calendar year, by first day."""
        return self.all("SELECT * FROM school_events WHERE start_day <= ? AND end_day >= ? ORDER BY start_day, end_day, id",
                        (f"{year:04d}-12-31", f"{year:04d}-01-01"))

    def get(self, event_id):
        return self.one("SELECT * FROM school_events WHERE id = ?", (event_id,))

    def create(self, start_day, end_day, name):
        return self.execute("INSERT INTO school_events (start_day, end_day, name) VALUES (?, ?, ?)",
                            (start_day, end_day, name)).lastrowid

    def update(self, event_id, start_day, end_day, name):
        self.execute("UPDATE school_events SET start_day = ?, end_day = ?, name = ? WHERE id = ?",
                     (start_day, end_day, name, event_id))

    def delete(self, event_id):
        self.execute("DELETE FROM school_events WHERE id = ?", (event_id,))

    def exists(self, start_day, end_day, name):
        """Is this exact event already there (same days, same name, ignoring capitals)?"""
        return self.one("SELECT 1 FROM school_events WHERE start_day = ? AND end_day = ? AND name = ? COLLATE NOCASE",
                        (start_day, end_day, name)) is not None
