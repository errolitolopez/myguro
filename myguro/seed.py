"""Sample accounts for trying out the app: teachers, and students in Grades 9 to 12
(two sections each).

Run with: flask --app app seed

All sample accounts have the password "1234" (easy for testing; shorter than the app allows
for real passwords). They don't have to change it, so they can log in right away. Safe to run again: accounts whose
username already exists are skipped.
"""

import click
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from myguro.database import get_db

TEACHER_PASSWORD = "1234"
STUDENT_PASSWORD = "1234"
STUDENTS_PER_SECTION = 6

# (name, username)
TEACHERS = [
    ("Elena Cruz", "ecruz"),
    ("Roberto Diaz", "rdiaz"),
    ("Liza Manalo", "lmanalo"),
    ("Ramon Aguilar", "raguilar"),
    ("Grace Pascual", "gpascual"),
    ("Arnel Valdez", "avaldez"),
]

SECTIONS = {
    "Grade 9": ["Rizal", "Bonifacio"],
    "Grade 10": ["Mabini", "Luna"],
    "Grade 11": ["STEM", "HUMSS"],
    "Grade 12": ["STEM", "ABM"],
}

FIRST_NAMES = [
    "Juan", "Maria", "Jose", "Ana", "Mark", "Angel", "John Paul", "Kristine", "Carlo", "Princess",
    "Miguel", "Andrea", "Paolo", "Bea", "Rafael", "Nicole", "Gabriel", "Camille", "Joshua", "Patricia",
    "Daniel", "Jasmine", "Christian", "Erica",
]
LAST_NAMES = [
    "Dela Cruz", "Santos", "Reyes", "Garcia", "Mendoza", "Torres", "Ramos", "Flores", "Gonzales",
    "Bautista", "Villanueva", "Aquino", "Castillo", "Navarro", "Domingo", "Mercado",
]


def sample_students():
    """(first name, last name, grade, section) for every sample student. The same list every run."""
    students = []
    number = 0
    for grade, sections in SECTIONS.items():
        for section in sections:
            for _ in range(STUDENTS_PER_SECTION):
                first = FIRST_NAMES[number % len(FIRST_NAMES)]
                last = LAST_NAMES[(number * 7) % len(LAST_NAMES)]
                students.append((first, last, grade, section))
                number += 1
    return students


def username_for(first, last, number):
    """"Juan", "Dela Cruz", 0 -> "jdelacruz01" (the number keeps sample usernames unique)."""
    return f"{first[0]}{last.replace(' ', '')}{number + 1:02d}".lower()


def add_account(db, name, username, password_hash, role, grade="", section=""):
    """Add one account unless the username is taken. Returns True when it was added."""
    if db.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
        return False
    db.execute(
        "INSERT INTO users (name, username, password_hash, role, must_change_password, grade, section) "
        "VALUES (?, ?, ?, ?, 0, ?, ?)",
        (name, username, password_hash, role, grade, section),
    )
    return True


@click.command("seed")
@with_appcontext
def seed_command():
    """Add sample teachers and students (Grades 9 to 12, two sections each)."""
    db = get_db()

    teacher_hash = generate_password_hash(TEACHER_PASSWORD)
    teachers = sum(add_account(db, name, username, teacher_hash, "teacher") for name, username in TEACHERS)

    student_hash = generate_password_hash(STUDENT_PASSWORD)
    students = sum(
        add_account(db, f"{first} {last}", username_for(first, last, number), student_hash, "student",
                    grade, section)
        for number, (first, last, grade, section) in enumerate(sample_students())
    )

    db.commit()
    click.echo(f"Added {teachers} sample teachers (password: {TEACHER_PASSWORD}) "
               f"and {students} sample students (password: {STUDENT_PASSWORD}).")
