"""Navigation chatbot rules: the pages it may open, its limits and fixed replies (no database, no Flask)."""

from myguro.domain.chat_guides import TEACHER_GUIDES
from myguro.errors import ValidationError

MAX_MESSAGE_LENGTH = 300
MAX_MESSAGES_PER_DAY = 50
MAX_QUESTIONS_PER_CHAT = 5  # then the teacher deletes the chat and starts a new one
# The earlier messages of the chat go to the model too, so it can follow "and how do I add students to it?"
MAX_CONTEXT_MESSAGES = 2 * (MAX_QUESTIONS_PER_CHAT - 1)
MAX_SHOWN_MESSAGES = 50  # the newest ones the bubble loads

NO_PAGE_KEY = "none"  # what the model picks when no page fits the question
NO_PAGE_REPLY = "I can only help you find pages."
CHAT_FULL_MESSAGE = f"This chat is full ({MAX_QUESTIONS_PER_CHAT} questions). Delete it and start a new chat."
UNAVAILABLE_REPLY = "The chatbot is not available right now."

# The pages a teacher can be sent to: key -> (title, path, what is there, extra note or ""). Only pages
# that need no id. Keys go to the model and into saved chats, so never rename one.
TEACHER_PAGES = {
    "dashboard": ("Dashboard", "/dashboard",
                  "The home page: what needs attention, scores to check, and the school year.", ""),
    "activities": ("Activities", "/activities",
                   "The teacher's activity sheets: write, import, print, export, give to classes, open or close them, and see results.", ""),
    "classes": ("Classes", "/classes",
                "The teacher's classes: add students, take attendance, open a class gradebook.",
                "Open a class there to find its gradebook and attendance."),
    "schedule": ("My schedule", "/my-schedule",
                 "The teacher's weekly timetable, once the admin published it.", ""),
    "feedback": ("Feedback", "/feedback", "Rate MyGuro and send feedback.", ""),
    "display": ("Display", "/display", "Theme (light or dark), text size and reading settings.", ""),
    "password": ("Change password", "/change-password", "Change the account password.", ""),
    "recovery-code": ("Recovery code", "/recovery-code",
                      "Make a recovery code to reset a forgotten password without the admin.", ""),
}

# Everything the model can pick from. A page: reply "Here is X." with a button. A how-to guide: the
# written steps with a button to the page where they start. Both come from the lists above, so the
# model only ever names a key and never writes text or an address.
TEACHER_TOPICS = {
    **{key: {"title": title, "path": path, "about": about, "steps": [], "note": note, "button": f"Open {title}"}
       for key, (title, path, about, note) in TEACHER_PAGES.items()},
    **{key: {"title": f"How to: {title}", "path": TEACHER_PAGES[page][1], "about": about, "steps": steps, "note": "",
             "button": f"Open {TEACHER_PAGES[page][0]}"}
       for key, (title, about, page, steps) in TEACHER_GUIDES.items()},
}

PROMPT = """You help a teacher use MyGuro, a learning activity sheet web app.
Always call the help tool with the key that best fits what the teacher asked for. Earlier messages are there so you can understand a follow-up question such as "and then?".
Pick a "how-" key when they ask how to do something. Pick a page key when they ask where something is.
If the question is not about using MyGuro, pick "none".
Never answer in text. These are the keys:
"""


def clean_message(message):
    """The question without extra spaces. Raises ValidationError if it is empty or too long."""
    text = " ".join(message.split()) if isinstance(message, str) else ""
    if not text:
        raise ValidationError("Write what you are looking for.")
    if len(text) > MAX_MESSAGE_LENGTH:
        raise ValidationError("Write a shorter question.")
    return text


def pages_for(role):
    """The topics (pages and how-to guides) this role may ask about (empty for a role with no chatbot)."""
    return TEACHER_TOPICS if role == "teacher" else {}


def build_prompt(topics):
    """The instructions for the model, with one line per topic."""
    return PROMPT + "\n".join(f'- "{key}": {topic["title"]}. {topic["about"]}' for key, topic in topics.items())


def answer_for(topics, key):
    """{reply, link} for the key the model picked. An unknown key (or "none") gets the fixed reply and
    no link, so the model can never name an address or write steps of its own."""
    topic = topics.get(key) if isinstance(key, str) else None
    if topic is None:
        return {"reply": NO_PAGE_REPLY, "link": None}
    if topic["steps"]:
        steps = "\n".join(f"{number}. {step}" for number, step in enumerate(topic["steps"], 1))
        reply = f"{topic['title']}\n{steps}"
    else:
        reply = f"Here is {topic['title']}. {topic['note']}".strip()
    return {"reply": reply, "link": {"label": topic["button"], "url": topic["path"]}}


def context_for(rows):
    """[(sender, text)] for the model from the teacher's latest saved messages (oldest first). A reply
    is cut to its first line (the page or guide title), so the steps are not sent again. It must start
    with the teacher's message."""
    messages = [(row["sender"], row["text"].split("\n")[0]) for row in rows]
    while messages and messages[0][0] != "teacher":
        messages.pop(0)
    return messages
