"""Navigation chatbot rules: the pages it may open, its limits and fixed replies (no database, no Flask)."""

from myguro.errors import ValidationError

MAX_MESSAGE_LENGTH = 300
MAX_MESSAGES_PER_DAY = 50

NO_PAGE_KEY = "none"  # what the model picks when no page fits the question
NO_PAGE_REPLY = "I can only help you find pages."
UNAVAILABLE_REPLY = "The chatbot is not available right now."

# The pages a teacher can be sent to: key -> (title, path, what is there, extra hint or ""). Only pages
# that need no id. The model only ever picks a key; the reply and the link come from this list, so it
# can never send anyone to an address that is not here. Keys go to the model, so never rename one.
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

PROMPT = """You help a teacher find a page in MyGuro, a learning activity sheet web app.
Always call the navigate tool. Pick the page that best fits what the teacher asked for.
If the question is not about finding a page in MyGuro, pick "none".
Never answer in text. These are the pages:
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
    """The pages this role may be sent to (empty for a role that has no chatbot)."""
    return TEACHER_PAGES if role == "teacher" else {}


def build_prompt(pages):
    """The instructions for the model, with one line per page."""
    return PROMPT + "\n".join(f'- "{key}": {title}. {about}' for key, (title, _, about, _) in pages.items())


def answer_for(pages, key):
    """{reply, link} for the page key the model picked. An unknown key (or "none") gets the fixed
    reply and no link, so the model can never name an address of its own."""
    page = pages.get(key) if isinstance(key, str) else None
    if page is None:
        return {"reply": NO_PAGE_REPLY, "link": None}
    title, path, _, hint = page
    return {"reply": f"Here is {title}. {hint}".strip(), "link": {"label": f"Open {title}", "url": path}}
