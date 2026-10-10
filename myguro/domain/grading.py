"""Students' answers: cleaning what they send, and checking it against the answer key.
A question here is a dict like the API's: {id, type, prompt, choices, answer, points}."""

from myguro.domain.sheets import MAX_ANSWER_LENGTH
from myguro.domain.text import clean_description, normalize
from myguro.errors import ValidationError

MAX_SHORT_ANSWER_LENGTH = 5000


def question_for_student(question):
    """A question without its answer key (students must never receive it)."""
    result = {key: question[key] for key in ("id", "type", "prompt", "choices", "points")}
    if question["type"] == "fill_blank":
        result["blanks"] = len(question["answer"])
    elif question["type"] == "matching":
        result["items"] = [match["item"] for match in question["answer"]]
    return result


def clean_student_answer(question, value):
    """One answer from a student: the value to save, or None when it's unanswered."""
    kind = question["type"]
    if value is None:
        return None
    if kind == "multiple_choice":
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < len(question["choices"]):
            return value
    elif kind == "true_false":
        if isinstance(value, bool):
            return value
    elif kind in ("identification", "short_answer"):
        if isinstance(value, str):
            limit = MAX_SHORT_ANSWER_LENGTH if kind == "short_answer" else MAX_ANSWER_LENGTH
            value = clean_description(value) if kind == "short_answer" else " ".join(value.split())
            if len(value) > limit:
                raise ValidationError(f"An answer is too long (at most {limit} characters).")
            return value or None
    elif kind == "fill_blank":
        blanks = len(question["answer"])
        if isinstance(value, list) and len(value) == blanks and all(isinstance(item, str) for item in value):
            value = [" ".join(item.split()) for item in value]
            if any(len(item) > MAX_ANSWER_LENGTH for item in value):
                raise ValidationError(f"An answer is too long (at most {MAX_ANSWER_LENGTH} characters).")
            return value if any(value) else None
    elif kind == "matching":
        items, choices = len(question["answer"]), len(question["choices"])
        if isinstance(value, list) and len(value) == items and all(
                item is None or (isinstance(item, int) and not isinstance(item, bool) and 0 <= item < choices)
                for item in value):
            return value if any(item is not None for item in value) else None
    raise ValidationError("An answer is not valid.")


def check_answer(question, value):
    """(is_correct, points) for a submitted answer. Short answers: (None, None) — the teacher
    scores them. Fill in the blank and matching give part of the points for each right blank / match."""
    kind = question["type"]
    if kind == "short_answer":
        return None, None
    if value is None:
        return False, 0
    if kind in ("multiple_choice", "true_false"):
        correct = value == question["answer"]
        return correct, question["points"] if correct else 0
    if kind == "identification":
        correct = normalize(value) in {normalize(answer) for answer in question["answer"]}
        return correct, question["points"] if correct else 0
    if kind == "matching":
        right = sum(given == match["match"] for given, match in zip(value, question["answer"]))
        items = len(question["answer"])
        return right == items, question["points"] * right // items
    right = sum(
        normalize(given) in {normalize(answer) for answer in accepted}
        for given, accepted in zip(value, question["answer"])
    )
    blanks = len(question["answer"])
    return right == blanks, question["points"] * right // blanks


def teacher_points(question, points):
    """Points the teacher gives a question: 0 to its points, or None to put a short answer back
    to "to check"."""
    if points is None and question["type"] == "short_answer":
        return None
    if isinstance(points, int) and not isinstance(points, bool) and 0 <= points <= question["points"]:
        return points
    raise ValidationError(f"Points must be a whole number from 0 to {question['points']}.")
