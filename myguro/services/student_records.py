"""Teacher: their students and one student's record (every activity the teacher gave them)."""

from myguro.domain.record import build_teacher_record
from myguro.errors import NotFoundError
from myguro.services.base import Service
from myguro.services.presenters import class_title, user_json
from myguro.services.results import ResultsService


class StudentRecordService(Service):
    """Read only: nothing here changes data or writes to the activity log."""

    def students(self):
        """The teacher's students in the school year being viewed, A to Z, each with the teacher's classes
        they are in (the individual students group counts as one)."""
        people = {}
        for row in self.classes.students_of_teacher(self.user["id"], self.year_id()):
            person = people.setdefault(row["id"], {**user_json(row), "classes": []})
            title = class_title(row["class_name"], row["class_subject"])
            if title not in person["classes"]:
                person["classes"].append(title)
        for person in people.values():
            person["classes"].sort(key=str.lower)
        return sorted(people.values(), key=lambda person: person["name"].lower())

    def record(self, student_id):
        """The student and their record with this teacher, or NotFoundError when the student is not one
        of the teacher's (the same answer as a student who does not exist)."""
        student = self.users.get(student_id)
        if student is None or student["role"] != "student":
            raise NotFoundError("Student not found.")

        results = ResultsService(self.db, self.user)
        rows = []
        # Newest first, so the latest work is at the top of each class.
        for assignment_id in self.assignments.ids_for_teacher(self.user["id"], self.year_id()):
            assignment = self.assignments.get_for_teacher(assignment_id, self.user["id"])
            if student_id not in {person["id"] for person in self.assignments.students(assignment)}:
                continue
            excluded = student_id in self.assignments.excluded_ids(assignment_id)
            result = results.student_row(assignment, student, excluded)
            rows.append({
                "assignment_id": assignment_id,
                "activity_id": assignment["activity_id"],
                "title": assignment["title"],
                "class_id": assignment["class_id"],
                "class_name": class_title(assignment["class_name"], assignment["class_subject"]),
                "due_date": assignment["due_date"],
                "assignment_status": assignment["status"],  # not_started, open or closed
                "scores_released": bool(assignment["scores_released"]),
                **{key: result[key] for key in ("status", "excluded", "attempts", "submitted_at", "late",
                                                "paper", "score")},
            })

        mine = {person["id"] for person in self.students()}
        if not rows and student_id not in mine:
            raise NotFoundError("Student not found.")
        return {"student": user_json(student), "record": build_teacher_record(rows)}
