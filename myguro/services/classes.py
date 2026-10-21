from myguro.domain.accounts import MAX_NAME_LENGTH, check_name
from myguro.domain.text import clean_name, like_pattern
from myguro.errors import NotFoundError, ValidationError
from myguro.services.base import Service
from myguro.services.presenters import class_json, user_json

# Enough for a whole section; the teacher can narrow the search for more.
MAX_SEARCH_RESULTS = 200


class ClassService(Service):
    """A teacher's classes and the students in them (picked from the school's student list)."""

    def require(self, class_id):
        """The teacher's class, or NotFoundError."""
        row = self.classes.get_for_teacher(class_id, self.user["id"])
        if row is None:
            raise NotFoundError("Class not found.")
        return row

    def require_open(self, class_id):
        """The teacher's class, if it belongs to the current school year (a past year is read-only)."""
        row = self.require(class_id)
        self.require_open_year(row["school_year_id"])
        return row

    def exists(self, class_id):
        return self.classes.get_for_teacher(class_id, self.user["id"]) is not None

    def list(self):
        return [dict(row) for row in self.classes.list_for_teacher(self.user["id"], self.year_id())]

    def clean_fields(self, data, year_id, class_id=None):
        name = check_name(clean_name(data.get("name")), "Class name")
        subject = clean_name(data.get("subject"))
        if len(subject) > MAX_NAME_LENGTH:
            raise ValidationError("Subject can be at most 100 characters.")
        same = self.classes.find_same(self.user["id"], name, subject, year_id)
        if same and same["id"] != class_id:
            raise ValidationError("You already have a class with this name and subject.")
        return name, subject

    def create(self, data):
        year_id = self.year_id()
        self.require_open_year(year_id)
        class_id = self.classes.create(self.user["id"], *self.clean_fields(data, year_id), year_id)
        self.commit()
        return class_json(self.require(class_id))

    def update(self, class_id, data):
        row = self.require_open(class_id)
        self.classes.update(class_id, *self.clean_fields(data, row["school_year_id"], class_id))
        self.commit()
        return class_json(self.require(class_id))

    def students(self, class_id):
        return [user_json(row) for row in self.classes.students(class_id)]

    def detail(self, class_id):
        """The class, its students, and the sheets given to it."""
        row = self.require(class_id)
        activities = [{
            "id": item["id"],
            "activity_id": item["activity_id"],
            "title": item["title"],
            "subject": item["subject"],
            "due_date": item["due_date"],
            "everyone": bool(item["everyone"]),
            "selected": item["selected"],
        } for item in self.assignments.for_class(class_id)]
        return {"class": class_json(row), "students": self.students(class_id), "activities": activities}

    def search_students(self, class_id, query="", grade=None, section=None):
        """Search the school's students to add: name, username or section; grade/section filter
        exactly (section "" = no section). Also the grade + section pairs, for the dropdowns."""
        self.require(class_id)
        rows = self.classes.search_students(
            class_id, like_pattern(clean_name(query)), grade or None,
            None if section is None else clean_name(section), MAX_SEARCH_RESULTS,
        )
        return {
            "students": [{**user_json(row), "in_class": bool(row["in_class"])} for row in rows],
            "more": len(rows) == MAX_SEARCH_RESULTS,
            "sections": [{"grade": row["grade"], "section": row["section"]} for row in self.classes.grade_sections()],
        }

    def add_students(self, class_id, data):
        """Put students in the class: student_ids (e.g. a whole section) or student_id.
        Students already in it are skipped. Returns the ones added."""
        self.require_open(class_id)
        ids = data.get("student_ids", [data.get("student_id")])
        if not isinstance(ids, list) or not ids:
            raise ValidationError("No students to add.")
        added = []
        for student_id in ids:
            student = self.users.get_student(student_id, active_only=True)
            if student is None:
                raise NotFoundError("Student not found.")
            if not self.classes.has_student(class_id, student["id"]):
                self.classes.add_student(class_id, student["id"])
                added.append(user_json(student))
        self.commit()
        if not added and len(ids) == 1:
            raise ValidationError("This student is already in the class.")
        return added

    def remove_student(self, class_id, student_id):
        """Take a student out of the class. Their account and other classes are kept."""
        if not self.exists(class_id) or not self.classes.has_student(class_id, student_id):
            raise NotFoundError("Student not found in this class.")
        self.require_open(class_id)
        self.classes.remove_student(class_id, student_id)
        self.commit()

    def remove_students(self, class_id, data):
        """Take several students out of the class: student_ids. Ids not in the class are skipped.
        Returns how many were removed."""
        self.require_open(class_id)
        ids = data.get("student_ids")
        if not isinstance(ids, list) or not ids:
            raise ValidationError("Choose at least one student.")
        removed = 0
        for student_id in set(ids):
            if isinstance(student_id, int) and self.classes.has_student(class_id, student_id):
                self.classes.remove_student(class_id, student_id)
                removed += 1
        self.commit()
        return removed
