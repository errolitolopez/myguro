"""The schedule generator in the app: the admin enters the data, builds, swaps and publishes; a teacher sees only their own."""

from conftest import login


def add(admin, path, **body):
    response = admin.post(f"/api/schedule/{path}", json=body)
    assert response.status_code == 201, response.get_json()
    return response.get_json()["id"]


def give(admin, section_id, subject, teacher_id, per_week):
    response = admin.put("/api/schedule/assignments", json={
        "section_id": section_id, "subject": subject, "teacher_id": teacher_id, "per_week": per_week})
    assert response.status_code == 200, response.get_json()
    return response.get_json()["id"]


def setup(admin):
    """Two sections and three teachers (the first is linked to the sample account `ecruz`)."""
    teacher_account = next(a["id"] for a in admin.get("/api/schedule").get_json()["accounts"] if a["username"] == "ecruz")
    one = add(admin, "sections", name="12-A", grade="12", room="101")
    two = add(admin, "sections", name="12-B", grade="12", room="102")
    t1 = add(admin, "teachers", name="Teacher One", user_id=teacher_account)
    t2 = add(admin, "teachers", name="Teacher Two")
    t3 = add(admin, "teachers", name="Teacher Three")
    for section in (one, two):
        give(admin, section, "MATH", t1, 5)
        give(admin, section, "sci", t2, 5)
        give(admin, section, "ENG", t3, 4)
    return one, two, t1, t2, t3


def test_only_the_admin_enters_the_schedule(admin, teacher, supervisor):
    assert admin.get("/schedule").status_code == 200
    for client in (teacher, supervisor):
        assert client.get("/api/schedule").status_code == 403
        assert client.post("/api/schedule/sections", json={"name": "X"}).status_code == 403
        assert client.post("/api/schedule/generate", json={}).status_code == 403
    assert teacher.get("/schedule").status_code == 302  # sent back to their own dashboard
    assert teacher.get("/my-schedule").status_code == 200 and admin.get("/my-schedule").status_code == 302


def test_sections_teachers_and_subjects_are_checked(admin):
    one, _, t1, _, _ = setup(admin)
    assert admin.post("/api/schedule/sections", json={"name": "12-a"}).status_code == 400  # same name, other capitals
    assert admin.post("/api/schedule/sections", json={"name": ""}).status_code == 400
    assert admin.post("/api/schedule/teachers", json={"name": "X", "blocked": [[9, 0]]}).status_code == 400
    assert admin.post("/api/schedule/teachers", json={"name": "Y", "user_id": 99999}).status_code == 400
    duplicate_link = admin.get("/api/schedule").get_json()["teachers"][0]["user_id"]
    assert admin.post("/api/schedule/teachers", json={"name": "Z", "user_id": duplicate_link}).status_code == 400
    assert admin.put("/api/schedule/assignments", json={"section_id": one, "subject": "MATH", "teacher_id": t1,
                                                        "per_week": 99}).status_code == 400
    assert admin.delete(f"/api/schedule/teachers/{t1}").status_code == 400  # still has subjects
    overview = admin.get("/api/schedule").get_json()
    assert {a["subject"] for a in overview["assignments"]} == {"MATH", "SCI", "ENG"}  # "sci" was kept in capitals


def test_building_places_every_period_and_a_teacher_is_never_double_booked(admin):
    one, two, t1, t2, t3 = setup(admin)
    answer = admin.post("/api/schedule/generate", json={"seed": 1}).get_json()
    assert answer["placed"] == 2 * 14 and answer["unplaced"] == []
    overview = admin.get("/api/schedule").get_json()
    assert overview["built"] and not overview["published"] and overview["problems"] == []
    grid = admin.get(f"/api/schedule/sections/{one}/grid").get_json()
    taught = [cell for row in grid["rows"] for cell in row if cell]
    assert len(taught) == 14 and grid["title"] == "12-A" and "Room 101" in grid["details"]
    teacher_grid = admin.get(f"/api/schedule/teachers/{t1}/grid").get_json()
    assert sum(1 for row in teacher_grid["rows"] for cell in row if cell) == 10  # MATH in two sections


