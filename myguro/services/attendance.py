from myguro.config import school_today
from myguro.domain.attendance import STATUSES, clean_day, clean_marks
from myguro.errors import ValidationError
from myguro.repositories import AttendanceRepository
from myguro.services.base import Service
from myguro.services.classes import ClassService
from myguro.services.presenters import class_json, user_json


class AttendanceService(Service):
    """A teacher's attendance record for a class: one mark per student per day, typed in by the
    teacher from the paper record."""

    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.attendance = AttendanceRepository(db)

    def sheet(self, class_id, day=None):
        """The class's students with their mark for one day (default today; status None = not marked
        yet), what each student has in total, and the days that have marks."""
        class_row = ClassService(self.db, self.user).require(class_id)
        day = clean_day(day, school_today())
        marks = self.attendance.for_day(class_id, day)
        totals = self.attendance.totals(class_id)
        students = []
        for student in self.classes.students(class_id):
            students.append({**user_json(student), "status": marks.get(student["id"]),
                             "totals": {status: totals.get(student["id"], {}).get(status, 0) for status in STATUSES}})
        return {"class": class_json(class_row), "day": day, "statuses": list(STATUSES),
                "students": students, "recorded_days": self.attendance.recorded_days(class_id)}

    def record(self, class_id):
        """The whole record for the exports: the days with marks (oldest first) and, for every
        student of the class, their mark on each day ({day: status}) and their totals."""
        class_row = ClassService(self.db, self.user).require(class_id)
        marks = {}  # student id -> {day: status}
        days = set()
        for row in self.attendance.all_marks(class_id):
            marks.setdefault(row["student_id"], {})[row["day"]] = row["status"]
            days.add(row["day"])
        students = []
        for student in self.classes.students(class_id):
            own = marks.get(student["id"], {})
            students.append({**user_json(student), "marks": own,
                             "totals": {status: list(own.values()).count(status) for status in STATUSES}})
        return {"class": class_json(class_row), "days": sorted(days), "students": students}

    def save(self, class_id, data):
        """Save the marks of one day: {day, marks: {student id: status, or null to clear}}. Only
        students of the class; a past school year can only be looked at."""
        class_row = ClassService(self.db, self.user).require_open(class_id)
        day = clean_day(data.get("day"), school_today())
        marks = clean_marks(data.get("marks"))
        for student_id in marks:
            if not self.classes.has_student(class_id, student_id):
                raise ValidationError("One of the students is not in this class.")
        for student_id, status in marks.items():
            self.attendance.set(class_id, student_id, day, status)
        self.log("attendance.saved", "classes", f"Saved the attendance of {class_row['name']} for {day}.",
                 ("class", class_id, class_row["name"]))
        self.commit()
        return self.sheet(class_id, day)
