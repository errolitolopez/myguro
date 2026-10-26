"""The activity log: who did what. Reading it (supervisor and admin) and the supervisor's read-only access."""

import pytest

PEOPLE = {"id": 7, "name": "Santos, Maria", "username": "msantos", "role": "teacher"}


def add_entries(app, rows):
    """Write log rows the way the services do (LogRepository.add). rows: [dict of keyword arguments]."""
    from myguro.database import get_db
    from myguro.repositories import LogRepository

    with app.app_context():
        for row in rows:
            LogRepository(get_db()).add(row.pop("actor", PEOPLE), **row)
        get_db().commit()


def entries(client, query=""):
    response = client.get(f"/api/log{query}")
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def test_read_requires_supervisor_or_admin(admin, supervisor, teacher):
    assert supervisor.get("/api/log").status_code == 200
    assert admin.get("/api/log").status_code == 200
    assert supervisor.get("/log").status_code == 200
    assert admin.get("/log").status_code == 200
    assert teacher.get("/api/log").status_code == 403
    assert teacher.get("/log").status_code == 302


def test_entries_newest_first_with_paging(app, supervisor):
    add_entries(app, [{"action": "a.b", "category": "classes", "summary": f"Entry {number}",
                       "at": f"2026-10-01 00:{number:02d}:00"} for number in range(25)])
    # (the supervisor's own login entries are from today, so the test day is picked out by date)
    day = "&from=2026-10-01&to=2026-10-01"
    first = entries(supervisor, "?per_page=10" + day)
    assert first["total"] == 25 and first["pages"] == 3 and first["page"] == 1
    assert first["entries"][0]["summary"] == "Entry 24"
    third = entries(supervisor, "?per_page=10&page=3" + day)
    assert [item["summary"] for item in third["entries"]] == [f"Entry {n}" for n in (4, 3, 2, 1, 0)]
    assert entries(supervisor, "?per_page=10&page=99" + day)["page"] == 3  # past the end shows the last page
    entry = first["entries"][0]
    assert entry["actor"] == {"id": 7, "name": "Santos, Maria", "username": "msantos", "role": "teacher"}
    assert entry["category"] == "classes" and entry["action"] == "a.b" and entry["target"]["name"] == ""


def test_filters(app, supervisor):
    other = {"id": 9, "name": "Reyes, Juan", "username": "jreyes", "role": "student"}
    add_entries(app, [
        {"action": "class.created", "category": "classes", "summary": "Created Grade 9 - Rizal.",
         "target_type": "class", "target_id": 1, "target_name": "Grade 9 - Rizal", "at": "2026-10-01 01:00:00"},
        {"actor": other, "action": "student.submitted", "category": "students", "summary": "Submitted Quiz 1.",
         "at": "2026-10-02 01:00:00"},
    ])
    assert entries(supervisor, "?q=maria")["total"] == 1  # actor name
    assert entries(supervisor, "?q=Quiz")["total"] == 1  # summary
    assert entries(supervisor, "?q=Rizal")["total"] == 1  # target name or summary
    assert entries(supervisor, "?role=student")["total"] == 1
    assert entries(supervisor, "?category=classes")["total"] == 1
    assert entries(supervisor, "?user_id=9")["entries"][0]["summary"] == "Submitted Quiz 1."
    assert entries(supervisor, "?from=2026-10-02&to=2026-10-02")["total"] == 1
    assert entries(supervisor, "?from=2026-10-01&to=2026-10-02")["total"] == 2
    assert entries(supervisor, "?to=2026-10-01")["total"] == 1
    assert entries(supervisor, "?q=zzz")["total"] == 0


def test_date_to_is_inclusive_in_school_time(app, supervisor):
    # School time is UTC+8: 15:30 UTC on Oct 1 is 23:30 on Oct 1; 16:30 UTC is 00:30 on Oct 2.
    add_entries(app, [
        {"action": "x.y", "category": "classes", "summary": "Late on the first", "at": "2026-10-01 15:30:00"},
        {"action": "x.y", "category": "classes", "summary": "Early on the second", "at": "2026-10-01 16:30:00"},
    ])
    on_first = entries(supervisor, "?from=2026-10-01&to=2026-10-01")
    assert [item["summary"] for item in on_first["entries"]] == ["Late on the first"]
    assert [item["summary"] for item in entries(supervisor, "?from=2026-10-02&to=2026-10-02")["entries"]] == [
        "Early on the second"]


