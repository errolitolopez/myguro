from myguro.services.base import Service
from myguro.services.classes import ClassService
from myguro.services.student_work import StudentWorkService


class DashboardService(Service):
    """The numbers on each role's dashboard."""

    def data(self):
        role = self.user["role"]
        year_id = self.year_id()
        if role == "admin":
            return {
                "role": "admin",
                "teachers": self.users.count("teacher"),
                "active_teachers": self.users.count("teacher", active_only=True),
                "classes": self.classes.count_all(year_id),
                "students": self.users.count("student"),
                "supervisors": self.users.count("supervisor"),
                "activities": self.activities.count_all(),
            }
        if role == "student":
            return {
                "role": "student",
                "classes": [dict(row) for row in self.classes.classes_of_student(self.user["id"], year_id)],
                "submitted": self.submissions.count_submitted_by_student(self.user["id"], year_id),
                "to_do": sum(1 for item in StudentWorkService(self.db, self.user).list() if not item["done"]),
            }
        teacher_id = self.user["id"]
        return {
            "role": "teacher",
            "classes": ClassService(self.db, self.user).list(),
            "students": self.classes.count_students_of_teacher(teacher_id, year_id),
            # Assignments (a sheet given to a class or group) by status
            "open": self.assignments.count_for_teacher(teacher_id, year_id, "open"),
            "not_started": self.assignments.count_for_teacher(teacher_id, year_id, "not_started"),
            "closed": self.assignments.count_for_teacher(teacher_id, year_id, "closed"),
            # Students who submitted (each student once per assignment, however many attempts)
            "submissions": self.submissions.count_submitted_for_teacher(teacher_id, year_id),
        }
