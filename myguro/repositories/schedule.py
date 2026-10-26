from myguro.repositories.base import Repository


class ScheduleRepository(Repository):
    """Everything of the schedule generator: sections, teachers, assignments and the built timetable."""

    # --- sections
    def sections(self):
        return self.all("SELECT * FROM schedule_sections ORDER BY name COLLATE NOCASE")

    def section(self, section_id):
        return self.one("SELECT * FROM schedule_sections WHERE id = ?", (section_id,))

    def section_by_name(self, name):
        return self.one("SELECT * FROM schedule_sections WHERE name = ? COLLATE NOCASE", (name,))

    def add_section(self, name, grade, room, adviser):
        return self.execute("INSERT INTO schedule_sections (name, grade, room, adviser) VALUES (?, ?, ?, ?)",
                            (name, grade, room, adviser)).lastrowid

    def update_section(self, section_id, name, grade, room, adviser):
        self.execute("UPDATE schedule_sections SET name = ?, grade = ?, room = ?, adviser = ? WHERE id = ?",
                     (name, grade, room, adviser, section_id))

    def delete_section(self, section_id):
        self.execute("DELETE FROM schedule_slots WHERE section_id = ?", (section_id,))
        self.execute("DELETE FROM schedule_assignments WHERE section_id = ?", (section_id,))
        self.execute("DELETE FROM schedule_sections WHERE id = ?", (section_id,))

    # --- teachers
    def teachers(self):
        return self.all("SELECT * FROM schedule_teachers ORDER BY name COLLATE NOCASE")

    def teacher(self, teacher_id):
        return self.one("SELECT * FROM schedule_teachers WHERE id = ?", (teacher_id,))

    def teacher_for_user(self, user_id):
        return self.one("SELECT * FROM schedule_teachers WHERE user_id = ?", (user_id,))

    def blocked(self):
        """{teacher id: sorted [(day, period)]} for every teacher who has any."""
        blocked = {}
        for row in self.all("SELECT * FROM schedule_blocked ORDER BY day, period"):
            blocked.setdefault(row["teacher_id"], []).append((row["day"], row["period"]))
        return blocked

    def add_teacher(self, name, user_id, max_gap, max_per_day):
        return self.execute("INSERT INTO schedule_teachers (name, user_id, max_gap, max_per_day) VALUES (?, ?, ?, ?)",
                            (name, user_id, max_gap, max_per_day)).lastrowid

    def update_teacher(self, teacher_id, name, user_id, max_gap, max_per_day):
        self.execute("UPDATE schedule_teachers SET name = ?, user_id = ?, max_gap = ?, max_per_day = ? WHERE id = ?",
                     (name, user_id, max_gap, max_per_day, teacher_id))

    def set_blocked(self, teacher_id, blocked):
        self.execute("DELETE FROM schedule_blocked WHERE teacher_id = ?", (teacher_id,))
        self.db.executemany("INSERT INTO schedule_blocked (teacher_id, day, period) VALUES (?, ?, ?)",
                            [(teacher_id, day, period) for day, period in blocked])

    def teacher_in_use(self, teacher_id):
        return self.value("SELECT COUNT(*) FROM schedule_assignments WHERE teacher_id = ?", (teacher_id,)) > 0

    def delete_teacher(self, teacher_id):
        self.execute("DELETE FROM schedule_blocked WHERE teacher_id = ?", (teacher_id,))
        self.execute("DELETE FROM schedule_teachers WHERE id = ?", (teacher_id,))

    def teacher_accounts(self):
        """The MyGuro teacher accounts that can be linked to a schedule teacher."""
        return self.all("SELECT id, name, username FROM users WHERE role = 'teacher' AND active = 1 "
                        "ORDER BY name COLLATE NOCASE")

    def user_taken(self, user_id, except_teacher_id=None):
        return self.one("SELECT 1 FROM schedule_teachers WHERE user_id = ? AND id IS NOT ?",
                        (user_id, except_teacher_id)) is not None

    # --- assignments
    def assignments(self):
        return self.all("SELECT * FROM schedule_assignments ORDER BY section_id, id")

    def assignment(self, assignment_id):
        return self.one("SELECT * FROM schedule_assignments WHERE id = ?", (assignment_id,))

    def set_assignment(self, section_id, subject, teacher_id, per_week):
        """Add the subject to the section, or change its teacher and periods. Returns the id."""
        self.execute(
            "INSERT INTO schedule_assignments (section_id, subject, teacher_id, per_week) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (section_id, subject) DO UPDATE SET teacher_id = excluded.teacher_id, "
            "per_week = excluded.per_week", (section_id, subject, teacher_id, per_week))
        return self.value("SELECT id FROM schedule_assignments WHERE section_id = ? AND subject = ?",
                          (section_id, subject))

    def delete_assignment(self, assignment_id):
        self.execute("DELETE FROM schedule_assignments WHERE id = ?", (assignment_id,))

    # --- the built timetable
    def slots(self):
        return self.all("SELECT * FROM schedule_slots ORDER BY section_id, day, period")

    def delete_slots_of(self, section_id, subject):
        """Take one subject of one section out of the built timetable."""
        self.execute("DELETE FROM schedule_slots WHERE section_id = ? AND subject = ?", (section_id, subject))

    def replace_slots(self, slots):
        """Throw the old timetable away and keep these (section, day, period, subject, teacher)."""
        self.execute("DELETE FROM schedule_slots")
        self.db.executemany("INSERT INTO schedule_slots (section_id, day, period, subject, teacher_id) "
                            "VALUES (?, ?, ?, ?, ?)", slots)
