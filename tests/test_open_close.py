"""Teacher: opening and closing an assignment. Students see a sheet only for the classes or groups it is open for."""

from conftest import assign, error, login, make_activity, make_class, open_assignment


def assigned_sheet(teacher):
    """A sheet given to a class, still closed (a new assignment starts closed)."""
    class_id, students = make_class(teacher)
    activity_id, questions = make_activity(teacher)
    return activity_id, assign(teacher, activity_id, class_id, opened=False), students, questions


def is_open(teacher, assignment_id):
    return teacher.get(f"/api/assignments/{assignment_id}/results").get_json()["assignment"]["is_open"]


def test_a_new_assignment_starts_closed_and_copies_are_not_given_to_anyone(teacher):
    activity_id, assignment_id, _, _ = assigned_sheet(teacher)
    assert is_open(teacher, assignment_id) is False
    listed = teacher.get("/api/activities").get_json()["activities"][0]
    assert (listed["assigned"], listed["open"]) == (1, 0)
    copy = teacher.post(f"/api/activities/{activity_id}/duplicate").get_json()["activity"]
    assert (copy["assigned"], copy["open"]) == (0, 0)


def test_students_see_an_assignment_only_while_it_is_open(teacher):
    activity_id, assignment_id, students, questions = assigned_sheet(teacher)
    student = login(students[0]["username"])
    answers = {"answers": {str(questions[0]): 1}}

    assert student.get("/api/my-activities").get_json()["activities"] == []
    assert student.get(f"/api/my-activities/{assignment_id}").status_code == 404
    assert student.put(f"/api/my-activities/{assignment_id}/answers", json=answers).status_code == 404
    assert student.post(f"/api/my-activities/{assignment_id}/submit", json=answers).status_code == 404
    dashboard = student.get("/api/dashboard").get_json()
    assert dashboard["classes"][0]["activities"] == 0 and dashboard["to_do"] == 0

    assert open_assignment(teacher, assignment_id).get_json() == {"is_open": True}
    assert [item["id"] for item in student.get("/api/my-activities").get_json()["activities"]] == [assignment_id]
    assert student.put(f"/api/my-activities/{assignment_id}/answers", json=answers).status_code == 200
    dashboard = student.get("/api/dashboard").get_json()
    assert dashboard["classes"][0]["activities"] == 1 and dashboard["to_do"] == 1


def test_closing_hides_it_and_opening_again_brings_back_saved_answers(teacher):
    _, assignment_id, students, questions = assigned_sheet(teacher)
    assert open_assignment(teacher, assignment_id).status_code == 200
    student = login(students[0]["username"])
    assert student.put(f"/api/my-activities/{assignment_id}/answers",
                       json={"answers": {str(questions[0]): 1}}).status_code == 200

    assert open_assignment(teacher, assignment_id, False).get_json() == {"is_open": False}
    assert student.get(f"/api/my-activities/{assignment_id}").status_code == 404

    assert open_assignment(teacher, assignment_id).status_code == 200
    detail = student.get(f"/api/my-activities/{assignment_id}").get_json()["activity"]
    assert detail["answers"][str(questions[0])] == 1


def test_closing_after_a_submission_hides_it_from_the_student_only(teacher):
    _, assignment_id, students, _ = assigned_sheet(teacher)
    assert open_assignment(teacher, assignment_id).status_code == 200
    student = login(students[0]["username"])
    assert student.post(f"/api/my-activities/{assignment_id}/submit", json={"answers": {}}).status_code == 200

    assert open_assignment(teacher, assignment_id, False).status_code == 200
    assert student.get("/api/my-activities").get_json()["activities"] == []
    results = teacher.get(f"/api/assignments/{assignment_id}/results").get_json()
    assert results["summary"]["submitted"] == 1

    assert open_assignment(teacher, assignment_id).status_code == 200
    seen = student.get("/api/my-activities").get_json()["activities"]
    assert [(item["id"], item["status"]) for item in seen] == [(assignment_id, "submitted")]


