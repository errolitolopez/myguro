from myguro.domain import scoring
from myguro.services.base import Service
from myguro.services.classes import ClassService
from myguro.services.presenters import class_json, user_json
from myguro.services.results import ResultsService


class GradebookService(Service):
    """A class gradebook: every student of the class against every activity given to the class."""

    def gradebook(self, class_id):
        """The teacher's class with one column per activity and one row per student. A cell is
        None when the student was not given that activity, else the status and the score that
        counts (what the results page shows). Also used by the Excel/PDF exports."""
        class_row = ClassService(self.db, self.user).require(class_id)
        results = ResultsService(self.db, self.user)

        # Oldest first, so new activities appear on the right.
        assignments = list(reversed(self.assignments.for_class(class_id)))
        activities = []
        by_student = {}  # student id -> {"person": ..., "cells": {assignment id: result row}}
        for student in self.classes.students(class_id):
            by_student[student["id"]] = {"person": user_json(student), "cells": {}}
        for assignment in assignments:
            data = results.results(assignment["id"])
            activities.append({
                "assignment_id": assignment["id"],
                "activity_id": data["assignment"]["activity_id"],
                "title": data["assignment"]["title"],
                "due_date": data["assignment"]["due_date"],
                "total_points": data["assignment"]["total_points"],
                "average": data["summary"]["average"],
            })
            for row in data["students"]:
                entry = by_student.setdefault(row["id"], {"person": {key: row[key] for key in (
                    "id", "name", "username", "grade", "section")}, "cells": {}})
                entry["cells"][assignment["id"]] = row

        students = []
        for entry in by_student.values():
            cells, scores = [], []
            for activity in activities:
                row = entry["cells"].get(activity["assignment_id"])
                cells.append(None if row is None else self.cell(row))
                if row and not row["excluded"] and row["score"]:
                    scores.append(row["score"])
            students.append({**entry["person"], "cells": cells, "submitted": len(scores),
                             "average": scoring.average_percent(scores)})
        students.sort(key=lambda student: student["name"].lower())
        return {"class": class_json(class_row), "activities": activities, "students": students}

    @staticmethod
    def cell(row):
        """One student's result for one activity."""
        score = row["score"]
        checkable = score["possible"] - score["pending"] if score else 0
        return {
            "status": row["status"],
            "earned": score["earned"] if score else None,
            "possible": score["possible"] if score else None,
            "pending": score["pending"] if score else 0,
            "percent": round(100 * score["earned"] / checkable) if score and checkable else None,
            "late": row["late"],
            "paper": row["paper"],
        }