def test_a_blocked_period_is_kept_free(admin):
    one, two, t1, _, _ = setup(admin)
    blocked = [[day, 0] for day in range(5)]
    admin.put(f"/api/schedule/teachers/{t1}", json={"name": "Teacher One", "blocked": blocked,
                                                    "user_id": admin.get("/api/schedule").get_json()["teachers"][0]["user_id"]})
    admin.post("/api/schedule/generate", json={"seed": 2})
    grid = admin.get(f"/api/schedule/teachers/{t1}/grid").get_json()
    assert not any(grid["rows"][0])  # nothing in the first period on any day


def test_a_teacher_sees_only_their_own_schedule_and_only_once_published(admin, teacher):
    setup(admin)
    assert teacher.get("/api/my-schedule").get_json() == {"available": False}  # nothing built
    admin.post("/api/schedule/generate", json={"seed": 1})
    assert teacher.get("/api/my-schedule").get_json() == {"available": False}  # built, not published
    assert admin.put("/api/schedule/published", json={"published": True}).status_code == 200
    mine = teacher.get("/api/my-schedule").get_json()
    assert mine["available"] and sum(1 for row in mine["rows"] for cell in row if cell) == 10
    assert {cell["subject"] for row in mine["rows"] for cell in row if cell} == {"MATH"}  # no one else's classes
    other = login("rdiaz")  # a teacher account that is not linked to any schedule teacher
    assert other.get("/api/my-schedule").get_json() == {"available": False}
    admin.put("/api/schedule/published", json={"published": False})
    assert teacher.get("/api/my-schedule").get_json() == {"available": False}


def test_building_again_unpublishes_and_publishing_needs_a_timetable(admin):
    setup(admin)
    assert admin.put("/api/schedule/published", json={"published": True}).status_code == 400
    admin.post("/api/schedule/generate", json={"seed": 1})
    admin.put("/api/schedule/published", json={"published": True})
    admin.post("/api/schedule/generate", json={"seed": 2})
    assert admin.get("/api/schedule").get_json()["published"] is False


def test_a_swap_moves_two_periods_and_a_double_booking_is_refused(admin):
    one, two, t1, t2, t3 = setup(admin)
    admin.post("/api/schedule/generate", json={"seed": 1})
    grid = admin.get(f"/api/schedule/sections/{one}/grid").get_json()
    cells = [(day, period) for period, row in enumerate(grid["rows"]) for day, cell in enumerate(row) if cell]
    first, second = cells[0], cells[-1]
    before = {(d, p): grid["rows"][p][d] for d, p in (first, second)}
    answer = admin.post("/api/schedule/swap", json={"section_id": one, "a": list(first), "b": list(second)})
    assert answer.status_code == 200, answer.get_json()
    after = admin.get(f"/api/schedule/sections/{one}/grid").get_json()
    assert after["rows"][second[1]][second[0]] == before[first] and after["rows"][first[1]][first[0]] == before[second]
    # Both periods free is not a swap, and the same period twice is refused
    assert admin.post("/api/schedule/swap", json={"section_id": one, "a": list(first), "b": list(first)}).status_code == 400

    # Put section 12-B's class of the same teacher into the period 12-A's teacher is busy in
    busy = admin.get(f"/api/schedule/teachers/{t1}/grid").get_json()
    other_grid = admin.get(f"/api/schedule/sections/{two}/grid").get_json()
    other_cells = [(d, p) for p, row in enumerate(other_grid["rows"]) for d, cell in enumerate(row) if cell]
    clash = next(((d, p), (d2, p2)) for (d, p) in other_cells for (d2, p2) in other_cells
                 if other_grid["rows"][p][d]["teacher"] == "Teacher One" and (d2, p2) != (d, p)
                 and busy["rows"][p2][d2] is not None and other_grid["rows"][p2][d2]["teacher"] != "Teacher One"
                 and other_grid["rows"][p2][d2] is not None)
    refused = admin.post("/api/schedule/swap", json={"section_id": two, "a": list(clash[0]), "b": list(clash[1])})
    assert refused.status_code == 400 and "Teacher One" in refused.get_json()["error"]


def test_the_schedule_log_never_holds_a_teacher_name(admin):
    setup(admin)
    admin.post("/api/schedule/generate", json={"seed": 1})
    text = str(admin.get("/api/log?q=schedule&per_page=100").get_json())
    assert "schedule.teacher_added" in text and "Teacher One" not in text and "Teacher Two" not in text
