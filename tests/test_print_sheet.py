"""Teacher: print an activity sheet as a PDF (student copy and answer key)."""

from conftest import make_activity


def test_print_student_copy_and_answer_key(teacher, other_teacher):
    activity_id, _ = make_activity(teacher)
    student_copy = teacher.get(f"/activities/{activity_id}/print.pdf")
    assert student_copy.status_code == 200 and student_copy.mimetype == "application/pdf"
    assert student_copy.data.startswith(b"%PDF")
    answer_key = teacher.post(f"/activities/{activity_id}/print.pdf", data={"key": "1", "password": "secret1"})
    assert answer_key.status_code == 200 and answer_key.data.startswith(b"%PDF")
    assert answer_key.data != student_copy.data  # the key adds the answers


def test_print_is_only_for_the_owner(teacher, other_teacher):
    activity_id, _ = make_activity(teacher)
    response = other_teacher.get(f"/activities/{activity_id}/print.pdf")
    assert response.status_code == 302 and "/activities" in response.headers["Location"]


def test_the_sheet_is_printed_in_a_times_style_font(teacher):
    # Liberation Serif has the same letter widths as Times New Roman; the sheet is compact to save paper.
    activity_id, _ = make_activity(teacher)
    data = teacher.get(f"/activities/{activity_id}/print.pdf").data
    assert b"LiberationSerif" in data and b"DejaVu" not in data


def test_the_answer_key_pdf_needs_a_password(teacher):
    activity_id, _ = make_activity(teacher)
    url = f"/activities/{activity_id}/print.pdf"
    assert teacher.get(url + "?key=1").status_code == 302  # never given without a password
    assert b"/Encrypt" not in teacher.get(url).data  # the student copy stays open to print
    for bad in ("", "abc"):
        response = teacher.post(url, data={"key": "1", "password": bad})
        assert response.status_code == 400 and "password" in response.get_json()["error"].lower()
    locked = teacher.post(url, data={"key": "1", "password": "secret1"}).data
    assert b"/Encrypt" in locked
    assert b"Name:" not in locked and b"ANSWER KEY" not in locked  # the text is not readable without the password
