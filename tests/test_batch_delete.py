"""Admin: deleting many students at once, only those never activated."""

from conftest import error


def new_student(admin, username):
    response = admin.post("/api/users", json={
        "role": "student", "last_name": "Fresh", "first_name": username, "username": username,
        "grade": "Grade 7", "section": "Delete",
    })
    assert response.status_code == 201
    return response.get_json()["user"]["id"]


def delete(admin, **data):
    return admin.post("/api/users/batch-delete", json=data)


def usernames(admin, query=""):
    return {u["username"] for u in admin.get(f"/api/users?role=student&per_page=100{query}").get_json()["users"]}


def test_deletes_fresh_students(admin):
    ids = [new_student(admin, "fresh_one"), new_student(admin, "fresh_two")]
    response = delete(admin, user_ids=ids)
    assert response.status_code == 200
    assert response.get_json() == {"deleted": 2, "skipped": 0}
    assert not {"fresh_one", "fresh_two"} & usernames(admin)


def test_activated_student_is_kept_even_when_deactivated(admin):
    fresh, used = new_student(admin, "fresh_one"), new_student(admin, "used_one")
    assert admin.put(f"/api/users/{used}", json={"active": True}).status_code == 200
    assert admin.put(f"/api/users/{used}", json={"active": False}).status_code == 200
    assert delete(admin, user_ids=[fresh, used]).get_json() == {"deleted": 1, "skipped": 1}
    assert "used_one" in usernames(admin) and "fresh_one" not in usernames(admin)


def test_seeded_active_students_are_kept(admin):
    ids = [s["id"] for s in admin.get("/api/users?role=student&per_page=3").get_json()["users"]]
    assert delete(admin, user_ids=ids).get_json() == {"deleted": 0, "skipped": 3}


def test_match_deletes_only_fresh_among_matching(admin):
    new_student(admin, "fresh_one")
    new_student(admin, "fresh_two")
    response = delete(admin, match={"section": "Delete"})
    assert response.get_json() == {"deleted": 2, "skipped": 0}


def test_fresh_student_in_a_class_is_deleted(admin, teacher):
    student = new_student(admin, "fresh_one")
    class_id = teacher.post("/api/classes", json={"name": "Grade 7 - Delete", "subject": "Math"}).get_json()["class"]["id"]
    teacher.post(f"/api/classes/{class_id}/students", json={"student_ids": [student]})
    assert delete(admin, user_ids=[student]).get_json()["deleted"] == 1


def test_rules(admin, teacher):
    assert error(delete(admin, user_ids=[])) == "Choose at least one student."
    teacher_id = admin.get("/api/users?role=teacher").get_json()["users"][0]["id"]
    assert error(delete(admin, user_ids=[teacher_id])) == "Only students can be deleted here."
    assert teacher.post("/api/users/batch-delete", json={"user_ids": [1]}).status_code == 403
