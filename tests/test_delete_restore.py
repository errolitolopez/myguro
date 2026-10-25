"""Teacher: deleting an assigned activity archives it (students lose access, work is kept) and restore."""

from conftest import assign, error, login, make_activity, make_class, open_assignment


def assigned_sheet(teacher):
    class_id, students = make_class(teacher)
    activity_id, questions = make_activity(teacher)
    return class_id, activity_id, assign(teacher, activity_id, class_id), students, questions


def listed(teacher, deleted=False):
    url = "/api/activities?deleted=1" if deleted else "/api/activities"
    return [item["id"] for item in teacher.get(url).get_json()["activities"]]


def test_deleting_an_unassigned_sheet_really_deletes_it(teacher):
    activity_id, _ = make_activity(teacher)
    response = teacher.delete(f"/api/activities/{activity_id}")
    assert response.status_code == 200 and response.get_json()["archived"] is False
    assert listed(teacher) == [] and listed(teacher, deleted=True) == []
    assert teacher.post(f"/api/activities/{activity_id}/restore").status_code == 404


def test_deleting_an_assigned_sheet_archives_it(teacher):
    class_id, activity_id, assignment_id, students, _ = assigned_sheet(teacher)
    student = login(students[0]["username"])
    assert len(student.get("/api/my-activities").get_json()["activities"]) == 1

    response = teacher.delete(f"/api/activities/{activity_id}")
    assert response.status_code == 200 and response.get_json()["archived"] is True

    assert student.get("/api/my-activities").get_json()["activities"] == []
    assert student.get(f"/api/my-activities/{assignment_id}").status_code == 404
    assert student.get("/api/dashboard").get_json()["to_do"] == 0
    assert listed(teacher) == [] and listed(teacher, deleted=True) == [activity_id]
    assert teacher.get(f"/api/classes/{class_id}").get_json()["activities"] == []
    assert teacher.get(f"/api/activities/{activity_id}").status_code == 404
    assert teacher.get(f"/api/activities/{activity_id}/assignments").status_code == 404
    assert teacher.get(f"/api/assignments/{assignment_id}/results").status_code == 404
    counts = teacher.get("/api/dashboard").get_json()
    assert (counts["open"], counts["closed"]) == (0, 0)
    classes = teacher.get("/api/classes").get_json()["classes"]
    assert [item["activities"] for item in classes] == [0]


def test_restore_brings_back_not_started_with_the_students_work(teacher):
    class_id, activity_id, assignment_id, students, questions = assigned_sheet(teacher)
    student = login(students[0]["username"])
    other = login(students[1]["username"])
    assert student.post(f"/api/my-activities/{assignment_id}/submit", json={"answers": {}}).status_code == 200
    assert other.put(f"/api/my-activities/{assignment_id}/answers",
                     json={"answers": {str(questions[0]): 1}}).status_code == 200

    assert teacher.delete(f"/api/activities/{activity_id}").get_json()["archived"] is True  # even though submitted
    restored = teacher.post(f"/api/activities/{activity_id}/restore").get_json()["activity"]
    assert restored["statuses"] == {"not_started": 1, "open": 0, "closed": 0} and restored["id"] == activity_id
    assert listed(teacher) == [activity_id] and listed(teacher, deleted=True) == []
    assert student.get("/api/my-activities").get_json()["activities"] == []  # not started again

    assert open_assignment(teacher, assignment_id).status_code == 200
    seen = student.get("/api/my-activities").get_json()["activities"]
    assert [(item["id"], item["status"]) for item in seen] == [(assignment_id, "submitted")]
    detail = other.get(f"/api/my-activities/{assignment_id}").get_json()["activity"]
    assert detail["answers"][str(questions[0])] == 1
    assert teacher.get(f"/api/assignments/{assignment_id}/results").get_json()["summary"]["submitted"] == 1


def test_delete_and_restore_rules(teacher, other_teacher):
    _, activity_id, _, students, _ = assigned_sheet(teacher)
    assert other_teacher.delete(f"/api/activities/{activity_id}").status_code == 404
    assert other_teacher.post(f"/api/activities/{activity_id}/restore").status_code == 404
    # A sheet that is not deleted cannot be "restored"
    response = teacher.post(f"/api/activities/{activity_id}/restore")
    assert response.status_code == 404 and error(response) == "Activity not found."
    assert teacher.delete(f"/api/activities/{activity_id}").status_code == 200
    assert other_teacher.post(f"/api/activities/{activity_id}/restore").status_code == 404
    assert login(students[0]["username"]).post(f"/api/activities/{activity_id}/restore").status_code == 403
    assert teacher.delete(f"/api/activities/{activity_id}").status_code == 404  # already deleted


def test_migration_adds_deleted_at(app, teacher):
    from myguro.database import get_db, init_db

    activity_id, _ = make_activity(teacher)
    with app.app_context():
        db = get_db()
        db.execute("ALTER TABLE activities DROP COLUMN deleted_at")
        db.commit()
        init_db()
        row = db.execute("SELECT id, deleted_at FROM activities WHERE id = ?", (activity_id,)).fetchone()
        assert (row["id"], row["deleted_at"]) == (activity_id, None)
