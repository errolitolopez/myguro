from myguro.domain.school_years import check_year_name
from myguro.errors import NotFoundError, ValidationError
from myguro.repositories import ClassRepository
from myguro.services.base import Service


class SchoolYearService(Service):
    """School years: everyone can pick the year they look at; the admin starts a new year."""

    def overview(self, viewing_id=None):
        """Every year (newest first), the current one, and the one this person is looking at
        (viewing_id when they just chose it: self.user was read before the change)."""
        current_id = self.years.current_id()
        return {
            "years": [{"id": row["id"], "name": row["name"], "current": row["id"] == current_id}
                      for row in self.years.list()],
            "current_id": current_id,
            "viewing_id": viewing_id or self.year_id(),
        }

    def view(self, year_id):
        """Look at another school year (a past one is read-only). Choosing the current year goes
        back to the default."""
        if not isinstance(year_id, int) or isinstance(year_id, bool) or self.years.get(year_id) is None:
            raise NotFoundError("School year not found.")
        self.years.set_view(self.user["id"], None if year_id == self.years.current_id() else year_id)
        self.commit()
        return self.overview(year_id)

    def start(self, data):
        """Admin: start a new school year and make it the current one. Last year becomes read-only."""
        name = check_year_name(data.get("name"))
        if self.years.by_name(name):
            raise ValidationError("This school year already exists.")
        copy_classes = data.get("copy_classes", False)
        if not isinstance(copy_classes, bool):
            raise ValidationError("Choose whether to copy last year's classes.")
        last_year_id = self.years.current_id()
        year_id = self.years.create(name)
        self.years.set_current(year_id)
        # Teachers start the year with last year's classes (empty: they add the students again).
        copied = ClassRepository(self.db).copy_to_year(last_year_id, year_id) if copy_classes else 0
        self.log("year.started", "settings", f"Started the school year {name}"
                 + (f" and copied {copied} classes from last year." if copy_classes else "."), ("school_year", year_id, name))
        self.commit()
        return {**self.overview(), "copied_classes": copied}
