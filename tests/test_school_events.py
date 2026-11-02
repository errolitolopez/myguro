"""School events on the calendar: the DepEd list is loaded once, everyone reads it, the admin changes it."""

from conftest import error, flask_app, login

from myguro.database import get_db, init_db
from myguro.domain.deped_calendar import SCHOOL_EVENTS
from myguro.domain.school_events import check_event


def events(client, year):
    return client.get(f"/api/calendar?year={year}").get_json()["events"]


def test_the_deped_list_is_valid_and_loaded(teacher):
    for start_day, end_day, name in SCHOOL_EVENTS:
        assert check_event({"start_day": start_day, "end_day": end_day, "name": name}) == (start_day, end_day, name)
    found = {(e["start_day"], e["end_day"], e["name"]) for e in events(teacher, 2026) + events(teacher, 2027)}
    assert found == set(SCHOOL_EVENTS)
    holidays = {(h["day"], h["name"]) for h in teacher.get("/api/calendar?year=2026").get_json()["holidays"]}
    assert ("2026-11-02", "All Souls' Day") in holidays


def test_a_deleted_event_does_not_come_back_on_restart(admin):
    first = events(admin, 2026)[0]
    assert admin.delete(f"/api/calendar/events/{first['id']}").status_code == 200
    with flask_app.app_context():
        init_db()
        assert get_db().execute("SELECT 1 FROM school_events WHERE id = ?", (first["id"],)).fetchone() is None


def test_admin_adds_changes_and_removes_an_event(admin, teacher):
    body = {"start_day": "2028-01-10", "end_day": "2028-01-12", "name": "  Science   Fair "}
    event_id = admin.post("/api/calendar/events", json=body).get_json()["id"]
    assert events(teacher, 2028) == [{"id": event_id, "start_day": "2028-01-10", "end_day": "2028-01-12", "name": "Science Fair"}]

    # No last day means one day
    assert admin.put(f"/api/calendar/events/{event_id}", json={"start_day": "2028-01-11", "name": "Fair"}).status_code == 200
    assert events(teacher, 2028)[0]["end_day"] == "2028-01-11"

    assert admin.delete(f"/api/calendar/events/{event_id}").status_code == 200
    assert events(teacher, 2028) == []
    assert admin.delete(f"/api/calendar/events/{event_id}").status_code == 404


def test_an_event_shows_in_every_year_it_touches(admin):
    admin.post("/api/calendar/events", json={"start_day": "2028-12-28", "end_day": "2029-01-03", "name": "Long break"})
    assert len(events(admin, 2028)) == len(events(admin, 2029)) == 1


def test_bad_input_and_duplicates(admin):
    good = {"start_day": "2028-01-10", "end_day": "2028-01-12", "name": "Fair"}
    assert error(admin.post("/api/calendar/events", json={**good, "end_day": "2028-01-09"})) == \
        "The end date cannot be before the start date."
    assert error(admin.post("/api/calendar/events", json={**good, "start_day": "2028-02-30"})) == "Choose a valid date."
    assert error(admin.post("/api/calendar/events", json={**good, "name": " "})) == "Type the name of the event."
    assert admin.post("/api/calendar/events", json=good).status_code == 201
    assert error(admin.post("/api/calendar/events", json={**good, "name": "fair"})) == "This event is already on the calendar."


def test_only_the_admin_can_change_events(teacher):
    student = login("jdelacruz01")
    body = {"start_day": "2028-01-10", "name": "Fair"}
    assert teacher.post("/api/calendar/events", json=body).status_code == 403
    assert student.post("/api/calendar/events", json=body).status_code == 403
    assert len(events(student, 2026)) > 0
    assert 'id="event-modal"' not in teacher.get("/calendar").get_data(as_text=True)
