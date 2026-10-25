"""Teacher: giving a sheet directly to individual students, with no class."""

from conftest import assign, error, login, make_activity, make_class, open_assignment

OLD_ASSIGNMENTS_TABLE = """
    CREATE TABLE assignments (
        id INTEGER PRIMARY KEY,
        activity_id INTEGER NOT NULL REFERENCES activities (id),
        class_id INTEGER NOT NULL REFERENCES classes (id),
        everyone INTEGER NOT NULL DEFAULT 1,
        due_date TEXT,
        scores_released INTEGER NOT NULL DEFAULT 0,
        assigned_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE (activity_id, class_id)
    )
"""


def test_migration_makes_class_optional_and_keeps_rows(app, teacher):
    from myguro.database import get_db, init_db

    class_id, students = make_class(teacher)
    activity_id, _ = make_activity(teacher)
    assignment_id = assign(teacher, activity_id, class_id, everyone=False,
                           student_ids=[students[0]["id"]], due_date="2026-10-15")
    student = login(students[0]["username"])
    student.put(f"/api/my-activities/{assignment_id}/answers", json={"answers": {}})
    student.post(f"/api/my-activities/{assignment_id}/submit", json={"answers": {}})

    with app.app_context():
        db = get_db()
        # Put the table back into its old shape (class_id NOT NULL), keeping the rows.
        rows = [dict(row) for row in db.execute("SELECT * FROM assignments")]
        db.commit()
        db.execute("PRAGMA foreign_keys = OFF")
        db.execute("DROP INDEX IF EXISTS one_direct_assignment_per_activity")
        db.execute("DROP TABLE assignments")
        db.execute(OLD_ASSIGNMENTS_TABLE)
        for row in rows:
            db.execute(
                "INSERT INTO assignments (id, activity_id, class_id, everyone, due_date, scores_released, "
                "assigned_at) VALUES (:id, :activity_id, :class_id, :everyone, :due_date, :scores_released, "
                ":assigned_at)", row)
        db.commit()
        db.execute("PRAGMA foreign_keys = ON")

        init_db()  # the upgrade under test

        info = {row["name"]: row for row in db.execute("PRAGMA table_info(assignments)")}
        assert info["class_id"]["notnull"] == 0
        kept = db.execute("SELECT * FROM assignments").fetchall()
        assert [(row["id"], row["class_id"], row["due_date"]) for row in kept] == \
            [(assignment_id, class_id, "2026-10-15")]
        assert db.execute("SELECT COUNT(*) FROM assignment_students WHERE assignment_id = ?",
                          (assignment_id,)).fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM submissions WHERE assignment_id = ? AND submitted_at IS NOT NULL",
                          (assignment_id,)).fetchone()[0] == 1
        # A direct assignment (no class) can now be stored, but only one per activity and school year.
        year_id = db.execute("SELECT id FROM school_years").fetchone()[0]
        db.execute("INSERT INTO assignments (activity_id, class_id, school_year_id) VALUES (?, NULL, ?)",
                   (activity_id, year_id))
        try:
            db.execute("INSERT INTO assignments (activity_id, class_id, school_year_id) VALUES (?, NULL, ?)",
                       (activity_id, year_id))
        except Exception as problem:
            assert "UNIQUE" in str(problem)
        else:
            raise AssertionError("a second direct assignment was accepted")
        db.rollback()


def outside_students(other_teacher, section="Bonifacio"):
    """Students who are in none of the first teacher's classes (they are in the other teacher's)."""
    return make_class(other_teacher, name=f"Grade 9 - {section}", section=section)[1]


def give_directly(teacher, activity_id, student_ids, classes=(), opened=True, **options):
    """Give the sheet to individual students and return the direct assignment (opened unless opened=False)."""
    response = teacher.put(f"/api/activities/{activity_id}/assignments", json={
        "assignments": list(classes), "direct": {"student_ids": student_ids, **options}})
    assert response.status_code == 200, response.get_json()
    direct = response.get_json()["direct"]
    if opened:
        assert open_assignment(teacher, direct["id"]).status_code == 200
    return direct


