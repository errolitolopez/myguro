"""Teacher: starting an assignment (Open), closing it and re-opening it. Students answer only while it is open."""

from conftest import assign, error, login, make_activity, make_class, open_assignment, set_status


def assigned_sheet(teacher):
    """A sheet given to a class, still not started (a new assignment starts that way)."""
    class_id, students = make_class(teacher)
    activity_id, questions = make_activity(teacher)
    return activity_id, assign(teacher, activity_id, class_id, opened=False), students, questions


def status_of(teacher, assignment_id):
    return teacher.get(f"/api/assignments/{assignment_id}/results").get_json()["assignment"]["status"]


def student_detail(student, assignment_id):
    return student.get(f"/api/my-activities/{assignment_id}").get_json()["activity"]


def test_a_new_assignment_starts_not_started_and_copies_are_not_given_to_anyone(teacher):
    activity_id, assignment_id, _, _ = assigned_sheet(teacher)
    assert status_of(teacher, assignment_id) == "not_started"
    listed = teacher.get("/api/activities").get_json()["activities"][0]
    assert listed["assigned"] == 1 and listed["statuses"] == {"not_started": 1, "open": 0, "closed": 0}
    copy = teacher.post(f"/api/activities/{activity_id}/duplicate").get_json()["activity"]
    assert copy["assigned"] == 0 and copy["statuses"] == {"not_started": 0, "open": 0, "closed": 0}


def test_students_see_an_assignment_only_after_it_is_opened(teacher):
    _, assignment_id, students, questions = assigned_sheet(teacher)
    student = login(students[0]["username"])
    answers = {"answers": {str(questions[0]): 1}}

    assert student.get("/api/my-activities").get_json()["activities"] == []
    assert student.get(f"/api/my-activities/{assignment_id}").status_code == 404
    assert student.put(f"/api/my-activities/{assignment_id}/answers", json=answers).status_code == 404
    assert student.post(f"/api/my-activities/{assignment_id}/submit", json=answers).status_code == 404
    dashboard = student.get("/api/dashboard").get_json()
    assert dashboard["classes"][0]["activities"] == 0 and dashboard["to_do"] == 0

    assert open_assignment(teacher, assignment_id).get_json() == {"status": "open", "changed": 0}
    assert [item["id"] for item in student.get("/api/my-activities").get_json()["activities"]] == [assignment_id]
    assert student.put(f"/api/my-activities/{assignment_id}/answers", json=answers).status_code == 200
    dashboard = student.get("/api/dashboard").get_json()
    assert dashboard["classes"][0]["activities"] == 1 and dashboard["to_do"] == 1


def test_close_submits_everyone_and_students_can_only_read(teacher):
    _, assignment_id, students, questions = assigned_sheet(teacher)
    open_assignment(teacher, assignment_id)
    finished, unfinished, never = (login(students[index]["username"]) for index in range(3))
    finished.post(f"/api/my-activities/{assignment_id}/submit", json={"answers": {str(questions[0]): 1}})
    unfinished.put(f"/api/my-activities/{assignment_id}/answers", json={"answers": {str(questions[0]): 1}})

    closed = set_status(teacher, assignment_id, "closed").get_json()
    total = len(students)
    assert closed["status"] == "closed" and closed["changed"] == total - 1  # everyone but the one who submitted

    results = teacher.get(f"/api/assignments/{assignment_id}/results").get_json()
    rows = {row["id"]: row for row in results["students"]}
    assert all(row["status"] == "submitted" for row in rows.values())
    assert not any(row["late"] for row in rows.values())  # a close is never late
    assert rows[students[1]["id"]]["score"]["earned"] == 1  # what was saved is scored
    assert rows[students[2]["id"]]["score"]["earned"] == 0  # never started: nothing answered

    # Students still see it, marked closed, but cannot answer, submit or try again
    seen = unfinished.get("/api/my-activities").get_json()["activities"]
    assert [(item["id"], item["closed"], item["status"], item["can_retry"]) for item in seen] == [
        (assignment_id, True, "submitted", False)]
    assert student_detail(never, assignment_id)["closed"] is True
    assert student_detail(unfinished, assignment_id)["sections"]  # the questions can be read again
    for response in (unfinished.put(f"/api/my-activities/{assignment_id}/answers", json={"answers": {}}),
                     never.post(f"/api/my-activities/{assignment_id}/submit", json={"answers": {}}),
                     finished.post(f"/api/my-activities/{assignment_id}/retry")):
        assert response.status_code == 400 and "closed" in error(response)


