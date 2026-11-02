"""Time in / time out for teachers (beta): off until the admin turns it on; many sessions a day; the admin reads all."""

from datetime import datetime, timedelta, timezone

import pytest

from conftest import login


class Clock:
    """A clock the tests move by hand."""

    def __init__(self):
        self.now = datetime(2026, 11, 2, 0, 0, 0, tzinfo=timezone.utc)  # 8:00 AM in the Philippines

    def advance(self, **delta):
        self.now += timedelta(**delta)


@pytest.fixture
def clock(monkeypatch):
    clock = Clock()
    monkeypatch.setattr("myguro.services.time_clock.utc_now", lambda: clock.now)
    return clock


@pytest.fixture
def on(admin):
    assert admin.put("/api/settings", json={"time_clock_enabled": True}).status_code == 200


def test_it_is_off_until_the_admin_turns_it_on(admin, teacher):
    assert admin.get("/api/settings").get_json()["settings"]["time_clock_enabled"] is False
    assert teacher.get("/api/time-clock").status_code == 404
    assert teacher.post("/api/time-clock/in").status_code == 404
    assert teacher.get("/time-clock").status_code == 404
    assert "/time-clock" not in teacher.get("/dashboard").get_data(as_text=True)
    admin.put("/api/settings", json={"time_clock_enabled": True})
    assert teacher.get("/time-clock").status_code == 200
    assert 'href="/time-clock"' in teacher.get("/dashboard").get_data(as_text=True)
    assert 'href="/time-records"' in admin.get("/dashboard").get_data(as_text=True)


def test_time_in_and_out_again_and_again_in_one_day(teacher, clock, on):
    assert teacher.get("/api/time-clock").get_json()["clocked_in"] is False
    teacher.post("/api/time-clock/in")
    assert teacher.post("/api/time-clock/in").get_json()["error"] == "You are already timed in."
    clock.advance(hours=4)  # 12:00 PM
    teacher.post("/api/time-clock/out")
    assert teacher.post("/api/time-clock/out").get_json()["error"] == "You are not timed in."
    clock.advance(hours=1)  # 1:00 PM, back from lunch
    teacher.post("/api/time-clock/in")
    clock.advance(hours=3, minutes=30)
    data = teacher.post("/api/time-clock/out").get_json()

    assert data["clocked_in"] is False and data["today"] == "2026-11-02"
    day = data["days"][0]
    assert day["day"] == "2026-11-02" and len(day["sessions"]) == 2
    assert day["total_seconds"] == 4 * 3600 + 3.5 * 3600
    assert day["sessions"][0]["time_in"] == "2026-11-02 05:00:00"  # newest session first


def test_the_page_knows_when_you_are_timed_in(teacher, clock, on):
    teacher.post("/api/time-clock/in")
    data = teacher.get("/api/time-clock").get_json()
    assert data["clocked_in"] is True and data["since"] == "2026-11-02 00:00:00"
    assert data["days"][0]["total_seconds"] == 0  # an open session adds nothing yet


def test_a_forgotten_time_out_does_not_block_the_next_day(teacher, clock, on):
    teacher.post("/api/time-clock/in")
    clock.advance(days=1)  # never timed out
    assert teacher.get("/api/time-clock").get_json()["clocked_in"] is False
    assert teacher.post("/api/time-clock/out").status_code == 400
    assert teacher.post("/api/time-clock/in").status_code == 200
    days = teacher.get("/api/time-clock").get_json()["days"]
    assert [day["day"] for day in days] == ["2026-11-03", "2026-11-02"]
    assert days[1]["sessions"][0]["time_out"] is None


def test_the_day_is_the_school_day_not_the_utc_day(teacher, clock, on):
    clock.advance(hours=17)  # 5:00 PM UTC = 1:00 AM next day in Manila
    assert teacher.post("/api/time-clock/in").get_json()["days"][0]["day"] == "2026-11-03"


def test_admin_reads_every_teachers_records(admin, teacher, other_teacher, clock, on):
    for client in (teacher, other_teacher):
        client.post("/api/time-clock/in")
    clock.advance(hours=2)
    teacher.post("/api/time-clock/out")
    data = admin.get("/api/time-records?from=2026-11-02").get_json()
    assert (data["first_day"], data["last_day"]) == ("2026-11-02", "2026-11-02")
    assert len(data["teachers"]) >= 2 and len(data["rows"]) == 2
    by_name = {row["teacher_name"]: row for row in data["rows"]}
    assert sorted(row["total_seconds"] for row in by_name.values()) == [0, 7200]
    one = admin.get(f"/api/time-records?from=2026-11-02&teacher_id={data['teachers'][0]['id']}").get_json()
    assert len(one["rows"]) <= 1
    assert admin.get("/api/time-records?from=2026-11-05").get_json()["rows"] == []
    assert admin.get("/time-records").status_code == 200


def test_the_dates_must_make_sense(admin):
    assert admin.get("/api/time-records?from=nope").status_code == 400
    assert admin.get("/api/time-records?from=2026-11-05&to=2026-11-01").status_code == 400
    assert admin.get("/api/time-records?from=2026-01-01&to=2026-12-31").status_code == 400


def test_only_teachers_clock_and_only_the_admin_reads_everything(admin, teacher, on):
    student = login("jdelacruz01")
    assert admin.get("/api/time-clock").status_code == 403
    assert student.get("/api/time-clock").status_code == 403
    assert teacher.get("/api/time-records").status_code == 403
    assert student.get("/api/time-records").status_code == 403
    assert teacher.get("/time-records").status_code == 302  # sent back to their dashboard
