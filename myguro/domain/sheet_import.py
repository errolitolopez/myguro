"""Turning the rows of an imported Excel file into sheet sections and questions.

Each row is a "text" section, an "activity" section, or a "question" of the activity above it.
The answer cell is read by question type (see sheets.py for the stored key):
  multiple_choice  the letter of the correct choice (B)
  true_false       True / False
  identification   accepted answers split by /
  fill_blank       one answer per blank split by ; (spellings of one blank split by /)
  short_answer     an optional guide for checking
"""

from myguro.domain.sheets import MAX_SECTIONS, QUESTION_TYPES, clean_question, clean_section
from myguro.errors import ValidationError

ROW_KINDS = {"text": "text", "activity": "activity", "question": "question"}
DEFAULT_POINTS = {"short_answer": 5}
QUESTION_TYPE_NAMES = {
    "mc": "multiple_choice", "multiple choice": "multiple_choice",
    "true or false": "true_false", "true/false": "true_false", "tf": "true_false",
    "fill in the blank": "fill_blank", "fill in the blanks": "fill_blank", "fill blank": "fill_blank",
    "short answer": "short_answer", "essay": "short_answer",
}
TRUE_FALSE = {"true": True, "t": True, "false": False, "f": False}
CHOICE_LETTERS = "abcdef"


def sections_from_rows(rows):
    """(sections, errors) from [(row number, record)] (see imports.read_sheet_rows).
    sections are domain.sheets.Section objects; errors are [{row, message}]. With any error,
    sections is not complete: use it only when errors is empty."""
    errors, raw_sections = [], []  # raw_sections: [(row number, {kind, title, description, questions})]
    for number, record in rows:
        kind = ROW_KINDS.get(record["row"].lower())
        try:
            if kind is None:
                raise ValidationError('Row must be "text", "activity" or "question".')
            if kind == "question":
                if not raw_sections or raw_sections[-1][1]["kind"] != "activity":
                    raise ValidationError("A question must come right after an activity row (or another question).")
                raw_sections[-1][1]["questions"].append(question_from_record(record))
            else:
                if len(raw_sections) >= MAX_SECTIONS:
                    raise ValidationError(f"An activity can have at most {MAX_SECTIONS} sections.")
                raw_sections.append((number, {"kind": kind, "title": record["title"],
                                              "description": record["description"], "questions": []}))
        except ValidationError as problem:
            errors.append({"row": number, "message": problem.message})
    if errors:
        return [], errors

    sections = []
    for position, (number, raw) in enumerate(raw_sections, start=1):
        try:
            sections.append(clean_section(raw, position))
        except ValidationError as problem:
            errors.append({"row": number, "message": problem.message})
    return sections, errors


def question_from_record(record):
    """The question dict (as the editor posts it) for a question row, checked.
    Raises ValidationError with a message about this row."""
    given = record["question_type"].lower()
    kind = QUESTION_TYPE_NAMES.get(given, given.replace(" ", "_"))
    if kind not in QUESTION_TYPES:
        raise ValidationError("Question type must be one of: " + ", ".join(QUESTION_TYPES) + ".")
    question = {"type": kind, "prompt": record["description"]}

    points = record["points"]
    question["points"] = DEFAULT_POINTS.get(kind, 1) if points == "" else int(points) if points.isdigit() else points

    answer = record["answer"]
    if kind == "multiple_choice":
        values = [record[f"choice_{letter}"] for letter in CHOICE_LETTERS]
        choices = [value for value in values if value]
        if values[:len(choices)] != choices:
            raise ValidationError("Fill the choices from A without gaps.")
        letter = answer.strip().lower()
        if len(letter) != 1 or letter not in CHOICE_LETTERS[:len(choices)]:
            raise ValidationError("Answer must be the letter of the correct choice (A, B, ...).")
        question["choices"] = choices
        question["answer"] = CHOICE_LETTERS.index(letter)
    elif kind == "true_false":
        value = TRUE_FALSE.get(answer.strip().lower())
        if value is None:
            raise ValidationError("Answer must be True or False.")
        question["answer"] = value
    elif kind == "identification":
        question["answer"] = answer.split("/")
    elif kind == "fill_blank":
        question["answer"] = [blank.split("/") for blank in answer.split(";")]
    else:  # short_answer
        question["answer"] = answer

    clean_question(question, "Question")
    return question