def test_students_see_their_answers_after_a_close_only_once_scores_are_released(teacher):
    _, assignment_id, students, questions = assigned_sheet(teacher)
    open_assignment(teacher, assignment_id)
    student = login(students[0]["username"])
    student.put(f"/api/my-activities/{assignment_id}/answers", json={"answers": {str(questions[0]): 1}})
    set_status(teacher, assignment_id, "closed")

    hidden = student_detail(student, assignment_id)
    assert hidden["answers"] == {} and hidden["score"] is None
    assert not any("answer" in question for section in hidden["sections"] for question in section["questions"])  # no key
    teacher.put(f"/api/assignments/{assignment_id}/release", json={"released": True})
    shown = student_detail(student, assignment_id)
    assert shown["answers"][str(questions[0])] == 1 and shown["score"] is not None


def test_reopen_puts_unfinished_work_back_and_keeps_submitted_work(teacher):
    _, assignment_id, students, questions = assigned_sheet(teacher)
    open_assignment(teacher, assignment_id)
    finished, unfinished, never = (login(students[index]["username"]) for index in range(3))
    finished.post(f"/api/my-activities/{assignment_id}/submit", json={"answers": {str(questions[0]): 1}})
    unfinished.put(f"/api/my-activities/{assignment_id}/answers", json={"answers": {str(questions[0]): 0}})
    set_status(teacher, assignment_id, "closed")

    reopened = open_assignment(teacher, assignment_id).get_json()
    assert reopened == {"status": "open", "changed": len(students) - 1}

    # The one who submitted on their own stays submitted
    assert student_detail(finished, assignment_id)["submitted_at"]
    # The unfinished student continues with the answers they really wrote, and can submit
    detail = student_detail(unfinished, assignment_id)
    assert detail["submitted_at"] is None and detail["closed"] is False and detail["answers"] == {str(questions[0]): 0}
    assert unfinished.post(f"/api/my-activities/{assignment_id}/submit", json={"answers": {}}).status_code == 200
    # The one who never started can start from nothing
    detail = student_detail(never, assignment_id)
    assert detail["submitted_at"] is None and detail["answers"] == {}
    assert never.put(f"/api/my-activities/{assignment_id}/answers",
                     json={"answers": {str(questions[0]): 1}}).status_code == 200
    results = teacher.get(f"/api/assignments/{assignment_id}/results").get_json()
    rows = {row["id"]: row["status"] for row in results["students"]}
    assert rows[students[0]["id"]] == "submitted" and rows[students[1]["id"]] == "submitted"
    assert rows[students[2]["id"]] == "in_progress" and rows[students[3]["id"]] == "not_started"


def test_a_student_added_after_the_close_can_only_read(teacher):
    class_id, _ = make_class(teacher)
    activity_id, questions = make_activity(teacher)
    assignment_id = assign(teacher, activity_id, class_id)
    set_status(teacher, assignment_id, "closed")
    late_student = make_class(teacher, name="Another", section="Bonifacio")[1][0]
    assert teacher.post(f"/api/classes/{class_id}/students", json={"student_id": late_student["id"]}).status_code == 201

    student = login(late_student["username"])
    detail = student_detail(student, assignment_id)
    assert detail["closed"] is True and detail["submitted_at"] is None and detail["sections"]
    response = student.put(f"/api/my-activities/{assignment_id}/answers", json={"answers": {str(questions[0]): 1}})
    assert response.status_code == 400 and "closed" in error(response)


def test_the_status_rules(teacher, other_teacher):
    _, assignment_id, students, _ = assigned_sheet(teacher)
    # A not started assignment can't be closed; unknown values and other teachers are refused
    response = set_status(teacher, assignment_id, "closed")
    assert response.status_code == 400 and error(response) == "Open the activity before closing it."
    response = set_status(teacher, assignment_id, "paused")
    assert response.status_code == 400 and error(response) == "Choose open or closed."
    assert set_status(other_teacher, assignment_id, "open").status_code == 404
    assert set_status(login(students[0]["username"]), assignment_id, "open").status_code == 403
    # Doing the same thing twice changes nothing
    assert set_status(teacher, assignment_id, "open").status_code == 200
    assert set_status(teacher, assignment_id, "open").get_json() == {"status": "open", "changed": 0}


def test_another_try_needs_the_activity_to_be_open(teacher):
    _, assignment_id, students, _ = assigned_sheet(teacher)
    open_assignment(teacher, assignment_id)
    student = login(students[0]["username"])
    student.post(f"/api/my-activities/{assignment_id}/submit", json={"answers": {}})
    set_status(teacher, assignment_id, "closed")
    response = teacher.post(f"/api/assignments/{assignment_id}/students/{students[0]['id']}/reopen")
    assert response.status_code == 400 and "Open the activity first" in error(response)
    open_assignment(teacher, assignment_id)
    assert teacher.post(f"/api/assignments/{assignment_id}/students/{students[0]['id']}/reopen").status_code == 200


