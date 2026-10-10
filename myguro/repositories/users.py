from myguro.domain.accounts import display_name
from myguro.repositories.base import Repository


class UserRepository(Repository):
    def get(self, user_id):
        return self.one("SELECT * FROM users WHERE id = ?", (user_id,))

    def get_active(self, user_id):
        return self.one("SELECT * FROM users WHERE id = ? AND active = 1", (user_id,))

    def by_username(self, username):
        return self.one("SELECT * FROM users WHERE username = ?", (username,))

    def username_taken(self, username):
        return self.by_username(username) is not None

    def get_account(self, user_id):
        """A teacher or student account (never the admin)."""
        return self.one("SELECT * FROM users WHERE id = ? AND role IN ('teacher', 'student')", (user_id,))

    def get_student(self, student_id, active_only=False):
        return self.one("SELECT * FROM users WHERE id = ? AND role = 'student'"
                        + (" AND active = 1" if active_only else ""), (student_id,))

    @staticmethod
    def _matching(role, pattern, grade, name_words=(), section_pattern=None):
        """WHERE for accounts of this role whose name, username or section matches the LIKE
        pattern; grade filters exactly ("" = no grade, None = any). Advanced filters: every
        word of name_words is in the full name, and the section contains section_pattern."""
        where = ("role = ? AND (name LIKE ? ESCAPE '\\' OR username LIKE ? ESCAPE '\\' "
                 "OR section LIKE ? ESCAPE '\\')")
        params = [role, pattern, pattern, pattern]
        if grade is not None:
            where += " AND grade = ?"
            params.append(grade)
        for word in name_words:
            where += " AND name LIKE ? ESCAPE '\\'"
            params.append(word)
        if section_pattern is not None:
            where += " AND section LIKE ? ESCAPE '\\'"
            params.append(section_pattern)
        return where, params

    def count_matching(self, role, pattern, grade=None, name_words=(), section_pattern=None):
        where, params = self._matching(role, pattern, grade, name_words, section_pattern)
        return self.value(f"SELECT COUNT(*) FROM users WHERE {where}", params)

    def search(self, role, pattern, grade=None, name_words=(), section_pattern=None, limit=20, offset=0):
        """One page of the matching accounts: active ones first, then by name (Last, First =
        by last name)."""
        where, params = self._matching(role, pattern, grade, name_words, section_pattern)
        return self.all(f"SELECT * FROM users WHERE {where} ORDER BY active DESC, name COLLATE NOCASE, id "
                        "LIMIT ? OFFSET ?", [*params, limit, offset])

    def matching_ids(self, role, pattern, grade=None, name_words=(), section_pattern=None):
        """Ids of every account matching a search (all pages)."""
        where, params = self._matching(role, pattern, grade, name_words, section_pattern)
        return [row["id"] for row in self.all(f"SELECT id FROM users WHERE {where}", params)]

    def count_students(self, user_ids):
        """How many of these ids are students."""
        marks = ",".join("?" * len(user_ids))
        return self.value(f"SELECT COUNT(*) FROM users WHERE role = 'student' AND id IN ({marks})", list(user_ids))

    def set_grade_many(self, user_ids, grade):
        self.db.executemany("UPDATE users SET grade = ? WHERE id = ?", [(grade, user_id) for user_id in user_ids])

    def set_section_many(self, user_ids, section):
        self.db.executemany("UPDATE users SET section = ? WHERE id = ?", [(section, user_id) for user_id in user_ids])

    def count_classes(self, user):
        """How many classes the teacher teaches or the student is in."""
        if user["role"] == "teacher":
            return self.value("SELECT COUNT(*) FROM classes WHERE teacher_id = ?", (user["id"],))
        return self.value("SELECT COUNT(*) FROM class_students WHERE student_id = ?", (user["id"],))

    def create(self, names, username, password_hash, role, grade="", section="", must_change_password=True,
               active=True):
        """names = (last name, first name, middle initial)."""
        return self.execute(
            "INSERT INTO users (name, last_name, first_name, middle_initial, username, password_hash, role, "
            "must_change_password, grade, section, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (display_name(*names), *names, username, password_hash, role, int(must_change_password), grade, section, int(active)),
        ).lastrowid

    def set_names(self, user_id, names):
        """names = (last name, first name, middle initial); the shown name follows."""
        self.execute("UPDATE users SET name = ?, last_name = ?, first_name = ?, middle_initial = ? WHERE id = ?",
                     (display_name(*names), *names, user_id))

    def set_grade_section(self, user_id, grade, section):
        self.execute("UPDATE users SET grade = ?, section = ? WHERE id = ?", (grade, section, user_id))

    def set_active(self, user_id, active):
        self.execute("UPDATE users SET active = ? WHERE id = ?", (int(active), user_id))

    def set_password(self, user_id, password_hash, must_change_password):
        self.execute("UPDATE users SET password_hash = ?, must_change_password = ? WHERE id = ?",
                     (password_hash, int(must_change_password), user_id))

    def section_spelling(self, section, except_student_id=None):
        """How an existing section with this name is spelled ("Rizal" for "rizal"), or None."""
        row = self.one(
            "SELECT section FROM users WHERE role = 'student' AND section = ? COLLATE NOCASE "
            "AND id IS NOT ? LIMIT 1",
            (section, except_student_id),
        )
        return row["section"] if row else None

    def student_usernames_by_identity(self):
        """{(last name, first name, middle initial, grade, section) in lowercase: username} of every
        student, to spot a student who already exists."""
        return {
            tuple(row[key].casefold() for key in ("last_name", "first_name", "middle_initial", "grade", "section")):
                row["username"]
            for row in self.all("SELECT last_name, first_name, middle_initial, grade, section, username "
                                "FROM users WHERE role = 'student' ORDER BY id DESC")
        }

    def count(self, role, active_only=False):
        return self.value("SELECT COUNT(*) FROM users WHERE role = ?" + (" AND active = 1" if active_only else ""),
                          (role,))
