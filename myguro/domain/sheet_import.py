"""Names and separators the Word import shares (see docx_import.py): question type spellings,
default points, and the " / " that splits accepted spellings."""

import re

DEFAULT_POINTS = {"short_answer": 5}
QUESTION_TYPE_NAMES = {
    "mc": "multiple_choice", "multiple choice": "multiple_choice",
    "true or false": "true_false", "true/false": "true_false", "tf": "true_false",
    "fill in the blank": "fill_blank", "fill in the blanks": "fill_blank", "fill blank": "fill_blank",
    "matching": "matching", "matching type": "matching",
    "short answer": "short_answer", "essay": "short_answer",
}
SPELLING_SEPARATOR = re.compile(r"\s+/\s+")  # spaces around it, so 1/2 and km/h stay whole
