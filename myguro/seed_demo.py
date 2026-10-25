"""Sample lessons for trying out the app: a class, an activity, and students' answers with the
teacher's scores and remarks.

Run with: flask --app app seed-demo   (run `flask --app app seed` first for the sample accounts)

It goes through the app's own API (the Flask test client), so every rule is checked the same way
as when a person uses the app. Safe to run again: it does nothing if the demo class exists.
"""

import threading

import click
from flask import current_app
from flask.cli import with_appcontext

from myguro.seed import STUDENT_PASSWORD, TEACHER_PASSWORD

TEACHER = "ecruz"
CLASS_NAME = "Grade 9 - Rizal"
ACTIVITY_TITLE = "Early Eastern Philosophy"

SECTIONS = [
    {"kind": "text", "title": "I. Title of the Lesson", "description": "Early Eastern\nBeginnings"},
    {"kind": "activity", "title": "III. Pre-test", "description": "Answer each item.", "questions": [
        {"type": "multiple_choice", "prompt": "Which originated in India?",
         "choices": ["Confucianism", "Hinduism", "Taoism"], "answer": 1, "points": 1},
        {"type": "true_false", "prompt": "Both Buddhism and Taoism originated in China.", "answer": False,
         "points": 1},
        {"type": "identification", "prompt": "The philosophy of living by the Dao.",
         "answer": ["Taoism", "Daoism"], "points": 2},
        {"type": "fill_blank", "prompt": "Buddhism began in ___ and Taoism in ___.",
         "answer": [["India"], ["China"]], "points": 2},
    ]},
    {"kind": "activity", "title": "XI. Reflection", "questions": [
        {"type": "short_answer", "prompt": "Why do these teachings still matter today?",
         "answer": "Any reasonable answer with an example.", "points": 5},
    ]},
]

# What each of the first students answers, in question order (None = left blank). The first
# student gets everything right, the last submits with mistakes; the rest stay unfinished.
GOOD = [1, False, "Taoism", ["India", "China"], "They teach us to live in balance, like staying calm in a busy day."]
MISTAKES = [0, True, "Confucianism", ["India", "Japan"], "Because."]
UNFINISHED = [1, None, "Daoism", None, None]


def log_in(client, username, password):
    response = client.post("/api/login", json={"username": username, "password": password})
    if response.status_code != 200:
        raise click.ClickException(f"Cannot log in as {username}. Run `flask --app app seed` first.")


def answers_for(question_ids, values):
    return {str(question_id): value for question_id, value in zip(question_ids, values) if value is not None}


def check(response, what):
    if response.status_code >= 400:
        raise click.ClickException(f"{what}: {response.get_json()['error']}")
    return response.get_json()


@click.command("seed-demo")
@with_appcontext
def seed_demo_command():
    """Add a sample class, activity, answers, scores and remarks for the teacher ecruz."""
    app = current_app._get_current_object()
    problems = []

    def work():
        try:
            add_demo(app)
        except click.ClickException as error:
            problems.append(error)

    # Run in its own thread: inside this command's app context the app would remember the first
    # logged-in person (flask's g) and treat every student as the teacher. A new thread starts
    # clean, like a real request.
    thread = threading.Thread(target=work)
    thread.start()
    thread.join()
    if problems:
        raise problems[0]


def add_demo(app):
    teacher = app.test_client()
    log_in(teacher, TEACHER, TEACHER_PASSWORD)

    if any(item["name"] == CLASS_NAME for item in teacher.get("/api/classes").get_json()["classes"]):
        click.echo(f"{TEACHER} already has the class {CLASS_NAME}. Nothing added.")
        return

    class_id = check(teacher.post("/api/classes", json={"name": CLASS_NAME, "subject": "Philosophy"}),
                     "class")["class"]["id"]
    found = teacher.get(f"/api/classes/{class_id}/student-search?grade=Grade+9&section=Rizal").get_json()["students"]
    check(teacher.post(f"/api/classes/{class_id}/students", json={"student_ids": [s["id"] for s in found]}),
          "students")

    activity_id = check(teacher.post("/api/activities", json={"title": ACTIVITY_TITLE, "subject": "Philosophy"}),
                        "activity")["activity"]["id"]
    saved = check(teacher.put(f"/api/activities/{activity_id}", json={"title": ACTIVITY_TITLE, "sections": SECTIONS}),
                  "sections")
    question_ids = [q["id"] for section in saved["activity"]["sections"] for q in section["questions"]]
    check(teacher.put(f"/api/activities/{activity_id}/settings", json={"max_attempts": 2}), "tries")
    given = check(teacher.put(f"/api/activities/{activity_id}/assignments", json={"assignments": [
        {"class_id": class_id, "due_date": "2026-12-31"}]}), "assign")
    assignment_id = next(item["assignment"]["id"] for item in given["classes"] if item["id"] == class_id)
    check(teacher.put(f"/api/assignments/{assignment_id}/open", json={"open": True}), "open")

    # Student 1 right, student 2 with mistakes (both submit), student 3 unfinished, the rest not started.
    plan = [(found[0], GOOD, True), (found[1], MISTAKES, True), (found[2], UNFINISHED, False)]
    for student, values, submit in plan:
        client = app.test_client()
        log_in(client, student["username"], STUDENT_PASSWORD)
        body = {"answers": answers_for(question_ids, values)}
        url = f"/api/my-activities/{assignment_id}"
        check(client.post(f"{url}/submit", json=body) if submit else client.put(f"{url}/answers", json=body),
              "answers")

    # The teacher scores the short answers, writes remarks, and releases the scores.
    for student, remark_points in ((found[0], 5), (found[1], 1)):
        result = teacher.get(f"/api/assignments/{assignment_id}/students/{student['id']}").get_json()
        submission_id = result["detail"]["id"]
        short_id = question_ids[-1]
        remarks = {
            str(short_id): "Good example." if remark_points == 5 else "Too short. Give a reason and an example.",
            str(question_ids[2]): "Well done." if remark_points == 5 else "Review the lesson on the Dao.",
        }
        check(teacher.put(f"/api/submissions/{submission_id}/points",
                          json={"points": {str(short_id): remark_points}, "feedback": remarks}), "scores")
    check(teacher.put(f"/api/assignments/{assignment_id}/release", json={"released": True}), "release")

    click.echo(f"Added the class {CLASS_NAME} with the activity {ACTIVITY_TITLE}: "
               f"{found[0]['username']} (all right), {found[1]['username']} (mistakes + remarks) submitted, "
               f"{found[2]['username']} unfinished, {len(found) - 3} not started. Passwords: {STUDENT_PASSWORD}.")
