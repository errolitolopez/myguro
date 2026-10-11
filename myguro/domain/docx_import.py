"""Turning the lines of an uploaded Word (.docx) activity sheet into sections and questions.

The file follows our template (see docx_files.py). Lines come as (kind, text), kind "h1" / "h2"
for headings and "p" for everything else (tables are already flattened into lines).

  Heading 1 "I. Lesson"       a section; plain lines under it are a text section
  Type: Multiple Choice       first line under the heading: makes it an activity section
  Points: 2                   optional, for every question of the section (default 1, short answer 5)
  Directions: ...             optional lines before the first item
  1. Question                 numbered items (A. B. C. lines under it are the choices)
  Heading 1 "ANSWER KEY"      the last section: the section's heading again, then "1. B", "2. TRUE",
                              "3. Taoism / Daoism", "4. India; Philippines / PH"

What counts as the answer is read by type, the rest of the line (such as "(Hinduism)") is ignored:
  multiple_choice  the letter           true_false     True / False
  identification   answers split by /   fill_blank      blanks split by ; (spellings by /)
  matching         one letter per Column A item         short_answer  optional guide for checking
A matching section is one question: Directions are its instruction, numbered lines are Column A,
lettered lines Column B.
"""

import re

from myguro.domain.sheet_import import DEFAULT_POINTS, QUESTION_TYPE_NAMES
from myguro.domain.sheets import QUESTION_TYPES, clean_question, clean_section
from myguro.errors import ValidationError

MAX_QUESTIONS = 500
KEY_HEADING = "answer key"
TYPE_LINE = re.compile(r"^type\s*:\s*(.*)$", re.IGNORECASE)
POINTS_LINE = re.compile(r"^points?\s*:\s*(.*)$", re.IGNORECASE)
DIRECTIONS_LINE = re.compile(r"^directions?\s*:\s*(.*)$", re.IGNORECASE)
ITEM = re.compile(r"^_*\s*(\d{1,3})\s*[.)]\s*(.*)$")
CHOICE = re.compile(r"^([A-La-l])\s*[.)]\s+(.*)$")
COLUMN_LABEL = re.compile(r"^column\s+[ab]\b", re.IGNORECASE)
ANSWER_SPACE = re.compile(r"\s*(?:answer\s*:)?\s*_{3,}\s*$", re.IGNORECASE)
PARENTHETICAL = re.compile(r"\s*\([^)]*\)\s*$")
LETTER = re.compile(r"^([A-Za-z])\b")
TRUE_FALSE = re.compile(r"^(true|false|t|f)\b", re.IGNORECASE)


def normal(text):
    return " ".join(text.split()).casefold()


def sections_from_lines(lines):
    """(sections, errors) from [(kind, text)]. errors are [{row: None, where, message}]; with any
    error, sections is not complete: use it only when errors is empty."""
    blocks, key_lines, current = [], None, None  # blocks: [(heading, [body lines])]
    for kind, text in lines:
        if kind == "h1" and key_lines is None and normal(text) == KEY_HEADING:
            key_lines = []
        elif key_lines is not None:
            key_lines.append((kind, text))
        elif kind == "h1":
            current = (text, [])
            blocks.append(current)
        elif current is not None:
            current[1].append(text)  # lines before the first heading (title, name table) are skipped

    activity_headings = [normal(heading) for heading, body in blocks if body and TYPE_LINE.match(body[0])]
    errors = []
    for heading in set(activity_headings):
        if activity_headings.count(heading) > 1:
            errors.append(problem("ANSWER KEY", f'Two activity sections are both called "{heading}". '
                                                "Give each its own heading so the answer key can tell them apart."))
    key = parse_key(key_lines or [], set(activity_headings))

    raw_sections, question_count = [], 0
    for heading, body in blocks:
        if body and TYPE_LINE.match(body[0]):
            raw, found = activity_section(heading, body, key.get(normal(heading)), key_lines is not None)
            errors.extend(found)
            question_count += len(raw["questions"])
        else:
            raw = {"kind": "text", "title": heading, "description": "\n".join(body)}
        raw_sections.append(raw)
    if not blocks:
        errors.append(problem("File", "No sections found. Each section starts with a Heading 1 line. "
                                      "Download the template to see the format."))
    if question_count > MAX_QUESTIONS:
        errors.append(problem("File", f"The file has more than {MAX_QUESTIONS} questions. Split it into smaller sheets."))
    if errors:
        return [], errors

    sections = []
    for position, raw in enumerate(raw_sections, start=1):
        try:
            sections.append(clean_section(raw, position))
        except ValidationError as failure:
            errors.append(problem(raw["title"], failure.message))
    return sections, errors


def problem(where, message):
    return {"row": None, "where": where, "message": message}


def parse_key(key_lines, activity_headings):
    """{normal heading: {item number: the rest of the line}}"""
    key, current = {}, None
    for kind, text in key_lines:
        if kind in ("h1", "h2") or normal(text) in activity_headings:
            current = key.setdefault(normal(text), {})
            continue
        item = ITEM.match(text)
        if item and current is not None:
            current.setdefault(int(item.group(1)), item.group(2).strip())
    return key


