from myguro.domain import scoring
from myguro.domain.grading import teacher_points
from myguro.domain.work import clean_paper_score
from myguro.errors import NotFoundError, ValidationError
from myguro.services.base import Service
from myguro.services.presenters import class_title, user_json


class ResultsService(Service):
    """A teacher's results for an assignment: scores, checking short answers, another try,
    paper scores."""

    def require(self, assignment_id):
        assignment = self.assignments.get_for_teacher(assignment_id, self.user["id"])
        if assignment is None:
            raise NotFoundError("Not found.")
        return assignment

    def exists(self, assignment_id):
        return self.assignments.get_for_teacher(assignment_id, self.user["id"]) is not None

    def require_included(self, assignment_id, student_id):
        """Refuse to work on a student the teacher excluded from this assignment."""
        if student_id in self.assignments.excluded_ids(assignment_id):
            raise ValidationError("Add the student back first.")

    def set_excluded(self, assignment_id, student_id, excluded):
        """Exclude a student from this assignment (for example absent) or add them back. Saved
        answers are kept. A student who already submitted can't be excluded."""
        assignment = self.require(assignment_id)
        if not isinstance(excluded, bool):
            raise ValidationError("Choose whether to exclude the student.")
        if student_id not in {row["id"] for row in self.assignments.students(assignment)}:
            raise NotFoundError("This student doesn't have this activity.")
        if excluded and self.submissions.latest(assignment_id, student_id, submitted_only=True):
            raise ValidationError("This student already submitted, so they can't be excluded.")
        self.assignments.set_excluded(assignment_id, student_id, excluded)
        self.commit()
        return {"excluded": excluded}

    def require_submission(self, submission_id, message="Not found."):
        submission = self.submissions.get_for_teacher(submission_id, self.user["id"])
        if submission is None:
            raise NotFoundError(message)
        return submission

    def results(self, assignment_id):
        """Every student of the assignment with status, tries and the score that counts (latest
        submitted attempt), in total and per activity section, plus a summary. Also used by the
        Excel/PDF exports."""
        assignment = self.require(assignment_id)
        activity_id = assignment["activity_id"]
        sections = [{"id": section["id"], "title": section["title"] or f"Section {number}",
                     "points": sum(question["points"] for question in section["questions"])}
                    for number, section in enumerate(self.activities.sections(activity_id), start=1)
                    if section["kind"] == "activity"]

        students = []
        for student in self.assignments.students(assignment):
            attempts = self.submissions.attempts(assignment_id, student["id"])
            submitted = [attempt for attempt in attempts if attempt["submitted_at"]]
            latest = attempts[-1] if attempts else None
            counted = submitted[-1] if submitted else None
            if latest is None:
                status = "not_started"
            elif latest["submitted_at"]:
                status = "submitted"
            else:
                status = "in_progress"  # first time, or trying again
            score = self.score(counted["id"], activity_id) if counted else None
            students.append({
                **user_json(student),
                "status": status,
                "attempts": len(submitted),
                "submitted_at": counted["submitted_at"] if counted else None,
                "late": bool(counted and counted["late"]),
                "paper": bool(counted and counted["paper"]),
                "score": score["total"] if score else None,
                "section_scores": {str(key): value for key, value in score["sections"].items()} if score else {},
            })

        scored = [student["score"] for student in students if student["score"]]
        summary = {
            "students": len(students),
            "submitted": len(scored),
            "not_started": sum(student["status"] == "not_started" for student in students),
            "late": sum(student["late"] for student in students),
            "to_check": sum(score["pending"] for score in scored),
            "average": scoring.average_percent(scored),
        }
        return {
            "assignment": {
                "id": assignment_id,
                "activity_id": activity_id,
                "title": assignment["title"],
                "subject": assignment["subject"],
                "class_id": assignment["class_id"],
                "class_name": class_title(assignment["class_name"], assignment["class_subject"]),
                "due_date": assignment["due_date"],
                "scores_released": bool(assignment["scores_released"]),
                "everyone": bool(assignment["everyone"]),
                "max_attempts": assignment["max_attempts"],
                "total_points": self.activities.total_points(activity_id),
            },
            "sections": sections,
            "students": students,
            "summary": summary,
        }

    def attempt_detail(self, submission, activity_id):
        """One attempt: every section and question with the answer key, the student's answer,
        whether it is right, and the points."""
        rows = self.submissions.answer_rows(submission["id"])
        given = self.submissions.answers(submission["id"])
        sections = self.activities.sections(activity_id)
        for section in sections:
            for question in section["questions"]:
                row = rows.get(question["id"])
                question["given"] = given.get(question["id"]) if row else None
                question["is_correct"] = None if row is None or row["is_correct"] is None else bool(row["is_correct"])
                question["earned"] = row["points"] if row else None
        return {
            "id": submission["id"],
            "attempt": submission["attempt"],
            "submitted_at": submission["submitted_at"],
            "late": bool(submission["late"]),
            "paper": bool(submission["paper"]),
            "note": submission["note"],
            "score": self.score(submission["id"], activity_id) if submission["submitted_at"] else None,
            "sections": sections,
        }

    def student_result(self, assignment_id, student_id, wanted_attempt=None):
        """One student's work: their attempts, and one in detail (default: the latest submitted
        one, or the latest if none was submitted)."""
        assignment = self.require(assignment_id)
        student = self.users.get_student(student_id)
        if student is None:
            raise NotFoundError("Student not found.")
        attempts = self.submissions.attempts(assignment_id, student_id)
        detail = None
        if attempts:
            submitted = [attempt for attempt in attempts if attempt["submitted_at"]]
            chosen = next((attempt for attempt in attempts if attempt["attempt"] == wanted_attempt), None) \
                or (submitted[-1] if submitted else attempts[-1])
            detail = self.attempt_detail(chosen, assignment["activity_id"])
        counted = next((attempt for attempt in reversed(attempts) if attempt["submitted_at"]), None)
        return {
            "student": user_json(student),
            "attempts": [{
                "attempt": attempt["attempt"],
                "submitted_at": attempt["submitted_at"],
                "late": bool(attempt["late"]),
                "paper": bool(attempt["paper"]),
                "counts": counted is not None and attempt["id"] == counted["id"],
            } for attempt in attempts],
            "detail": detail,
            "can_reopen": bool(attempts and attempts[-1]["submitted_at"]),
            "possible": self.activities.total_points(assignment["activity_id"]),
        }

    def set_points(self, submission_id, posted):
        """The teacher scores a submitted attempt: {question id: points}. For short answers, and
        to change any auto-checked score (e.g. accept a different spelling)."""
        submission = self.require_submission(submission_id)
        if not submission["submitted_at"]:
            raise ValidationError("The student hasn't submitted this attempt yet.")
        if submission["paper"]:
            raise ValidationError("This is a paper score: change its total instead.")
        if not isinstance(posted, dict):
            raise ValidationError("Points are not valid.")
        questions = {str(question["id"]): question for question in self.activities.questions(submission["activity_id"])}
        for key, points in posted.items():
            question = questions.get(str(key))
            if question is None:
                raise ValidationError("Question not found.")
            value = teacher_points(question, points)
            self.submissions.set_teacher_points(submission_id, question["id"],
                                                None if value is None else int(value == question["points"]), value)
        self.commit()
        return self.attempt_detail(self.require_submission(submission_id), submission["activity_id"])

    def set_released(self, assignment_id, released):
        """Show (or hide again) the students' scores of this assignment to the students."""
        self.require(assignment_id)
        if not isinstance(released, bool):
            raise ValidationError("Choose whether to release the scores.")
        self.assignments.set_scores_released(assignment_id, released)
        self.commit()
        return {"scores_released": released}

    def reopen(self, assignment_id, student_id):
        """Give one student another try, even past the activity's limit: a new attempt starting
        from their last answers. Their counted score stays until they submit it."""
        self.require(assignment_id)
        self.require_included(assignment_id, student_id)
        attempts = self.submissions.attempts(assignment_id, student_id)
        if not attempts:
            raise ValidationError("The student hasn't started yet.")
        last = attempts[-1]
        if not last["submitted_at"]:
            raise ValidationError("The student is already answering (not submitted yet).")
        new_id = self.submissions.create_attempt(assignment_id, student_id, last["attempt"] + 1)
        self.submissions.copy_answers(last["id"], new_id)
        self.commit()
        return self.student_result(assignment_id, student_id)

    def add_paper(self, assignment_id, student_id, data):
        """The student answered on paper: save the total score as a new attempt (the latest
        submission counts). {score, late, note}"""
        assignment = self.require(assignment_id)
        if student_id not in {row["id"] for row in self.assignments.students(assignment)}:
            raise NotFoundError("This student doesn't have this activity.")
        self.require_included(assignment_id, student_id)
        possible = self.activities.total_points(assignment["activity_id"])
        if possible == 0:
            raise ValidationError("This activity has no questions to score.")
        score, late, note = clean_paper_score(data, possible)
        attempts = self.submissions.attempts(assignment_id, student_id)
        self.submissions.add_paper(assignment_id, student_id, (attempts[-1]["attempt"] + 1) if attempts else 1,
                                   score, late, note)
        self.commit()
        return self.student_result(assignment_id, student_id)

    def require_paper(self, submission_id):
        submission = self.require_submission(submission_id, "Paper score not found.")
        if not submission["paper"]:
            raise NotFoundError("Paper score not found.")
        return submission

    def edit_paper(self, submission_id, data):
        submission = self.require_paper(submission_id)
        score, late, note = clean_paper_score(data, self.activities.total_points(submission["activity_id"]))
        self.submissions.update_paper(submission_id, score, late, note)
        self.commit()
        return self.student_result(submission["assignment_id"], submission["student_id"])

    def delete_paper(self, submission_id):
        """Remove a paper score (e.g. typed for the wrong student). The attempt before it counts again."""
        submission = self.require_paper(submission_id)
        self.submissions.delete(submission_id)
        self.commit()
        return self.student_result(submission["assignment_id"], submission["student_id"])
