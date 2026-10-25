"""Teacher: excluding a student from one assigned activity (absent) and adding them back."""

from conftest import assign, error, login, make_activity, make_class, open_assignment


def class_assignment(teacher):
    class_id, students = make_class(teacher)
    activity_id, questions = make_activity(teacher)
    return class_id, activity_id, assign(teacher, activity_id, class_id), students, questions


def exclude(teacher, assignment_id, student_id, excluded=True):
    return teacher.put(f"/api/assignments/{assignment_id}/students/{student_id}/excluded",
                       json={"excluded": excluded})


def test_excluded_student_cannot_open_it_and_comes_back_with_saved_answers(teacher):
    _, _, assignment_id, students, questions = class_assignment(teacher)
    student = login(students[0]["username"])
    answers = {"answers": {str(questions[0]): 1}}
    assert student.put(f"/api/my-activities/{assignment_id}/answers", json=answers).status_code == 200

    assert exclude(teacher, assignment_id, students[0]["id"]).get_json() == {"excluded": True}
    assert student.get("/api/my-activities").get_json()["activities"] == []
    assert student.get(f"/api/my-activities/{assignment_id}").status_code == 404
    assert student.put(f"/api/my-activities/{assignment_id}/answers", json=answers).status_code == 404
    assert student.post(f"/api/my-activities/{assignment_id}/submit", json=answers).status_code == 404
    # The others in the class still have it
    other = login(students[1]["username"]).get("/api/my-activities").get_json()["activities"]
    assert [item["id"] for item in other] == [assignment_id]

    assert exclude(teacher, assignment_id, students[0]["id"], False).get_json() == {"excluded": False}
    detail = student.get(f"/api/my-activities/{assignment_id}").get_json()["activity"]
    assert detail["answers"][str(questions[0])] == 1


def test_excluding_twice_or_adding_back_a_never_excluded_student_is_fine(teacher):
    _, _, assignment_id, students, _ = class_assignment(teacher)
    assert exclude(teacher, assignment_id, students[0]["id"], False).status_code == 200
    assert exclude(teacher, assignment_id, students[0]["id"]).status_code == 200
    assert exclude(teacher, assignment_id, students[0]["id"]).status_code == 200
    assert exclude(teacher, assignment_id, students[0]["id"], False).status_code == 200


def test_a_student_who_submitted_cannot_be_excluded(teacher):
    _, _, assignment_id, students, _ = class_assignment(teacher)
    student = login(students[0]["username"])
    assert student.post(f"/api/my-activities/{assignment_id}/submit", json={"answers": {}}).status_code == 200
    response = exclude(teacher, assignment_id, students[0]["id"])
    assert response.status_code == 400
    assert error(response) == "This student already submitted, so they can't be excluded."
    assert student.get(f"/api/my-activities/{assignment_id}").status_code == 200


def test_exclusion_rules(teacher, other_teacher):
    _, _, assignment_id, students, _ = class_assignment(teacher)
    outside = make_class(other_teacher, name="Grade 9 - Bonifacio", section="Bonifacio")[1]
    assert exclude(other_teacher, assignment_id, students[0]["id"]).status_code == 404
    assert exclude(teacher, assignment_id, outside[0]["id"]).status_code == 404
    assert exclude(teacher, 999999, students[0]["id"]).status_code == 404
    response = teacher.put(f"/api/assignments/{assignment_id}/students/{students[0]['id']}/excluded",
                           json={"excluded": "yes"})
    assert response.status_code == 400
    assert error(response) == "Choose whether to exclude the student."
    assert login(students[0]["username"]).put(
        f"/api/assignments/{assignment_id}/students/{students[0]['id']}/excluded",
        json={"excluded": True}).status_code == 403


def test_paper_score_and_another_try_need_the_student_added_back(teacher):
    _, _, assignment_id, students, _ = class_assignment(teacher)
    student_id = students[0]["id"]
    assert exclude(teacher, assignment_id, student_id).status_code == 200
    paper = teacher.post(f"/api/assignments/{assignment_id}/students/{student_id}/paper", json={"score": 3})
    assert paper.status_code == 400 and error(paper) == "Add the student back first."
    reopen = teacher.post(f"/api/assignments/{assignment_id}/students/{student_id}/reopen")
    assert reopen.status_code == 400 and error(reopen) == "Add the student back first."
    assert exclude(teacher, assignment_id, student_id, False).status_code == 200
    paper = teacher.post(f"/api/assignments/{assignment_id}/students/{student_id}/paper", json={"score": 3})
    assert paper.status_code == 200