def test_one_sheet_can_have_a_different_status_for_each_class(teacher):
    first_class, first_students = make_class(teacher)
    second_class, second_students = make_class(teacher, name="Grade 9 - Bonifacio", section="Bonifacio")
    activity_id, _ = make_activity(teacher)
    given = teacher.put(f"/api/activities/{activity_id}/assignments", json={"assignments": [
        {"class_id": first_class, "everyone": True}, {"class_id": second_class, "everyone": True}]}).get_json()
    ids = {item["id"]: item["assignment"]["id"] for item in given["classes"]}
    open_assignment(teacher, ids[first_class])

    assert len(login(first_students[0]["username"]).get("/api/my-activities").get_json()["activities"]) == 1
    assert login(second_students[0]["username"]).get("/api/my-activities").get_json()["activities"] == []
    listed = teacher.get("/api/activities").get_json()["activities"][0]
    assert listed["statuses"] == {"not_started": 1, "open": 1, "closed": 0}
    set_status(teacher, ids[first_class], "closed")
    assert teacher.get("/api/activities").get_json()["activities"][0]["statuses"] == \
        {"not_started": 1, "open": 0, "closed": 1}


def test_the_check_card_shows_the_status_of_each_assignment(teacher):
    _, assignment_id, _, _ = assigned_sheet(teacher)
    card = lambda: teacher.get("/api/results/to-check").get_json()["assignments"][0]["status"]
    assert card() == "not_started"
    open_assignment(teacher, assignment_id)
    assert card() == "open"
    set_status(teacher, assignment_id, "closed")
    assert card() == "closed"


def test_teacher_dashboard_counts_each_status(teacher):
    class_id, _ = make_class(teacher)
    first, _ = make_activity(teacher)
    second, _ = make_activity(teacher, title="Second")
    third, _ = make_activity(teacher, title="Third")
    first_assignment = assign(teacher, first, class_id, opened=False)
    second_assignment = assign(teacher, second, class_id, opened=False)
    assign(teacher, third, class_id, opened=False)
    counts = lambda: {key: teacher.get("/api/dashboard").get_json()[key] for key in ("not_started", "open", "closed")}
    assert counts() == {"not_started": 3, "open": 0, "closed": 0}
    open_assignment(teacher, first_assignment)
    open_assignment(teacher, second_assignment)
    set_status(teacher, second_assignment, "closed")
    assert counts() == {"not_started": 1, "open": 1, "closed": 1}


def test_migration_keeps_what_was_visible_and_runs_once(app, teacher):
    from myguro.database import get_db, init_db

    class_id, _ = make_class(teacher)
    shown, _ = make_activity(teacher, title="Shown")
    hidden, _ = make_activity(teacher, title="Hidden")
    shown_assignment = assign(teacher, shown, class_id, opened=False)
    hidden_assignment = assign(teacher, hidden, class_id, opened=False)

    with app.app_context():
        db = get_db()
        # The database as it was before: a sheet-level published flag and no status on assignments
        db.execute("ALTER TABLE activities ADD COLUMN published INTEGER NOT NULL DEFAULT 0")
        db.execute("UPDATE activities SET published = 1 WHERE id = ?", (shown,))
        db.execute("ALTER TABLE assignments DROP COLUMN status")
        db.commit()

        init_db()  # the upgrade under test
        rows = {row["id"]: row["status"] for row in db.execute("SELECT id, status FROM assignments")}
        assert rows == {shown_assignment: "open", hidden_assignment: "not_started"}

        # A teacher's later Close must survive the app starting again.
        db.execute("UPDATE assignments SET status = 'closed' WHERE id = ?", (shown_assignment,))
        db.commit()
        init_db()
        assert db.execute("SELECT status FROM assignments WHERE id = ?", (shown_assignment,)).fetchone()[0] == "closed"


def test_migration_from_the_open_flag(app, teacher):
    from myguro.database import get_db, init_db

    class_id, _ = make_class(teacher)
    activity_id, _ = make_activity(teacher)
    assignment_id = assign(teacher, activity_id, class_id)  # open

    with app.app_context():
        db = get_db()
        db.execute("ALTER TABLE assignments ADD COLUMN is_open INTEGER NOT NULL DEFAULT 0")  # the previous version
        db.execute("UPDATE assignments SET is_open = 1 WHERE id = ?", (assignment_id,))
        db.execute("ALTER TABLE assignments DROP COLUMN status")
        db.commit()
        init_db()
        assert db.execute("SELECT status FROM assignments WHERE id = ?", (assignment_id,)).fetchone()[0] == "open"
