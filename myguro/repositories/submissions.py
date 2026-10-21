import json

from myguro.repositories.base import Repository


class SubmissionRepository(Repository):
    """Students' attempts (submissions) and their answers (submission_answers)."""

    def latest(self, assignment_id, student_id, submitted_only=False):
        """The student's latest attempt (or latest submitted one), or None."""
        return self.one(
            "SELECT * FROM submissions WHERE assignment_id = ? AND student_id = ?"
            + (" AND submitted_at IS NOT NULL" if submitted_only else "")
            + " ORDER BY attempt DESC LIMIT 1",
            (assignment_id, student_id),
        )

    def attempts(self, assignment_id, student_id):
        return self.all("SELECT * FROM submissions WHERE assignment_id = ? AND student_id = ? ORDER BY attempt",
                        (assignment_id, student_id))

    def get(self, submission_id):
        return self.one("SELECT * FROM submissions WHERE id = ?", (submission_id,))

    def get_for_teacher(self, submission_id, teacher_id):
        """A submission of the teacher's sheet, with its activity id."""
        return self.one(
            """
            SELECT sub.*, asg.activity_id FROM submissions sub
            JOIN assignments asg ON asg.id = sub.assignment_id
            JOIN activities a ON a.id = asg.activity_id
            WHERE sub.id = ? AND a.teacher_id = ? AND a.deleted_at IS NULL
            """,
            (submission_id, teacher_id),
        )

    def create_attempt(self, assignment_id, student_id, attempt):
        return self.execute("INSERT INTO submissions (assignment_id, student_id, attempt) VALUES (?, ?, ?)",
                            (assignment_id, student_id, attempt)).lastrowid

    def copy_answers(self, from_submission_id, to_submission_id):
        """Start a new attempt with the answers of an earlier one (not the checks)."""
        self.execute(
            "INSERT INTO submission_answers (submission_id, question_id, answer) "
            "SELECT ?, question_id, answer FROM submission_answers WHERE submission_id = ? AND answer != 'null'",
            (to_submission_id, from_submission_id),
        )

    def answers(self, submission_id):
        """{question id: answer} of a submission."""
        if submission_id is None:
            return {}
        return {row["question_id"]: json.loads(row["answer"]) for row in self.all(
            "SELECT question_id, answer FROM submission_answers WHERE submission_id = ?", (submission_id,))}

    def answer_rows(self, submission_id):
        """{question id: row with answer, is_correct, points}."""
        return {row["question_id"]: row for row in self.all(
            "SELECT * FROM submission_answers WHERE submission_id = ?", (submission_id,))}

    def scored_answers(self, submission_id):
        """{question id: (answer, points)} for answers that have points."""
        return {row["question_id"]: (json.loads(row["answer"]), row["points"]) for row in self.all(
            "SELECT question_id, answer, points FROM submission_answers WHERE submission_id = ? "
            "AND points IS NOT NULL", (submission_id,))}

    def save_answer(self, submission_id, question_id, value):
        """Save (or with None, remove) one answer while the student works."""
        if value is None:
            self.execute("DELETE FROM submission_answers WHERE submission_id = ? AND question_id = ?",
                         (submission_id, question_id))
        else:
            self.execute(
                "INSERT INTO submission_answers (submission_id, question_id, answer) VALUES (?, ?, ?) "
                "ON CONFLICT (submission_id, question_id) DO UPDATE SET answer = excluded.answer",
                (submission_id, question_id, json.dumps(value)),
            )

    def touch(self, submission_id):
        self.execute("UPDATE submissions SET updated_at = datetime('now') WHERE id = ?", (submission_id,))

    def set_check(self, submission_id, question_id, is_correct, points, answered=True):
        """Store the check of one answer. An unanswered question gets an empty answer row."""
        correct = None if is_correct is None else int(is_correct)
        if answered:
            self.execute("UPDATE submission_answers SET is_correct = ?, points = ? "
                         "WHERE submission_id = ? AND question_id = ?",
                         (correct, points, submission_id, question_id))
        else:
            self.execute("INSERT INTO submission_answers (submission_id, question_id, answer, is_correct, points) "
                         "VALUES (?, ?, 'null', ?, ?)", (submission_id, question_id, correct, points))

    def set_teacher_points(self, submission_id, question_id, is_correct, points):
        self.execute(
            "INSERT INTO submission_answers (submission_id, question_id, answer, is_correct, points) "
            "VALUES (?, ?, 'null', ?, ?) "
            "ON CONFLICT (submission_id, question_id) DO UPDATE SET is_correct = excluded.is_correct, "
            "points = excluded.points",
            (submission_id, question_id, is_correct, points),
        )

    def set_feedback(self, submission_id, question_id, feedback):
        """Save the teacher's remark on one answer ('' removes it). An unanswered question gets an
        empty answer row, like set_teacher_points."""
        self.execute(
            "INSERT INTO submission_answers (submission_id, question_id, answer, feedback) "
            "VALUES (?, ?, 'null', ?) "
            "ON CONFLICT (submission_id, question_id) DO UPDATE SET feedback = excluded.feedback",
            (submission_id, question_id, feedback),
        )

    def feedback(self, submission_id):
        """{question id: remark} of the answers that have one."""
        return {row["question_id"]: row["feedback"] for row in self.all(
            "SELECT question_id, feedback FROM submission_answers WHERE submission_id = ? AND feedback != ''",
            (submission_id,))}

    def mark_submitted(self, submission_id, late):
        self.execute("UPDATE submissions SET submitted_at = datetime('now'), updated_at = datetime('now'), late = ? "
                     "WHERE id = ?", (int(late), submission_id))

    def score_rows(self, submission_id, activity_id):
        """Each question's section, points and the points the submission earned."""
        return self.all(
            """
            SELECT q.section_id, q.points AS possible, sa.points AS earned, q.type
            FROM questions q
            LEFT JOIN submission_answers sa ON sa.question_id = q.id AND sa.submission_id = ?
            WHERE q.activity_id = ?
            """,
            (submission_id, activity_id),
        )

    def add_paper(self, assignment_id, student_id, attempt, score, late, note):
        self.execute(
            "INSERT INTO submissions (assignment_id, student_id, attempt, submitted_at, late, paper, paper_score, note) "
            "VALUES (?, ?, ?, datetime('now'), ?, 1, ?, ?)",
            (assignment_id, student_id, attempt, int(late), score, note),
        )

    def update_paper(self, submission_id, score, late, note):
        self.execute("UPDATE submissions SET paper_score = ?, late = ?, note = ? WHERE id = ?",
                     (score, int(late), note, submission_id))

    def delete(self, submission_id):
        self.execute("DELETE FROM submission_answers WHERE submission_id = ?", (submission_id,))
        self.execute("DELETE FROM submissions WHERE id = ?", (submission_id,))

    def count_submitted_by_student(self, student_id):
        """How many assignments the student submitted (however many attempts)."""
        return self.value("SELECT COUNT(DISTINCT assignment_id) FROM submissions "
                          "WHERE student_id = ? AND submitted_at IS NOT NULL", (student_id,))

    def count_submitted_for_teacher(self, teacher_id):
        """Students who submitted the teacher's sheets (each once per assignment)."""
        return self.value(
            "SELECT COUNT(*) FROM (SELECT DISTINCT assignment_id, student_id FROM submissions "
            "WHERE submitted_at IS NOT NULL AND assignment_id IN "
            "(SELECT asg.id FROM assignments asg JOIN activities a ON a.id = asg.activity_id "
            "WHERE a.teacher_id = ?))",
            (teacher_id,),
        )
