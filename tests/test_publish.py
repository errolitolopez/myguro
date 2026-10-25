"""Teacher: publishing and unpublishing a sheet. Students see an assigned sheet only while it is published."""

from conftest import assign, error, login, make_activity, make_class
from test_docx_import import GOOD, docx_bytes, upload


def publish(teacher, activity_id, published=True):
    return teacher.put(f"/api/activities/{activity_id}/published", json={"published": published})


def assigned_sheet(teacher):
    class_id, students = make_class(teacher)
    activity_id, questions = make_activity(teacher, published=False)
    return activity_id, assign(teacher, activity_id, class_id), students, questions


def test_new_sheets_copies_and_imports_start_unpublished(teacher):
    activity_id, _ = make_activity(teacher, published=False)
    assert teacher.get(f"/api/activities/{activity_id}").get_json()["activity"]["published"] is False
    assert publish(teacher, activity_id).get_json()["activity"]["published"] is True
    copy = teacher.post(f"/api/activities/{activity_id}/duplicate").get_json()["activity"]
    assert copy["published"] is False
    imported = upload(teacher, docx_bytes(GOOD), dry_run=False).get_json()["activity"]
    assert imported["published"] is False


def test_students_see_an_assigned_sheet_only_while_published(teacher):
    activity_id, assignment_id, students, questions = assigned_sheet(teacher)
    student = login(students[0]["username"])
    answers = {"answers": {str(questions[0]): 1}}

    assert student.get("/api/my-activities").get_json()["activities"] == []
    assert student.get(f"/api/my-activities/{assignment_id}").status_code == 404
    assert student.put(f"/api/my-activities/{assignment_id}/answers", json=answers).status_code == 404
    assert student.post(f"/api/my-activities/{assignment_id}/submit", json=answers).status_code == 404
    dashboard = student.get("/api/dashboard").get_json()
    assert dashboard["classes"][0]["activities"] == 0 and dashboard["to_do"] == 0

    assert publish(teacher, activity_id).get_json()["activity"]["published"] is True
    assert [item["id"] for item in student.get("/api/my-activities").get_json()["activities"]] == [assignment_id]
    assert student.put(f"/api/my-activities/{assignment_id}/answers", json=answers).status_code == 200
    dashboard = student.get("/api/dashboard").get_json()
    assert dashboard["classes"][0]["activities"] == 1 and dashboard["to_do"] == 1


def test_unpublish_hides_it_and_publish_restores_saved_answers(teacher):
    activity_id, assignment_id, students, questions = assigned_sheet(teacher)
    assert publish(teacher, activity_id).status_code == 200
    student = login(students[0]["username"])
    assert student.put(f"/api/my-activities/{assignment_id}/answers",
                       json={"answers": {str(questions[0]): 1}}).status_code == 200

    assert publish(teacher, activity_id, False).get_json()["activity"]["published"] is False
    assert student.get(f"/api/my-activities/{assignment_id}").status_code == 404

    assert publish(teacher, activity_id).status_code == 200
    detail = student.get(f"/api/my-activities/{assignment_id}").get_json()["activity"]
    assert detail["answers"][str(questions[0])] == 1


def test_unpublish_after_a_submission_hides_it_from_the_student_only(teacher):
    activity_id, assignment_id, students, _ = assigned_sheet(teacher)
    assert publish(teacher, activity_id).status_code == 200
    student = login(students[0]["username"])
    assert student.post(f"/api/my-activities/{assignment_id}/submit", json={"answers": {}}).status_code == 200

    assert publish(teacher, activity_id, False).status_code == 200
    assert student.get("/api/my-activities").get_json()["activities"] == []
    results = teacher.get(f"/api/assignments/{assignment_id}/results").get_json()
    assert results["summary"]["submitted"] == 1

    assert publish(teacher, activity_id).status_code == 200
    seen = student.get("/api/my-activities").get_json()["activities"]
    assert [(item["id"], item["status"]) for item in seen] == [(assignment_id, "submitted")]


def test_publish_rules(teacher, other_teacher):
    activity_id, _ = make_activity(teacher, published=False)
    empty_id = teacher.post("/api/activities", json={"title": "Empty"}).get_json()["activity"]["id"]  # no sections
    response = publish(teacher, empty_id)
    assert response.status_code == 400 and error(response) == "Add at least one section before publishing."
    assert publish(teacher, empty_id, False).status_code == 200  # hiding is always fine

    assert publish(other_teacher, activity_id).status_code == 404
    response = teacher.put(f"/api/activities/{activity_id}/published", json={"published": "yes"})
    assert response.status_code == 400 and error(response) == "Choose whether to publish the activity."
    _, students = make_class(teacher)
    assert login(students[0]["username"]).put(
        f"/api/activities/{activity_id}/published", json={"published": True}).status_code == 403


def test_teacher_dashboard_counts_published_and_unpublished(teacher):
    first, _ = make_activity(teacher, published=False)
    make_activity(teacher, title="Second", published=False)
    counts = lambda: {key: teacher.get("/api/dashboard").get_json()[key] for key in ("published", "drafts")}
    assert counts() == {"published": 0, "drafts": 2}
    assert publish(teacher, first).status_code == 200
    assert counts() == {"published": 1, "drafts": 1}


def test_migration_publishes_assigned_sheets_once(app, teacher):
    from myguro.database import get_db, init_db

    class_id, _ = make_class(teacher)
    given_id, _ = make_activity(teacher, title="Given", published=False)
    idle_id, _ = make_activity(teacher, title="Idle", published=False)
    assign(teacher, given_id, class_id)

    with app.app_context():
        db = get_db()
        db.execute("ALTER TABLE activities DROP COLUMN published")  # the database as it was before
        db.commit()

        init_db()  # the upgrade under test
        rows = {row["id"]: row["published"] for row in db.execute("SELECT id, published FROM activities")}
        assert rows == {given_id: 1, idle_id: 0}

        # A teacher's later Unpublish must survive the app starting again.
        db.execute("UPDATE activities SET published = 0 WHERE id = ?", (given_id,))
        db.commit()
        init_db()
        assert db.execute("SELECT published FROM activities WHERE id = ?", (given_id,)).fetchone()[0] == 0
