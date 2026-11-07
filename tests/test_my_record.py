"""The student's record: scores by teacher and subject, only once released."""

from conftest import assign, login, make_activity, make_class


def submit_one(teacher, students, release):
    class_id, students = make_class(teacher)
    activity_id, q = make_activity(teacher)
    assignment_id = assign(teacher, activity_id, class_id)
    student = login(students[0]["username"])
    student.post(f"/api/my-activities/{assignment_id}/submit", json={"answers": {str(q[0]): 1}})
    if release:
        teacher.put(f"/api/assignments/{assignment_id}/release", json={"released": True})
    return student, students, assignment_id


def test_record_shows_released_score_and_average(teacher):
    student, _, assignment_id = submit_one(teacher, None, release=True)
    record = student.get("/api/my-record").get_json()["record"]
    assert record["given"] == 1 and record["done"] == 1
    subject = record["subjects"][0]
    assert subject["subject"] == "Philosophy" and subject["teacher_id"]
    row = subject["activities"][0]
    assert row["id"] == assignment_id and row["score"]["earned"] == 1
    assert subject["average"] == record["average"] == row["percent"]


def test_record_hides_a_score_that_is_not_released(teacher):
    student, _, _ = submit_one(teacher, None, release=False)
    record = student.get("/api/my-record").get_json()["record"]
    row = record["subjects"][0]["activities"][0]
    assert row["done"] and row["score"] is None and row["percent"] is None
    assert record["average"] is None and record["subjects"][0]["average"] is None


def test_record_has_only_the_students_own_activities(teacher):
    student, students, _ = submit_one(teacher, None, release=True)
    other = login(students[-1]["username"])  # same class, nothing submitted
    mine = student.get("/api/my-record").get_json()["record"]
    theirs = other.get("/api/my-record").get_json()["record"]
    assert mine["done"] == 1 and theirs["done"] == 0 and theirs["average"] is None
    assert theirs["subjects"][0]["activities"][0]["score"] is None


def test_record_is_for_students_only(teacher):
    assert teacher.get("/api/my-record").status_code == 403
    assert teacher.get("/my-record").status_code in (302, 403)
    student, _, _ = submit_one(teacher, None, release=True)
    assert student.get("/my-record").status_code == 200
