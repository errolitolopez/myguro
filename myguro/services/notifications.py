from myguro.domain import notifications as rules
from myguro.errors import say_with
from myguro.repositories import NotificationRepository
from myguro.services.base import Service


class NotificationService(Service):
    """The bell of the logged-in person: their own notes only."""

    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.notes = NotificationRepository(db)

    def mine(self):
        """{unread, notifications: [{id, text, link, created_at, read}]}, newest first. The sentence is made
        now, in the language the person has chosen."""
        rows = self.notes.newest(self.user["id"], rules.LIST_LIMIT)
        return {
            "unread": self.notes.unread_count(self.user["id"]),
            "notifications": [{"id": row["id"], "text": say_with(rules.MESSAGES[row["kind"]], title=row["title"])
                               if row["kind"] in rules.MESSAGES else row["title"],
                               "link": rules.link_for(row["assignment_id"]), "created_at": row["created_at"],
                               "read": row["read_at"] is not None} for row in rows],
        }

    def read(self, note_id):
        self.notes.mark_read(self.user["id"], note_id)
        self.commit()

    def read_all(self):
        self.notes.mark_all_read(self.user["id"])
        self.commit()
