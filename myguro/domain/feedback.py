"""Feedback rules: the questions people rate, and what counts as a valid rating (no database, no Flask)."""

from myguro.errors import ValidationError

MIN_RATING = 1
MAX_RATING = 5

# The roles that give feedback, and the filter choices the admin sees. Nobody else rates.
FEEDBACK_ROLES = ("teacher", "student")

# (key, the sentence people rate from 1 to 5). The keys are saved, so never rename one; add new ones.
QUESTIONS = [
    ("easy", "MyGuro is easy to use."),
    ("read", "The text is easy to read on my screen."),
    ("clear", "I know what to do on each page."),
    ("look", "I like how MyGuro looks."),
    ("overall", "Overall, how would you rate MyGuro?"),
]
QUESTION_KEYS = [key for key, _ in QUESTIONS]


def clean_ratings(data):
    """{"easy": 4, ...} -> the same dict, checked. Only known questions, whole numbers 1 to 5, at least one.
    Raises ValidationError with a plain message."""
    if not isinstance(data, dict) or not data:
        raise ValidationError("Choose a rating for at least one question.")
    ratings = {}
    for key, value in data.items():
        if key not in QUESTION_KEYS:
            raise ValidationError("Unknown question.")
        # bool is a kind of int in Python, so True would pass as 1 without this check
        if isinstance(value, bool) or not isinstance(value, int) or not MIN_RATING <= value <= MAX_RATING:
            raise ValidationError(f"A rating is a whole number from {MIN_RATING} to {MAX_RATING}.")
        ratings[key] = value
    return ratings


def summarize(rows, respondents):
    """rows = [(question key, rating, how many gave it)], respondents = people who rated anything.
    Returns the questions in order, each with count, average (one decimal, None if nobody rated)
    and counts = how many gave 1, 2, 3, 4, 5."""
    counts = {key: {rating: 0 for rating in range(MIN_RATING, MAX_RATING + 1)} for key in QUESTION_KEYS}
    for key, rating, how_many in rows:
        if key in counts and rating in counts[key]:
            counts[key][rating] = how_many
    questions = []
    for key, text in QUESTIONS:
        total = sum(counts[key].values())
        points = sum(rating * how_many for rating, how_many in counts[key].items())
        questions.append({
            "key": key,
            "text": text,
            "count": total,
            "average": round(points / total, 1) if total else None,
            "counts": [counts[key][rating] for rating in range(MIN_RATING, MAX_RATING + 1)],
        })
    return {"respondents": respondents, "questions": questions}