@pytest.mark.parametrize("query", ["?from=2026-13-01", "?to=nope", "?role=boss", "?category=fun"])
def test_bad_filters_are_refused(supervisor, query):
    assert supervisor.get(f"/api/log{query}").status_code == 400


def test_no_route_edits_or_deletes_entries(admin, supervisor):
    for client in (admin, supervisor):
        for method in ("put", "patch", "delete", "post"):
            for path in ("/api/log", "/api/log/1"):
                assert getattr(client, method)(path).status_code in (404, 405)


WRITE_ROUTES = [
    ("post", "/api/users"), ("put", "/api/users/1"), ("post", "/api/users/batch-delete"),
    ("post", "/api/classes"), ("put", "/api/classes/1"), ("post", "/api/classes/1/students"),
    ("post", "/api/activities"), ("put", "/api/activities/1"), ("delete", "/api/activities/1"),
    ("put", "/api/activities/1/assignments"), ("put", "/api/assignments/1/status"),
    ("put", "/api/assignments/1/release"), ("put", "/api/submissions/1/points"),
    ("put", "/api/my-activities/1/answers"), ("post", "/api/my-activities/1/submit"),
    ("put", "/api/settings"), ("post", "/api/school-years"), ("put", "/api/school-year"),
]
READ_ROUTES = ["/api/dashboard", "/api/school-years", "/api/settings", "/api/users", "/api/classes",
               "/api/activities", "/api/my-activities", "/api/assignments/1/results"]
OTHER_PAGES = ["/users", "/teachers", "/students", "/supervisors", "/settings", "/activities", "/classes",
               "/my-activities", "/results/1", "/classes/1/gradebook"]


def test_supervisor_is_read_only_everywhere(supervisor):
    for method, path in WRITE_ROUTES:
        response = getattr(supervisor, method)(path, json={})
        assert response.status_code == 403, (method, path, response.status_code)
    for path in READ_ROUTES:
        assert supervisor.get(path).status_code == 403, path
    for path in OTHER_PAGES:
        response = supervisor.get(path)
        assert response.status_code in (302, 404), (path, response.status_code)
        if response.status_code == 302:
            assert response.headers["Location"].endswith(("/dashboard", "/log")), path
    assert supervisor.get("/dashboard").headers["Location"].endswith("/log")
    assert supervisor.post("/api/change-password", json={"current_password": "supervisor1",
                                                         "new_password": "supervisor2"}).status_code == 200
    assert supervisor.post("/api/logout").status_code == 200


def test_supervisor_navbar_has_only_log(supervisor):
    page = supervisor.get("/log").get_data(as_text=True)
    assert "/log" in page and "Log" in page
    for link in ("/dashboard", "/users", "/teachers", "/activities", "/classes", "year-select", "tip-box"):
        assert link not in page, link


# --- Sign-in entries -----------------------------------------------------------------------

def log_of(admin, **filters):
    """Entries of the admin's view of the log, oldest first, for the given filters."""
    from urllib.parse import urlencode
    data = admin.get("/api/log?" + urlencode({"per_page": 100, **filters})).get_json()
    return list(reversed(data["entries"]))


def test_login_logout_and_password_change_are_logged(app, admin):
    client = app.test_client()
    assert client.post("/api/login", json={"username": "ecruz", "password": "1234"}).status_code == 200
    assert client.post("/api/change-password",
                       json={"current_password": "1234", "new_password": "newpass99"}).status_code == 200
    assert client.post("/api/logout").status_code == 200
    mine = [(item["action"], item["category"], item["address"], item["actor"]["username"], item["actor"]["role"])
            for item in log_of(admin, q="ecruz")]
    assert mine == [("auth.login", "sign-in", "127.0.0.1", "ecruz", "teacher"),
                    ("auth.password_changed", "sign-in", "", "ecruz", "teacher"),
                    ("auth.logout", "sign-in", "", "ecruz", "teacher")]


