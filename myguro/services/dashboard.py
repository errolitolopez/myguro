from myguro.services.base import Service
from myguro.services.classes import ClassService
from myguro.services.student_work import StudentWorkService


class DashboardService(Service):
    """The numbers on each role's dashboard."""

    def data(self):
        role = self.user["role"]
        if role == "admin":
            return {
                "role": "admin",
                "teachers": self.users.count("teacher"),
                "active_teachers": self.users.count("teacher", active_only=True),
                "classes": self.classes.count_all(),
                "students": self.users.count("student"),
                "activities": self.activities.count_all(),
            }
        if role == "student":
            return {
                "role": "student",
                "classes": [dict(row) for row in self.classes.classes_of_student(self.user["id"])],
                "submitted": self.submissions.count_submitted_by_student(self.user["id"]),
                "to_do": sum(1 for item in StudentWorkService(self.db, self.user).list() if not item["done"]),
            }
        teacher_id = self.user["id"]
        return {
            "role": "teacher",
            "classes": ClassService(self.db, self.user).list(),
            "students": self.classes.count_students_of_teacher(teacher_id),
            "published": self.activities.count_for_teacher(teacher_id, published=True),
            "drafts": self.activities.count_for_teacher(teacher_id, published=False),
            # Students who submitted (each student once per assignment, however many attempts)
            "submissions": self.submissions.count_submitted_for_teacher(teacher_id),
        }
