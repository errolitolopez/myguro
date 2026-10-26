from myguro import chat_client
from myguro.config import school_today
from myguro.domain import chat as rules
from myguro.errors import NotFoundError, ValidationError
from myguro.repositories import ChatRepository
from myguro.services.base import Service
from myguro.services.settings import SettingsService


class ChatService(Service):
    """The navigation chatbot: it only turns a question into a link to a page. It reads and changes
    no data and sends no names to the AI service. It keeps each teacher's own chat, for that teacher only."""

    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.usage = ChatRepository(db)

    def require_chat(self):
        """The pages this person may be sent to. Not found when the chatbot is off or the person has none
        (only teachers do), so it looks like it does not exist."""
        pages = rules.pages_for(self.user["role"])
        if not pages or not SettingsService(self.db, self.user).chatbot_enabled():
            raise NotFoundError("Page not found.")
        return pages

    def history(self):
        """{messages: [{sender, text, link}]}: this teacher's newest messages, oldest first."""
        self.require_chat()
        rows = self.usage.recent_messages(self.user["id"], rules.MAX_SHOWN_MESSAGES)
        return {"messages": [{"sender": row["sender"], "text": row["text"],
                              "link": {"label": row["link_label"], "url": row["link_url"]} if row["link_url"] else None}
                             for row in rows]}

    def clear_history(self):
        """Delete this teacher's saved messages."""
        self.require_chat()
        self.usage.clear_messages(self.user["id"])
        self.commit()
        return {"messages": []}

    def ask(self, data):
        """{message} -> {reply, link}. link is {label, url} from the page list, or None. Not found
        when the chatbot is off or the person has none (only teachers do), so it looks like it does not exist."""
        pages = self.require_chat()
        message = rules.clean_message(data.get("message"))
        today = school_today().isoformat()
        if self.usage.count_today(self.user["id"], today) >= rules.MAX_MESSAGES_PER_DAY:
            raise ValidationError("You reached today's limit. Try again tomorrow.")
        # Counted before the call, so a failing service cannot be used to send without limit
        self.usage.add_one(self.user["id"], today)
        self.commit()
        key = chat_client.ask_model(message, pages, rules.build_prompt(pages))
        answer = {"reply": rules.UNAVAILABLE_REPLY, "link": None} if key is None else rules.answer_for(pages, key)
        # The history is only for the teacher to read again. It is never sent to the AI service.
        self.usage.add_message(self.user["id"], "teacher", message, None)
        self.usage.add_message(self.user["id"], "bot", answer["reply"], answer["link"])
        self.usage.trim_messages(self.user["id"], rules.MAX_SAVED_MESSAGES)
        self.commit()
        return answer