def test_exclusion_works_for_direct_assignments(teacher, other_teacher):
    outside = make_class(other_teacher, name="Grade 9 - Bonifacio", section="Bonifacio")[1]
    activity_id, _ = make_activity(teacher)
    direct = teacher.put(f"/api/activities/{activity_id}/assignments", json={
        "assignments": [], "direct": {"student_ids": [outside[0]["id"], outside[1]["id"]]}}).get_json()["direct"]
    open_assignment(teacher, direct["id"])
    assert exclude(teacher, direct["id"], outside[0]["id"]).status_code == 200
    assert login(outside[0]["username"]).get("/api/my-activities").get_json()["activities"] == []
    assert len(login(outside[1]["username"]).get("/api/my-activities").get_json()["activities"]) == 1


def test_taking_the_sheet_back_clears_its_exclusions(teacher):
    class_id, activity_id, assignment_id, students, _ = class_assignment(teacher)
    assert exclude(teacher, assignment_id, students[0]["id"]).status_code == 200
    put = lambda items: teacher.put(f"/api/activities/{activity_id}/assignments", json={"assignments": items})
    assert put([]).status_code == 200
    again = assign(teacher, activity_id, class_id)  # SQLite may reuse the old id
    seen = login(students[0]["username"]).get("/api/my-activities").get_json()["activities"]
    assert [item["id"] for item in seen] == [again]


def test_deleting_a_student_clears_their_exclusions(app, teacher):
    from myguro.database import get_db
    from myguro.repositories.users import UserRepository

    _, _, assignment_id, students, _ = class_assignment(teacher)
    assert exclude(teacher, assignment_id, students[0]["id"]).status_code == 200
    with app.app_context():
        db = get_db()
        UserRepository(db).delete_students([students[0]["id"]])
        db.commit()
        assert db.execute("SELECT COUNT(*) FROM assignment_exclusions").fetchone()[0] == 0


def test_results_leave_excluded_students_out_of_the_totals(teacher):
    _, _, assignment_id, students, _ = class_assignment(teacher)
    total = len(students)
    first = login(students[0]["username"])
    assert first.post(f"/api/my-activities/{assignment_id}/submit", json={"answers": {}}).status_code == 200
    assert exclude(teacher, assignment_id, students[1]["id"]).status_code == 200

    results = teacher.get(f"/api/assignments/{assignment_id}/results").get_json()
    by_id = {item["id"]: item for item in results["students"]}
    assert len(results["students"]) == total  # still listed
    assert by_id[students[1]["id"]]["status"] == "excluded"
    assert by_id[students[1]["id"]]["excluded"] is True
    assert by_id[students[0]["id"]]["excluded"] is False
    summary = results["summary"]
    assert (summary["students"], summary["submitted"], summary["not_started"], summary["excluded"]) == \
        (total - 1, 1, total - 2, 1)

    assert exclude(teacher, assignment_id, students[1]["id"], False).status_code == 200
    results = teacher.get(f"/api/assignments/{assignment_id}/results").get_json()
    assert results["summary"]["students"] == total and results["summary"]["excluded"] == 0
    assert {item["id"]: item for item in results["students"]}[students[1]["id"]]["status"] == "not_started"


def test_exports_list_excluded_students(teacher):
    _, _, assignment_id, students, _ = class_assignment(teacher)
    assert exclude(teacher, assignment_id, students[0]["id"]).status_code == 200
    for kind in ("xlsx", "pdf"):
        assert teacher.get(f"/results/{assignment_id}/export.{kind}").status_code == 200


def test_student_dashboard_does_not_count_an_excluded_activity(teacher):
    _, _, assignment_id, students, _ = class_assignment(teacher)
    student = login(students[0]["username"])
    count = lambda: student.get("/api/dashboard").get_json()["classes"][0]["activities"]
    assert count() == 1
    assert exclude(teacher, assignment_id, students[0]["id"]).status_code == 200
    assert count() == 0
    assert student.get("/api/dashboard").get_json()["to_do"] == 0