def test_give_to_students_without_a_class(teacher, other_teacher):
    outside = outside_students(other_teacher)
    activity_id, _ = make_activity(teacher)
    direct = give_directly(teacher, activity_id, [outside[0]["id"], outside[1]["id"]], due_date="2026-10-15")
    assert direct["due_date"] == "2026-10-15"
    assert sorted(direct["student_ids"]) == sorted([outside[0]["id"], outside[1]["id"]])
    assert {student["id"] for student in direct["students"]} == set(direct["student_ids"])
    assert teacher.get(f"/api/activities/{activity_id}/assignments").get_json()["direct"]["id"] == direct["id"]
    assert teacher.get("/api/activities").get_json()["activities"][0]["assigned"] == 1

    given = login(outside[0]["username"]).get("/api/my-activities").get_json()["activities"]
    assert len(given) == 1
    assert given[0]["id"] == direct["id"]
    assert given[0]["class_name"] == "Individual students"
    assert given[0]["due_date"] == "2026-10-15"
    assert login(outside[2]["username"]).get("/api/my-activities").get_json()["activities"] == []


def test_direct_student_answers_and_teacher_sees_results(teacher, other_teacher):
    outside = outside_students(other_teacher)
    activity_id, _ = make_activity(teacher)
    direct = give_directly(teacher, activity_id, [outside[0]["id"]])
    student = login(outside[0]["username"])
    detail = student.get(f"/api/my-activities/{direct['id']}")
    assert detail.status_code == 200
    assert detail.get_json()["activity"]["class_name"] == "Individual students"
    assert student.put(f"/api/my-activities/{direct['id']}/answers", json={"answers": {}}).status_code == 200
    assert student.post(f"/api/my-activities/{direct['id']}/submit", json={"answers": {}}).status_code == 200

    results = teacher.get(f"/api/assignments/{direct['id']}/results").get_json()
    assert results["assignment"]["class_id"] is None
    assert results["assignment"]["class_name"] == "Individual students"
    assert [item["id"] for item in results["students"]] == [outside[0]["id"]]
    assert results["summary"]["submitted"] == 1
    assert teacher.get(f"/results/{direct['id']}").status_code == 200
    for kind in ("xlsx", "pdf"):
        response = teacher.get(f"/results/{direct['id']}/export.{kind}")
        assert response.status_code == 200
        assert "Individual" in response.headers["Content-Disposition"]


def test_other_teacher_cannot_open_direct_results(teacher, other_teacher):
    outside = outside_students(other_teacher)
    activity_id, _ = make_activity(teacher)
    direct = give_directly(teacher, activity_id, [outside[0]["id"]])
    assert other_teacher.get(f"/api/assignments/{direct['id']}/results").status_code == 404
    assert other_teacher.get(f"/results/{direct['id']}/export.xlsx").status_code == 302


def test_student_in_class_and_direct_sees_both(teacher):
    class_id, students = make_class(teacher)
    activity_id, _ = make_activity(teacher)
    class_assignment = assign(teacher, activity_id, class_id)
    direct = give_directly(teacher, activity_id, [students[0]["id"]], classes=[{"class_id": class_id}])
    seen = login(students[0]["username"]).get("/api/my-activities").get_json()["activities"]
    assert sorted(item["id"] for item in seen) == sorted([class_assignment, direct["id"]])


def test_saving_classes_keeps_direct_and_null_removes_it(teacher, other_teacher):
    outside = outside_students(other_teacher)
    class_id, _ = make_class(teacher)
    activity_id, _ = make_activity(teacher)
    direct = give_directly(teacher, activity_id, [outside[0]["id"]])
    put = lambda body: teacher.put(f"/api/activities/{activity_id}/assignments", json=body)

    kept = put({"assignments": [{"class_id": class_id}]}).get_json()
    assert kept["direct"]["id"] == direct["id"]
    assert [item["assignment"] is not None for item in kept["classes"]] == [True]

    removed = put({"assignments": [{"class_id": class_id}], "direct": None}).get_json()
    assert removed["direct"] is None
    assert login(outside[0]["username"]).get("/api/my-activities").get_json()["activities"] == []


