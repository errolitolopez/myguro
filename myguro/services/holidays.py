from myguro.config import school_today
from myguro.domain import holidays as rules
from myguro.errors import NotFoundError, ValidationError
from myguro.repositories import HolidayRepository, SchoolEventRepository
from myguro.services.base import Service
from myguro.services.settings import SettingsService


class HolidayService(Service):
    """The holiday calendar: anyone reads the holidays (even without logging in), the admin adds local holidays."""

    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.holidays = HolidayRepository(db)
        self.events = SchoolEventRepository(db)

    def events_hidden(self):
        """True when this person must not see school events: anyone not logged in (the public calendar shows
        only holidays), a supervisor, or a student while the admin keeps events from students."""
        if self.user is None or self.user["role"] == "supervisor":
            return True
        return self.user["role"] == "student" and SettingsService(self.db, self.user).hide_events_from_students()

    def year(self, value):
        """Every holiday of a calendar year, national and local, by date (local ones carry their id), and the
        school events with a day in that year."""
        year = rules.check_year(value)
        items = rules.national_holidays(year)
        items += [{"id": row["id"], "day": row["day"], "name": row["name"], "kind": rules.LOCAL,
                   "description": row["description"]}
                  for row in self.holidays.in_year(year)]
        items.sort(key=lambda item: item["day"])
        events = [{"id": row["id"], "start_day": row["start_day"], "end_day": row["end_day"], "name": row["name"]}
                  for row in self.events.in_year(year)] if not self.events_hidden() else []
        return {"year": year, "holidays": items, "events": events}

    def upcoming(self):
        """The next holidays from today on, for the dashboard. Next year is included so December can reach January."""
        today = school_today()
        holidays = self.year(today.year)["holidays"] + self.year(today.year + 1)["holidays"]
        ahead = [holiday for holiday in holidays if holiday["day"] >= today.isoformat()]
        return {"today": today.isoformat(), "holidays": ahead[:rules.MAX_UPCOMING_HOLIDAYS]}

    def search(self, query):
        """Holidays and school events with this text in their name, what is still to come first. National holidays
        repeat every year and are worked out, so only this year's and next year's are searched."""
        text = " ".join(query.split())
        if len(text) < rules.MIN_SEARCH_LENGTH:
            return {"results": []}
        today = school_today()
        results = [{"start_day": holiday["day"], "end_day": holiday["day"], "name": holiday["name"], "kind": holiday["kind"]}
                   for year in (today.year, today.year + 1) for holiday in rules.national_holidays(year)
                   if text.lower() in holiday["name"].lower()]
        results += [{"start_day": row["day"], "end_day": row["day"], "name": row["name"], "kind": rules.LOCAL}
                    for row in self.holidays.search(text)]
        if not self.events_hidden():
            results += [{"start_day": row["start_day"], "end_day": row["end_day"], "name": row["name"],
                         "kind": "event"} for row in self.events.search(text)]
        results.sort(key=lambda item: (item["end_day"] < today.isoformat(), item["start_day"]))
        return {"results": results[:rules.MAX_SEARCH_RESULTS]}

    def add(self, data):
        """Admin: add a local holiday. Returns its id."""
        day, name, description = rules.check_holiday(data)
        if self.holidays.exists(day, name):
            raise ValidationError("This holiday is already on the calendar.")
        holiday_id = self.holidays.create(day, name, description)
        self.log("holiday.added", "settings", f"Added the holiday {name} on {day}.", ("holiday", holiday_id, name))
        self.commit()
        return holiday_id

    def update(self, holiday_id, data):
        """Admin: change a local holiday's date, name or description."""
        row = self.holiday_or_404(holiday_id)
        day, name, description = rules.check_holiday(data)
        if (day, name.lower()) != (row["day"], row["name"].lower()) and self.holidays.exists(day, name):
            raise ValidationError("This holiday is already on the calendar.")
        self.holidays.update(holiday_id, day, name, description)
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
