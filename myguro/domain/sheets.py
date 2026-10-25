"""Rules for learning activity sheets: title, sections (text or activity) and questions.

Question types and their answer keys (stored as JSON):
  multiple_choice  choices ["Hinduism", ...], answer 1 (the index of the correct choice)
  true_false       answer true / false
  identification   answer ["Taoism", "Daoism"] (any of them is correct)
  fill_blank       ___ in the prompt for each blank, answer [["India"], ["China"]] (per blank)
  matching         choices = Column B texts, answer [{"item": "Hinduism", "match": 2}, ...] (Column A item and
                   the index of its Column B choice); the prompt is the instruction line
  short_answer     a short essay the teacher scores; answer is an optional guide for checking
"""

import re
from dataclasses import dataclass, field

from myguro.domain.accounts import MAX_NAME_LENGTH
from myguro.domain.richtext import clean_rich_text, rich_text_length
from myguro.domain.text import clean_description, clean_name, whole_number
from myguro.errors import ValidationError

MAX_TITLE_LENGTH = 150
MAX_SECTIONS = 50
MAX_DESCRIPTION_LENGTH = 20000
SECTION_KINDS = ("text", "activity")
DESCRIPTION_FORMATS = ("plain", "rich")
QUESTION_TYPES = ("multiple_choice", "true_false", "identification", "fill_blank", "matching", "short_answer")
MAX_QUESTIONS_PER_SECTION = 100
MAX_CHOICES = 6
MAX_MATCH_ITEMS = 10  # Column A of a matching question
MAX_MATCH_CHOICES = 12  # Column B
MAX_POINTS = 100
MAX_ANSWER_LENGTH = 200
MAX_ATTEMPTS_CHOICE = 10  # "Submissions allowed": 1 to 10, or unlimited (None)
BLANK = re.compile(r"_{3,}")  # ___ (three or more underscores) marks a blank


@dataclass
class Question:
    type: str
    prompt: str
    answer: object
    points: int
    choices: list | None = None
    id: int | None = None  # set when it already exists (kept when saving)


@dataclass
class Section:
    kind: str
    title: str
    description: str
    questions: list = field(default_factory=list)
    id: int | None = None
    description_format: str = "plain"  # "rich" = description is HTML from clean_rich_text()


def clean_title_subject(data):
    """(title, subject) of a sheet. Both are required."""
    title = clean_name(data.get("title"))
    subject = clean_name(data.get("subject"))
    if not title:
        raise ValidationError("Title is required.")
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError(f"Title can be at most {MAX_TITLE_LENGTH} characters.")
    if not subject:
        raise ValidationError("Subject is required.")
    if len(subject) > MAX_NAME_LENGTH:
        raise ValidationError(f"Subject can be at most {MAX_NAME_LENGTH} characters.")
    return title, subject


def clean_max_attempts(value):
    """1 to 10, or None (unlimited)."""
    if value is not None and not whole_number(value, 1, MAX_ATTEMPTS_CHOICE):
        raise ValidationError(f"Submissions allowed must be 1 to {MAX_ATTEMPTS_CHOICE}, or unlimited.")
    return value


def clean_sections(sections):
    """The posted list of sections, each with its questions, as Section objects."""
    if not isinstance(sections, list):
        raise ValidationError("Sections must be a list.")
    if len(sections) > MAX_SECTIONS:
        raise ValidationError(f"An activity can have at most {MAX_SECTIONS} sections.")
    return [clean_section(section, number) for number, section in enumerate(sections, start=1)]


def clean_section(section, number):
    if not isinstance(section, dict):
        raise ValidationError(f"Section {number} is not valid.")
    kind = section.get("kind", "text")
    if kind not in SECTION_KINDS:
        raise ValidationError(f"Section {number}: unknown kind of section.")
    title = clean_name(section.get("title"))
    description_format = section.get("description_format", "plain")
    if description_format not in DESCRIPTION_FORMATS:
        raise ValidationError(f"Section {number}: unknown text format.")
    if description_format == "rich":
        description = clean_rich_text(section.get("description"))
        description_length = rich_text_length(description)
    else:
        description = clean_description(section.get("description"))
        description_length = len(description)
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError(f"Section {number}: the title can be at most {MAX_TITLE_LENGTH} characters.")
    if description_length > MAX_DESCRIPTION_LENGTH:
        raise ValidationError(f"Section {number}: the text can be at most {MAX_DESCRIPTION_LENGTH} characters.")

    questions = []
    if kind == "text":
        if not title and not description:
            raise ValidationError(f"Section {number} is empty. Type a title or description, or delete it.")
    else:
        posted = section.get("questions", [])
        if not isinstance(posted, list):
            raise ValidationError(f"Section {number}: the questions are not valid.")
        if not posted:
            raise ValidationError(f"Section {number} is an activity with no questions. Add a question, or delete it.")
        if len(posted) > MAX_QUESTIONS_PER_SECTION:
            raise ValidationError(f"Section {number}: at most {MAX_QUESTIONS_PER_SECTION} questions.")
        questions = [clean_question(question, f"Section {number}, question {question_number}")
                     for question_number, question in enumerate(posted, start=1)]
    return Section(kind=kind, title=title, description=description, questions=questions, id=section.get("id"),
                   description_format=description_format)