def test_direct_assignment_id_stays_when_changed(teacher, other_teacher):
    outside = outside_students(other_teacher)
    activity_id, _ = make_activity(teacher)
    first = give_directly(teacher, activity_id, [outside[0]["id"]])
    second = give_directly(teacher, activity_id, [outside[0]["id"], outside[1]["id"]], due_date="2026-11-01")
    assert first["id"] == second["id"] and second["due_date"] == "2026-11-01"


def test_cannot_take_back_direct_after_a_submission(teacher, other_teacher):
    outside = outside_students(other_teacher)
    activity_id, _ = make_activity(teacher)
    direct = give_directly(teacher, activity_id, [outside[0]["id"], outside[1]["id"]])
    first = login(outside[0]["username"])
    second = login(outside[1]["username"])
    put = lambda body: teacher.put(f"/api/activities/{activity_id}/assignments", json=body)

    # Answers saved but not submitted go away with the assignment.
    assert first.put(f"/api/my-activities/{direct['id']}/answers", json={"answers": {}}).status_code == 200
    assert put({"assignments": [], "direct": None}).status_code == 200
    direct = give_directly(teacher, activity_id, [outside[0]["id"], outside[1]["id"]])

    assert second.post(f"/api/my-activities/{direct['id']}/submit", json={"answers": {}}).status_code == 200
    response = put({"assignments": [], "direct": None})
    assert response.status_code == 400
    assert error(response) == "Students you gave it to directly already submitted, so it can't be taken back."


def test_direct_assignment_rules(teacher, other_teacher, admin):
    outside = outside_students(other_teacher)
    activity_id, _ = make_activity(teacher)
    empty_id = teacher.post("/api/activities", json={"title": "Empty", "subject": "Philosophy"}).get_json()["activity"]["id"]  # no sections
    put = lambda target, direct: teacher.put(f"/api/activities/{target}/assignments",
                                             json={"assignments": [], "direct": direct})
    assert error(put(activity_id, "everyone")) == "Individual students are not valid."
    assert error(put(activity_id, {"student_ids": []})) == "Individual students: choose at least one student."
    assert error(put(activity_id, {"student_ids": [outside[0]["id"]], "due_date": "2026-13-40"})).endswith(
        "the due date is not valid.")
    not_found = "Individual students: a chosen student was not found or is deactivated."
    teacher_id = next(user["id"] for user in admin.get("/api/users?role=teacher&per_page=100").get_json()["users"]
                      if user["username"] == "ecruz")
    for bad in (teacher_id, 999999, True, "3", None):
        assert error(put(activity_id, {"student_ids": [outside[0]["id"], bad]})) == not_found

    assert admin.put(f"/api/users/{outside[1]['id']}", json={"active": False}).status_code == 200
    assert error(put(activity_id, {"student_ids": [outside[1]["id"]]})) == not_found

    assert put(empty_id, {"student_ids": [outside[0]["id"]]}).status_code == 400


def test_student_search_covers_the_whole_school(teacher, other_teacher):
    outside = outside_students(other_teacher)
    activity_id, _ = make_activity(teacher)
    found = teacher.get(f"/api/activities/{activity_id}/student-search?grade=Grade+9&section=Bonifacio").get_json()
    assert {student["id"] for student in found["students"]} == {student["id"] for student in outside}
    assert found["more"] is False
    assert {"grade": "Grade 9", "section": "Bonifacio"} in found["sections"]

    by_name = teacher.get(
        f"/api/activities/{activity_id}/student-search?q={outside[0]['last_name']}").get_json()["students"]
    assert outside[0]["id"] in [student["id"] for student in by_name]

    assert other_teacher.get(f"/api/activities/{activity_id}/student-search").status_code == 404
    assert login(outside[0]["username"]).get(f"/api/activities/{activity_id}/student-search").status_code == 403
