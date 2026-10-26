from myguro.repositories.base import Repository


class ChatRepository(Repository):
    """How many chatbot messages each person sent each day (counts only, never the messages)."""

    def count_today(self, user_id, day):
        return self.value("SELECT COALESCE(SUM(count), 0) FROM chat_usage WHERE user_id = ? AND day = ?",
                          (user_id, day))

    def add_one(self, user_id, day):
        self.execute(
            "INSERT INTO chat_usage (user_id, day, count) VALUES (?, ?, 1) "
            "ON CONFLICT (user_id, day) DO UPDATE SET count = count + 1",
            (user_id, day),
        )
