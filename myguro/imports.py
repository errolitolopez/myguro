"""Reading students from an uploaded Excel file, and the template to fill in.

Names: Last name, First name, Middle initial (optional) columns, or one Name column.

Only the reading is here (rows of text by column); the rules for each student are in
services/accounts.py (AccountService.import_students).
"""

import io
import zipfile

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
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


def read_student_rows(content):
    """[(row number, {last_name, first_name, middle_initial, name, username, grade, section,
    password})] from an .xlsx file (bytes).
    Row numbers are as Excel shows them (the column names are row 1); empty rows are skipped."""
    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except (zipfile.BadZipFile, KeyError, ValueError, OSError):
        raise ValidationError("This is not an Excel .xlsx file. In Excel, use Save As → "
                              "Excel Workbook (.xlsx).") from None
    sheet = workbook.worksheets[0]
    rows = sheet.iter_rows(values_only=True)
    header = next(rows, None) or ()
    fields = [HEADER_NAMES.get(cell_text(value).lower()) for value in header]
    if not ({"last_name", "first_name"} <= set(fields) or "name" in fields):
        raise ValidationError('The first row must have the column names: "Last name" and "First name" '
                              '(or one "Name" column).')

    students = []
    for number, values in enumerate(rows, start=2):
        record = {field: "" for field in set(HEADER_NAMES.values())}
        for field, value in zip(fields, values):
            if field:
                record[field] = cell_text(value)
        if any(record.values()):
            students.append((number, record))
            if len(students) > MAX_ROWS:
                raise ValidationError(f"The file has more than {MAX_ROWS} students. Split it into smaller files.")
    workbook.close()
    if not students:
        raise ValidationError("The file has no students.")
    return students


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
