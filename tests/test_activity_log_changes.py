"""The activity log records what people change: one entry per action, written with the change."""

import io
from urllib.parse import urlencode

from conftest import make_class
from test_export_sheet import download_docx
from test_student_import import upload, xlsx


def log_of(admin, **filters):
    """The log as the admin sees it, oldest first, minus the sign-in entries (those have their own tests)."""
    data = admin.get("/api/log?" + urlencode({"per_page": 100, **filters})).get_json()
    return [item for item in reversed(data["entries"]) if item["category"] != "sign-in"]


def new_student(admin, last="Lopez", first="Ana", username="alopez"):
    response = admin.post("/api/users", json={"role": "student", "last_name": last, "first_name": first,
                                              "username": username, "password": "123qwe", "grade": "Grade 9",
                                              "section": "Rizal"})
    assert response.status_code == 201, response.get_json()
    return response.get_json()["user"]


def only(admin, **filters):
    """The one entry the last action wrote."""
    found = log_of(admin, **filters)
    assert len(found) == 1, found
    return found[0]


# --- Accounts ---------------------------------------------------------------------------------

def test_account_created(admin):
    user = new_student(admin)
    entry = only(admin)
    assert (entry["action"], entry["category"], entry["actor"]["role"]) == ("account.created", "accounts", "admin")
    assert entry["target"] == {"type": "user", "id": user["id"], "name": user["name"]}
    assert "Lopez, Ana" in entry["summary"] and "123qwe" not in entry["summary"]


def test_rename_edit_enable_disable_and_reset_password(admin):
    user = new_student(admin)
    uid = user["id"]
    admin.put(f"/api/users/{uid}", json={"first_name": "Anna"})
    admin.put(f"/api/users/{uid}", json={"section": "Mabini"})
    admin.put(f"/api/users/{uid}", json={"active": True})
    admin.put(f"/api/users/{uid}", json={"active": False})
    admin.put(f"/api/users/{uid}", json={"reset_password": True, "password": "newsecret1"})
    actions = [item["action"] for item in log_of(admin)]
    assert actions == ["account.created", "account.renamed", "account.edited", "account.activated",
                       "account.deactivated", "account.password_reset"]
    renamed = log_of(admin)[1]
    assert "Lopez, Ana" in renamed["summary"] and "Lopez, Anna" in renamed["summary"]
    assert all("newsecret1" not in item["summary"] for item in log_of(admin))


def test_update_that_changes_nothing_writes_nothing(admin):
    user = new_student(admin)
    admin.put(f"/api/users/{user['id']}", json={"first_name": "Ana", "active": False, "section": "Rizal"})
    assert [item["action"] for item in log_of(admin)] == ["account.created"]


def test_batch_actions_write_one_entry_each(admin):
    ids = [new_student(admin, "Lopez", "Ana", "alopez")["id"], new_student(admin, "Sy", "Bea", "bsy")["id"],
           new_student(admin, "Tan", "Cy", "ctan")["id"]]
    before = len(log_of(admin))
    assert admin.put("/api/users/batch", json={"user_ids": ids, "section": "Luna"}).status_code == 200
    assert admin.post("/api/users/batch-activate", json={"user_ids": ids[:2]}).status_code == 200
    assert admin.post("/api/users/batch-delete", json={"user_ids": ids[2:]}).status_code == 200
    new = log_of(admin)[before:]
    assert [item["action"] for item in new] == ["account.batch_edited", "account.batch_activated",
                                                "account.batch_deleted"]
    assert ["3 students" in new[0]["summary"], "2 students" in new[1]["summary"], "1 student" in new[2]["summary"]] \
        == [True, True, True]
    # Nothing to do (they are already active): no entry
    admin.post("/api/users/batch-activate", json={"user_ids": ids[:2]})
    assert len(log_of(admin)) == before + 3


