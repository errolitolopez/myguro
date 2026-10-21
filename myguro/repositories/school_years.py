from myguro.repositories.base import Repository

CURRENT_KEY = "current_school_year"


class SchoolYearRepository(Repository):
    """School years, and which one is the current year (a setting)."""

    def list(self):
        """Every year, newest first."""
        return self.all("SELECT * FROM school_years ORDER BY id DESC")

    def get(self, year_id):
        return self.one("SELECT * FROM school_years WHERE id = ?", (year_id,))

    def by_name(self, name):
        return self.one("SELECT * FROM school_years WHERE name = ?", (name,))

    def create(self, name):
        return self.execute("INSERT INTO school_years (name) VALUES (?)", (name,)).lastrowid

    def current_id(self):
        """The id of the current school year."""
        return int(self.value("SELECT value FROM settings WHERE key = ?", (CURRENT_KEY,)))

    def set_current(self, year_id):
        self.execute("UPDATE settings SET value = ? WHERE key = ?", (str(year_id), CURRENT_KEY))

    def set_view(self, user_id, year_id):
        """Remember which year a person is looking at (None = the current year)."""
        self.execute("UPDATE users SET view_year_id = ? WHERE id = ?", (year_id, user_id))
