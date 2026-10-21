"""School years: classes and work belong to a year, the picker, and past years being read-only."""

from conftest import assign, error, login, make_activity, make_class


def start_year(admin, name="2027-2028"):
    response = admin.post("/api/school-years", json={"name": name})
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def test_first_year_exists_and_owns_old_data(teacher):
    class_id, _ = make_class(teacher)
    years = teacher.get("/api/school-years").get_json()
    assert len(years["years"]) == 1 and years["years"][0]["current"] is True
    assert years["viewing_id"] == years["current_id"]
    assert [item["id"] for item in teacher.get("/api/classes").get_json()["classes"]] == [class_id]


def test_new_year_starts_empty_and_old_year_is_read_only(admin, teacher):
    class_id, students = make_class(teacher)
    activity_id, questions = make_activity(teacher)
    assignment_id = assign(teacher, activity_id, class_id)
    teacher.put(f"/api/assignments/{assignment_id}/release", json={"released": True})
    student = login(students[0]["username"])
    student.post(f"/api/my-activities/{assignment_id}/submit", json={"answers": {str(questions[0]): 1}})
    old_id = teacher.get("/api/school-years").get_json()["current_id"]

    years = start_year(admin)
    assert years["years"][0]["name"] == "2027-2028" and years["years"][0]["current"] is True

    # Everyone now looks at the new year: nothing in it yet
    assert teacher.get("/api/classes").get_json()["classes"] == []
    assert student.get("/api/my-activities").get_json()["activities"] == []
    assert student.get("/api/dashboard").get_json()["classes"] == []
    assert teacher.get("/api/dashboard").get_json()["students"] == 0

    # The same class name is fine in the new year
    again = teacher.post("/api/classes", json={"name": "Grade 9 - Rizal", "subject": "Philosophy"})
    assert again.status_code == 201

    # Look at the old year: the class, the work and the results are there...
    assert teacher.put("/api/school-year", json={"id": old_id}).status_code == 200
    assert [item["id"] for item in teacher.get("/api/classes").get_json()["classes"]] == [class_id]
    assert teacher.get(f"/api/assignments/{assignment_id}/results").status_code == 200
    assert student.put("/api/school-year", json={"id": old_id}).status_code == 200
    assert student.get("/api/my-activities").get_json()["activities"][0]["done"] is True

    # ...but nothing can be changed
    over = "This school year is over. You can only look at it."
    assert error(teacher.post("/api/classes", json={"name": "New", "subject": ""})) == over
    assert error(teacher.put(f"/api/classes/{class_id}", json={"name": "Renamed"})) == over
    assert error(teacher.post(f"/api/classes/{class_id}/students", json={"student_id": students[1]["id"]})) == over
    assert error(teacher.put(f"/api/activities/{activity_id}/assignments", json={"assignments": []})) == over
    assert error(teacher.put(f"/api/assignments/{assignment_id}/release", json={"released": False})) == over
    assert error(teacher.post(f"/api/assignments/{assignment_id}/students/{students[0]['id']}/reopen")) == over
    assert error(student.put(f"/api/my-activities/{assignment_id}/answers", json={"answers": {}})) == over
    detail = teacher.get(f"/api/assignments/{assignment_id}/students/{students[0]['id']}").get_json()["detail"]
    assert error(teacher.put(f"/api/submissions/{detail['id']}/points", json={"feedback": {str(questions[0]): "x"}})) \
        == over

    # Choosing the current year again goes back to the default view
    new_id = years["current_id"]
    assert teacher.put("/api/school-year", json={"id": new_id}).get_json()["viewing_id"] == new_id
    assert teacher.put("/api/school-year", json={"id": 9999}).status_code == 404


def test_new_year_can_copy_last_years_classes(admin, teacher):
    make_class(teacher)
    result = admin.post("/api/school-years", json={"name": "2027-2028", "copy_classes": True}).get_json()
    assert result["copied_classes"] == 1
    copied = teacher.get("/api/classes").get_json()["classes"]
    assert [(item["name"], item["students"]) for item in copied] == [("Grade 9 - Rizal", 0)]
    assert error(admin.post("/api/school-years", json={"name": "2028-2029", "copy_classes": "yes"})) == \
        "Choose whether to copy last year's classes."


def test_only_the_admin_starts_a_year_and_names_are_checked(admin, teacher):
    assert teacher.post("/api/school-years", json={"name": "2027-2028"}).status_code == 403
    bad = 'Write the school year like "2026-2027".'
    for name in ("", "2027", "2027-2029", "2027-28", None):
        assert error(admin.post("/api/school-years", json={"name": name})) == bad
    first = admin.get("/api/school-years").get_json()["years"][0]["name"]
    assert error(admin.post("/api/school-years", json={"name": first})) == "This school year already exists."
