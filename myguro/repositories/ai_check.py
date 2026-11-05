from myguro.repositories.base import Repository


class AiCheckRepository(Repository):
    """How many short answers each teacher sent to the AI each day (counts only, never the answers)."""

    def count_today(self, user_id, day):
        return self.value("SELECT COALESCE(SUM(count), 0) FROM ai_check_usage WHERE user_id = ? AND day = ?",
                          (user_id, day))

    def add_one(self, user_id, day):
        self.execute(
            "INSERT INTO ai_check_usage (user_id, day, count) VALUES (?, ?, 1) "
            "ON CONFLICT (user_id, day) DO UPDATE SET count = count + 1",
            (user_id, day),
        )