def test_wrong_password_is_logged_for_known_and_unknown_usernames(app, admin):
    client = app.test_client()
    known = client.post("/api/login", json={"username": "ecruz", "password": "nope"})
    unknown = client.post("/api/login", json={"username": "nobody", "password": "nope"})
    assert known.status_code == unknown.status_code == 401
    assert known.get_json() == unknown.get_json()  # the login page does not tell them apart
    failed = log_of(admin, q="ecruz") + log_of(admin, q="nobody")
    by_user = {item["actor"]["username"]: item for item in failed if item["action"] == "auth.login_failed"}
    assert by_user["ecruz"]["actor"]["id"] is not None and by_user["ecruz"]["actor"]["role"] == "teacher"
    assert by_user["nobody"]["actor"] == {"id": None, "name": "nobody", "username": "nobody", "role": ""}
    assert by_user["nobody"]["address"] == "127.0.0.1"


def test_lockout_is_logged_once(app, admin):
    client = app.test_client()
    for _ in range(5):
        client.post("/api/login", json={"username": "lmanalo", "password": "bad"})
    assert client.post("/api/login", json={"username": "lmanalo", "password": "1234"}).status_code == 429
    actions = [item["action"] for item in log_of(admin, q="lmanalo")]
    assert actions.count("auth.login_failed") == 5 and actions.count("auth.locked") == 1
    assert "auth.login" not in actions  # the blocked try is not a login


def test_deactivated_account_login_is_logged(app, admin):
    teacher_id = next(u["id"] for u in admin.get("/api/users?role=teacher").get_json()["users"]
                      if u["username"] == "ecruz")
    assert admin.put(f"/api/users/{teacher_id}", json={"active": False}).status_code == 200
    assert app.test_client().post("/api/login", json={"username": "ecruz", "password": "1234"}).status_code == 403
    entry = log_of(admin, q="ecruz")[-1]
    assert entry["action"] == "auth.login_failed" and "deactivated" in entry["summary"]


def test_no_password_text_in_any_entry(app, admin):
    import sqlite3
    import os
    client = app.test_client()
    client.post("/api/login", json={"username": "ecruz", "password": "wrong-secret-77"})
    client.post("/api/login", json={"username": "ecruz", "password": "1234"})
    client.post("/api/change-password", json={"current_password": "1234", "new_password": "brand-new-secret-88"})
    admin.put("/api/users/2", json={"reset_password": True, "password": "reset-secret-99"})
    rows = sqlite3.connect(os.environ["MYGURO_DATABASE"]).execute("SELECT * FROM activity_log").fetchall()
    text = " ".join(str(cell) for row in rows for cell in row)
    for secret in ("wrong-secret-77", "brand-new-secret-88", "reset-secret-99", "pbkdf2", "scrypt"):
        assert secret not in text


def test_old_entries_keep_names_after_rename_and_delete(app, admin):
    app.test_client().post("/api/login", json={"username": "ecruz", "password": "1234"})
    teacher_id = next(u["id"] for u in admin.get("/api/users?role=teacher").get_json()["users"]
                      if u["username"] == "ecruz")
    before = log_of(admin, q="ecruz")[0]
    admin.put(f"/api/users/{teacher_id}", json={"first_name": "Renamed"})
    assert log_of(admin, q="ecruz")[0] == before


def test_admin_navbar_links_to_the_log(admin):
    page = admin.get("/dashboard").get_data(as_text=True)
    assert 'href="/log"' in page
    assert "Activity log" in admin.get("/log").get_data(as_text=True)


