"""Students: list, answering (saved as they go), submitting, checking, attempts."""

import json

from conftest import assign, error, login, make_activity, make_class


def setup(teacher, release=True, **assign_options):
    class_id, students = make_class(teacher)
    activity_id, questions = make_activity(teacher)
    assignment_id = assign(teacher, activity_id, class_id, **assign_options)
    if release:
        assert teacher.put(f"/api/assignments/{assignment_id}/release", json={"released": True}).status_code == 200
    return assignment_id, activity_id, questions, students


def test_sheet_has_no_answer_keys(teacher):
    assignment_id, _, _, students = setup(teacher)
    student = login(students[0]["username"])
    sheet = student.get(f"/api/my-activities/{assignment_id}").get_json()["activity"]
    text = json.dumps(sheet)
    assert "Daoism" not in text and "key points" not in text and '"answer"' not in text
    assert sheet["sections"][1]["questions"][3]["blanks"] == 2


def test_save_as_you_go(teacher):
    assignment_id, _, q, students = setup(teacher, due_date="2026-10-20")
    student = login(students[0]["username"])
    put = lambda answers: student.put(f"/api/my-activities/{assignment_id}/answers", json={"answers": answers})
    assert put({str(q[0]): 1, str(q[2]): "  taoism ", str(q[3]): ["India", ""]}).status_code == 200
    assert error(put({str(q[0]): 9})) == "An answer is not valid."
    assert error(put({str(q[1]): "false"})) == "An answer is not valid."
    assert put({"99999": "ignored"}).status_code == 200
    assert put({str(q[0]): None}).status_code == 200
    saved = student.get(f"/api/my-activities/{assignment_id}").get_json()["activity"]["answers"]
    assert saved == {str(q[2]): "taoism", str(q[3]): ["India", ""]}
    listed = student.get("/api/my-activities").get_json()["activities"][0]
    assert listed["status"] == "in_progress" and listed["due_date"] == "2026-10-20"


def test_submit_checks_answers(teacher):
    assignment_id, activity_id, q, students = setup(teacher)
    student = login(students[0]["username"])
    response = student.post(f"/api/my-activities/{assignment_id}/submit", json={"answers": {
        str(q[0]): 1, str(q[1]): True, str(q[2]): "DAOISM", str(q[3]): ["india", "Japan"], str(q[4]): "Because"}})
    activity = response.get_json()["activity"]
    # MC 1 + identification 2 + 1 of 2 blanks = 1; short answer (5) waits for the teacher
    assert activity["score"]["total"] == {"earned": 4, "pending": 5, "possible": 11}
    assert activity["late"] is False and activity["can_retry"] is False
    # The submitted sheet is shown blank: questions stay, the student's answers are not sent back
    assert activity["answers"] == {} and activity["sections"][1]["questions"]
    assert student.get(f"/api/my-activities/{assignment_id}").get_json()["activity"]["answers"] == {}
    assert error(student.post(f"/api/my-activities/{assignment_id}/submit", json={"answers": {}})) == \
        "You already submitted this activity."
    assert student.get("/api/dashboard").get_json()["submitted"] == 1
    # The sheet is locked for the teacher now
    assert teacher.get(f"/api/activities/{activity_id}").get_json()["activity"]["locked"] is True
    assert teacher.put(f"/api/activities/{activity_id}", json={"title": "x", "sections": []}).status_code == 400
    assert teacher.put(f"/api/activities/{activity_id}/assignments", json={"assignments": []}).status_code == 400


def test_late_and_overdue(teacher):
    assignment_id, _, _, students = setup(teacher, due_date="2020-01-01")
    student = login(students[0]["username"])
    assert student.get("/api/my-activities").get_json()["activities"][0]["overdue"] is True
    activity = student.post(f"/api/my-activities/{assignment_id}/submit", json={"answers": {}}).get_json()["activity"]
    assert activity["late"] is True and activity["score"]["total"]["earned"] == 0


def test_attempts_latest_counts(teacher):
    assignment_id, activity_id, q, students = setup(teacher)
    teacher.put(f"/api/activities/{activity_id}/settings", json={"max_attempts": 3})
    student = login(students[0]["username"])
    submit = lambda answers: student.post(f"/api/my-activities/{assignment_id}/submit",
                                          json={"answers": answers}).get_json()["activity"]
    assert submit({str(q[0]): 0})["can_retry"] is True
    retry = student.post(f"/api/my-activities/{assignment_id}/retry").get_json()["activity"]
    assert retry["attempt"] == 2 and retry["answers"] == {str(q[0]): 0}  # last answers copied
    assert error(student.post(f"/api/my-activities/{assignment_id}/retry")) == "Submit this activity first."
    assert submit({str(q[0]): 1})["score"]["total"]["earned"] == 1
    student.post(f"/api/my-activities/{assignment_id}/retry")
    last = submit({str(q[0]): 0})
    assert last["score"]["total"]["earned"] == 0  # the latest counts, even if lower
    assert last["can_retry"] is False
    assert error(student.post(f"/api/my-activities/{assignment_id}/retry")) == \
        "You have used all your tries for this activity."


def test_students_outside_the_class_cannot_open(teacher):
    assignment_id, _, _, _ = setup(teacher)
    outsider = login("ksantos08")  # Grade 9 - Bonifacio
    assert outsider.get(f"/api/my-activities/{assignment_id}").status_code == 404
    assert teacher.get("/api/my-activities").status_code == 403


def test_score_hidden_until_teacher_releases(teacher, other_teacher):
    assignment_id, _, q, students = setup(teacher, release=False)
    student = login(students[0]["username"])
    submitted = student.post(f"/api/my-activities/{assignment_id}/submit",
                            json={"answers": {str(q[0]): 1, str(q[2]): "Daoism"}}).get_json()["activity"]
    assert submitted["submitted_at"] and submitted["score"] is None and submitted["scores_released"] is False
    listed = student.get("/api/my-activities").get_json()["activities"][0]
    assert listed["done"] is True and listed["score"] is None
    assert student.get("/api/dashboard").get_json()["to_do"] == 0
    # The teacher still sees the score
    results = teacher.get(f"/api/assignments/{assignment_id}/results").get_json()
    assert results["assignment"]["scores_released"] is False
    assert results["summary"]["average"] is not None

    # Only the teacher of the activity can release, with a true / false
    assert other_teacher.put(f"/api/assignments/{assignment_id}/release", json={"released": True}).status_code == 404
    assert student.put(f"/api/assignments/{assignment_id}/release", json={"released": True}).status_code == 403
    assert error(teacher.put(f"/api/assignments/{assignment_id}/release", json={"released": "yes"})) == \
        "Choose whether to release the scores."

    assert teacher.put(f"/api/assignments/{assignment_id}/release", json={"released": True}).get_json() == \
        {"scores_released": True}
    shown = student.get(f"/api/my-activities/{assignment_id}").get_json()["activity"]
    assert shown["score"]["total"]["earned"] == 3 and shown["scores_released"] is True
    teacher.put(f"/api/assignments/{assignment_id}/release", json={"released": False})
    assert student.get(f"/api/my-activities/{assignment_id}").get_json()["activity"]["score"] is None
