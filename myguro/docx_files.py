"""Reading an uploaded Word (.docx) activity sheet into lines, and the template to fill in.

Only the reading is here (lines of text with their heading level); the rules for a sheet are in
domain/docx_import.py.
"""

import io
import zipfile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from docx.text.paragraph import Paragraph

from myguro.errors import ValidationError

NAME_TABLE_START = "name of student"  # the Name / Grade / Date box at the top of a LAS is skipped


def read_docx_lines(content):
    """[(kind, text)] from a .docx file (bytes) in reading order. kind is "h1" (Heading 1), "h2"
    (Heading 2) or "p". Empty lines are skipped; a table row becomes one line, cells joined by " | "."""
    try:
        document = Document(io.BytesIO(content))
    except (PackageNotFoundError, zipfile.BadZipFile, KeyError, ValueError, OSError):
        raise ValidationError("This is not a Word .docx file. In Word, use Save As → "
                              "Word Document (.docx).") from None
    lines = []
    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            paragraph = Paragraph(child, document)
            text = " ".join(paragraph.text.split())
            style = paragraph.style.name if paragraph.style is not None else ""
            if text:
                lines.append(({"Heading 1": "h1", "Heading 2": "h2"}.get(style, "p"), text))
        elif child.tag.endswith("}tbl"):
            table = Table(child, document)
            rows = [[" ".join(cell.text.split()) for cell in row.cells] for row in table.rows]
            if any(cell.casefold().startswith(NAME_TABLE_START) for row in rows for cell in row):
                continue
            for row in rows:
                cells = []
                for cell in row:
                    if cell and cell not in cells:  # merged cells repeat their text
                        cells.append(cell)
                if cells:
                    lines.append(("p", " | ".join(cells)))
    return lines


EXAMPLE = [
    ("h1", "I. Lesson"),
    ("p", "Text sections have no Type line. Write the lesson here, one paragraph per line."),
    ("h1", "II. Pre-test"),
    ("p", "Type: Multiple Choice"),
    ("p", "Points: 1"),
    ("p", "Directions: Choose the letter of the correct answer."),
    ("p", "1. Which tradition originated in India?"),
    ("p", "A. Confucianism"),
    ("p", "B. Hinduism"),
    ("p", "C. Taoism"),
    ("p", "2. What is the central concern of Buddhism?"),
    ("p", "A. Social hierarchy"),
    ("p", "B. Suffering and liberation"),
    ("p", "C. Military strategy"),
    ("h1", "III. True or False"),
    ("p", "Type: True or False"),
    ("p", "Directions: Write True if the statement is correct, False if not."),
    ("p", "1. Wu wei means doing nothing at all."),
    ("p", "2. Karma is about action and its moral consequences."),
    ("h1", "IV. Identification"),
    ("p", "Type: Identification"),
    ("p", "Directions: Write the answer."),
    ("p", "1. Which tradition teaches the Four Noble Truths?"),
    ("p", "2. Which tradition teaches living in harmony with the Tao?"),
    ("h1", "V. Fill in the Blank"),
    ("p", "Type: Fill in the Blank"),
    ("p", "Directions: Write the missing words. Each ___ is one blank."),
    ("p", "1. Hinduism started in ___ and Confucianism started in ___."),
    ("h1", "VI. Matching"),
    ("p", "Type: Matching"),
    ("p", "Points: 4"),
    ("p", "Directions: Match each concept in Column A to its meaning in Column B."),
    ("p", "1. Ren"),
    ("p", "2. Dharma"),
    ("p", "3. Wu wei"),
    ("p", "A. Effortless action"),
    ("p", "B. Ethical duty"),
    ("p", "C. Humaneness"),
    ("p", "D. Cycle of rebirth"),
    ("h1", "VII. Reflection"),
    ("p", "Type: Short Answer"),
    ("p", "Points: 5"),
    ("p", "Directions: Answer in 2 to 3 sentences."),
    ("p", "1. Which tradition speaks most to you, and why?"),
    ("h1", "ANSWER KEY"),
    ("h2", "II. Pre-test"),
    ("p", "1. B (Hinduism)"),
    ("p", "2. B"),
    ("h2", "III. True or False"),
    ("p", "1. FALSE"),
    ("p", "2. TRUE"),
    ("h2", "IV. Identification"),
    ("p", "1. Buddhism"),
    ("p", "2. Taoism / Daoism"),
    ("h2", "V. Fill in the Blank"),
    ("p", "1. India; China"),
    ("h2", "VI. Matching"),
    ("p", "1. C"),
    ("p", "2. B"),
    ("p", "3. A"),
    ("h2", "VII. Reflection"),
    ("p", "1. Any tradition, if the reasons come from the lesson. (optional guide for checking)"),
]

INSTRUCTIONS = [
    "How to use this template",
    "1. Keep each section heading as Heading 1 (Home > Styles > Heading 1). Everything under a heading "
    "belongs to that section.",
    "2. A section with no Type line is a text section (lesson, objectives, discussion).",
    "3. A section whose first line is Type: ... is an activity. Types: Multiple Choice, True or False, "
    "Identification, Fill in the Blank, Matching, Short Answer.",
    "4. Optional lines: Points: 2 (for every question of the section; default 1, Short Answer 5) and "
    "Directions: ... (shown above the questions).",
    "5. Number every question: 1. 2. 3. Multiple choice choices are A. B. C. lines under the question. "
    "Fill in the blank uses ___ for each blank. A Matching section is one question: numbered lines are "
    "Column A, lettered lines (A. B. C.) are Column B.",
    "6. The last section is Heading 1 ANSWER KEY. Repeat each activity's heading (Heading 2), then one line "
    "per question: 1. B  |  2. TRUE  |  3. Taoism / Daoism  |  4. India; China. Matching: the Column B "
    "letter for each Column A number. Short Answer: an optional guide for checking. Put spaces around the "
    "slash between accepted answers (Taoism / Daoism); a slash without spaces, like 1/2, is part of the answer.",
    "7. Anything before the first Heading 1 (like this page) is not imported. Delete the example below "
    "and write your own.",
]


def sheet_template_docx_bytes():
    """The Word file to fill in: how to use it, then an example of every type and its answer key."""
    document = Document()
    document.add_heading("myguro activity template", level=0)
    document.add_paragraph().add_run(INSTRUCTIONS[0]).bold = True
    for text in INSTRUCTIONS[1:]:
        document.add_paragraph(text)
    for kind, text in EXAMPLE:
        if kind == "h1":
            document.add_heading(text, level=1)
        elif kind == "h2":
            document.add_heading(text, level=2)
        else:
            document.add_paragraph(text)
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()
