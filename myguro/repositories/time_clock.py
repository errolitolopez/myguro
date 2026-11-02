from myguro.repositories.base import Repository


class TimeClockRepository(Repository):
    def latest_open(self, teacher_id):
        """The teacher's newest time in that has no time out yet, or None."""
        return self.one("SELECT * FROM time_records WHERE teacher_id = ? AND time_out IS NULL "
                        "ORDER BY id DESC LIMIT 1", (teacher_id,))

    def time_in(self, teacher_id, day, time_in):
        return self.execute("INSERT INTO time_records (teacher_id, day, time_in) VALUES (?, ?, ?)",
                            (teacher_id, day, time_in)).lastrowid

    def time_out(self, record_id, time_out):
        self.execute("UPDATE time_records SET time_out = ? WHERE id = ?", (time_out, record_id))

    def for_teacher(self, teacher_id, first_day):
        """The teacher's records from this day on, oldest first."""
        return self.all("SELECT * FROM time_records WHERE teacher_id = ? AND day >= ? ORDER BY id",
                        (teacher_id, first_day))

    def between(self, first_day, last_day, teacher_id=None):
        """Every teacher's records in a range of days (both included), with the teacher's name, by day then name."""
        sql = ("SELECT r.*, u.name AS teacher_name FROM time_records r JOIN users u ON u.id = r.teacher_id "
               "WHERE r.day BETWEEN ? AND ?")
        params = [first_day, last_day]
        if teacher_id is not None:
            sql += " AND r.teacher_id = ?"
            params.append(teacher_id)
        return self.all(sql + " ORDER BY r.day DESC, u.name COLLATE NOCASE, r.id", params)
