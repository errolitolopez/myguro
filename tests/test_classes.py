"""Teacher: classes and adding students from the school list."""

from conftest import error, login, make_class


def test_create_and_edit_class(teacher):
    created = teacher.post("/api/classes", json={"name": " Grade 9  - Rizal ", "subject": "Science"})
    assert created.status_code == 201
    class_id = created.get_json()["class"]["id"]
    assert error(teacher.post("/api/classes", json={"name": "grade 9 - rizal", "subject": "science"})) == \
        "You already have a class with this name and subject."
    assert teacher.post("/api/classes", json={"name": "Grade 9 - Rizal", "subject": "Math"}).status_code == 201
    assert error(teacher.post("/api/classes", json={"subject": "x"})) == "Class name is required."
    assert teacher.put(f"/api/classes/{class_id}", json={"name": "Grade 9 - Rizal", "subject": "Science"}) \
        .status_code == 200


def test_classes_are_private(teacher, other_teacher):
    class_id, _ = make_class(teacher)
    assert other_teacher.get(f"/api/classes/{class_id}").status_code == 404
    assert other_teacher.put(f"/api/classes/{class_id}", json={"name": "x"}).status_code == 404
    assert other_teacher.get(f"/classes/{class_id}").headers["Location"].endswith("/classes")


def test_search_filters_and_add_all(teacher):
    class_id = teacher.post("/api/classes", json={"name": "C"}).get_json()["class"]["id"]
    data = teacher.get(f"/api/classes/{class_id}/student-search?grade=Grade+9&section=rizal").get_json()
    assert len(data["students"]) == 6 and all(s["section"] == "Rizal" for s in data["students"])
    assert {"grade": "Grade 12", "section": "ABM"} in data["sections"]
    ids = [student["id"] for student in data["students"]]
    assert len(teacher.post(f"/api/classes/{class_id}/students", json={"student_ids": ids}).get_json()["added"]) == 6
    assert teacher.post(f"/api/classes/{class_id}/students", json={"student_ids": ids}).get_json()["added"] == []
    assert error(teacher.post(f"/api/classes/{class_id}/students", json={"student_id": ids[0]})) == \
        "This student is already in the class."
    again = teacher.get(f"/api/classes/{class_id}/student-search?q=rizal").get_json()["students"]
    assert all(student["in_class"] for student in again if student["section"] == "Rizal" and student["grade"] == "Grade 9")
    assert teacher.post(f"/api/classes/{class_id}/students", json={"student_ids": []}).status_code == 400


def test_search_escapes_wildcards(teacher):
    class_id = teacher.post("/api/classes", json={"name": "C"}).get_json()["class"]["id"]
    assert teacher.get(f"/api/classes/{class_id}/student-search?q=%25").get_json()["students"] == []


def test_remove_student(teacher):
    class_id, students = make_class(teacher)
    student_id = students[0]["id"]
    assert teacher.delete(f"/api/classes/{class_id}/students/{student_id}").status_code == 200
    assert teacher.delete(f"/api/classes/{class_id}/students/{student_id}").status_code == 404
    assert len(teacher.get(f"/api/classes/{class_id}").get_json()["students"]) == 5


def test_batch_remove_students(teacher, other_teacher):
    class_id, students = make_class(teacher)
    ids = [student["id"] for student in students]
    url = f"/api/classes/{class_id}/students/remove"
    assert error(teacher.post(url, json={"student_ids": []})) == "Choose at least one student."
    assert error(teacher.post(url, json={"student_ids": "1"})) == "Choose at least one student."
    assert other_teacher.post(url, json={"student_ids": ids}).status_code == 404
    assert teacher.post(url, json={"student_ids": ids[:3] + [999999, "x"]}).get_json()["removed"] == 3
    assert teacher.post(url, json={"student_ids": ids[:3]}).get_json()["removed"] == 0
    remaining = teacher.get(f"/api/classes/{class_id}").get_json()["students"]
    assert [student["id"] for student in remaining] == ids[3:]


def test_students_and_admin_cannot_use_classes(admin):
    assert admin.get("/api/classes").status_code == 403
    assert login("jdelacruz01").get("/api/classes").status_code == 403


def test_student_dashboard_lists_classes(teacher):
    make_class(teacher)
    student = login("jdelacruz01").get("/api/dashboard").get_json()
    assert [c["name"] for c in student["classes"]] == ["Grade 9 - Rizal"]
    assert student["classes"][0]["teacher"] == "Cruz, Elena M."