def clean_question(question, where):
    """One posted question. where is like "Section 3, question 2", for error messages."""
    if not isinstance(question, dict):
        raise ValidationError(f"{where} is not valid.")
    kind = question.get("type")
    if kind not in QUESTION_TYPES:
        raise ValidationError(f"{where}: unknown question type.")
    prompt = clean_description(question.get("prompt"))
    if not prompt:
        raise ValidationError(f"{where}: type the question.")
    if len(prompt) > MAX_DESCRIPTION_LENGTH:
        raise ValidationError(f"{where}: the question is too long.")
    points = question.get("points", 1)
    if not whole_number(points, 1, MAX_POINTS):
        raise ValidationError(f"{where}: points must be a whole number from 1 to {MAX_POINTS}.")

    choices = None
    if kind == "multiple_choice":
        choices = clean_choices(question.get("choices"), where)
        answer = question.get("answer")
        if not whole_number(answer, 0, len(choices) - 1):
            raise ValidationError(f"{where}: choose the correct answer.")
    elif kind == "true_false":
        answer = question.get("answer")
        if not isinstance(answer, bool):
            raise ValidationError(f"{where}: choose True or False as the correct answer.")
    elif kind == "identification":
        answer = clean_accepted_answers(question.get("answer"), where)
    elif kind == "matching":
        choices = clean_choices(question.get("choices"), where, maximum=MAX_MATCH_CHOICES)
        answer = clean_matches(question.get("answer"), len(choices), where)
    elif kind == "short_answer":
        # No right answer: the student writes their own and the teacher scores it.
        # The answer is an optional guide for checking (key points), seen only by the teacher.
        answer = clean_description(question.get("answer"))
        if len(answer) > MAX_DESCRIPTION_LENGTH:
            raise ValidationError(f"{where}: the guide for checking is too long.")
    else:  # fill_blank
        answer = clean_blank_answers(prompt, question.get("answer"), where)
    return Question(type=kind, prompt=prompt, answer=answer, points=points, choices=choices, id=question.get("id"))


def clean_choices(choices, where, maximum=MAX_CHOICES):
    if not isinstance(choices, list):
        raise ValidationError(f"{where}: the choices are not valid.")
    choices = [clean_name(choice) for choice in choices]
    if len(choices) < 2 or len(choices) > maximum:
        raise ValidationError(f"{where}: give 2 to {maximum} choices.")
    if not all(choices):
        raise ValidationError(f"{where}: a choice is empty. Type it or remove it.")
    if any(len(choice) > MAX_ANSWER_LENGTH for choice in choices):
        raise ValidationError(f"{where}: a choice can be at most {MAX_ANSWER_LENGTH} characters.")
    return choices


def clean_matches(values, choice_count, where):
    """Column A of a matching question: [{"item": text, "match": index of the Column B choice}]."""
    if not isinstance(values, list):
        raise ValidationError(f"{where}: the items are not valid.")
    if len(values) < 2 or len(values) > MAX_MATCH_ITEMS:
        raise ValidationError(f"{where}: give 2 to {MAX_MATCH_ITEMS} items to match.")
    matches = []
    for number, value in enumerate(values, start=1):
        if not isinstance(value, dict):
            raise ValidationError(f"{where}: the items are not valid.")
        item = clean_name(value.get("item"))
        if not item:
            raise ValidationError(f"{where}: item {number} is empty. Type it or remove it.")
        if len(item) > MAX_ANSWER_LENGTH:
            raise ValidationError(f"{where}: an item can be at most {MAX_ANSWER_LENGTH} characters.")
        if not whole_number(value.get("match"), 0, choice_count - 1):
            raise ValidationError(f"{where}: choose the match of item {number}.")
        matches.append({"item": item, "match": value["match"]})
    return matches


def clean_accepted_answers(values, where):
    """A list of accepted answers ("Taoism", "Daoism"), cleaned."""
    if not isinstance(values, list):
        raise ValidationError(f"{where}: the answer is not valid.")
    answers = [clean_name(value) for value in values if clean_name(value)]
    if not answers:
        raise ValidationError(f"{where}: type the correct answer.")
    if any(len(answer) > MAX_ANSWER_LENGTH for answer in answers):
        raise ValidationError(f"{where}: an answer can be at most {MAX_ANSWER_LENGTH} characters.")
    return answers


def clean_blank_answers(prompt, answer, where):
    """Accepted answers for each ___ in the prompt."""
    blanks = len(BLANK.findall(prompt))
    if blanks == 0:
        raise ValidationError(f"{where}: put ___ (three underscores) where the blank goes.")
    if not isinstance(answer, list) or len(answer) != blanks:
        raise ValidationError(f"{where}: type the answer for each blank.")
    return [clean_accepted_answers(values, f"{where}, blank {number}")
            for number, values in enumerate(answer, start=1)]
