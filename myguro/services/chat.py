from myguro import chat_client
from myguro.config import school_today
from myguro.domain import chat as rules
from myguro.errors import NotFoundError, ValidationError
from myguro.repositories import ChatRepository
from myguro.services.base import Service
from myguro.services.settings import SettingsService


class ChatService(Service):
    """The navigation chatbot: it only turns a question into a link to a page. It reads and changes
    no data, sends no names to the AI service, and keeps no messages."""

    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.usage = ChatRepository(db)

    def ask(self, data):
        """{message} -> {reply, link}. link is {label, url} from the page list, or None. Not found
        when the chatbot is off or the person has none (only teachers do), so it looks like it does not exist."""
        pages = rules.pages_for(self.user["role"])
        if not pages or not SettingsService(self.db, self.user).chatbot_enabled():
            raise NotFoundError("Page not found.")
        message = rules.clean_message(data.get("message"))
        today = school_today().isoformat()
        if self.usage.count_today(self.user["id"], today) >= rules.MAX_MESSAGES_PER_DAY:
            raise ValidationError("You reached today's limit. Try again tomorrow.")
        # Counted before the call, so a failing service cannot be used to send without limit
        self.usage.add_one(self.user["id"], today)
        self.commit()
        key = chat_client.ask_model(message, pages, rules.build_prompt(pages))
        if key is None:
            return {"reply": rules.UNAVAILABLE_REPLY, "link": None}
        return rules.answer_for(pages, key)
