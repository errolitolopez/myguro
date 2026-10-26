"""Recovery codes: a person who forgot their password chooses a new one without the admin."""

import re

import pytest

from conftest import PASSWORD, flask_app, login

CODE_SHAPE = re.compile(r"^([A-HJKMNP-Z2-9]{5}-){4}[A-HJKMNP-Z2-9]{5}$")
USER = "jdelacruz01"


def make_code(client=None, password=PASSWORD):
    client = client or login(USER)
    response = client.post("/api/recovery-code", json={"current_password": password, "replace": True})
    assert response.status_code == 201, response.get_json()
    return response.get_json()["code"]


def recover(code, username=USER, password="brandnew1"):
    return flask_app.test_client().post("/api/recover", json={"username": username, "code": code, "new_password": password})


def test_a_code_is_long_random_and_shown_once(admin):
    student = login(USER)
    assert student.get("/api/recovery-code").get_json() == {"has_code": False, "created_at": None}
    code = make_code(student)
    assert CODE_SHAPE.match(code)
    assert code != make_code(student)  # random
    status = student.get("/api/recovery-code")
    assert status.get_json()["has_code"] is True and "code" not in status.get_json()


def test_making_a_code_needs_the_current_password(admin):
    response = login(USER).post("/api/recovery-code", json={"current_password": "wrong"})
    assert response.status_code == 400 and "Current password" in response.get_json()["error"]
    assert flask_app.test_client().post("/api/recovery-code", json={"current_password": PASSWORD}).status_code == 401


def test_replacing_a_code_needs_a_confirmation(admin):
    student = login(USER)
    first = student.post("/api/recovery-code", json={"current_password": PASSWORD})  # the first code needs none
    assert first.status_code == 201
    for body in ({"current_password": PASSWORD}, {"current_password": PASSWORD, "replace": False},
                 {"current_password": PASSWORD, "replace": "yes"}):
        refused = student.post("/api/recovery-code", json=body)
        assert refused.status_code == 400 and "already have a recovery code" in refused.get_json()["error"]
    assert recover(first.get_json()["code"]).status_code == 200  # the code was kept, not replaced


def test_a_new_code_replaces_the_old_one(admin):
    student = login(USER)
    old = make_code(student)
    new = make_code(student)
    assert recover(old).status_code == 401
    assert recover(new).status_code == 200


def test_recovering_sets_the_password_and_uses_the_code_up(admin):
    code = make_code()
    response = recover(code)
    assert response.status_code == 200
    fresh = response.get_json()["code"]
    assert CODE_SHAPE.match(fresh) and fresh != code

    assert flask_app.test_client().post("/api/login", json={"username": USER, "password": PASSWORD}).status_code == 401
    ok = flask_app.test_client().post("/api/login", json={"username": USER, "password": "brandnew1"})
    assert ok.status_code == 200 and ok.get_json()["must_change_password"] is False
    assert recover(code, password="another123").status_code == 401  # used up
    assert recover(fresh, password="another123").status_code == 200  # the new one works


def test_the_code_can_be_typed_loosely(admin):
    code = make_code()
    assert recover(code.lower().replace("-", " ")).status_code == 200


def test_a_wrong_code_and_a_wrong_username_answer_the_same(admin):
    make_code()
    wrong_code = recover("AAAAA-AAAAA-AAAAA-AAAAA-AAAAA")
    no_user = recover("AAAAA-AAAAA-AAAAA-AAAAA-AAAAA", username="nobody")
    bad_shape = recover("12345")
    for response in (wrong_code, no_user, bad_shape):
        assert response.status_code == 401
        assert response.get_json() == wrong_code.get_json()


def test_a_person_without_a_code_cannot_recover(admin):
    assert recover("AAAAA-AAAAA-AAAAA-AAAAA-AAAAA").status_code == 401


def test_a_deactivated_account_cannot_recover(admin):
    code = make_code()
    user_id = next(user["id"] for user in admin.get("/api/users?role=student").get_json()["users"]
                   if user["username"] == USER)
    assert admin.put(f"/api/users/{user_id}", json={"active": False}).status_code == 200
    response = recover(code)
    assert response.status_code == 401 and "deactivated" not in response.get_json()["error"]


def test_a_bad_new_password_is_refused_and_keeps_the_code(admin):
    code = make_code()
    assert recover(code, password="abc").status_code == 400
    assert recover(code, password=USER).status_code == 400  # same as the username
    assert recover(code).status_code == 200


def test_too_many_wrong_codes_lock_the_try(admin):
    make_code()
    for _ in range(5):
        assert recover("AAAAA-AAAAA-AAAAA-AAAAA-AAAAA").status_code == 401
    assert recover("AAAAA-AAAAA-AAAAA-AAAAA-AAAAA").status_code == 429
    code_locked = recover("AAAAA-AAAAA-AAAAA-AAAAA-AAAAA")
    assert code_locked.status_code == 429


def test_the_log_records_it_without_the_code(admin):
    code = make_code()
    fresh = recover(code).get_json()["code"]
    recover("AAAAA-AAAAA-AAAAA-AAAAA-AAAAA")
    entries = admin.get("/api/log?per_page=100").get_json()["entries"]
    actions = [entry["action"] for entry in entries]
    assert {"auth.recovery_code_made", "auth.password_recovered", "auth.recovery_failed"} <= set(actions)
    text = admin.get("/api/log?per_page=100").get_data(as_text=True)
    assert code not in text and fresh not in text
    assert code.replace("-", "") not in text and fresh.replace("-", "") not in text


@pytest.mark.parametrize("role_client", ["admin", "teacher", "supervisor"])
def test_every_role_can_make_a_code(request, admin, role_client):
    client = request.getfixturevalue(role_client)
    password = {"admin": "adminpass1", "teacher": PASSWORD, "supervisor": "supervisor1"}[role_client]
    assert CODE_SHAPE.match(make_code(client, password))


def test_pages(admin):
    anonymous = flask_app.test_client()
    assert anonymous.get("/forgot-password").status_code == 200
    assert anonymous.get("/recovery-code").status_code == 302
    student = login(USER)
    assert 'id="recovery-page"' in student.get("/recovery-code").get_data(as_text=True)
    assert student.get("/forgot-password").status_code == 302  # already logged in


def test_the_dashboard_nudges_until_a_code_is_made(admin):
    student = login(USER)
    assert 'id="recovery-nudge"' in student.get("/dashboard").get_data(as_text=True)
    make_code(student)
    assert 'id="recovery-nudge"' not in student.get("/dashboard").get_data(as_text=True)


def test_the_first_password_change_leads_to_the_recovery_page(admin):
    # (a new student starts disabled until the admin enables the account, so a teacher is used here)
    admin.post("/api/users", json={"role": "teacher", "last_name": "Bautista", "first_name": "Ana Marie",
                                   "username": "abautista", "password": "temp1234"})
    newcomer = login("abautista", "temp1234")
    page = newcomer.get("/change-password").get_data(as_text=True)
    assert 'data-first-time="1"' in page
    newcomer.post("/api/change-password", json={"current_password": "temp1234", "new_password": "mine1234"})
    assert 'data-first-time="0"' in newcomer.get("/change-password").get_data(as_text=True)
