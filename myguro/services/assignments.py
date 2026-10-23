from myguro.config import school_today
from myguro.domain.text import clean_name, like_pattern, plural
from myguro.domain.work import clean_due_date
from myguro.errors import ValidationError
from myguro.repositories.assignments import DIRECT_CLASS_NAME
from myguro.services.activities import ActivityService
from myguro.services.base import Service
from myguro.services.classes import MAX_SEARCH_RESULTS, ClassService
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
        direct_row = self.assignments.get_direct(activity_id, self.year_id())
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
        if class_row is None or class_row["school_year_id"] != self.year_id():
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

    def search_students(self, activity_id, query="", grade=None, section=None):
        """Search the school's active students to give the sheet to directly: name, username or
        section; grade / section filter exactly (section "" = no section). Also the grade + section
        pairs, for the dropdown."""
        ActivityService(self.db, self.user).require(activity_id)
        # Class id None: nobody is "in the class", so the in_class column is not used here.
        rows = self.classes.search_students(
            None, like_pattern(clean_name(query)), grade or None,
            None if section is None else clean_name(section), MAX_SEARCH_RESULTS,
        )
        return {
            "students": [user_json(row) for row in rows],
            "more": len(rows) == MAX_SEARCH_RESULTS,
            "sections": [{"grade": row["grade"], "section": row["section"]} for row in self.classes.grade_sections()],
        }

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

    def log_giving(self, action, summary, title, group, assignment_id):
        """An activity log entry about giving a sheet to a class (group = its name) or to individual students."""
        self.log(action, "giving", summary, ("assignment", assignment_id, f"{title} - {group}"))

    def changed(self, existing, everyone, due_date, student_ids):
        """Whether an existing assignment differs from what was posted (who gets it, or the due date)."""
        return (bool(existing["everyone"]) != bool(everyone) or existing["due_date"] != due_date
                or set(self.assignments.chosen_students(existing["id"])) != set(student_ids))

    def save_direct(self, activity_id, direct):
        """Make, change or (direct None) take back the sheet's assignment to individual students."""
        existing = self.assignments.get_direct(activity_id, self.year_id())
        title = self.activities.get_for_teacher(activity_id, self.user["id"])["title"]
        if direct is None:
            if existing is None:
                return
            if self.assignments.has_submitted_work(existing["id"]):
                raise ValidationError("Students you gave it to directly already submitted, "
                                      "so it can't be taken back.")
            self.assignments.delete(existing["id"])  # with answers saved but not submitted yet
            self.log_giving("assignment.taken_back", f"Took back {title} from {DIRECT_CLASS_NAME}.", title,
                            DIRECT_CLASS_NAME, existing["id"])
            return
        if existing:
            assignment_id = existing["id"]
            if self.changed(existing, True, direct["due_date"], direct["student_ids"]):
                self.log_giving("assignment.updated", f"Changed how {title} is given to {DIRECT_CLASS_NAME}.", title,
                                DIRECT_CLASS_NAME, assignment_id)
            self.assignments.update(assignment_id, True, direct["due_date"])
        else:
            assignment_id = self.assignments.create(activity_id, None, True, direct["due_date"], self.year_id())
            self.log_giving("assignment.given", f"Gave {title} to {plural(len(direct['student_ids']), 'student')} "
                            f"({DIRECT_CLASS_NAME}).", title, DIRECT_CLASS_NAME, assignment_id)
        self.assignments.set_chosen_students(assignment_id, direct["student_ids"])

    def save(self, activity_id, data):
        """Give the sheet to the posted classes. The list is complete: classes left out stop
        having the sheet. Changing a class keeps its assignment id (students' work stays linked).
        A "direct" key (individual students, or null to take it back) is optional: leaving it
        out keeps it as it is."""
        title = ActivityService(self.db, self.user).require(activity_id)["title"]
        year_id = self.year_id()
        self.require_open_year(year_id)
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

        old = self.assignments.ids_by_class(activity_id, year_id)
        for assignment in cleaned:
            class_name = self.classes.get_for_teacher(assignment["class_id"], self.user["id"])["name"]
            if assignment["class_id"] in old:
                assignment_id = old.pop(assignment["class_id"])
                existing = self.assignments.get(activity_id, assignment["class_id"])
                if self.changed(existing, assignment["everyone"], assignment["due_date"], assignment["student_ids"]):
                    self.log_giving("assignment.updated", f"Changed how {title} is given to {class_name}.", title,
                                    class_name, assignment_id)
                self.assignments.update(assignment_id, assignment["everyone"], assignment["due_date"])
            else:
                assignment_id = self.assignments.create(activity_id, assignment["class_id"], assignment["everyone"],
                                                        assignment["due_date"], year_id)
                self.log_giving("assignment.given", f"Gave {title} to {class_name}"
                                + (f", due {assignment['due_date']}." if assignment["due_date"] else "."), title,
                                class_name, assignment_id)
            self.assignments.set_chosen_students(assignment_id, assignment["student_ids"])
        for class_id, assignment_id in old.items():  # classes no longer listed
            name = self.classes.get_for_teacher(class_id, self.user["id"])["name"]
            if self.assignments.has_submitted_work(assignment_id):
                raise ValidationError(f"Students in {name} already submitted, so it can't be taken back.")
            self.assignments.delete(assignment_id)  # with answers saved but not submitted yet
            self.log_giving("assignment.taken_back", f"Took back {title} from {name}.", title, name, assignment_id)
        if change_direct:
            self.save_direct(activity_id, direct)
        self.commit()
        return self.overview(activity_id)

