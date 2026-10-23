"""Reading students and activity sheets from an uploaded Excel file, and the templates to fill in.

Students: Last name, First name, Middle initial (optional) columns, or one Name column.
Activity sheets: one row per section or question (Row, Title, Description, Question type, ...).

Only the reading is here (rows of text by column); the rules for each student are in
services/accounts.py (AccountService.import_students), the ones for a sheet in
domain/sheet_import.py.
"""

import io
import zipfile

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from myguro.domain.accounts import GRADES
from myguro.errors import ValidationError

MAX_ROWS = 1000
COLUMNS = ["Last name", "First name", "Middle initial", "Username", "Grade", "Section", "Password"]
# Column names people may use, lowercased -> the field. Instead of the three name columns, one
# "Name" column written "Last, First" also works.
HEADER_NAMES = {
    "last name": "last_name", "lastname": "last_name", "surname": "last_name", "family name": "last_name",
    "first name": "first_name", "firstname": "first_name", "given name": "first_name",
    "middle initial": "middle_initial", "mi": "middle_initial", "m.i.": "middle_initial", "m.i": "middle_initial",
    "middle name": "middle_initial",
    "name": "name", "full name": "name", "student name": "name",
    "username": "username", "user name": "username",
    "grade": "grade", "grade level": "grade",
    "section": "section",
    "password": "password", "temporary password": "password",
}


def cell_text(value):
    """A cell as text: 8.0 -> "8", None -> ""."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def read_table(content, header_names, header_ok, header_message, empty_message, max_rows, too_many_message):
    """[(row number, {field: text})] from the first sheet of an .xlsx file (bytes).
    Row numbers are as Excel shows them (the column names are row 1); empty rows are skipped.
    header_names maps a lowercased column name to its field; header_ok(fields) says if the
    columns are enough."""
    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except (zipfile.BadZipFile, KeyError, ValueError, OSError):
        raise ValidationError("This is not an Excel .xlsx file. In Excel, use Save As → "
                              "Excel Workbook (.xlsx).") from None
    sheet = workbook.worksheets[0]
    rows = sheet.iter_rows(values_only=True)
    header = next(rows, None) or ()
    fields = [header_names.get(cell_text(value).lower()) for value in header]
    if not header_ok(set(fields)):
        raise ValidationError(header_message)

    records = []
    for number, values in enumerate(rows, start=2):
        record = {field: "" for field in set(header_names.values())}
        for field, value in zip(fields, values):
            if field:
                record[field] = cell_text(value)
        if any(record.values()):
            records.append((number, record))
            if len(records) > max_rows:
                raise ValidationError(too_many_message)
    workbook.close()
    if not records:
        raise ValidationError(empty_message)
    return records


def read_student_rows(content):
    """[(row number, {last_name, first_name, middle_initial, name, username, grade, section,
    password})] from an .xlsx file (bytes)."""
    return read_table(
        content, HEADER_NAMES,
        lambda fields: {"last_name", "first_name"} <= fields or "name" in fields,
        'The first row must have the column names: "Last name" and "First name" (or one "Name" column).',
        "The file has no students.",
        MAX_ROWS, f"The file has more than {MAX_ROWS} students. Split it into smaller files.")


def template_xlsx_bytes():
    """The file to fill in: the columns (Grade as a dropdown) and a sheet explaining them."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Students"
    sheet.append(COLUMNS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="E9ECEF")
    for letter, width in zip("ABCDEFG", (20, 24, 15, 18, 12, 16, 18)):
        sheet.column_dimensions[letter].width = width
    grades = DataValidation(type="list", formula1='"' + ",".join(GRADES) + '"', allow_blank=True)
    grades.add(f"E2:E{MAX_ROWS + 1}")
    sheet.add_data_validation(grades)
    sheet.freeze_panes = "A2"

    help_sheet = workbook.create_sheet("How to fill")
    for line in [
        ["One student per row on the Students sheet. Keep the first row (the column names)."],
        [],
        ["Last name", "Required, e.g. Altamerano or Dela Cruz."],
        ["First name", "Required, e.g. Rian Joshua."],
        ["Middle initial", "Optional, one letter, e.g. M."],
        ["Username", "Optional. Leave empty to make one from the name (Altamerano, Rian Joshua -> raltamerano)."],
        ["Grade", "Optional. Kinder or Grade 1 to Grade 12 (you can also type just 9)."],
        ["Section", "Optional. Leave empty for irregular students."],
        ["Password", "Optional, at least 6 characters. Leave empty to make one."],
        [],
        ["Students change their password the first time they log in."],
        ["Instead of the three name columns you can use one Name column: Altamerano, Rian Joshua, M"],
    ]:
        help_sheet.append(line)
    help_sheet.column_dimensions["A"].width = 14
    help_sheet.column_dimensions["B"].width = 80

    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


