from myguro.domain import holidays as rules
from myguro.errors import NotFoundError, ValidationError
from myguro.repositories import HolidayRepository
from myguro.services.base import Service


class HolidayService(Service):
    """The holiday calendar: everyone reads it, the admin adds local holidays."""

    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.holidays = HolidayRepository(db)

    def year(self, value):
        """Every holiday of a calendar year, national and local, by date. Local ones carry their id."""
        year = rules.check_year(value)
        items = rules.national_holidays(year)
        items += [{"id": row["id"], "day": row["day"], "name": row["name"], "kind": rules.LOCAL}
                  for row in self.holidays.in_year(year)]
        items.sort(key=lambda item: item["day"])
        return {"year": year, "holidays": items}

    def add(self, data):
        """Admin: add a local holiday. Returns its id."""
        day, name = rules.check_holiday(data)
        if self.holidays.exists(day, name):
            raise ValidationError("This holiday is already on the calendar.")
        holiday_id = self.holidays.create(day, name)
        self.log("holiday.added", "settings", f"Added the holiday {name} on {day}.", ("holiday", holiday_id, name))
        self.commit()
        return holiday_id

    def update(self, holiday_id, data):
        """Admin: change a local holiday's date or name."""
        row = self.holiday_or_404(holiday_id)
        day, name = rules.check_holiday(data)
        if (day, name.lower()) != (row["day"], row["name"].lower()) and self.holidays.exists(day, name):
            raise ValidationError("This holiday is already on the calendar.")
        self.holidays.update(holiday_id, day, name)
        self.log("holiday.updated", "settings", f"Changed the holiday {row['name']} to {name} on {day}.",
                 ("holiday", holiday_id, name))
        self.commit()

    def delete(self, holiday_id):
        """Admin: remove a local holiday."""
        row = self.holiday_or_404(holiday_id)
        self.holidays.delete(holiday_id)
        self.log("holiday.deleted", "settings", f"Removed the holiday {row['name']} on {row['day']}.",
                 ("holiday", holiday_id, row["name"]))
        self.commit()

    def holiday_or_404(self, holiday_id):
        row = self.holidays.get(holiday_id)
        if row is None:
            raise NotFoundError("Holiday not found.")
        return row
