"""Admin: activating many students at once."""

from conftest import error


def new_student(admin, username):
    response = admin.post("/api/users", json={
        "role": "student", "last_name": "Fresh", "first_name": username, "username": username,
        "grade": "Grade 7", "section": "Activate",
    })
    assert response.status_code == 201
    return response.get_json()["user"]["id"]


def activate(admin, **data):
    return admin.post("/api/users/batch-activate", json=data)


def by_id(admin, user_id):
    users = admin.get("/api/users?role=student&per_page=100&section=Activate").get_json()["users"]
    return next(u for u in users if u["id"] == user_id)


def test_activates_selected_and_marks_activated(admin):
    ids = [new_student(admin, "fresh_one"), new_student(admin, "fresh_two")]
    assert activate(admin, user_ids=ids).get_json() == {"activated": 2, "skipped": 0}
    assert all(by_id(admin, i)["active"] and by_id(admin, i)["activated"] for i in ids)
    # Activated once: no longer deletable.
    admin.put(f"/api/users/{ids[0]}", json={"active": False})
    assert admin.post("/api/users/batch-delete", json={"user_ids": ids[:1]}).get_json()["deleted"] == 0


def test_already_active_skipped(admin):
    fresh = new_student(admin, "fresh_one")
    seeded = admin.get("/api/users?role=student&per_page=1").get_json()["users"][0]["id"]
    assert activate(admin, user_ids=[fresh, seeded]).get_json() == {"activated": 1, "skipped": 1}


def test_match_and_rules(admin, teacher):
    new_student(admin, "fresh_one")
    new_student(admin, "fresh_two")
    assert activate(admin, match={"section": "Activate"}).get_json() == {"activated": 2, "skipped": 0}
    assert error(activate(admin, user_ids=[])) == "Choose at least one student."
    teacher_id = admin.get("/api/users?role=teacher").get_json()["users"][0]["id"]
    assert error(activate(admin, user_ids=[teacher_id])) == "Only students can be activated here."
    assert teacher.post("/api/users/batch-activate", json={"user_ids": [1]}).status_code == 403