# ---- Activity sheets ----------------------------------------------------------------------------

MAX_SHEET_ROWS = 500
CHOICE_FIELDS = [f"choice_{letter}" for letter in "abcdef"]
SHEET_COLUMNS = ["Row", "Title", "Description", "Question type",
                 "Choice A", "Choice B", "Choice C", "Choice D", "Choice E", "Choice F", "Answer", "Points"]
SHEET_HEADER_NAMES = {
    "row": "row", "row type": "row", "kind": "row", "type": "row",
    "title": "title", "section title": "title",
    "description": "description", "text": "description", "directions": "description",
    "prompt": "description", "question": "description",
    "question type": "question_type", "activity type": "question_type", "answer type": "question_type",
    "answer": "answer", "correct answer": "answer", "key": "answer",
    "points": "points", "point": "points", "score": "points",
}
for _letter in "abcdef":
    SHEET_HEADER_NAMES[f"choice {_letter}"] = f"choice_{_letter}"
    SHEET_HEADER_NAMES[f"choice{_letter}"] = f"choice_{_letter}"
    SHEET_HEADER_NAMES[_letter] = f"choice_{_letter}"


def read_sheet_rows(content):
    """[(row number, {row, title, description, question_type, choice_a..choice_f, answer, points})]
    from an activity sheet .xlsx file (bytes)."""
    return read_table(
        content, SHEET_HEADER_NAMES,
        lambda fields: "row" in fields and ("title" in fields or "description" in fields),
        'The first row must have the column names "Row", "Title" and "Description" '
        "(download the template to see them all).",
        "The file has no rows.",
        MAX_SHEET_ROWS, f"The file has more than {MAX_SHEET_ROWS} rows. Split it into smaller sheets.")


