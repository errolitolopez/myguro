from myguro.domain.notifications import MAX_PER_USER
from myguro.repositories.base import Repository


class NotificationRepository(Repository):
    def add_many(self, user_ids, kind, assignment_id, title):
        """The same note for each person, then keep only the newest MAX_PER_USER of each."""
        self.db.executemany(
            "INSERT INTO notifications (user_id, kind, assignment_id, title) VALUES (?, ?, ?, ?)",
            [(user_id, kind, assignment_id, title) for user_id in user_ids])
        self.db.executemany(
            "DELETE FROM notifications WHERE user_id = ? AND id NOT IN "
            "(SELECT id FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT ?)",
            [(user_id, user_id, MAX_PER_USER) for user_id in user_ids])

    def newest(self, user_id, limit):
        """The person's newest notes, newest first."""
        return self.all("SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))

    def unread_count(self, user_id):
        return self.value("SELECT COUNT(*) FROM notifications WHERE user_id = ? AND read_at IS NULL", (user_id,))

    def mark_read(self, user_id, note_id):
        """Mark one note read. Only the owner's own note changes; another person's id does nothing."""
        self.execute("UPDATE notifications SET read_at = datetime('now') WHERE id = ? AND user_id = ? "
                     "AND read_at IS NULL", (note_id, user_id))

    def mark_all_read(self, user_id):
        self.execute("UPDATE notifications SET read_at = datetime('now') WHERE user_id = ? AND read_at IS NULL",
                     (user_id,))
