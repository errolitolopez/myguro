from myguro.config import school_today
from myguro.domain.work import clean_due_date
from myguro.errors import ValidationError
from myguro.repositories.assignments import DIRECT_CLASS_NAME
from myguro.services.activities import ActivityService
from myguro.services.base import Service
from myguro.services.classes import ClassService
from myguro.services.presenters import class_title, user_json


class AssignmentService(Service):
    """Giving a teacher's sheet to classes (everyone or chosen students) and directly to individual
    students, with an optional due date."""

    def overview(self, activity_id):
        """All the teacher's classes with their students, and how the sheet is given to each
        (assignment None when it isn't). Everything the Assign popup needs."""
        ActivityService(self.db, self.user).require(activity_id)
        class_service = ClassService(self.db, self.user)
        classes = []
        for item in class_service.list():
            row = self.assignments.get(activity_id, item["id"])
            assignment = None
            if row:
                assignment = {
                    "id": row["id"],
                    "due_date": row["due_date"],
                    "everyone": bool(row["everyone"]),
                    "student_ids": self.assignments.chosen_students(row["id"]),
                }
            classes.append({"id": item["id"], "name": item["name"], "subject": item["subject"],
                            "students": class_service.students(item["id"]), "assignment": assignment})
        direct_row = self.assignments.get_direct(activity_id)
        direct = None
        if direct_row:
            students = [user_json(self.users.get_student(student_id))
                        for student_id in self.assignments.chosen_students(direct_row["id"])]
            students.sort(key=lambda student: student["name"].lower())
            direct = {
                "id": direct_row["id"],
                "due_date": direct_row["due_date"],
                "student_ids": [student["id"] for student in students],
                "students": students,
            }
        return {"classes": classes, "direct": direct, "today": school_today().isoformat()}

    def clean_assignment(self, posted):
        """One posted assignment: {class_id, everyone, student_ids, due_date}."""
        if not isinstance(posted, dict):
            raise ValidationError("An assignment is not valid.")
        class_row = self.classes.get_for_teacher(posted.get("class_id"), self.user["id"])
        if class_row is None:
            raise ValidationError("Class not found.")
        label = class_title(class_row["name"], class_row["subject"])
        due_date = clean_due_date(posted.get("due_date"), label)
        everyone = bool(posted.get("everyone", True))
        student_ids = []
        if not everyone:
            student_ids = posted.get("student_ids")
            if not isinstance(student_ids, list) or not student_ids:
                raise ValidationError(f"{label}: choose at least one student, or give it to everyone.")
            in_class = {row["id"] for row in self.classes.students(class_row["id"])}
            if not set(student_ids) <= in_class:
                raise ValidationError(f"{label}: a chosen student is not in this class.")
            student_ids = sorted(set(student_ids))
        return {"class_id": class_row["id"], "everyone": everyone, "student_ids": student_ids, "due_date": due_date}

    def clean_direct(self, posted):
        """{due_date, student_ids} for the individual students, or None to take it back.
        Students are the whole school's, so they need not be in the teacher's classes."""
        if posted is None:
            return None
        if not isinstance(posted, dict):
            raise ValidationError(f"{DIRECT_CLASS_NAME} are not valid.")
        due_date = clean_due_date(posted.get("due_date"), DIRECT_CLASS_NAME)
        student_ids = posted.get("student_ids")
        if not isinstance(student_ids, list) or not student_ids:
            raise ValidationError(f"{DIRECT_CLASS_NAME}: choose at least one student.")
        for student_id in student_ids:
            is_id = isinstance(student_id, int) and not isinstance(student_id, bool)
            if not is_id or self.users.get_student(student_id, active_only=True) is None:
                raise ValidationError(f"{DIRECT_CLASS_NAME}: a chosen student was not found or is deactivated.")
        return {"due_date": due_date, "student_ids": sorted(set(student_ids))}

    def save_direct(self, activity_id, direct):
        """Make, change or (direct None) take back the sheet's assignment to individual students."""
        existing = self.assignments.get_direct(activity_id)
        if direct is None:
            if existing is None:
                return
            if self.assignments.has_submitted_work(existing["id"]):
                raise ValidationError("Students you gave it to directly already submitted, "
                                      "so it can't be taken back.")
            self.assignments.delete(existing["id"])  # with answers saved but not submitted yet
            return
        if existing:
            assignment_id = existing["id"]
            self.assignments.update(assignment_id, True, direct["due_date"])
        else:
            assignment_id = self.assignments.create(activity_id, None, True, direct["due_date"])
        self.assignments.set_chosen_students(assignment_id, direct["student_ids"])

    def save(self, activity_id, data):
        """Give the sheet to the posted classes. The list is complete: classes left out stop
        having the sheet. Changing a class keeps its assignment id (students' work stays linked).
        A "direct" key (individual students, or null to take it back) is optional: leaving it
        out keeps it as it is."""
        ActivityService(self.db, self.user).require(activity_id)
        posted = data.get("assignments")
        if not isinstance(posted, list):
            raise ValidationError("Assignments must be a list.")
        change_direct = "direct" in data
        direct = self.clean_direct(data["direct"]) if change_direct else None
        if (posted or direct) and not self.activities.has_sections(activity_id):
            raise ValidationError("Add at least one section before giving this activity to a class.")
        cleaned = []
        for item in posted:
            assignment = self.clean_assignment(item)
            if any(other["class_id"] == assignment["class_id"] for other in cleaned):
                raise ValidationError("A class is listed twice.")
            cleaned.append(assignment)

        old = self.assignments.ids_by_class(activity_id)
        for assignment in cleaned:
            if assignment["class_id"] in old:
                assignment_id = old.pop(assignment["class_id"])
                self.assignments.update(assignment_id, assignment["everyone"], assignment["due_date"])
            else:
                assignment_id = self.assignments.create(activity_id, assignment["class_id"], assignment["everyone"],
                                                        assignment["due_date"])
            self.assignments.set_chosen_students(assignment_id, assignment["student_ids"])
        for class_id, assignment_id in old.items():  # classes no longer listed
            if self.assignments.has_submitted_work(assignment_id):
                name = self.classes.get_for_teacher(class_id, self.user["id"])["name"]
                raise ValidationError(f"Students in {name} already submitted, so it can't be taken back.")
            self.assignments.delete(assignment_id)  # with answers saved but not submitted yet
        if change_direct:
            self.save_direct(activity_id, direct)
        self.commit()
        return self.overview(activity_id)

