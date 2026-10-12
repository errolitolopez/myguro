"""Teacher: giving a sheet to classes (everyone or selected students, due date)."""

from conftest import assign, error, login, make_activity, make_class


def test_assign_everyone_and_selected(teacher):
    rizal_id, rizal = make_class(teacher)
    bonifacio_id, bonifacio = make_class(teacher, name="Grade 9 - Bonifacio", section="Bonifacio")
    activity_id, _ = make_activity(teacher)
    response = teacher.put(f"/api/activities/{activity_id}/assignments", json={"assignments": [
        {"class_id": rizal_id, "due_date": "2026-10-15"},
        {"class_id": bonifacio_id, "everyone": False, "student_ids": [bonifacio[0]["id"], bonifacio[1]["id"]]},
    ]})
    classes = {item["id"]: item["assignment"] for item in response.get_json()["classes"]}
    assert classes[rizal_id]["due_date"] == "2026-10-15" and classes[rizal_id]["everyone"] is True
    assert sorted(classes[bonifacio_id]["student_ids"]) == sorted([bonifacio[0]["id"], bonifacio[1]["id"]])
    assert teacher.get("/api/activities").get_json()["activities"][0]["assigned"] == 2
    # Only chosen students see it
    seen = lambda username: login(username).get("/api/my-activities").get_json()["activities"]
    assert len(seen(rizal[0]["username"])) == 1
    assert len(seen(bonifacio[0]["username"])) == 1
    assert len(seen(bonifacio[2]["username"])) == 0


def test_assignment_ids_stay_when_changed(teacher):
    class_id, _ = make_class(teacher)
    activity_id, _ = make_activity(teacher)
    first = assign(teacher, activity_id, class_id, due_date="2026-10-15")
    second = assign(teacher, activity_id, class_id)
    assert first == second


def test_assignment_rules(teacher, other_teacher):
    class_id, students = make_class(teacher)
    other_class = other_teacher.post("/api/classes", json={"name": "Other"}).get_json()["class"]["id"]
    activity_id, _ = make_activity(teacher)
    put = lambda items: teacher.put(f"/api/activities/{activity_id}/assignments", json={"assignments": items})
    assert error(put({})) == "Assignments must be a list."
    assert error(put([{"class_id": other_class}])) == "Class not found."
    assert error(put([{"class_id": class_id, "due_date": "2026-13-40"}])).endswith("the due date is not valid.")
    assert error(put([{"class_id": class_id, "everyone": False, "student_ids": []}])).endswith(
        "choose at least one student, or give it to everyone.")
    assert error(put([{"class_id": class_id}, {"class_id": class_id}])) == "A class is listed twice."


def test_class_page_lists_assignment_and_unassign(teacher):
    class_id, _ = make_class(teacher)
    activity_id, _ = make_activity(teacher)
    assignment_id = assign(teacher, activity_id, class_id, due_date="2026-10-15")
    activities = teacher.get(f"/api/classes/{class_id}").get_json()["activities"]
    assert activities[0]["id"] == assignment_id and activities[0]["due_date"] == "2026-10-15"
    # Deleting an assigned sheet archives it (students lose access, work is kept)
    assert teacher.delete(f"/api/activities/{activity_id}").get_json()["archived"] is True
    assert teacher.post(f"/api/activities/{activity_id}/restore").status_code == 200
    assert teacher.put(f"/api/activities/{activity_id}/assignments", json={"assignments": []}).status_code == 200
    assert teacher.get("/api/activities").get_json()["activities"][0]["assigned"] == 0


def test_removing_student_from_class_drops_selected_assignment(teacher):
    class_id, students = make_class(teacher)
    activity_id, _ = make_activity(teacher)
    assign(teacher, activity_id, class_id, everyone=False, student_ids=[students[0]["id"], students[1]["id"]])
    teacher.delete(f"/api/classes/{class_id}/students/{students[0]['id']}")
    item = teacher.get(f"/api/activities/{activity_id}/assignments").get_json()["classes"][0]["assignment"]
    assert item["student_ids"] == [students[1]["id"]]
