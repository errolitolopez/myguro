import random

from myguro.domain.schedule import (BREAK_AFTER, DAY_NAMES, DAYS, DEFAULT_RULES, PERIOD_TIMES, check, generate)
from myguro.domain.schedule_input import clean_whole, clean_assignment, clean_section, clean_teacher
from myguro.errors import NotFoundError, ValidationError, say
from myguro.repositories import ScheduleRepository
from myguro.services.base import Service

PUBLISHED_KEY = "schedule_published"
MAX_GAP_KEY = "schedule_max_gap"
MAX_PER_DAY_KEY = "schedule_max_per_day"
# A swap that breaks one of these is refused; the other broken rules are only warned about.
HARD_KINDS = ("teacher_double", "teacher_blocked", "too_long_day")


def period_label(index):
    start, end = PERIOD_TIMES[index]
    return f"{start} - {end}"


class ScheduleService(Service):
    """The schedule generator. Admin: enter the data, build, swap by hand, publish. Teacher: see their own."""

    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.schedule = ScheduleRepository(db)

    # --- the school's rules --------------------------------------------------------------------

    def rules(self):
        """{"max_gap", "max_per_day"} as the admin set them (the defaults until then)."""
        saved_gap = self.settings.get(MAX_GAP_KEY)
        saved_day = self.settings.get(MAX_PER_DAY_KEY)
        return {"max_gap": int(saved_gap) if saved_gap not in (None, "") else DEFAULT_RULES["max_gap"],
                "max_per_day": int(saved_day) if saved_day not in (None, "") else None}

    def set_rules(self, data):
        gap = clean_whole(data.get("max_gap"), "Longest gap", 0, len(PERIOD_TIMES))
        per_day = clean_whole(data.get("max_per_day"), "Most periods a day", 1, len(PERIOD_TIMES), required=False)
        self.settings.set(MAX_GAP_KEY, str(gap))
        self.settings.set(MAX_PER_DAY_KEY, "" if per_day is None else str(per_day))
        self.log("schedule.rules_changed", "settings", "Changed the schedule rules.")
        self.commit()
        return self.rules()

    # --- reading ---------------------------------------------------------------------------------

    def teacher_json(self, row, blocked):
        return {"id": row["id"], "name": row["name"], "user_id": row["user_id"], "max_gap": row["max_gap"],
                "max_per_day": row["max_per_day"], "blocked": [list(item) for item in blocked.get(row["id"], [])]}

    def engine_input(self):
        """The assignments and teachers in the shapes the generator and the checker take."""
        blocked = self.schedule.blocked()
        assignments = [{"section_id": row["section_id"], "subject": row["subject"], "teacher_id": row["teacher_id"],
                        "per_week": row["per_week"]} for row in self.schedule.assignments()]
        teachers = {row["id"]: {"blocked": set(blocked.get(row["id"], [])), "max_gap": row["max_gap"],
                                "max_per_day": row["max_per_day"]} for row in self.schedule.teachers()}
        return assignments, teachers

    def current_slots(self):
        return [(row["section_id"], row["day"], row["period"], row["subject"], row["teacher_id"])
                for row in self.schedule.slots()]

    def overview(self):
        """Everything the admin's page shows: the data, the rules, and whether a timetable exists."""
        blocked = self.schedule.blocked()
        assignments, teachers = self.engine_input()
        slots = self.current_slots()
        problems = check(slots, assignments, teachers, len(PERIOD_TIMES), self.rules()) if slots else []
        names = {row["id"]: row["name"] for row in self.schedule.teachers()}
        return {
            "sections": [{"id": row["id"], "name": row["name"], "grade": row["grade"], "room": row["room"],
                          "adviser": row["adviser"]} for row in self.schedule.sections()],
            "teachers": [self.teacher_json(row, blocked) for row in self.schedule.teachers()],
            "assignments": [{"id": row["id"], "section_id": row["section_id"], "subject": row["subject"],
                             "teacher_id": row["teacher_id"], "per_week": row["per_week"]}
                            for row in self.schedule.assignments()],
            "accounts": [dict(row) for row in self.schedule.teacher_accounts()],
            "rules": self.rules(),
            "periods": [{"label": period_label(i), "break_after": i == BREAK_AFTER} for i in range(len(PERIOD_TIMES))],
            "days": list(DAY_NAMES),
            "built": bool(slots),
            "published": self.settings.get(PUBLISHED_KEY) == "1",
            "problems": [self.describe(problem, names) for problem in problems],
        }

    def describe(self, problem, names):
        """A problem for the admin to read, with the teacher's name and the day when it has them."""
        text = say(problem["message"])  # in the admin's language
        if problem.get("teacher_id") in names:
            text = f"{names[problem['teacher_id']]}: {text}"
        if "day" in problem:
            text += f" ({DAY_NAMES[problem['day']]})"
        return text

    # --- editing the data ---------------------------------------------------------------------

    def add_section(self, data):
        fields = clean_section(data)
        if self.schedule.section_by_name(fields[0]):
            raise ValidationError("There is already a section with this name.")
        section_id = self.schedule.add_section(*fields)
        self.log("schedule.section_added", "settings", f"Added the schedule section {fields[0]}.",
                 ("schedule_section", section_id, fields[0]))
        self.commit()
        return section_id

    def update_section(self, section_id, data):
        self.require_section(section_id)
        fields = clean_section(data)
        same = self.schedule.section_by_name(fields[0])
        if same and same["id"] != section_id:
            raise ValidationError("There is already a section with this name.")
        self.schedule.update_section(section_id, *fields)
        self.log("schedule.section_changed", "settings", f"Changed the schedule section {fields[0]}.",
                 ("schedule_section", section_id, fields[0]))
        self.commit()

    def delete_section(self, section_id):
        row = self.require_section(section_id)
        self.schedule.delete_section(section_id)
        self.log("schedule.section_deleted", "settings", f"Deleted the schedule section {row['name']}.",
                 ("schedule_section", section_id, row["name"]))
        self.commit()

    def require_section(self, section_id):
        row = self.schedule.section(section_id)
        if row is None:
            raise NotFoundError("Section not found.")
        return row

    def require_teacher(self, teacher_id):
        row = self.schedule.teacher(teacher_id)
        if row is None:
            raise NotFoundError("Teacher not found.")
        return row

    def check_account(self, user_id, teacher_id=None):
        """The account (if any) must be a teacher account used by no other schedule teacher."""
        if user_id is None:
            return
        if user_id not in {row["id"] for row in self.schedule.teacher_accounts()}:
            raise ValidationError("Choose one of the teacher accounts.")
        if self.schedule.user_taken(user_id, teacher_id):
            raise ValidationError("That account is already linked to another teacher.")

    def add_teacher(self, data):
        name, user_id, max_gap, max_per_day, blocked = clean_teacher(data)
        self.check_account(user_id)
        teacher_id = self.schedule.add_teacher(name, user_id, max_gap, max_per_day)
        self.schedule.set_blocked(teacher_id, blocked)
        # The name is a person's name, so the log only says that a teacher was added
        self.log("schedule.teacher_added", "settings", "Added a schedule teacher.", ("schedule_teacher", teacher_id, ""))
        self.commit()
        return teacher_id

    def update_teacher(self, teacher_id, data):
        self.require_teacher(teacher_id)
        name, user_id, max_gap, max_per_day, blocked = clean_teacher(data)
        self.check_account(user_id, teacher_id)
        self.schedule.update_teacher(teacher_id, name, user_id, max_gap, max_per_day)
        self.schedule.set_blocked(teacher_id, blocked)
        self.log("schedule.teacher_changed", "settings", "Changed a schedule teacher.", ("schedule_teacher", teacher_id, ""))
        self.commit()

    def delete_teacher(self, teacher_id):
        self.require_teacher(teacher_id)
        if self.schedule.teacher_in_use(teacher_id):
            raise ValidationError("This teacher still has subjects. Remove or change those first.")
        self.schedule.delete_teacher(teacher_id)
        self.log("schedule.teacher_deleted", "settings", "Deleted a schedule teacher.", ("schedule_teacher", teacher_id, ""))
        self.commit()

    def set_assignment(self, data):
        section_id, subject, teacher_id, per_week = clean_assignment(data)
        section = self.require_section(section_id)
        self.require_teacher(teacher_id)
        assignment_id = self.schedule.set_assignment(section_id, subject, teacher_id, per_week)
        # Its periods in the built timetable no longer match: they are dropped, so Generate (or a swap) refills
        self.schedule.delete_slots_of(section_id, subject)
        self.log("schedule.assignment_set", "settings", f"Set {subject} for {section['name']}: {per_week} periods a week.",
                 ("schedule_section", section_id, section["name"]))
        self.commit()
        return assignment_id

    def delete_assignment(self, assignment_id):
        row = self.schedule.assignment(assignment_id)
        if row is None:
            raise NotFoundError("Subject not found.")
        self.schedule.delete_slots_of(row["section_id"], row["subject"])
        self.schedule.delete_assignment(assignment_id)
        self.log("schedule.assignment_deleted", "settings", f"Removed {row['subject']} from a schedule section.")
        self.commit()

    # --- building and changing the timetable ------------------------------------------------------

    def generate(self, data=None):
        """Build a new timetable from the data and the rules, replacing the old one (it becomes unpublished).
        Returns the lessons that could not be placed and any problem with the data."""
        assignments, teachers = self.engine_input()
        if not assignments:
            raise ValidationError("Add the sections, teachers and their subjects first.")
        seed = (data or {}).get("seed")
        if seed is None:
            seed = random.randrange(1, 10**6)
        result = generate(assignments, teachers, len(PERIOD_TIMES), self.rules(), seed=seed)
        self.schedule.replace_slots(result["slots"])
        self.settings.set(PUBLISHED_KEY, "0")
        names = {row["id"]: row["name"] for row in self.schedule.teachers()}
        sections = {row["id"]: row["name"] for row in self.schedule.sections()}
        self.log("schedule.generated", "settings", f"Built the schedule: {len(result['slots'])} periods placed, "
                 f"{len(result['unplaced'])} not placed.")
        self.commit()
        return {
            "placed": len(result["slots"]),
            "unplaced": [f"{sections.get(item['section_id'], '?')}: {item['subject']} ({names.get(item['teacher_id'], '?')})"
                         for item in result["unplaced"]],
            "problems": [problem["message"] for problem in result["problems"]],
        }

    def swap(self, data):
        """Swap what two periods of one section hold, as {section_id, a: [day, period], b: [day, period]}. A free
        period can be swapped with a lesson (it moves there). Refused when a teacher would be in two places, in a
        period they cannot teach, or over their limit a day; other broken rules come back as warnings."""
        section = self.require_section(data.get("section_id"))
        cells = []
        for key in ("a", "b"):
            cell = data.get(key)
            if not (isinstance(cell, (list, tuple)) and len(cell) == 2):
                raise ValidationError("Choose two periods.")
            cells.append((clean_whole(cell[0], "Day", 0, DAYS - 1), clean_whole(cell[1], "Period", 0, len(PERIOD_TIMES) - 1)))
        if cells[0] == cells[1]:
            raise ValidationError("Choose two different periods.")
        slots = self.current_slots()
        mine = {(slot[1], slot[2]): slot for slot in slots if slot[0] == section["id"]}
        first, second = mine.get(cells[0]), mine.get(cells[1])
        if first is None and second is None:
            raise ValidationError("Both periods are free.")
        others = [slot for slot in slots if slot not in (first, second)]
        moved = []
        if first is not None:
            moved.append((section["id"], *cells[1], first[3], first[4]))
        if second is not None:
            moved.append((section["id"], *cells[0], second[3], second[4]))
        assignments, teachers = self.engine_input()
        names = {row["id"]: row["name"] for row in self.schedule.teachers()}
        before = check(slots, assignments, teachers, len(PERIOD_TIMES), self.rules())
        after = check(others + moved, assignments, teachers, len(PERIOD_TIMES), self.rules())
        known = {self.problem_key(problem) for problem in before}
        new = [problem for problem in after if self.problem_key(problem) not in known]
        refused = [problem for problem in new if problem["kind"] in HARD_KINDS]
        if refused:
            raise ValidationError(self.describe(refused[0], names))
        self.schedule.replace_slots(others + moved)
        self.log("schedule.swapped", "settings", f"Swapped two periods of {section['name']}.",
                 ("schedule_section", section["id"], section["name"]))
        self.commit()
        return {"warnings": [self.describe(problem, names) for problem in new]}

    @staticmethod
    def problem_key(problem):
        return (problem["kind"], problem.get("teacher_id"), problem.get("section_id"), problem.get("day"),
                problem.get("period"), problem.get("subject"))

    def set_published(self, data):
        published = data.get("published")
        if not isinstance(published, bool):
            raise ValidationError("Choose publish or unpublish.")
        if published and not self.schedule.slots():
            raise ValidationError("Build the schedule first.")
        self.settings.set(PUBLISHED_KEY, "1" if published else "0")
        self.log("schedule.published" if published else "schedule.unpublished", "settings",
                 "Published the schedule to the teachers." if published else "Took the schedule back from the teachers.")
        self.commit()
        return published

    # --- the weekly grids -------------------------------------------------------------------------

    def grid(self, cells):
        """{"periods", "days", "rows": [[cell or None x 5] per period]} from {(day, period): cell}."""
        return {"periods": [{"label": period_label(i), "break_after": i == BREAK_AFTER} for i in range(len(PERIOD_TIMES))],
                "days": list(DAY_NAMES),
                "rows": [[cells.get((day, period)) for day in range(DAYS)] for period in range(len(PERIOD_TIMES))]}

    def section_grid(self, section_id):
        section = self.require_section(section_id)
        names = {row["id"]: row["name"] for row in self.schedule.teachers()}
        cells = {(row["day"], row["period"]): {"subject": row["subject"], "teacher": names.get(row["teacher_id"], "")}
                 for row in self.schedule.slots() if row["section_id"] == section_id}
        return {"title": section["name"], "details": " · ".join(filter(None, [section["room"] and f"Room {section['room']}",
                                                                              section["adviser"]])), **self.grid(cells)}

    def teacher_cells(self, teacher_id):
        sections = {row["id"]: row for row in self.schedule.sections()}
        return {(row["day"], row["period"]): {"subject": row["subject"], "section": sections[row["section_id"]]["name"],
                                              "room": sections[row["section_id"]]["room"]}
                for row in self.schedule.slots() if row["teacher_id"] == teacher_id}

    def teacher_grid(self, teacher_id):
        teacher = self.require_teacher(teacher_id)
        cells = self.teacher_cells(teacher_id)
        return {"title": teacher["name"], "details": plural_periods(len(cells)), **self.grid(cells)}

    def my_schedule(self):
        """A teacher's own weekly grid, once the admin published it (None-like answer before that)."""
        teacher = self.schedule.teacher_for_user(self.user["id"])
        if teacher is None or self.settings.get(PUBLISHED_KEY) != "1":
            return {"available": False}
        cells = self.teacher_cells(teacher["id"])
        return {"available": True, "title": "My schedule", "details": plural_periods(len(cells)), **self.grid(cells)}


def plural_periods(count):
    return f"{count} period{'' if count == 1 else 's'} a week"