def test_student_import_writes_one_entry_and_a_check_none(admin):
    content = xlsx([("Reyes", "Zed", "", "zreyes", "Grade 7", "Rizal", ""),
                    ("Cruz", "Yan", "", "ycruz", "Grade 7", "Rizal", "")])
    assert upload(admin, content, dry_run=True).status_code == 200
    assert log_of(admin) == []
    assert upload(admin, content, dry_run=False).status_code == 200
    entry = only(admin)
    assert entry["action"] == "account.imported" and "2 students" in entry["summary"]


def test_failed_account_actions_write_nothing(admin):
    new_student(admin)
    before = len(log_of(admin))
    assert admin.post("/api/users", json={"role": "student", "last_name": "X", "first_name": "Y",
                                          "username": "alopez", "password": "123qwe"}).status_code == 400
    assert admin.put("/api/users/99999", json={"first_name": "Nope"}).status_code == 404
    assert len(log_of(admin)) == before


# --- Classes ----------------------------------------------------------------------------------

def test_class_created_edited_students_added_and_removed(admin, teacher):
    class_id = teacher.post("/api/classes", json={"name": "Grade 9 - Rizal", "subject": "Science"}).get_json()["class"]["id"]
    teacher.put(f"/api/classes/{class_id}", json={"name": "Grade 9 - Rizal A", "subject": "Science"})
    students = teacher.get(f"/api/classes/{class_id}/student-search?grade=Grade+9&section=Rizal").get_json()["students"]
    ids = [student["id"] for student in students]
    teacher.post(f"/api/classes/{class_id}/students", json={"student_ids": ids})
    teacher.delete(f"/api/classes/{class_id}/students/{ids[0]}")
    teacher.post(f"/api/classes/{class_id}/students/remove", json={"student_ids": ids[1:]})
    entries = log_of(admin, category="classes")
    assert [item["action"] for item in entries] == ["class.created", "class.edited", "class.student_added",
                                                    "class.student_removed", "class.student_removed"]
    assert all(item["actor"]["username"] == "ecruz" for item in entries)
    assert entries[0]["target"]["name"] == "Grade 9 - Rizal" and entries[0]["target"]["type"] == "class"
    assert f"{len(ids)} students" in entries[2]["summary"] and "Grade 9 - Rizal A" in entries[2]["summary"]
    assert f"{len(ids) - 1} students" in entries[4]["summary"]


def test_failed_class_actions_write_nothing(admin, teacher, other_teacher):
    class_id, _ = make_class(teacher)
    before = len(log_of(admin, category="classes"))
    assert teacher.post("/api/classes", json={"name": ""}).status_code == 400
    assert other_teacher.post(f"/api/classes/{class_id}/students", json={"student_ids": [1]}).status_code == 404
    assert teacher.post(f"/api/classes/{class_id}/students", json={"student_ids": []}).status_code == 400
    assert len(log_of(admin, category="classes")) == before


# --- School years and settings ------------------------------------------------------------------

def test_new_school_year_and_settings_changes(admin):
    assert admin.post("/api/school-years", json={"name": "2027-2028", "copy_classes": False}).status_code == 201
    assert admin.put("/api/settings", json={"grades_high_to_low": False}).status_code == 200
    started, changed = log_of(admin)
    assert (started["action"], started["category"]) == ("year.started", "settings")
    assert "2027-2028" in started["summary"]
    assert (changed["action"], changed["category"]) == ("settings.changed", "settings")


def test_choosing_the_year_to_look_at_is_not_logged(admin, teacher):
    year = teacher.get("/api/school-years").get_json()["current_id"]
    assert teacher.put("/api/school-year", json={"id": year}).status_code == 200
    assert log_of(admin) == []


# --- Activities, giving, checking and the students' own actions ---------------------------------

from conftest import assign, login, make_activity  # noqa: E402


def sheet_log(admin, **filters):
    return [(item["action"], item["summary"]) for item in log_of(admin, **filters)]


