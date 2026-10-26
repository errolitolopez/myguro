from myguro.repositories.base import Repository

# What students, results and exports call the group of students given a sheet with no class.
DIRECT_CLASS_NAME = "Individual students"

# A student sees an assignment when they are in its class and it is for everyone, or they are one
# of its chosen students. A direct assignment (class_id NULL) is seen only by its chosen students.
# A student the teacher excluded (for example absent) does not see it until added back.
# An assignment the teacher has not started, or of a deleted sheet, is seen by nobody. A closed one is
# seen (to read the questions again) but can't be answered.
VISIBLE_TO_STUDENT = """
    (
        (
            (asg.class_id IN (SELECT class_id FROM class_students WHERE student_id = :student)
             AND (asg.everyone = 1 OR EXISTS (SELECT 1 FROM assignment_students s
                                              WHERE s.assignment_id = asg.id AND s.student_id = :student)))
            OR (asg.class_id IS NULL AND EXISTS (SELECT 1 FROM assignment_students s
                                                 WHERE s.assignment_id = asg.id AND s.student_id = :student))
        )
        AND NOT EXISTS (SELECT 1 FROM assignment_exclusions x
                        WHERE x.assignment_id = asg.id AND x.student_id = :student)
        AND asg.status IN ('open', 'closed')
        AND a.deleted_at IS NULL
    )
"""


