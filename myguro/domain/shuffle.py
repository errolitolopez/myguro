"""Shuffled questions and choices (a beta feature each teacher turns on for their own activities): the order is
worked out from a seed, so the same student sees the same order every time they open the sheet, other students
see another order, and nothing about the order is stored. No database, no Flask."""

import hashlib
import random

TEACHER_SETTING_KEYS = ("shuffle_questions", "shuffle_choices")


def seed_for(student_id, assignment_id, attempt):
    """A number that is the same for the same student, assignment and attempt (a new attempt is shuffled again).
    sha256, not hash(): Python's hash() changes every time the program starts."""
    digest = hashlib.sha256(f"{student_id}:{assignment_id}:{attempt}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def permutation(count, seed, label):
    """The numbers 0 .. count-1 in a shuffled order that depends only on the seed and the label."""
    order = list(range(count))
    random.Random(f"{seed}:{label}").shuffle(order)
    return order


def shuffled_questions(questions, seed, section_id):
    """The questions of one activity section in the student's order (the section's own place is kept)."""
    return [questions[i] for i in permutation(len(questions), seed, f"section{section_id}")]


def choice_order(choice_count, seed, question_id):
    """order[shown position] = the choice's place in the teacher's list."""
    return permutation(choice_count, seed, f"question{question_id}")


def to_shown(order, stored):
    """The place a stored choice (teacher's list) has on the student's screen."""
    return order.index(stored) if isinstance(stored, int) and not isinstance(stored, bool) and stored in order else stored


def to_stored(order, shown):
    """The teacher's-list place of the choice at this place on the student's screen. A value that is not a place
    on the screen is left alone, so the usual checks reject it."""
    if isinstance(shown, int) and not isinstance(shown, bool) and 0 <= shown < len(order):
        return order[shown]
    return shown