def test_activity_lifecycle_is_logged(admin, teacher):
    activity_id = teacher.post("/api/activities", json={"title": "Quiz 1", "subject": "Science"}).get_json()["activity"]["id"]
    teacher.put(f"/api/activities/{activity_id}", json={"title": "Quiz 1", "subject": "Science", "sections": [
        {"kind": "text", "title": "Lesson", "description": "Read."}]})
    teacher.put(f"/api/activities/{activity_id}/settings", json={"max_attempts": 3})
    copy_id = teacher.post(f"/api/activities/{activity_id}/duplicate").get_json()["activity"]["id"]
    teacher.delete(f"/api/activities/{copy_id}")  # never given: really deleted
    docx = download_docx(teacher, activity_id)
    teacher.post("/api/activities/import", data={"file": (io.BytesIO(docx), "s.docx"), "title": "Imported", "subject": "Science",
                                                 "dry_run": "1"}, content_type="multipart/form-data")  # a check only
    teacher.post("/api/activities/import", data={"file": (io.BytesIO(docx), "s.docx"), "title": "Imported", "subject": "Science",
                                                 "dry_run": "0"}, content_type="multipart/form-data")
    actions = [item["action"] for item in log_of(admin, category="activities")]
    assert actions == ["activity.created", "activity.saved",
                       "activity.attempts_changed", "activity.copied", "activity.deleted", "activity.imported"]
    first = log_of(admin, category="activities")[0]
    assert first["target"] == {"type": "activity", "id": activity_id, "name": "Quiz 1"}
    assert first["actor"]["username"] == "ecruz"


def test_archive_and_restore_are_logged(admin, teacher):
    class_id, _ = make_class(teacher)
    activity_id, _ = make_activity(teacher)
    assign(teacher, activity_id, class_id)
    teacher.delete(f"/api/activities/{activity_id}")  # given to a class: archived
    teacher.post(f"/api/activities/{activity_id}/restore")
    entries = sheet_log(admin, category="activities")[-2:]
    assert entries[0][0] == "activity.deleted" and "archived" in entries[0][1]
    assert entries[1][0] == "activity.restored"


def test_giving_changing_and_taking_back(admin, teacher):
    class_id, students = make_class(teacher)
    activity_id, _ = make_activity(teacher, title="Quiz 2")
    url = f"/api/activities/{activity_id}/assignments"
    teacher.put(url, json={"assignments": [{"class_id": class_id, "everyone": True}]})
    teacher.put(url, json={"assignments": [{"class_id": class_id, "everyone": True}]})  # the same again
    teacher.put(url, json={"assignments": [{"class_id": class_id, "everyone": True, "due_date": "2030-01-01"}]})
    teacher.put(url, json={"assignments": [], "direct": {"due_date": None, "student_ids": [students[0]["id"]]}})
    teacher.put(url, json={"assignments": [], "direct": None})
    entries = sheet_log(admin, category="giving")
    assert [action for action, _ in entries] == ["assignment.given", "assignment.updated", "assignment.taken_back",
                                                 "assignment.given", "assignment.taken_back"]
    assert "Quiz 2" in entries[0][1] and "Grade 9 - Rizal" in entries[0][1]
    assert "Individual students" in entries[3][1]


def test_open_release_exclude_and_include(admin, teacher):
    class_id, students = make_class(teacher)
    activity_id, _ = make_activity(teacher)
    assignment_id = assign(teacher, activity_id, class_id)
    status = lambda value: teacher.put(f"/api/assignments/{assignment_id}/status", json={"status": value})
    status("open")  # already open: no entry
    status("closed")
    status("open")  # a re-open
    teacher.put(f"/api/assignments/{assignment_id}/release", json={"released": True})
    teacher.put(f"/api/assignments/{assignment_id}/release", json={"released": False})
    student_id = students[0]["id"]
    url = f"/api/assignments/{assignment_id}/students/{student_id}/excluded"
    teacher.put(url, json={"excluded": True})
    teacher.put(url, json={"excluded": False})
    actions = [action for action, _ in sheet_log(admin, category="giving")][1:]  # the first is "given"
    assert actions == ["assignment.opened", "assignment.closed", "assignment.reopened", "assignment.released",
                       "assignment.hidden", "assignment.excluded", "assignment.included"]


