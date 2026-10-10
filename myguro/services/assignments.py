from myguro.config import school_today
from myguro.domain.work import clean_due_date
from myguro.errors import ValidationError
from myguro.services.activities import ActivityService
from myguro.services.base import Service
from myguro.services.classes import ClassService
from myguro.services.presenters import class_title


class AssignmentService(Service):
    """Giving a teacher's sheet to classes: everyone or chosen students, optional due date."""

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
        return {"classes": classes, "today": school_today().isoformat()}

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

    def save(self, activity_id, data):
        """Give the sheet to the posted classes. The list is complete: classes left out stop
        having the sheet. Changing a class keeps its assignment id (students' work stays linked)."""
        ActivityService(self.db, self.user).require(activity_id)
        posted = data.get("assignments")
        if not isinstance(posted, list):
            raise ValidationError("Assignments must be a list.")
        if posted and not self.activities.has_sections(activity_id):
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
        self.commit()
        return self.overview(activity_id)

