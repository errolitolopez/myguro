"""The holiday calendar: national holidays for everyone, local holidays added by the admin."""

from conftest import error, login


def names(response):
    return {(item["day"], item["name"]) for item in response.get_json()["holidays"]}


def test_national_holidays_for_2026(teacher):
    found = names(teacher.get("/api/calendar?year=2026"))
    assert ("2026-01-01", "New Year's Day") in found
    assert ("2026-04-02", "Maundy Thursday") in found  # Easter 2026 is April 5
    assert ("2026-04-03", "Good Friday") in found
    assert ("2026-08-31", "National Heroes Day") in found  # last Monday of August
    assert ("2026-12-25", "Christmas Day") in found


def test_easter_moves_each_year(teacher):
    assert ("2027-03-26", "Good Friday") in names(teacher.get("/api/calendar?year=2027"))
    assert ("2025-04-18", "Good Friday") in names(teacher.get("/api/calendar?year=2025"))


def test_students_can_read_but_not_change(admin, teacher):
    student = login("jdelacruz01")
    assert student.get("/api/calendar").status_code == 200
    assert student.get("/calendar").status_code == 200
    assert teacher.get("/calendar").status_code == 200
    body = {"day": "2026-03-10", "name": "Town Fiesta"}
    assert student.post("/api/calendar/holidays", json=body).status_code == 403
    assert teacher.post("/api/calendar/holidays", json=body).status_code == 403


def test_admin_adds_changes_and_removes_a_local_holiday(admin, teacher):
    response = admin.post("/api/calendar/holidays", json={"day": "2026-03-10", "name": "  Town   Fiesta "})
    assert response.status_code == 201
    holiday_id = response.get_json()["id"]
    local = [h for h in teacher.get("/api/calendar?year=2026").get_json()["holidays"] if h["kind"] == "local"]
    assert local == [{"id": holiday_id, "day": "2026-03-10", "name": "Town Fiesta", "kind": "local"}]
    # Another year does not show it
    assert not [h for h in teacher.get("/api/calendar?year=2027").get_json()["holidays"] if h["kind"] == "local"]

    assert admin.put(f"/api/calendar/holidays/{holiday_id}", json={"day": "2026-03-11", "name": "Fiesta"}).status_code == 200
    assert ("2026-03-11", "Fiesta") in names(teacher.get("/api/calendar?year=2026"))

    assert admin.delete(f"/api/calendar/holidays/{holiday_id}").status_code == 200
    assert ("2026-03-11", "Fiesta") not in names(teacher.get("/api/calendar?year=2026"))
    assert admin.delete(f"/api/calendar/holidays/{holiday_id}").status_code == 404


def test_bad_input_and_duplicates(admin):
    assert error(admin.post("/api/calendar/holidays", json={"day": "2026-02-30", "name": "X"})) == "Choose a valid date."
    assert error(admin.post("/api/calendar/holidays", json={"day": "2026-03-10", "name": " "})) == "Type the name of the holiday."
    assert admin.post("/api/calendar/holidays", json={"day": "2026-03-10", "name": "Fiesta"}).status_code == 201
    again = admin.post("/api/calendar/holidays", json={"day": "2026-03-10", "name": "fiesta"})
    assert error(again) == "This holiday is already on the calendar."
    assert error(admin.get("/api/calendar?year=abc")) == "Choose a valid year."
    assert admin.put("/api/calendar/holidays/999", json={"day": "2026-03-10", "name": "X"}).status_code == 404


def test_navbar_has_calendar_for_everyone(admin, teacher):
    for client in (admin, teacher, login("jdelacruz01")):
        assert 'href="/calendar"' in client.get("/dashboard").get_data(as_text=True)