def test_student_submit_retry_and_autosave(admin, teacher):
    class_id, students = make_class(teacher)
    activity_id, q = make_activity(teacher)
    teacher.put(f"/api/activities/{activity_id}/settings", json={"max_attempts": 3})
    assignment_id = assign(teacher, activity_id, class_id)
    student = login(students[0]["username"])
    for _ in range(3):
        assert student.put(f"/api/my-activities/{assignment_id}/answers",
                           json={"answers": {str(q[0]): 1}}).status_code == 200
    assert log_of(admin, category="students") == []  # autosave is not logged
    student.post(f"/api/my-activities/{assignment_id}/submit", json={"answers": {str(q[0]): 1}})
    student.post(f"/api/my-activities/{assignment_id}/retry")
    entries = log_of(admin, category="students")
    assert [item["action"] for item in entries] == ["student.submitted", "student.retry"]
    assert entries[0]["actor"]["username"] == students[0]["username"] and entries[0]["actor"]["role"] == "student"
    assert "Early Eastern Philosophy" in entries[0]["summary"]


def test_checking_points_remarks_paper_and_another_try(admin, teacher):
    class_id, students = make_class(teacher)
    activity_id, q = make_activity(teacher)
    teacher.put(f"/api/activities/{activity_id}/settings", json={"max_attempts": 3})
    assignment_id = assign(teacher, activity_id, class_id)
    login(students[0]["username"]).post(f"/api/my-activities/{assignment_id}/submit",
                                        json={"answers": {str(q[0]): 1, str(q[2]): "Dao", str(q[4]): "Because"}})
    student_id = students[0]["id"]
    detail = teacher.get(f"/api/assignments/{assignment_id}/students/{student_id}").get_json()["detail"]
    points_url = f"/api/submissions/{detail['id']}/points"
    teacher.put(points_url, json={"points": {str(q[4]): 4, str(q[2]): 2}})
    teacher.put(points_url, json={"points": {str(q[4]): 4}})  # nothing changed
    teacher.put(points_url, json={"feedback": {str(q[4]): "Good reasoning"}})
    teacher.post(f"/api/assignments/{assignment_id}/students/{student_id}/reopen")
    other = students[1]["id"]
    paper = teacher.post(f"/api/assignments/{assignment_id}/students/{other}/paper", json={"score": 9}).get_json()
    teacher.put(f"/api/submissions/{paper['detail']['id']}/paper", json={"score": 10})
    teacher.delete(f"/api/submissions/{paper['detail']['id']}/paper")
    entries = sheet_log(admin, category="checking")
    assert [action for action, _ in entries] == ["checking.points", "checking.remark", "checking.retry_given",
                                                 "checking.paper_set", "checking.paper_changed",
                                                 "checking.paper_removed"]
    points = entries[0][1]
    assert "0 to 2" in points and "unchecked to 4" in points and students[0]["name"] in points


def test_failed_activity_and_checking_actions_write_nothing(admin, teacher, other_teacher):
    class_id, students = make_class(teacher)
    activity_id, _ = make_activity(teacher)
    before = len(log_of(admin))
    assert teacher.put("/api/assignments/999/open", json={"open": True}).status_code == 404
    assert other_teacher.put(f"/api/activities/{activity_id}/assignments",
                             json={"assignments": [{"class_id": class_id, "everyone": True}]}).status_code == 404
    assert other_teacher.put("/api/submissions/1/points", json={"points": {}}).status_code == 404
    assert teacher.post("/api/activities", json={"title": ""}).status_code == 400
    assert len(log_of(admin)) == before
