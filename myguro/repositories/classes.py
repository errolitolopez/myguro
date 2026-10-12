from myguro.repositories.base import Repository


class ClassRepository(Repository):
    def get_for_teacher(self, class_id, teacher_id):
        """The class, or None if it doesn't exist or belongs to another teacher."""
        return self.one("SELECT * FROM classes WHERE id = ? AND teacher_id = ?", (class_id, teacher_id))

    def list_for_teacher(self, teacher_id):
        """The teacher's classes with how many students and activities each has."""
        return self.all(
            """
            SELECT c.id, c.name, c.subject,
                   (SELECT COUNT(*) FROM class_students cs WHERE cs.class_id = c.id) AS students,
                   (SELECT COUNT(*) FROM assignments asg WHERE asg.class_id = c.id) AS activities
            FROM classes c
            WHERE c.teacher_id = ?
            ORDER BY c.name COLLATE NOCASE, c.subject COLLATE NOCASE
            """,
            (teacher_id,),
        )

    def find_same(self, teacher_id, name, subject):
        """The teacher's class with this name and subject (any capitals), or None."""
        return self.one(
            "SELECT id FROM classes WHERE teacher_id = ? AND name = ? COLLATE NOCASE AND subject = ? COLLATE NOCASE",
            (teacher_id, name, subject),
        )

    def create(self, teacher_id, name, subject):
        return self.execute("INSERT INTO classes (teacher_id, name, subject) VALUES (?, ?, ?)",
                            (teacher_id, name, subject)).lastrowid

    def update(self, class_id, name, subject):
        self.execute("UPDATE classes SET name = ?, subject = ? WHERE id = ?", (name, subject, class_id))

    def students(self, class_id):
        return self.all(
            "SELECT u.* FROM class_students cs JOIN users u ON u.id = cs.student_id "
            "WHERE cs.class_id = ? ORDER BY u.name COLLATE NOCASE",
            (class_id,),
        )

    def has_student(self, class_id, student_id):
        return self.one("SELECT 1 FROM class_students WHERE class_id = ? AND student_id = ?",
                        (class_id, student_id)) is not None

    def add_student(self, class_id, student_id):
        self.execute("INSERT INTO class_students (class_id, student_id) VALUES (?, ?)", (class_id, student_id))

    def remove_student(self, class_id, student_id):
        """Take the student out of the class, and off its activities given to selected students."""
        self.execute("DELETE FROM class_students WHERE class_id = ? AND student_id = ?", (class_id, student_id))
        self.execute(
            "DELETE FROM assignment_students WHERE student_id = ? "
            "AND assignment_id IN (SELECT id FROM assignments WHERE class_id = ?)",
            (student_id, class_id),
        )

    def search_students(self, class_id, pattern, grade=None, section=None, limit=200):
        """Active students whose name, username or section matches the LIKE pattern, with in_class.
        grade / section filter exactly (section "" = students with no section)."""
        sql = """
            SELECT u.*,
                   EXISTS (SELECT 1 FROM class_students cs
                           WHERE cs.class_id = ? AND cs.student_id = u.id) AS in_class
            FROM users u
            WHERE u.role = 'student' AND u.active = 1
              AND (u.name LIKE ? ESCAPE '\\' OR u.username LIKE ? ESCAPE '\\' OR u.section LIKE ? ESCAPE '\\')
        """
        params = [class_id, pattern, pattern, pattern]
        if grade:
            sql += " AND u.grade = ?"
            params.append(grade)
        if section is not None:
            sql += " AND u.section = ? COLLATE NOCASE"
            params.append(section)
        sql += f" ORDER BY u.name COLLATE NOCASE LIMIT {int(limit)}"
        return self.all(sql, params)

    def grade_sections(self):
        """The grade + section pairs active students have, for filter dropdowns."""
        return self.all(
            "SELECT DISTINCT grade, section FROM users WHERE role = 'student' AND active = 1 "
            "AND (grade != '' OR section != '') ORDER BY grade, section COLLATE NOCASE"
        )

    def classes_of_student(self, student_id):
        """The student's classes with teacher and how many activities the student got in each."""
        return self.all(
            """
            SELECT c.id, c.name, c.subject, t.name AS teacher,
                   (SELECT COUNT(*) FROM assignments asg
                    WHERE asg.class_id = c.id AND (asg.everyone = 1 OR EXISTS (
                        SELECT 1 FROM assignment_students s
                        WHERE s.assignment_id = asg.id AND s.student_id = cs.student_id))
                      AND NOT EXISTS (SELECT 1 FROM assignment_exclusions x
                                      WHERE x.assignment_id = asg.id AND x.student_id = cs.student_id)
                      AND EXISTS (SELECT 1 FROM activities a
                                  WHERE a.id = asg.activity_id AND a.published = 1)) AS activities
            FROM class_students cs
            JOIN classes c ON c.id = cs.class_id
            JOIN users t ON t.id = c.teacher_id
            WHERE cs.student_id = ?
            ORDER BY c.name COLLATE NOCASE, c.subject COLLATE NOCASE
            """,
            (student_id,),
        )

    def count_all(self):
        return self.value("SELECT COUNT(*) FROM classes")

    def count_students_of_teacher(self, teacher_id):
        return self.value(
            "SELECT COUNT(DISTINCT student_id) FROM class_students "
            "WHERE class_id IN (SELECT id FROM classes WHERE teacher_id = ?)",
            (teacher_id,),
        )