def test_one_sheet_can_be_open_for_one_class_and_closed_for_another(teacher):
    first_class, first_students = make_class(teacher)
    second_class, second_students = make_class(teacher, name="Grade 9 - Bonifacio", section="Bonifacio")
    activity_id, _ = make_activity(teacher)
    given = teacher.put(f"/api/activities/{activity_id}/assignments", json={"assignments": [
        {"class_id": first_class, "everyone": True}, {"class_id": second_class, "everyone": True}]}).get_json()
    ids = {item["id"]: item["assignment"]["id"] for item in given["classes"]}
    assert open_assignment(teacher, ids[first_class]).status_code == 200

    assert len(login(first_students[0]["username"]).get("/api/my-activities").get_json()["activities"]) == 1
    assert login(second_students[0]["username"]).get("/api/my-activities").get_json()["activities"] == []
    listed = teacher.get("/api/activities").get_json()["activities"][0]
    assert (listed["assigned"], listed["open"]) == (2, 1)


def test_the_check_card_shows_whether_each_assignment_is_open(teacher):
    _, assignment_id, _, _ = assigned_sheet(teacher)
    card = lambda: teacher.get("/api/results/to-check").get_json()["assignments"][0]["is_open"]
    assert card() is False
    open_assignment(teacher, assignment_id)
    assert card() is True


def test_open_close_rules(teacher, other_teacher):
    _, assignment_id, students, _ = assigned_sheet(teacher)
    assert open_assignment(other_teacher, assignment_id).status_code == 404
    response = teacher.put(f"/api/assignments/{assignment_id}/open", json={"open": "yes"})
    assert response.status_code == 400 and error(response) == "Choose whether to open the activity."
    assert open_assignment(login(students[0]["username"]), assignment_id).status_code == 403


def test_teacher_dashboard_counts_open_and_closed_assignments(teacher):
    class_id, _ = make_class(teacher)
    first, _ = make_activity(teacher)
    second, _ = make_activity(teacher, title="Second")
    first_assignment = assign(teacher, first, class_id, opened=False)
    assign(teacher, second, class_id, opened=False)
    counts = lambda: {key: teacher.get("/api/dashboard").get_json()[key] for key in ("open", "closed")}
    assert counts() == {"open": 0, "closed": 2}
    assert open_assignment(teacher, first_assignment).status_code == 200
    assert counts() == {"open": 1, "closed": 1}


def test_migration_keeps_what_was_visible_and_runs_once(app, teacher):
    from myguro.database import get_db, init_db

    class_id, _ = make_class(teacher)
    shown, _ = make_activity(teacher, title="Shown")
    hidden, _ = make_activity(teacher, title="Hidden")
    shown_assignment = assign(teacher, shown, class_id, opened=False)
    hidden_assignment = assign(teacher, hidden, class_id, opened=False)

    with app.app_context():
        db = get_db()
        # The database as it was before: a sheet-level published flag and no is_open on assignments
        db.execute("ALTER TABLE activities ADD COLUMN published INTEGER NOT NULL DEFAULT 0")
        db.execute("UPDATE activities SET published = 1 WHERE id = ?", (shown,))
        db.execute("ALTER TABLE assignments DROP COLUMN is_open")
        db.commit()

        init_db()  # the upgrade under test
        rows = {row["id"]: row["is_open"] for row in db.execute("SELECT id, is_open FROM assignments")}
        assert rows == {shown_assignment: 1, hidden_assignment: 0}

        # A teacher's later Close must survive the app starting again.
        db.execute("UPDATE assignments SET is_open = 0 WHERE id = ?", (shown_assignment,))
        db.commit()
        init_db()
        assert db.execute("SELECT is_open FROM assignments WHERE id = ?", (shown_assignment,)).fetchone()[0] == 0
