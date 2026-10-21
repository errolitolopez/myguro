from myguro.config import school_today
from myguro.domain.grading import check_answer, clean_student_answer, question_for_student
from myguro.domain.work import can_try_again, is_late
from myguro.errors import NotFoundError, ValidationError
from myguro.services.base import Service
from myguro.services.presenters import class_title


class StudentWorkService(Service):
    """A student answering what was given to them: saved as they go, submitted, tried again."""

    def require(self, assignment_id):
        """The assignment, if this student was given it; else NotFoundError."""
        assignment = self.assignments.get_for_student(assignment_id, self.user["id"])
        if assignment is None:
            raise NotFoundError("Activity not found.")
        return assignment

    def exists(self, assignment_id):
        return self.assignments.get_for_student(assignment_id, self.user["id"]) is not None

    def list(self):
        """Everything given to the student, with how far they are: for My activities."""
        today = school_today().isoformat()
        result = []
        for row in self.assignments.list_for_student(self.user["id"]):
            if row["submitted_at"]:
                status = "submitted"
            elif row["submission_id"]:
                status = "in_progress"
            else:
                status = "not_started"
            result.append({
                "id": row["id"],
                "title": row["title"],
                "subject": row["subject"],
                "class_name": class_title(row["class_name"], row["class_subject"]),
                "teacher": row["teacher"],
                "due_date": row["due_date"],
                # Overdue only when nothing was ever submitted
                "overdue": bool(row["due_date"] and row["last_id"] is None and today > row["due_date"]),
                "status": status,
                "attempt": row["attempt"] or 0,
                "max_attempts": row["max_attempts"],
                "can_retry": status == "submitted" and can_try_again(row, row["max_attempts"]),
                "late": bool(row["last_late"]),
                "paper": bool(row["last_paper"]),
                # Submitted at least once (stays true while trying again)
                "done": row["last_id"] is not None,
                "scores_released": bool(row["scores_released"]),
                # The score that counts: the latest submitted attempt. Hidden until the teacher
                # releases the scores.
                "score": self.score(row["last_id"], row["activity_id"])["total"]
                if row["last_id"] and row["scores_released"] else None,
            })
        return result

    def detail(self, assignment_id):
        """The sheet to answer (no answer keys), the saved answers, and the score that counts."""
        assignment = self.require(assignment_id)
        submission = self.submissions.latest(assignment_id, self.user["id"])
        last_submitted = self.submissions.latest(assignment_id, self.user["id"], submitted_only=True)
        sections = self.activities.sections(assignment["activity_id"])
        for section in sections:
            section["questions"] = [question_for_student(question) for question in section["questions"]]
        feedback = self.submissions.feedback(last_submitted["id"]) \
            if last_submitted and assignment["scores_released"] and submission["submitted_at"] else {}
        return {
            "id": assignment_id,
            "title": assignment["title"],
            "subject": assignment["subject"],
            "class_name": class_title(assignment["class_name"], assignment["class_subject"]),
            "teacher": assignment["teacher"],
            "due_date": assignment["due_date"],
            "sections": sections,
            # A submitted attempt shows the blank sheet: the student's answers are not shown back.
            "answers": {} if submission and submission["submitted_at"]
            else self.submissions.answers(submission["id"] if submission else None),
            "submitted_at": submission["submitted_at"] if submission else None,
            "attempt": submission["attempt"] if submission else 1,
            "max_attempts": assignment["max_attempts"],
            "can_retry": bool(submission and submission["submitted_at"]
                              and can_try_again(submission, assignment["max_attempts"])),
            # The latest submitted attempt counts. While working on a new attempt, this is the
            # earlier one's score (submitting again replaces it).
            # Hidden until the teacher releases the scores.
            "scores_released": bool(assignment["scores_released"]),
            "score": self.score(last_submitted["id"], assignment["activity_id"])
            if last_submitted and assignment["scores_released"] else None,
            # The teacher's remarks, only on the submitted sheet and once the scores are released.
            "feedback": feedback,
            # The student's own answer, only for the questions that have a remark (so a released
            # sheet does not hand out every answer to be passed around).
            "feedback_answers": {question_id: answer for question_id, answer in
                                 self.submissions.answers(last_submitted["id"]).items() if question_id in feedback}
            if feedback else {},
            "late": bool(last_submitted and last_submitted["late"]),
            "paper": bool(last_submitted and last_submitted["paper"]),
            "note": last_submitted["note"] if last_submitted and assignment["scores_released"] else "",
        }

    def current_attempt(self, assignment_id):
        """The attempt being answered, made (as attempt 1) the first time they save."""
        submission = self.submissions.latest(assignment_id, self.user["id"])
        if submission and submission["submitted_at"]:
            raise ValidationError("You already submitted this activity.")
        if submission is None:
            self.submissions.create_attempt(assignment_id, self.user["id"], 1)
            submission = self.submissions.latest(assignment_id, self.user["id"])
        return submission

    def save_answers(self, submission, questions, posted):
        """Save the posted {question id: answer} (only questions of this sheet)."""
        if not isinstance(posted, dict):
            raise ValidationError("Answers are not valid.")
        by_id = {str(question["id"]): question for question in questions}
        for key, value in posted.items():
            question = by_id.get(str(key))
            if question is None:
                continue  # a question removed by the teacher while the student worked
            self.submissions.save_answer(submission["id"], question["id"], clean_student_answer(question, value))
        self.submissions.touch(submission["id"])

    def save(self, assignment_id, posted):
        """Save answers while working (called automatically as the student types)."""
        assignment = self.require(assignment_id)
        submission = self.current_attempt(assignment_id)
        self.save_answers(submission, self.activities.questions(assignment["activity_id"]), posted)
        self.commit()

    def submit(self, assignment_id, posted):
        """Save the last answers, check them, and submit. Late when after the due date."""
        assignment = self.require(assignment_id)
        submission = self.current_attempt(assignment_id)
        questions = self.activities.questions(assignment["activity_id"])
        self.save_answers(submission, questions, posted)

        answers = self.submissions.answers(submission["id"])
        # Short answers the teacher already scored in the previous attempt keep their score when
        # the student didn't change them, so the teacher doesn't check the same text twice.
        previous = self.submissions.latest(assignment_id, self.user["id"], submitted_only=True)
        earlier_scores = self.submissions.scored_answers(previous["id"]) if previous else {}
        for question in questions:
            is_correct, points = check_answer(question, answers.get(question["id"]))
            earlier = earlier_scores.get(question["id"])
            if (question["type"] == "short_answer" and earlier and question["id"] in answers
                    and earlier[0] == answers[question["id"]]):
                points = earlier[1]
                is_correct = points == question["points"]
            # Unanswered questions get an empty answer, so they show as 0 points (short answers too).
            answered = question["id"] in answers
            self.submissions.set_check(submission["id"], question["id"],
                                       is_correct if answered else False, points if answered else 0, answered)
        self.submissions.mark_submitted(submission["id"], is_late(assignment["due_date"], school_today()))
        self.commit()
        return self.detail(assignment_id)

    def retry(self, assignment_id):
        """Start the next attempt, if the activity allows more. It starts with the answers of the
        last attempt so the student only changes what they want."""
        assignment = self.require(assignment_id)
        submission = self.submissions.latest(assignment_id, self.user["id"])
        if submission is None or not submission["submitted_at"]:
            raise ValidationError("Submit this activity first.")
        if submission["paper"]:
            raise ValidationError("Your teacher already scored this from your paper.")
        if not can_try_again(submission, assignment["max_attempts"]):
            raise ValidationError("You have used all your tries for this activity.")
        new_id = self.submissions.create_attempt(assignment_id, self.user["id"], submission["attempt"] + 1)
        self.submissions.copy_answers(submission["id"], new_id)
        self.commit()
        return self.detail(assignment_id)
