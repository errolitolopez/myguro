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

    def add_message(self, user_id, sender, text, link):
        """Save one message of the chat. link is {label, url} or None."""
        self.execute(
            "INSERT INTO chat_messages (user_id, sender, text, link_label, link_url) VALUES (?, ?, ?, ?, ?)",
            (user_id, sender, text, link["label"] if link else None, link["url"] if link else None),
        )

    def count_questions(self, user_id):
        """How many questions the person asked in the chat they have now."""
        return self.value("SELECT COUNT(*) FROM chat_messages WHERE user_id = ? AND sender = 'teacher'", (user_id,))

    def recent_messages(self, user_id, limit):
        """The newest `limit` messages of this person, oldest first."""
        rows = self.all(
            "SELECT sender, text, link_label, link_url FROM chat_messages WHERE user_id = ? "
            "ORDER BY id DESC LIMIT ?", (user_id, limit))
        return list(reversed(rows))

    def clear_messages(self, user_id):
        self.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