def test_log_keeps_only_the_newest_entries(app, admin, monkeypatch):
    from myguro.domain import log as log_rules
    monkeypatch.setattr(log_rules, "MAX_LOG_ENTRIES", 5)  # a small cap to try the trim
    client = app.test_client()
    for _ in range(4):  # a login and a logout each: eight new entries
        client.post("/api/login", json={"username": "ecruz", "password": "1234"})
        client.post("/api/logout")
    data = admin.get("/api/log?per_page=100").get_json()
    assert data["total"] == 5
    assert data["entries"][0]["summary"] == "Logged out."  # the newest is kept
    ids = [item["id"] for item in data["entries"]]
    assert ids == sorted(ids, reverse=True) and ids[0] - ids[-1] == 4  # the five newest, in a row


def test_log_page_says_how_many_entries_are_kept(supervisor):
    from myguro.domain.log import MAX_LOG_ENTRIES
    assert f"{MAX_LOG_ENTRIES:,}" in supervisor.get("/log").get_data(as_text=True)


def chart(client, query=""):
    response = client.get(f"/api/log/chart{query}")
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def test_chart_by_day_counts_school_time_days_and_fills_empty_days(app, supervisor):
    # 2026-10-01 23:30 in Manila (UTC+8) is 15:30 UTC the same day; 17:00 UTC on Oct 1 is already Oct 2 there.
    add_entries(app, [
        {"action": "a.b", "category": "classes", "summary": "x", "at": "2026-10-01 15:30:00"},
        {"action": "a.b", "category": "classes", "summary": "x", "at": "2026-10-01 17:00:00"},
        {"action": "a.b", "category": "classes", "summary": "x", "at": "2026-10-01 18:00:00"},
    ])
    data = chart(supervisor, "?view=day&from=2026-09-30&to=2026-10-03")
    assert [item["key"] for item in data["items"]] == ["2026-09-30", "2026-10-01", "2026-10-02", "2026-10-03"]
    assert [item["count"] for item in data["items"]] == [0, 1, 2, 0] and data["total"] == 3


def test_chart_by_day_defaults_to_the_last_14_days_and_never_more_than_62(supervisor):
    assert len(chart(supervisor, "?view=day")["items"]) == 14
    assert len(chart(supervisor, "?view=day&from=2020-01-01&to=2026-10-01")["items"]) == 62
    assert supervisor.get("/api/log/chart?view=day&from=2026-10-05&to=2026-10-01").status_code == 400
    assert supervisor.get("/api/log/chart?view=day&from=nope").status_code == 400


def test_chart_breakdowns_follow_the_filters_but_ignore_their_own(app, supervisor):
    add_entries(app, [
        {"action": "a.b", "category": "classes", "summary": "x", "at": "2026-10-01 01:00:00"},
        {"action": "a.b", "category": "giving", "summary": "x", "at": "2026-10-01 02:00:00"},
        {"action": "a.b", "category": "giving", "summary": "x", "at": "2026-10-01 03:00:00",
         "actor": {"id": 8, "name": "Reyes, Ana", "username": "areyes", "role": "student"}},
    ])
    day = "&from=2026-10-01&to=2026-10-01"
    by_category = {item["key"]: item["count"] for item in chart(supervisor, "?view=category" + day)["items"]}
    assert by_category["classes"] == 1 and by_category["giving"] == 2 and by_category["sign-in"] == 0
    # With a category picked, the category chart still shows every category
    still = {item["key"]: item["count"] for item in chart(supervisor, "?view=category&category=classes" + day)["items"]}
    assert still == by_category
    # ...but the role chart is narrowed to that category
    by_role = {item["key"]: item["count"] for item in chart(supervisor, "?view=role&category=giving" + day)["items"]}
    assert by_role["teacher"] == 1 and by_role["student"] == 1 and by_role["admin"] == 0


def test_chart_is_read_only_counts_for_supervisor_and_admin(app, admin, supervisor, teacher):
    assert admin.get("/api/log/chart").status_code == 200
    assert teacher.get("/api/log/chart").status_code == 403
    assert supervisor.get("/api/log/chart?view=nope").status_code == 400
    assert supervisor.post("/api/log/chart", json={}).status_code == 405
    text = supervisor.get("/api/log/chart?view=category").get_data(as_text=True)
    assert "username" not in text and "name" not in text.replace("view", "")
