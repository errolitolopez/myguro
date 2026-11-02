from myguro.domain.text import like_pattern
from myguro.repositories.base import Repository


class HolidayRepository(Repository):
    """The holidays the admin added (the national ones are worked out in domain/holidays.py)."""

    def in_year(self, year):
        """The local holidays of a calendar year, by date."""
        return self.all("SELECT * FROM local_holidays WHERE day LIKE ? ORDER BY day, id", (f"{year:04d}-%",))

    def search(self, text):
        """The local holidays with this text in their name, in any year."""
        return self.all("SELECT * FROM local_holidays WHERE name LIKE ? ESCAPE '\\' ORDER BY day, id", (like_pattern(text),))

    def get(self, holiday_id):
        return self.one("SELECT * FROM local_holidays WHERE id = ?", (holiday_id,))

    def create(self, day, name, description=""):
        return self.execute("INSERT INTO local_holidays (day, name, description) VALUES (?, ?, ?)",
                            (day, name, description)).lastrowid

    def update(self, holiday_id, day, name, description=""):
        self.execute("UPDATE local_holidays SET day = ?, name = ?, description = ? WHERE id = ?",
                     (day, name, description, holiday_id))

    def delete(self, holiday_id):
        self.execute("DELETE FROM local_holidays WHERE id = ?", (holiday_id,))

    def exists(self, day, name):
        """Is this exact holiday already added (same day, same name, ignoring capitals)?"""
        return self.one("SELECT 1 FROM local_holidays WHERE day = ? AND name = ? COLLATE NOCASE", (day, name)) is not None
