import json

from myguro.repositories.base import Repository


def question_json(row):
    return {
        "id": row["id"],
        "type": row["type"],
        "prompt": row["prompt"],
        "choices": json.loads(row["choices"]) if row["choices"] else None,
        "answer": json.loads(row["answer"]),
        "points": row["points"],
    }


class ActivityRepository(Repository):
    def get_for_teacher(self, activity_id, teacher_id, include_deleted=False):
        """The teacher's sheet, or None if it doesn't exist, isn't theirs, or was deleted (archived)."""
        return self.one("SELECT * FROM activities WHERE id = ? AND teacher_id = ?"
                        + ("" if include_deleted else " AND deleted_at IS NULL"), (activity_id, teacher_id))

    def list_for_teacher(self, teacher_id, deleted=False):
        """The teacher's sheets (or, with deleted=True, their deleted ones), last edited first,
        with how many sections and questions."""
        return self.all(
            f"""
            SELECT a.*,
                   (SELECT COUNT(*) FROM activity_sections s WHERE s.activity_id = a.id) AS sections,
                   (SELECT COUNT(*) FROM questions q WHERE q.activity_id = a.id) AS questions
            FROM activities a
            WHERE a.teacher_id = ? AND a.deleted_at IS {"NOT NULL" if deleted else "NULL"}
            ORDER BY a.updated_at DESC, a.id DESC
            """,
            (teacher_id,),
        )

    def subjects_for_teacher(self, teacher_id):
        """The subjects the teacher already used on a sheet or a class, once each (capitals ignored,
        the first spelling kept), sorted A to Z."""
        rows = self.all(
            """
            SELECT subject FROM activities WHERE teacher_id = ? AND deleted_at IS NULL AND subject != ''
            UNION ALL
            SELECT subject FROM classes WHERE teacher_id = ? AND subject != ''
            """,
            (teacher_id, teacher_id),
        )
        seen = {}
        for row in rows:
            seen.setdefault(row["subject"].lower(), row["subject"])
        return sorted(seen.values(), key=str.lower)

    def create(self, teacher_id, title, subject):
        return self.execute("INSERT INTO activities (teacher_id, title, subject) VALUES (?, ?, ?)",
                            (teacher_id, title, subject)).lastrowid

    def copy(self, source_id, title):
        """A new draft with the same settings, sections and questions as the source sheet
        (no assignments, no student answers). Returns the new sheet's id."""
        new_id = self.execute(
            "INSERT INTO activities (teacher_id, title, subject, max_attempts) "
            "SELECT teacher_id, ?, subject, max_attempts FROM activities WHERE id = ?",
            (title, source_id)).lastrowid
        section_ids = {}
        for row in self.all("SELECT * FROM activity_sections WHERE activity_id = ? ORDER BY position", (source_id,)):
            section_ids[row["id"]] = self.execute(
                "INSERT INTO activity_sections (activity_id, position, kind, title, description, description_format) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (new_id, row["position"], row["kind"], row["title"], row["description"],
                 row["description_format"])).lastrowid
        for row in self.all("SELECT * FROM questions WHERE activity_id = ? ORDER BY position", (source_id,)):
            self.execute(
                "INSERT INTO questions (activity_id, section_id, position, type, prompt, choices, answer, points) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (new_id, section_ids[row["section_id"]], row["position"], row["type"], row["prompt"],
                 row["choices"], row["answer"], row["points"]))
        return new_id

    def update_title(self, activity_id, title, subject):
        self.execute("UPDATE activities SET title = ?, subject = ?, updated_at = datetime('now') WHERE id = ?",
                     (title, subject, activity_id))

    def set_max_attempts(self, activity_id, max_attempts):
        self.execute("UPDATE activities SET max_attempts = ? WHERE id = ?", (max_attempts, activity_id))

    def archive(self, activity_id):
        """Hide a sheet from the teacher and the students, keeping every assignment and answer."""
        self.execute("UPDATE activities SET deleted_at = datetime('now') WHERE id = ?",
                     (activity_id,))

    def restore(self, activity_id):
        """Bring an archived sheet back (its assignments stay closed: archiving closed them)."""
        self.execute("UPDATE activities SET deleted_at = NULL WHERE id = ?", (activity_id,))

    def delete(self, activity_id):
        self.execute("DELETE FROM questions WHERE activity_id = ?", (activity_id,))
        self.execute("DELETE FROM activity_sections WHERE activity_id = ?", (activity_id,))
        self.execute("DELETE FROM activities WHERE id = ?", (activity_id,))

    def has_sections(self, activity_id):
        return self.one("SELECT 1 FROM activity_sections WHERE activity_id = ?", (activity_id,)) is not None

    def sections(self, activity_id):
        """The sections in order, each with its questions (with the answer key: teacher only)."""
        sections = [dict(row) for row in self.all(
            "SELECT id, kind, title, description, description_format FROM activity_sections "
            "WHERE activity_id = ? ORDER BY position",
            (activity_id,),
        )]
        questions = self.all("SELECT * FROM questions WHERE activity_id = ? ORDER BY position", (activity_id,))
        for section in sections:
            section["questions"] = [question_json(row) for row in questions if row["section_id"] == section["id"]]
        return sections

    def questions(self, activity_id):
        """All questions of the sheet, in order."""
        return [question for section in self.sections(activity_id) for question in section["questions"]]

    def total_points(self, activity_id):
        return self.value("SELECT COALESCE(SUM(points), 0) FROM questions WHERE activity_id = ?", (activity_id,))

    def save_sections(self, activity_id, sections):
        """Save the sections (domain.sheets.Section) and their questions in order. Ones with the
        id of an existing section or question of this sheet are updated (so students' answers keep
        pointing to them), new ones are added, and ones no longer in the list are deleted."""
        old_sections = {row["id"] for row in self.all(
            "SELECT id FROM activity_sections WHERE activity_id = ?", (activity_id,))}
        old_questions = {row["id"] for row in self.all("SELECT id FROM questions WHERE activity_id = ?", (activity_id,))}
        kept_sections, kept_questions = set(), set()

        for position, section in enumerate(sections):
            values = (section.kind, section.title, section.description, section.description_format, position)
            if section.id in old_sections and section.id not in kept_sections:
                section_id = section.id
                self.execute("UPDATE activity_sections SET kind = ?, title = ?, description = ?, description_format = ?, "
                             "position = ? "
                             "WHERE id = ?", (*values, section_id))
            else:
                section_id = self.execute(
                    "INSERT INTO activity_sections (kind, title, description, description_format, position, "
                    "activity_id) VALUES (?, ?, ?, ?, ?, ?)", (*values, activity_id)).lastrowid
            kept_sections.add(section_id)

            for question_position, question in enumerate(section.questions):
                values = (
                    section_id, question_position, question.type, question.prompt,
                    json.dumps(question.choices) if question.choices is not None else None,
                    json.dumps(question.answer), question.points,
                )
                if question.id in old_questions and question.id not in kept_questions:
                    question_id = question.id
                    self.execute("UPDATE questions SET section_id = ?, position = ?, type = ?, prompt = ?, "
                                 "choices = ?, answer = ?, points = ? WHERE id = ?", (*values, question_id))
                else:
                    question_id = self.execute(
                        "INSERT INTO questions (section_id, position, type, prompt, choices, answer, points, "
                        "activity_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (*values, activity_id)).lastrowid
                kept_questions.add(question_id)

        for question_id in old_questions - kept_questions:
            # Answers students saved (not submitted yet) to a deleted question go with it.
            self.execute("DELETE FROM submission_answers WHERE question_id = ?", (question_id,))
            self.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        for section_id in old_sections - kept_sections:
            self.execute("DELETE FROM activity_sections WHERE id = ?", (section_id,))

    def has_submissions(self, activity_id):
        """True once any student submitted this sheet (in any class)."""
        return self.one(
            "SELECT 1 FROM submissions sub JOIN assignments asg ON asg.id = sub.assignment_id "
            "WHERE asg.activity_id = ? AND sub.submitted_at IS NOT NULL LIMIT 1",
            (activity_id,),
        ) is not None

    def count_assigned(self, activity_id):
        """How many classes the sheet is given to (0 = a draft)."""
        return self.value("SELECT COUNT(*) FROM assignments WHERE activity_id = ?", (activity_id,))

    def given_to(self, activity_id, year_id):
        """Where the sheet is given in one school year: a row per class (its name) or per direct
        assignment (class_name NULL), with the assignment's status, oldest first."""
        return self.all(
            """
            SELECT asg.id, asg.status, c.name AS class_name
            FROM assignments asg LEFT JOIN classes c ON c.id = asg.class_id
            WHERE asg.activity_id = ? AND asg.school_year_id = ?
            ORDER BY asg.assigned_at, asg.id
            """,
            (activity_id, year_id),
        )

    def count_all(self):
        return self.value("SELECT COUNT(*) FROM activities WHERE deleted_at IS NULL")

    def count_by_status(self, activity_id):
        """{status: how many of the sheet's assignments have it}, for not_started, open and closed."""
        counts = {"not_started": 0, "open": 0, "closed": 0}
        for row in self.all("SELECT status, COUNT(*) AS n FROM assignments WHERE activity_id = ? GROUP BY status",
                            (activity_id,)):
            counts[row["status"]] = row["n"]
        return counts
