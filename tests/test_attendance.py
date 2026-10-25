"""Attendance: a teacher marks each student of a class present, late, absent or excused for a day."""

from datetime import date, timedelta

from conftest import login, make_class

DAY = (date.today() - timedelta(days=1)).isoformat()


def sheet(teacher, class_id, day=DAY):
    return teacher.get(f"/api/classes/{class_id}/attendance?date={day}").get_json()


def test_marks_are_saved_for_the_day_and_counted(teacher):
    class_id, students = make_class(teacher)
    first, second = students[0]["id"], students[1]["id"]
    assert all(row["status"] is None for row in sheet(teacher, class_id)["students"])

    response = teacher.put(f"/api/classes/{class_id}/attendance",
                           json={"day": DAY, "marks": {str(first): "present", str(second): "absent"}})
    assert response.status_code == 200, response.get_json()
    by_id = {row["id"]: row for row in sheet(teacher, class_id)["students"]}
    assert by_id[first]["status"] == "present" and by_id[second]["status"] == "absent"
    assert by_id[second]["totals"] == {"present": 0, "late": 0, "absent": 1, "excused": 0}
    assert sheet(teacher, class_id)["recorded_days"] == [DAY]

    # Saving again replaces the mark; null clears it; another day is separate
    teacher.put(f"/api/classes/{class_id}/attendance",
                json={"day": DAY, "marks": {str(first): "late", str(second): None}})
    by_id = {row["id"]: row for row in sheet(teacher, class_id)["students"]}
    assert by_id[first]["status"] == "late" and by_id[second]["status"] is None
    other_day = (date.today() - timedelta(days=2)).isoformat()
    assert all(row["status"] is None for row in sheet(teacher, class_id, other_day)["students"])


def test_bad_requests_are_refused(teacher):
    class_id, students = make_class(teacher)
    student_id = str(students[0]["id"])
    put = lambda body: teacher.put(f"/api/classes/{class_id}/attendance", json=body)
    assert put({"day": DAY, "marks": {student_id: "sleeping"}}).status_code == 400
    assert put({"day": "not a date", "marks": {}}).status_code == 400
    tomorrow = (date.today() + timedelta(days=2)).isoformat()
    assert put({"day": tomorrow, "marks": {student_id: "present"}}).status_code == 400
    assert put({"day": DAY, "marks": {"999999": "present"}}).status_code == 400


def test_only_the_classs_teacher_can_use_it(teacher, other_teacher):
    class_id, students = make_class(teacher)
    assert other_teacher.get(f"/api/classes/{class_id}/attendance").status_code == 404
    assert other_teacher.put(f"/api/classes/{class_id}/attendance",
                             json={"day": DAY, "marks": {str(students[0]["id"]): "present"}}).status_code == 404
    student = login(students[0]["username"])
    assert student.get(f"/api/classes/{class_id}/attendance").status_code in (401, 403)


def test_the_page_opens_and_the_save_is_logged(teacher):
    class_id, students = make_class(teacher)
    assert teacher.get(f"/classes/{class_id}/attendance").status_code == 200
    teacher.put(f"/api/classes/{class_id}/attendance", json={"day": DAY, "marks": {str(students[0]["id"]): "present"}})
    admin = login("admin", "admin")
    admin.post("/api/change-password", json={"current_password": "admin", "new_password": "adminpass1"})
    entries = admin.get("/api/log?q=attendance").get_json()["entries"]
    assert any(entry["action"] == "attendance.saved" for entry in entries)
