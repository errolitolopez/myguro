from myguro.repositories.base import Repository


class AttendanceRepository(Repository):
    def for_day(self, class_id, day):
        """{student id: status} of the marks saved for that class on that day."""
        return {row["student_id"]: row["status"] for row in self.all(
            "SELECT student_id, status FROM attendance WHERE class_id = ? AND day = ?", (class_id, day))}

    def totals(self, class_id):
        """{student id: {status: days}} over every day recorded for the class."""
        totals = {}
        for row in self.all(
                "SELECT student_id, status, COUNT(*) AS days FROM attendance WHERE class_id = ? "
                "GROUP BY student_id, status", (class_id,)):
            totals.setdefault(row["student_id"], {})[row["status"]] = row["days"]
        return totals

    def all_marks(self, class_id):
        """Every mark of the class: rows of (student_id, day, status), oldest day first."""
        return self.all("SELECT student_id, day, status FROM attendance WHERE class_id = ? ORDER BY day",
                        (class_id,))

    def recorded_days(self, class_id):
        """The days (newest first) the class has any mark."""
        return [row["day"] for row in self.all(
            "SELECT DISTINCT day FROM attendance WHERE class_id = ? ORDER BY day DESC", (class_id,))]

    def set(self, class_id, student_id, day, status):
        """Save one mark, replacing the old one for that day; None removes it."""
        if status is None:
            self.execute("DELETE FROM attendance WHERE class_id = ? AND student_id = ? AND day = ?",
                         (class_id, student_id, day))
        else:
            self.execute(
                "INSERT INTO attendance (class_id, student_id, day, status) VALUES (?, ?, ?, ?) "
                "ON CONFLICT (class_id, student_id, day) DO UPDATE SET status = excluded.status",
                (class_id, student_id, day, status))
