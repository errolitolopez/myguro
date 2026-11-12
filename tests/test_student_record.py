"""The teacher's Students tab and one student's record: every activity the teacher gave them, with scores."""

from conftest import assign, login, make_activity, make_class


def test_students_list_has_the_teachers_classes(teacher, other_teacher):
    _, students = make_class(teacher)
    listed = teacher.get("/api/my-students").get_json()["students"]
    assert {person["id"] for person in listed} == {person["id"] for person in students}
    assert [person["name"].lower() for person in listed] == sorted(person["name"].lower() for person in listed)
    assert listed[0]["classes"] == ["Grade 9 - Rizal · Philosophy"]
    assert other_teacher.get("/api/my-students").get_json()["students"] == []


def test_record_shows_every_score_released_or_not(teacher):
    class_id, students = make_class(teacher)
    activity_id, q = make_activity(teacher)
    assignment_id = assign(teacher, activity_id, class_id)
    second_id, _ = make_activity(teacher, title="Second quiz")
    assign(teacher, second_id, class_id)
    login(students[0]["username"]).post(f"/api/my-activities/{assignment_id}/submit",
                                        json={"answers": {str(q[0]): 1, str(q[4]): "Because"}})

    data = teacher.get(f"/api/my-students/{students[0]['id']}/record").get_json()
    assert data["student"]["id"] == students[0]["id"]
    record = data["record"]
    assert record["given"] == 2 and record["done"] == 1 and record["to_check"] == 5
    group = record["classes"][0]
    assert group["class_name"] == "Grade 9 - Rizal · Philosophy"
    rows = {row["title"]: row for row in group["activities"]}
    done = rows["Early Eastern Philosophy"]
    # Not released to the student, but the teacher sees it
    assert done["score"]["earned"] == 1 and not done["scores_released"]
    assert rows["Second quiz"]["status"] == "not_started" and rows["Second quiz"]["score"] is None
    assert record["average"] == group["average"] == done["percent"]


def test_excluded_activity_is_left_out_of_the_totals(teacher):
    class_id, students = make_class(teacher)
    activity_id, _ = make_activity(teacher)
    assignment_id = assign(teacher, activity_id, class_id)
    teacher.put(f"/api/assignments/{assignment_id}/students/{students[0]['id']}/excluded", json={"excluded": True})
    record = teacher.get(f"/api/my-students/{students[0]['id']}/record").get_json()["record"]
    assert record["given"] == 0 and record["classes"][0]["activities"][0]["excluded"]


def test_record_is_only_for_the_teachers_own_students(teacher, other_teacher):
    class_id, students = make_class(teacher)
    activity_id, _ = make_activity(teacher)
    assign(teacher, activity_id, class_id)
    # Another teacher sees neither the student nor this teacher's activities
    assert other_teacher.get(f"/api/my-students/{students[0]['id']}/record").status_code == 404
    assert teacher.get("/api/my-students/999999/record").status_code == 404
    assert login(students[0]["username"]).get(f"/api/my-students/{students[0]['id']}/record").status_code == 403
    assert teacher.get("/my-students").status_code == 200
    assert teacher.get(f"/my-students/{students[0]['id']}").status_code == 200