class AssignmentRepository(Repository):
    def get(self, activity_id, class_id):
        return self.one("SELECT * FROM assignments WHERE activity_id = ? AND class_id = ?", (activity_id, class_id))

    def get_direct(self, activity_id, year_id):
        """The sheet's direct assignment of that school year (given to students with no class), or None."""
        return self.one("SELECT * FROM assignments WHERE activity_id = ? AND class_id IS NULL "
                        "AND school_year_id = ?", (activity_id, year_id))

    def ids_by_class(self, activity_id, year_id):
        """{class id: assignment id} of a sheet in one school year (the direct assignment has no
        class and is left out)."""
        return {row["class_id"]: row["id"] for row in self.all(
            "SELECT id, class_id FROM assignments WHERE activity_id = ? AND class_id IS NOT NULL "
            "AND school_year_id = ?", (activity_id, year_id))}

    def chosen_students(self, assignment_id):
        return [row["student_id"] for row in self.all(
            "SELECT student_id FROM assignment_students WHERE assignment_id = ?", (assignment_id,))]

    def create(self, activity_id, class_id, everyone, due_date, year_id):
        return self.execute(
            "INSERT INTO assignments (everyone, due_date, activity_id, class_id, school_year_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (int(everyone), due_date, activity_id, class_id, year_id),
        ).lastrowid

    def update(self, assignment_id, everyone, due_date):
        self.execute("UPDATE assignments SET everyone = ?, due_date = ? WHERE id = ?",
                     (int(everyone), due_date, assignment_id))

    def set_status(self, assignment_id, status):
        self.execute("UPDATE assignments SET status = ? WHERE id = ?", (status, assignment_id))

    def reset_all(self, activity_id):
        """Put every assignment of a sheet back to not started (when the sheet is deleted and archived)."""
        self.execute("UPDATE assignments SET status = 'not_started' WHERE activity_id = ?", (activity_id,))

    def count_for_teacher(self, teacher_id, year_id, status):
        """How many of the teacher's assignments in one school year have this status."""
        return self.value(
            "SELECT COUNT(*) FROM assignments asg JOIN activities a ON a.id = asg.activity_id "
            "WHERE a.teacher_id = ? AND asg.school_year_id = ? AND asg.status = ? AND a.deleted_at IS NULL",
            (teacher_id, year_id, status))

    def set_scores_released(self, assignment_id, released):
        self.execute("UPDATE assignments SET scores_released = ? WHERE id = ?", (int(released), assignment_id))

    def set_chosen_students(self, assignment_id, student_ids):
        self.execute("DELETE FROM assignment_students WHERE assignment_id = ?", (assignment_id,))
        self.db.executemany("INSERT INTO assignment_students (assignment_id, student_id) VALUES (?, ?)",
                            [(assignment_id, student_id) for student_id in student_ids])

    def excluded_ids(self, assignment_id):
        """Ids of the students the teacher excluded from this assignment."""
        return [row["student_id"] for row in self.all(
            "SELECT student_id FROM assignment_exclusions WHERE assignment_id = ?", (assignment_id,))]

    def set_excluded(self, assignment_id, student_id, excluded):
        """Exclude a student from the assignment, or add them back. Doing it twice is fine."""
        if excluded:
            self.execute("INSERT OR IGNORE INTO assignment_exclusions (assignment_id, student_id) VALUES (?, ?)",
                         (assignment_id, student_id))
        else:
            self.execute("DELETE FROM assignment_exclusions WHERE assignment_id = ? AND student_id = ?",
                         (assignment_id, student_id))

    def has_submitted_work(self, assignment_id):
        return self.one("SELECT 1 FROM submissions WHERE assignment_id = ? AND submitted_at IS NOT NULL",
                        (assignment_id,)) is not None

    def delete(self, assignment_id):
        """Delete the assignment with any unsubmitted work saved on it."""
        self.execute("DELETE FROM submission_answers WHERE submission_id IN "
                     "(SELECT id FROM submissions WHERE assignment_id = ?)", (assignment_id,))
        self.execute("DELETE FROM submissions WHERE assignment_id = ?", (assignment_id,))
        self.execute("DELETE FROM assignment_students WHERE assignment_id = ?", (assignment_id,))
        self.execute("DELETE FROM assignment_exclusions WHERE assignment_id = ?", (assignment_id,))
        self.execute("DELETE FROM assignments WHERE id = ?", (assignment_id,))

    def for_class(self, class_id):
        """The sheets given to a class, newest first, with how many students were chosen."""
        return self.all(
            """
            SELECT asg.*, a.title, a.subject,
                   (SELECT COUNT(*) FROM assignment_students s WHERE s.assignment_id = asg.id) AS selected
            FROM assignments asg JOIN activities a ON a.id = asg.activity_id
            WHERE asg.class_id = ? AND a.deleted_at IS NULL
            ORDER BY asg.assigned_at DESC, asg.id DESC
            """,
            (class_id,),
        )

    def ids_for_teacher(self, teacher_id, year_id):
        """The ids of the teacher's assignments in one school year (not of deleted sheets), newest first."""
        rows = self.all(
            """
            SELECT asg.id
            FROM assignments asg JOIN activities a ON a.id = asg.activity_id
            WHERE a.teacher_id = ? AND asg.school_year_id = ? AND a.deleted_at IS NULL
            ORDER BY asg.assigned_at DESC, asg.id DESC
            """,
            (teacher_id, year_id),
        )
        return [row["id"] for row in rows]

    def get_for_teacher(self, assignment_id, teacher_id):
        """An assignment of the teacher's sheet, with the sheet and class details."""
        return self.one(
            f"""
            SELECT asg.*, a.title, a.subject, a.max_attempts,
                   COALESCE(c.name, '{DIRECT_CLASS_NAME}') AS class_name, COALESCE(c.subject, '') AS class_subject
            FROM assignments asg
            JOIN activities a ON a.id = asg.activity_id
            LEFT JOIN classes c ON c.id = asg.class_id
            WHERE asg.id = ? AND a.teacher_id = ? AND a.deleted_at IS NULL
            """,
            (assignment_id, teacher_id),
        )

    def get_for_student(self, assignment_id, student_id):
        """The assignment with its sheet, class and teacher, if the student was given it."""
        return self.one(
            f"""
            SELECT asg.*, a.title, a.subject, a.teacher_id, a.max_attempts,
                   COALESCE(c.name, '{DIRECT_CLASS_NAME}') AS class_name, COALESCE(c.subject, '') AS class_subject,
                   t.name AS teacher
            FROM assignments asg
            JOIN activities a ON a.id = asg.activity_id
            LEFT JOIN classes c ON c.id = asg.class_id
            JOIN users t ON t.id = a.teacher_id
            WHERE asg.id = :assignment AND {VISIBLE_TO_STUDENT}
            """,
            {"assignment": assignment_id, "student": student_id},
        )

    def list_for_student(self, student_id, year_id):
        """Everything given to a student in one school year, soonest due first, with their latest attempt (sub) and
        latest submitted attempt (last: the one that counts)."""
        return self.all(
            f"""
            SELECT asg.id, asg.due_date, asg.scores_released, asg.status AS assignment_status, a.title, a.subject, a.id AS activity_id, a.max_attempts,
                   COALESCE(c.name, '{DIRECT_CLASS_NAME}') AS class_name, COALESCE(c.subject, '') AS class_subject,
                   t.name AS teacher, t.id AS teacher_id,
                   sub.id AS submission_id, sub.submitted_at, sub.attempt, sub.paper,
                   last.id AS last_id, last.late AS last_late, last.paper AS last_paper,
                   (SELECT COUNT(*) FROM questions q WHERE q.activity_id = a.id) AS question_count,
                   (SELECT COUNT(*) FROM submission_answers sa WHERE sa.submission_id = sub.id) AS answered_count
            FROM assignments asg
            JOIN activities a ON a.id = asg.activity_id
            LEFT JOIN classes c ON c.id = asg.class_id
            JOIN users t ON t.id = a.teacher_id
            LEFT JOIN submissions sub ON sub.id = (
                SELECT id FROM submissions WHERE assignment_id = asg.id AND student_id = :student
                ORDER BY attempt DESC LIMIT 1)
            LEFT JOIN submissions last ON last.id = (
                SELECT id FROM submissions WHERE assignment_id = asg.id AND student_id = :student
                AND submitted_at IS NOT NULL ORDER BY attempt DESC LIMIT 1)
            WHERE {VISIBLE_TO_STUDENT} AND asg.school_year_id = :year
            ORDER BY asg.due_date IS NULL, asg.due_date, asg.assigned_at DESC
            """,
            {"student": student_id, "year": year_id},
        )

    def students(self, assignment):
        """The students who got this assignment, plus anyone who already worked on it
        (e.g. removed from the class later), in name order."""
        if assignment["class_id"] is None:
            given = "SELECT student_id FROM assignment_students WHERE assignment_id = :assignment"
        elif assignment["everyone"]:
            given = "SELECT student_id FROM class_students WHERE class_id = :class"
        else:
            given = ("SELECT student_id FROM assignment_students WHERE assignment_id = :assignment "
                     "AND student_id IN (SELECT student_id FROM class_students WHERE class_id = :class)")
        return self.all(
            f"""
            SELECT * FROM users WHERE role = 'student' AND (
                id IN ({given}) OR id IN (SELECT student_id FROM submissions WHERE assignment_id = :assignment))
            ORDER BY name COLLATE NOCASE
            """,
            {"class": assignment["class_id"], "assignment": assignment["id"]},
        )
