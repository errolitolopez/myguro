"""Admin: changing grade and section of many students at once."""

from conftest import error


def students(admin, query=""):
    return admin.get(f"/api/users?role=student&per_page=100{query}").get_json()["users"]


def batch(admin, **data):
    return admin.put("/api/users/batch", json=data)


def test_set_grade_and_section_by_ids(admin):
    stem11 = students(admin, "&grade=Grade+11&q=stem")
    assert len(stem11) == 6
    ids = [s["id"] for s in stem11]
    response = batch(admin, user_ids=ids, grade="Grade 12", section="stem")  # existing "STEM" spelling
    assert response.status_code == 200 and response.get_json()["updated"] == 6
    moved = {s["id"]: s for s in students(admin, "&grade=Grade+12")}
    assert all(moved[i]["section"] == "STEM" for i in ids)


def test_keep_one_field(admin):
    rizal = [s["id"] for s in students(admin, "&q=rizal")]
    batch(admin, user_ids=rizal, section="Sampaguita")  # grade not sent: kept
    after = {s["id"]: s for s in students(admin)}
    assert all(after[i]["grade"] == "Grade 9" and after[i]["section"] == "Sampaguita" for i in rizal)
    batch(admin, user_ids=rizal[:2], grade="")  # no grade
    after = {s["id"]: s for s in students(admin)}
    assert after[rizal[0]]["grade"] == "" and after[rizal[2]]["grade"] == "Grade 9"


def test_clear_section(admin):
    ids = [s["id"] for s in students(admin, "&q=luna")]
    assert batch(admin, user_ids=ids, section="").get_json()["updated"] == 6
    assert len(students(admin, "&grade=Grade+10&q=luna")) == 0


def test_all_matching_a_search(admin):
    response = batch(admin, match={"q": "", "grade": "Grade 12"}, grade="Grade 11")
    assert response.get_json()["updated"] == 12
    assert len(students(admin, "&grade=Grade+12")) == 0
    assert len(students(admin, "&grade=Grade+11")) == 24


def test_rules(admin, teacher):
    ids = [s["id"] for s in students(admin)][:2]
    assert error(batch(admin, user_ids=ids)) == "Choose a grade or section to change."
    assert error(batch(admin, user_ids=[], grade="Grade 7")) == "Choose at least one student."
    assert error(batch(admin, user_ids=ids, grade="Grade 13")) == "Choose a grade from the list."
    assert error(batch(admin, user_ids=ids, section="x" * 51)) == "Section can be at most 50 characters."
    assert error(batch(admin, user_ids="1", grade="Grade 7")) == "Choose at least one student."
    teacher_id = admin.get("/api/users?role=teacher").get_json()["users"][0]["id"]
    assert error(batch(admin, user_ids=[ids[0], teacher_id], grade="Grade 7")) == "Only students can be changed here."
    assert students(admin)[0]["grade"] != "Grade 7"  # nothing changed
    assert teacher.put("/api/users/batch", json={"user_ids": ids, "grade": "Grade 7"}).status_code == 403


def test_all_matching_uses_name_and_section_filters(admin):
    response = batch(admin, match={"grade": "Grade 12", "section": "stem"}, section="Atis")
    assert response.get_json()["updated"] == 6
    assert len(students(admin, "&grade=Grade+12&section=Atis")) == 6
    assert len(students(admin, "&grade=Grade+12&section=stem")) == 0
