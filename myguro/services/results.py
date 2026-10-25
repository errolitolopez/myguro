from myguro.domain import scoring
from myguro.domain.grading import clean_feedback, teacher_points
from myguro.domain.work import clean_paper_score
from myguro.errors import NotFoundError, ValidationError
from myguro.services.attempts import grade_attempt
from myguro.services.base import Service
from myguro.domain.text import plural
from myguro.services.presenters import class_title, user_json


class ResultsService(Service):
    """A teacher's results for an assignment: scores, checking short answers, another try,
    paper scores."""

    def require(self, assignment_id):
        assignment = self.assignments.get_for_teacher(assignment_id, self.user["id"])
        if assignment is None:
            raise NotFoundError("Not found.")
        return assignment

    def require_open(self, assignment_id):
        """Like require(), but only while its school year is the current one (past years are read-only)."""
        assignment = self.require(assignment_id)
        self.require_open_year(assignment["school_year_id"])
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
        assignment = self.require_open(assignment_id)
        if not isinstance(excluded, bool):
            raise ValidationError("Choose whether to exclude the student.")
        if student_id not in {row["id"] for row in self.assignments.students(assignment)}:
            raise NotFoundError("This student doesn't have this activity.")
        if excluded and self.submissions.latest(assignment_id, student_id, submitted_only=True):
            raise ValidationError("This student already submitted, so they can't be excluded.")
        was_excluded = student_id in self.assignments.excluded_ids(assignment_id)
        self.assignments.set_excluded(assignment_id, student_id, excluded)
        if was_excluded != excluded:
            self.log_giving("assignment.excluded" if excluded else "assignment.included",
                            f"{'Excluded' if excluded else 'Added back'} {self.student_name(student_id)} "
                            f"{'from' if excluded else 'to'} {assignment['title']} ({assignment['class_name']}).", assignment)
        self.commit()
        return {"excluded": excluded}

    def student_name(self, student_id):
        return self.users.get(student_id)["name"]

    def log_giving(self, action, summary, assignment):
        """An activity log entry about an assignment (the row from assignments.get_for_teacher)."""
        self.log(action, "giving", summary, ("assignment", assignment["id"],
                                             f"{assignment['title']} - {class_title(assignment['class_name'], assignment['class_subject'])}"))

    def log_checking(self, action, summary, assignment_id, student_id):
        """An activity log entry about checking one student's work on an assignment."""
        assignment = self.assignments.get_for_teacher(assignment_id, self.user["id"])
        self.log(action, "checking", summary, ("assignment", assignment_id,
                                               f"{assignment['title']} - {self.student_name(student_id)}"))

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

        excluded_ids = set(self.assignments.excluded_ids(assignment_id))
        students = []
        for student in self.assignments.students(assignment):
            attempts = self.submissions.attempts(assignment_id, student["id"])
            submitted = [attempt for attempt in attempts if attempt["submitted_at"]]
            latest = attempts[-1] if attempts else None
            counted = submitted[-1] if submitted else None
            excluded = student["id"] in excluded_ids
            if excluded:
                status = "excluded"  # the teacher took this student off the activity (absent)
            elif latest is None:
                status = "not_started"
            elif latest["submitted_at"]:
                status = "submitted"
            else:
                status = "in_progress"  # first time, or trying again
            score = self.score(counted["id"], activity_id) if counted else None
            students.append({
                **user_json(student),
                "status": status,
                "excluded": excluded,
                "attempts": len(submitted),
                "submitted_at": counted["submitted_at"] if counted else None,
                # When that attempt (the one that counts, else the one being answered) was started;
                # a paper score has no real start
                "started_at": (counted or latest)["started_at"] if latest and not (counted or latest)["paper"] else None,
                "auto_submitted": bool(counted and counted["auto_submitted"]),
                "late": bool(counted and counted["late"]),
                "paper": bool(counted and counted["paper"]),
                "score": score["total"] if score else None,
                "section_scores": {str(key): value for key, value in score["sections"].items()} if score else {},
            })

        # Excluded students stay in the list but do not count in the totals or the average.
        counted_students = [student for student in students if not student["excluded"]]
        scored = [student["score"] for student in counted_students if student["score"]]
        summary = {
            "students": len(counted_students),
            "submitted": len(scored),
            "not_started": sum(student["status"] == "not_started" for student in counted_students),
            "late": sum(student["late"] for student in counted_students),
            "to_check": sum(score["pending"] for score in scored),
            "average": scoring.average_percent(scored),
            "excluded": len(students) - len(counted_students),
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
                "status": assignment["status"],
                "everyone": bool(assignment["everyone"]),
                "max_attempts": assignment["max_attempts"],
                "total_points": self.activities.total_points(activity_id),
            },
            "sections": sections,
            "students": students,
            "summary": summary,
        }

    def to_check(self, activity_id=None):
        """The cards for checking results: every assignment of the school year the teacher is
        looking at (of one sheet, if activity_id is given), the ones with points still to check first."""
        cards = []
        for assignment_id in self.assignments.ids_for_teacher(self.user["id"], self.year_id()):
            data = self.results(assignment_id)
            summary = data["summary"]
            if activity_id and data["assignment"]["activity_id"] != activity_id:
                continue
            cards.append({
                "id": assignment_id,
                "title": data["assignment"]["title"],
                "class_name": data["assignment"]["class_name"],
                "students": summary["students"],
                "submitted": summary["submitted"],
                "to_check": summary["to_check"],
                "average": summary["average"],  # None until something is checked
                "due_date": data["assignment"]["due_date"],
                "status": data["assignment"]["status"],
            })
        # sorted() is stable, so assignments with the same to-check state stay newest first
        return sorted(cards, key=lambda card: card["to_check"] == 0)

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
                question["feedback"] = row["feedback"] if row else ""
        return {
            "id": submission["id"],
            "attempt": submission["attempt"],
            "started_at": None if submission["paper"] else submission["started_at"],
            "submitted_at": submission["submitted_at"],
            "auto_submitted": bool(submission["auto_submitted"]),  # submitted by a close, not by the student
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

    def set_points(self, submission_id, posted, remarks=None):
        """The teacher scores a submitted attempt: {question id: points}. For short answers, and
        to change any auto-checked score (e.g. accept a different spelling). `remarks` is
        {question id: text}: the teacher's feedback on an answer ('' removes it)."""
        submission = self.require_submission(submission_id)
        self.require_open_year(submission["school_year_id"])
        if not submission["submitted_at"]:
            raise ValidationError("The student hasn't submitted this attempt yet.")
        if submission["paper"]:
            raise ValidationError("This is a paper score: change its total instead.")
        posted = {} if posted is None else posted
        remarks = {} if remarks is None else remarks
        if not isinstance(posted, dict) or not isinstance(remarks, dict):
            raise ValidationError("Points are not valid.")
        questions = {str(question["id"]): question for question in self.activities.questions(submission["activity_id"])}
        numbers = {str(question["id"]): number for number, question in enumerate(questions.values(), start=1)}
        before = self.submissions.answer_rows(submission_id)
        for key, points in posted.items():
            question = questions.get(str(key))
            if question is None:
                raise ValidationError("Question not found.")
            value = teacher_points(question, points)
            self.submissions.set_teacher_points(submission_id, question["id"],
                                                None if value is None else int(value == question["points"]), value)
        for key, text in remarks.items():
            question = questions.get(str(key))
            if question is None:
                raise ValidationError("Question not found.")
            self.submissions.set_feedback(submission_id, question["id"], clean_feedback(text))
        self.log_scoring(submission, numbers, before, self.submissions.answer_rows(submission_id))
        self.commit()
        return self.attempt_detail(self.require_submission(submission_id), submission["activity_id"])

    def log_scoring(self, submission, numbers, before, after):
        """Log the points that changed ("question 3: 0 to 2") and, separately, the remarks written."""
        points, remarks = [], []
        for key, number in numbers.items():
            old, new = before.get(int(key)), after.get(int(key))
            old_points = old["points"] if old else None
            new_points = new["points"] if new else None
            if old_points != new_points:
                points.append(f"question {number}: {'unchecked' if old_points is None else old_points} to "
                              f"{'unchecked' if new_points is None else new_points}")
            if (old["feedback"] if old else "") != (new["feedback"] if new else ""):
                remarks.append(str(number))
        who = self.student_name(submission["student_id"])
        if points:
            self.log_checking("checking.points", f"Changed points of {who}: {'; '.join(points)}.",
                              submission["assignment_id"], submission["student_id"])
        if remarks:
            self.log_checking("checking.remark", f"Wrote or changed remarks for {who} on question "
                              f"{', '.join(remarks)}.", submission["assignment_id"], submission["student_id"])

    def set_released(self, assignment_id, released):
        """Show (or hide again) the students' scores of this assignment to the students."""
        assignment = self.require_open(assignment_id)
        if not isinstance(released, bool):
            raise ValidationError("Choose whether to release the scores.")
        self.assignments.set_scores_released(assignment_id, released)
        if bool(assignment["scores_released"]) != released:
            self.log_giving("assignment.released" if released else "assignment.hidden",
                            f"{'Released' if released else 'Hid'} the scores of {assignment['title']} "
                            f"({assignment['class_name']}) {'to' if released else 'from'} the students.", assignment)
        self.commit()
        return {"scores_released": released}

    def set_status(self, assignment_id, status):
        """Open the assignment (from not started, or re-open it after a close) or close it (from open).

        Closing is final for the students: every attempt not submitted yet, and every student who
        never started, is submitted as it stands (answers saved so far, unanswered = 0 points, never
        late). Students can still read the activity but not answer it. Re-opening puts those
        attempts back to in progress with the answers the student really wrote, so they can continue;
        students who submitted on their own stay submitted.
        Returns {status, changed: how many attempts the close submitted or the re-open put back}."""
        assignment = self.require_open(assignment_id)
        before = assignment["status"]
        if status not in ("open", "closed"):
            raise ValidationError("Choose open or closed.")
        if status == "closed" and before != "open":
            raise ValidationError("Open the activity before closing it.")
        if status == before:
            return {"status": status, "changed": 0}
        changed = 0
        if status == "closed":
            changed = self.submit_unfinished(assignment)
        elif before == "closed":
            changed = self.put_back_in_progress(assignment)
        self.assignments.set_status(assignment_id, status)
        where = f"{assignment['title']} ({assignment['class_name']})"
        if status == "closed":
            self.log_giving("assignment.closed", f"Closed {where}; {plural(changed, 'unfinished attempt')} "
                            "submitted as they were.", assignment)
        elif before == "closed":
            self.log_giving("assignment.reopened", f"Re-opened {where}; {plural(changed, 'attempt')} "
                            "back to in progress.", assignment)
        else:
            self.log_giving("assignment.opened", f"Opened {where} to the students.", assignment)
        self.commit()
        return {"status": status, "changed": changed}

    def submit_unfinished(self, assignment):
        """Submit what the students have so far, for the close: attempts being answered, and
        students who never started (an empty attempt, 0 points). Excluded students are left out."""
        assignment_id = assignment["id"]
        questions = self.activities.questions(assignment["activity_id"])
        excluded = set(self.assignments.excluded_ids(assignment_id))
        count = 0
        for student in self.assignments.students(assignment):
            if student["id"] in excluded:
                continue
            latest = self.submissions.latest(assignment_id, student["id"])
            if latest and latest["submitted_at"]:
                continue
            if latest is None:
                latest = self.submissions.get(self.submissions.create_attempt(assignment_id, student["id"], 1))
            grade_attempt(self, assignment_id, latest, questions, student["id"])
            self.submissions.mark_auto_submitted(latest["id"])
            count += 1
        return count

    def put_back_in_progress(self, assignment):
        """Undo the close for the attempts it submitted (see set_status)."""
        attempts = self.submissions.auto_submitted_latest(assignment["id"])
        for submission in attempts:
            self.submissions.back_to_in_progress(submission["id"])  # an empty one is simply removed
        return len(attempts)

    def reopen(self, assignment_id, student_id):
        """Give one student another try, even past the activity's limit: a new attempt starting
        from their last answers. Their counted score stays until they submit it."""
        assignment = self.require_open(assignment_id)
        if assignment["status"] != "open":
            raise ValidationError("Open the activity first: students can't answer while it is closed.")
        self.require_included(assignment_id, student_id)
        attempts = self.submissions.attempts(assignment_id, student_id)
        if not attempts:
            raise ValidationError("The student hasn't started yet.")
        last = attempts[-1]
        if not last["submitted_at"]:
            raise ValidationError("The student is already answering (not submitted yet).")
        new_id = self.submissions.create_attempt(assignment_id, student_id, last["attempt"] + 1)
        self.submissions.copy_answers(last["id"], new_id)
        self.log_checking("checking.retry_given", f"Gave {self.student_name(student_id)} another try "
                          f"(attempt {last['attempt'] + 1}).", assignment_id, student_id)
        self.commit()
        return self.student_result(assignment_id, student_id)

    def add_paper(self, assignment_id, student_id, data):
        """The student answered on paper: save the total score as a new attempt (the latest
        submission counts). {score, late, note}"""
        assignment = self.require_open(assignment_id)
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
        self.log_checking("checking.paper_set", f"Entered a paper score of {score} for {self.student_name(student_id)}.",
                          assignment_id, student_id)
        self.commit()
        return self.student_result(assignment_id, student_id)

    def require_paper(self, submission_id):
        submission = self.require_submission(submission_id, "Paper score not found.")
        if not submission["paper"]:
            raise NotFoundError("Paper score not found.")
        self.require_open_year(submission["school_year_id"])
        return submission

    def edit_paper(self, submission_id, data):
        submission = self.require_paper(submission_id)
        score, late, note = clean_paper_score(data, self.activities.total_points(submission["activity_id"]))
        self.submissions.update_paper(submission_id, score, late, note)
        self.log_checking("checking.paper_changed", f"Changed the paper score of {self.student_name(submission['student_id'])} "
                          f"to {score}.", submission["assignment_id"], submission["student_id"])
        self.commit()
        return self.student_result(submission["assignment_id"], submission["student_id"])

    def delete_paper(self, submission_id):
        """Remove a paper score (e.g. typed for the wrong student). The attempt before it counts again."""
        submission = self.require_paper(submission_id)
        self.submissions.delete(submission_id)
        self.log_checking("checking.paper_removed", f"Removed the paper score of {self.student_name(submission['student_id'])}.",
                          submission["assignment_id"], submission["student_id"])
        self.commit()
        return self.student_result(submission["assignment_id"], submission["student_id"])