def sheet_template_xlsx_bytes():
    """The file to fill in: the columns (Row and Question type as dropdowns), an example, and
    a sheet explaining them. Only the first sheet is imported."""
    from myguro.domain.sheets import QUESTION_TYPES

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Activity"
    sheet.append(SHEET_COLUMNS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="E9ECEF")
    for letter, width in zip("ABCDEFGHIJKL", (12, 28, 60, 20, 16, 16, 16, 16, 16, 16, 28, 9)):
        sheet.column_dimensions[letter].width = width
    kinds = DataValidation(type="list", formula1='"text,activity,question"', allow_blank=True)
    kinds.add(f"A2:A{MAX_SHEET_ROWS + 1}")
    types = DataValidation(type="list", formula1='"' + ",".join(QUESTION_TYPES) + '"', allow_blank=True)
    types.add(f"D2:D{MAX_SHEET_ROWS + 1}")
    sheet.add_data_validation(kinds)
    sheet.add_data_validation(types)
    sheet.freeze_panes = "A2"

    example = workbook.create_sheet("Example")
    example.append(SHEET_COLUMNS)
    for cell in example[1]:
        cell.font = Font(bold=True)
    for line in [
        ("text", "I. Lesson", "Reading material for the students.", "", "", "", "", "", "", "", "", ""),
        ("activity", "II. Let's check", "Directions: answer the questions.", "", "", "", "", "", "", "", "", ""),
        ("question", "", "What is 2 + 2?", "multiple_choice", "3", "4", "5", "", "", "", "B", 1),
        ("question", "", "The sky is blue.", "true_false", "", "", "", "", "", "", "True", 1),
        ("question", "", "Capital of the Philippines?", "identification", "", "", "", "", "", "",
         "Manila / City of Manila", 2),
        ("question", "", "___ is the capital of ___.", "fill_blank", "", "", "", "", "", "",
         "Manila ; Philippines", 2),
        ("question", "", "Match the country with its capital.", "matching", "Tokyo", "", "", "", "", "",
         "Philippines = Manila ; Japan = Kyoto ; Thailand = Bangkok", 3),
        ("question", "", "Explain why the sky is blue.", "short_answer", "", "", "", "", "", "",
         "Mention scattering of light (optional guide for checking)", 5),
    ]:
        example.append(line)
    for letter, width in zip("ABCDEFGHIJKL", (12, 20, 40, 20, 8, 8, 8, 8, 8, 8, 50, 9)):
        example.column_dimensions[letter].width = width

    help_sheet = workbook.create_sheet("How to fill")
    for line in [
        ["One row per section or question, in the order students see them. Keep the first row (the column names)."],
        ["See the Example sheet. Only the Activity sheet is imported."],
        [],
        ["Row", "text = a reading section (Title + Description). activity = a section with questions "
                "(Title + Description as directions). question = a question of the activity row above it."],
        ["Title", "For text and activity rows. Leave empty on question rows."],
        ["Description", "text: the reading. activity: the directions. question: the question itself."],
        ["Question type", "multiple_choice, true_false, identification, fill_blank, matching or short_answer "
                          "(question rows only)."],
        ["Choice A to F", "Multiple choice: 2 to 6 choices, filled from A without gaps. "
                          "Matching: optional extra choices that match nothing."],
        ["Answer", "Multiple choice: the letter (B). True or false: True or False. "
                   "Identification: accepted answers split by a slash with spaces around it (Manila / City of Manila); "
                   "a slash without spaces, like 1/2, is part of the answer. "
                   "Fill in the blank: put ___ for each blank in the Description and one answer per blank "
                   "split by ; (more spellings of one blank split by \" / \"). "
                   "Matching: the Description is the instruction; the Answer is item = match pairs split by ; "
                   "(Hinduism = India ; Taoism = China), 2 to 10 pairs. Column B is made from the matches "
                   "(sorted A to Z) plus any extra choices in Choice A to F. Don't use = or ; inside a pair. "
                   "Short answer: an optional guide for checking."],
        ["Points", "Optional, 1 to 100. Empty = 1 (short answer = 5)."],
    ]:
        help_sheet.append(line)
    help_sheet.column_dimensions["A"].width = 16
    help_sheet.column_dimensions["B"].width = 100

    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def sheet_xlsx_bytes(activity):
    """An activity as an Excel file in the import format (one row per section or question), so the
    teacher can keep it, edit it, or import it as a new activity. activity is ActivityService.get."""
    from myguro.domain.richtext import rich_to_text

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Activity"
    sheet.append(SHEET_COLUMNS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="E9ECEF")
    for letter, width in zip("ABCDEFGHIJKL", (12, 28, 60, 20, 16, 16, 16, 16, 16, 16, 28, 9)):
        sheet.column_dimensions[letter].width = width
    sheet.freeze_panes = "A2"
    wrap = Alignment(wrap_text=True, vertical="top")

    for section in activity["sections"]:
        description = rich_to_text(section["description"]) if section["description_format"] == "rich" \
            else section["description"]
        sheet.append([section["kind"], section["title"], description])
        for question in section["questions"]:
            choices, answer = question_cells(question)
            choices = choices + [""] * (len(CHOICE_FIELDS) - len(choices))  # keeps Answer in its column
            sheet.append(["question", "", question["prompt"], question["type"], *choices, answer, question["points"]])
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = wrap
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def question_cells(question):
    """([Choice A to F], the Answer cell) of a question, as the importer reads them."""
    kind, answer, choices = question["type"], question["answer"], question["choices"] or []
    if kind == "multiple_choice":
        return choices, "ABCDEF"[answer]
    if kind == "true_false":
        return [], "True" if answer else "False"
    if kind == "identification":
        return [], " / ".join(answer)
    if kind == "fill_blank":
        return [], " ; ".join(" / ".join(blank) for blank in answer)
    if kind == "matching":
        # Column B comes back sorted from the matches, so only the unused choices are listed
        used = {pair["match"] for pair in answer}
        extras = [choice for index, choice in enumerate(choices) if index not in used][:len(CHOICE_FIELDS)]
        return extras, " ; ".join(f"{pair['item']} = {choices[pair['match']]}" for pair in answer)
    return [], answer or ""  # short answer: the guide for checking
