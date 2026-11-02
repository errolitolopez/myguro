from datetime import date, timedelta

from myguro.config import SCHOOL_TIMEZONE, utc_now
from myguro.domain import time_clock as rules
from myguro.errors import NotFoundError, ValidationError
from myguro.repositories import TimeClockRepository
from myguro.services.base import Service
from myguro.services.settings import SettingsService


def school_day(moment):
    """The school date of a moment (a UTC datetime)."""
    return moment.astimezone(SCHOOL_TIMEZONE).date()


def group_by_day(rows):
    """[{day, sessions: [{id, time_in, time_out}], total_seconds}] in the order the rows come."""
    days = {}
    for row in rows:
        days.setdefault(row["day"], []).append({"id": row["id"], "time_in": row["time_in"], "time_out": row["time_out"]})
    return [{"day": day, "sessions": sessions, "total_seconds": rules.day_total(sessions)}
            for day, sessions in days.items()]


class TimeClockService(Service):
    """Time in / time out for teachers (a beta the admin turns on). A teacher can time in again after timing out, as
    often as they like; the admin reads every teacher's records."""

    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.clock = TimeClockRepository(db)

    def require_enabled(self):
        """The teacher's page and API do not exist while the admin has the beta off."""
        if not SettingsService(self.db, self.user).time_clock_enabled():
            raise NotFoundError("Page not found.")

    def open_session(self, now):
        """The teacher's time in that is still waiting for its time out, or None (an old forgotten one does not count)."""
        row = self.clock.latest_open(self.user["id"])
        return row if row and rules.is_open(row["time_in"], now) else None

    def mine(self):
        """{clocked_in, since, today, days}: whether the teacher is timed in now (and since when, UTC), today's
        date and the last HISTORY_DAYS days that have records, newest first, each with its sessions and total."""
        self.require_enabled()
        now = utc_now()
        today = school_day(now)
        first = (today - timedelta(days=rules.HISTORY_DAYS - 1)).isoformat()
        days = group_by_day(self.clock.for_teacher(self.user["id"], first))[::-1]
        days = sorted(days, key=lambda item: item["day"], reverse=True)
        for day in days:
            day["sessions"].reverse()  # newest session first, like the days
        open_row = self.open_session(now)
        return {"clocked_in": open_row is not None, "since": open_row["time_in"] if open_row else None,
                "today": today.isoformat(), "days": days}

    def time_in(self):
        """Start a session now. Refused while already timed in."""
        self.require_enabled()
        now = utc_now()
        if self.open_session(now):
            raise ValidationError("You are already timed in.")
        self.clock.time_in(self.user["id"], school_day(now).isoformat(), rules.to_text(now))
        self.commit()
        return self.mine()

    def time_out(self):
        """End the current session now. Refused when not timed in."""
        self.require_enabled()
        now = utc_now()
        open_row = self.open_session(now)
        if open_row is None:
            raise ValidationError("You are not timed in.")
        self.clock.time_out(open_row["id"], rules.to_text(now))
        self.commit()
        return self.mine()

    def records(self, first_day="", last_day="", teacher_id=None):
        """Admin: every teacher's records from first_day to last_day (school dates, both included; both default to
        today; at most MAX_RANGE_DAYS apart), optionally one teacher. Returns
        {first_day, last_day, teachers: [{id, name}], rows: [{day, teacher_id, teacher_name, sessions, total_seconds}]}."""
        today = school_day(utc_now())
        try:
            first = date.fromisoformat(first_day) if first_day else today
            last = date.fromisoformat(last_day) if last_day else first
        except ValueError:
            raise ValidationError("Choose a valid date.") from None
        if last < first:
            raise ValidationError("The last day is before the first day.")
        if (last - first).days >= rules.MAX_RANGE_DAYS:
            raise ValidationError("Choose at most 62 days.")
        rows = []
        for record in self.clock.between(first.isoformat(), last.isoformat(), teacher_id):
            if rows and (rows[-1]["day"], rows[-1]["teacher_id"]) == (record["day"], record["teacher_id"]):
                group = rows[-1]
            else:
                group = {"day": record["day"], "teacher_id": record["teacher_id"],
                         "teacher_name": record["teacher_name"], "sessions": []}
                rows.append(group)
            group["sessions"].append({"id": record["id"], "time_in": record["time_in"], "time_out": record["time_out"]})
        for group in rows:
            group["total_seconds"] = rules.day_total(group["sessions"])
        teachers = [{"id": row["id"], "name": row["name"]} for row in self.users.active_teachers()]
        return {"first_day": first.isoformat(), "last_day": last.isoformat(), "teachers": teachers, "rows": rows}
