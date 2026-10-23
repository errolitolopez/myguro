"""Shared test setup: a throwaway database, seeded with the sample accounts before each test.

Run with: .venv/bin/pytest
"""

import os
import sqlite3
import tempfile

import pytest

# The app reads its database path from MYGURO_DATABASE when it is imported.
_DB_DIR = tempfile.mkdtemp(prefix="myguro-tests-")
os.environ["MYGURO_DATABASE"] = os.path.join(_DB_DIR, "test.db")

from app import app as flask_app  # noqa: E402  (must come after setting the database path)

PASSWORD = "1234"  # every sample account (see seed.py)


def reset_database():
    """Empty every table, then create the default admin and the sample accounts again."""
    connection = sqlite3.connect(os.environ["MYGURO_DATABASE"])
    tables = [row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]
    connection.execute("PRAGMA foreign_keys = OFF")
    for table in tables:
        connection.execute(f"DELETE FROM {table}")
    if connection.execute("SELECT 1 FROM sqlite_master WHERE name = 'sqlite_sequence'").fetchone():
        connection.execute("DELETE FROM sqlite_sequence")
    connection.commit()
    connection.close()
    runner = flask_app.test_cli_runner()
    assert runner.invoke(args=["init-db"]).exit_code == 0
    assert runner.invoke(args=["seed"]).exit_code == 0


def reset_login_throttle():
    """Forget wrong-password counts from earlier tests."""
    import app as app_module
    throttle = getattr(app_module, "failed_logins", None)
    if throttle is not None:
        throttle.clear()
    for extension in flask_app.extensions.values():
        if hasattr(extension, "reset"):
            extension.reset()


@pytest.fixture(autouse=True)
def fresh_database():
    reset_database()
    reset_login_throttle()
    yield


@pytest.fixture
def app():
    return flask_app


def login(username, password=PASSWORD):
    """A test client logged in as this user."""
    client = flask_app.test_client()
    response = client.post("/api/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.get_json()
    return client


@pytest.fixture
def admin():
    client = login("admin", "admin")
    assert client.post("/api/change-password",
                       json={"current_password": "admin", "new_password": "adminpass1"}).status_code == 200
    return client


@pytest.fixture
def supervisor(admin):
    """A supervisor (read-only, sees only the activity log), already past the forced password change."""
    response = admin.post("/api/users", json={"role": "supervisor", "last_name": "Garcia", "first_name": "Sam",
                                              "username": "sgarcia", "password": "123qwe"})
    assert response.status_code == 201, response.get_json()
    client = login("sgarcia", "123qwe")
    assert client.post("/api/change-password",
                       json={"current_password": "123qwe", "new_password": "supervisor1"}).status_code == 200
    return client


@pytest.fixture
def teacher():
    return login("ecruz")


@pytest.fixture
def other_teacher():
    return login("rdiaz")


def make_class(teacher, name="Grade 9 - Rizal", subject="Philosophy", grade="Grade 9", section="Rizal"):
    """A class of the teacher with the sample students of one grade + section. Returns (class id, students)."""
    class_id = teacher.post("/api/classes", json={"name": name, "subject": subject}).get_json()["class"]["id"]
    students = teacher.get(
        f"/api/classes/{class_id}/student-search?grade={grade.replace(' ', '+')}&section={section}"
    ).get_json()["students"]
    assert teacher.post(f"/api/classes/{class_id}/students",
                        json={"student_ids": [student["id"] for student in students]}).status_code == 201
    return class_id, students


SAMPLE_SECTIONS = [
    {"kind": "text", "title": "I. Title of the Lesson", "description": "Early Eastern\nBeginnings"},
    {"kind": "activity", "title": "III. Pre-test", "description": "Choose the letter.", "questions": [
        {"type": "multiple_choice", "prompt": "Which originated in India?",
         "choices": ["Confucianism", "Hinduism", "Taoism"], "answer": 1, "points": 1},
        {"type": "true_false", "prompt": "Both originated in China.", "answer": False, "points": 1},
        {"type": "identification", "prompt": "Living by the Dao.", "answer": ["Taoism", "Daoism"], "points": 2},
        {"type": "fill_blank", "prompt": "Buddhism in ___ and Taoism in ___.", "answer": [["India"], ["China"]],
         "points": 2},
    ]},
    {"kind": "activity", "title": "XI. Reflection", "questions": [
        {"type": "short_answer", "prompt": "Why?", "answer": "key points", "points": 5},
    ]},
]


def make_activity(teacher, title="Early Eastern Philosophy", sections=None, published=True):
    """An activity with sections, published unless published=False. Returns (activity id, question ids in order)."""
    activity_id = teacher.post("/api/activities", json={"title": title}).get_json()["activity"]["id"]
    response = teacher.put(f"/api/activities/{activity_id}",
                           json={"title": title, "sections": sections or SAMPLE_SECTIONS})
    assert response.status_code == 200, response.get_json()
    if published:
        assert teacher.put(f"/api/activities/{activity_id}/published", json={"published": True}).status_code == 200
    questions = [question["id"] for section in response.get_json()["activity"]["sections"]
                 for question in section["questions"]]
    return activity_id, questions


def assign(teacher, activity_id, class_id, **options):
    response = teacher.put(f"/api/activities/{activity_id}/assignments",
                           json={"assignments": [{"class_id": class_id, **options}]})
    assert response.status_code == 200, response.get_json()
    return next(item["assignment"]["id"] for item in response.get_json()["classes"] if item["id"] == class_id)


def error(response):
    return response.get_json()["error"]