def activity_section(heading, body, key, has_key):
    """(raw section dict, [problems]) for an activity section."""
    problems = []

    def fail(item, message):
        problems.append(problem(f"{heading}, item {item}" if item else heading, message))

    given = normal(TYPE_LINE.match(body[0]).group(1))
    kind = QUESTION_TYPE_NAMES.get(given, given.replace(" ", "_"))
    raw = {"kind": "activity", "title": heading, "description": "", "questions": []}
    if kind not in QUESTION_TYPES:
        fail(None, 'Type must be one of: Multiple Choice, True or False, Identification, '
                   'Fill in the Blank, Matching, Short Answer.')
        return raw, problems

    points, directions, items = None, [], []  # items: [{number, text, choices}]
    for line in body[1:]:
        points_line = POINTS_LINE.match(line)
        item = ITEM.match(line)
        choice = CHOICE.match(line)
        if points_line and not items:
            points = points_line.group(1).strip()
            if not points.isdigit():
                fail(None, "Points must be a whole number.")
        elif item and (kind != "matching" or not items or not items[-1]["choices"]):
            items.append({"number": int(item.group(1)), "text": item.group(2).strip(), "choices": []})
        elif choice and items:
            items[-1]["choices"].append((choice.group(1).upper(), choice.group(2).strip()))
        elif COLUMN_LABEL.match(line):
            continue
        elif not items:
            directions.append(DIRECTIONS_LINE.sub(r"\1", line) if DIRECTIONS_LINE.match(line) else line)
        else:
            fail(items[-1]["number"], f'Unexpected text after this item: "{line[:60]}". '
                                      "Every question must start with its number, like 3.")
    raw["description"] = "\n".join(directions)

    if not items:
        fail(None, "No numbered questions found. Start each question with its number, like 1.")
        return raw, problems
    if kind == "matching":
        found = matching_question(heading, items, directions, key, has_key, fail)
        raw["questions"] = [found] if found else []
    else:
        for item in items:
            found = single_question(kind, item, key, has_key, fail)
            if found:
                raw["questions"].append(found)
        for number in sorted(set(key or {}) - {item["number"] for item in items}):
            fail(number, "The ANSWER KEY has this item but the activity does not.")
    default = DEFAULT_POINTS.get(kind, 1)
    for question in raw["questions"]:
        question["points"] = int(points) if points and points.isdigit() else default
    return raw, problems


def key_text(item, key, has_key, fail, required=True):
    """The answer-key text for a numbered item, or None after reporting the problem."""
    if key is None or item["number"] not in key:
        if required:
            fail(item["number"], "No answer in the ANSWER KEY." if has_key
                 else "The file has no ANSWER KEY section (Heading 1 \"ANSWER KEY\" at the end).")
        return None
    return key[item["number"]]


def single_question(kind, item, key, has_key, fail):
    number = item["number"]
    prompt = item["text"]
    question = {"type": kind}
    answer = key_text(item, key, has_key, fail, required=kind != "short_answer")
    if kind == "multiple_choice":
        letters = [letter for letter, _ in item["choices"]]
        if letters != list("ABCDEFGHIJKL"[:len(letters)]):
            fail(number, "Choices must be lettered A., B., C. ... in order, one per line under the question.")
            return None
        question["choices"] = [text for _, text in item["choices"]]
        if answer is None:
            return None
        found = LETTER.match(answer)
        index = "abcdefghijkl".find(found.group(1).lower()) if found else -1
        if index < 0 or index >= len(letters):
            fail(number, f'The answer "{answer[:30]}" must be the letter of a choice (A to {letters[-1]}).')
            return None
        question["answer"] = index
    else:
        if item["choices"]:
            fail(number, "Lettered lines are only for Multiple Choice and Matching.")
            return None
        if kind == "true_false":
            if answer is None:
                return None
            found = TRUE_FALSE.match(answer)
            if not found:
                fail(number, f'The answer "{answer[:30]}" must be True or False.')
                return None
            question["answer"] = found.group(1).lower() in ("true", "t")
        elif kind == "identification":
            prompt = ANSWER_SPACE.sub("", prompt)
            if answer is None:
                return None
            question["answer"] = accepted(answer)
        elif kind == "fill_blank":
            if answer is None:
                return None
            question["answer"] = [accepted(blank) for blank in answer.split(";")]
        else:  # short_answer
            prompt = ANSWER_SPACE.sub("", prompt)
            question["answer"] = answer or ""
    question["prompt"] = prompt
    question["points"] = 1
    return checked(question, number, fail)


def accepted(text):
    """The accepted spellings in "Card 3 (Taoism) / Card three": split by /, notes in () dropped."""
    return [PARENTHETICAL.sub("", spelling).strip() for spelling in text.split("/")]


def matching_question(heading, items, directions, key, has_key, fail):
    column_b = items[-1]["choices"]  # the lettered lines come after the last numbered item
    letters = [letter for letter, _ in column_b]
    if not column_b or letters != list("ABCDEFGHIJKL"[:len(letters)]):
        fail(None, "Matching needs Column B lettered A., B., C. ... in order, one per line after the numbered items.")
        return None
    pairs, failed = [], False
    for item in items:
        answer = key_text(item, key, has_key, fail)
        found = LETTER.match(answer) if answer is not None else None
        index = "abcdefghijkl".find(found.group(1).lower()) if found else -1
        if answer is not None and (index < 0 or index >= len(letters)):
            fail(item["number"], f'The answer "{answer[:30]}" must be a Column B letter (A to {letters[-1]}).')
        if index < 0 or index >= len(letters):
            failed = True
            continue
        pairs.append({"item": item["text"], "match": index})
    if failed:
        return None
    extra = sorted(set(key or {}) - {item["number"] for item in items})
    for number in extra:
        fail(number, "The ANSWER KEY has this item but the activity does not.")
    question = {"type": "matching", "prompt": " ".join(directions) or heading, "choices": [text for _, text in column_b],
                "answer": pairs, "points": 1}
    return checked(question, None, fail)


def checked(question, number, fail):
    """The question when the shared rules accept it, else None after reporting why."""
    try:
        clean_question(question, "Question")
    except ValidationError as failure:
        fail(number, failure.message.removeprefix("Question: "))
        return None
    return question
