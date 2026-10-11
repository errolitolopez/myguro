# myguro

A learning activity sheet web app: teachers write learning activities with questions, students read them and answer online.

Built with Python (Flask), SQLite, vanilla JavaScript and Bootstrap 5.

## Features

- Names are **Last name, First name, Middle initial (optional)**, typed in three boxes and shown as "Altamerano, Rian Joshua J."; every list sorts by last name. Usernames are suggested as first letter + last name (raltamerano)

- One login page for admin, teachers and students (no sign-up; 5 wrong tries locks that device + username for 5 minutes; the login ends when the browser is closed)
- Default admin account `admin` / `admin`, created on first start — the password must be changed at first login
- Change password (forced while using a temporary password)
- Batch edit (Students page): tick students (kept across pages), a whole page, or all students matching the search and filters, then change their grade and/or section at once (keep as is, set, or no grade / no section)
- Teachers and Students pages (admin only), 20 per page with Prev / Next; search (name, username, section) and, on the Students page, the **Filters** panel (full name in any order, grade, section) run on the server across all accounts: the admin makes every account — one account per student for the whole school. Students have an optional grade (Kinder, Grade 1–12) and section (empty for irregular students); the Students page filters by grade. **Import from Excel** (Students page): download the template (Last name and First name required; Middle initial, Username, Grade, Section, Password optional — or one Name column written "Altamerano, Rian Joshua, J"), check the file — a preview, or every problem with its row number — then import. All or nothing: a file with a bad row imports no one. Empty usernames are made from the name (with a number if taken), empty passwords are made, grades can be typed as "9". Afterwards download the login details (CSV) to give out Create with a temporary password (shown once, with a Copy button), search, rename, reset a password, deactivate or activate. Deactivated accounts can't log in; their classes are kept
- Settings (admin): one school-wide switch saved in the database — show grades from highest to lowest (Grade 12 first, the default) or lowest to highest (Kinder first) in every grade dropdown. Grades the school doesn't use can be turned off: they leave the dropdowns and can't be given to a student (students who have one keep it, and the Students filter still lists it so they can be moved)
- Support link (admin, Settings): an optional "Support myguro" note in the footer; its button opens a window listing the ways to give (a Ko-fi link and/or a GCash number with a Copy button; more can be added), for admin and teachers, never for students. Off by default; the admin sets the link, message and button text and turns it on or off
- Every page has a small footer: "myguro is a free, non-profit tool for schools."
- Dashboard: admin sees totals (teachers, classes, students, activities); teachers see their students, activities, answers submitted, and their classes; students see their classes and teachers
- Classes (teacher): create classes (name + optional subject), edit them
- Students in a class (teacher): search the school's student list (filter by grade and section) and add them one by one or a whole section with "Add all", search the class, remove a student from the class (account kept). Several teachers add the same student account to their own classes
- Learning activity sheets (teacher, Activities tab): start a sheet with a title and optional subject, then build it section by section (like the LAS parts I–XI). Each section is either **text** (a title + description, for reading) or an **activity** (a title + directions + questions). Question types: multiple choice, true or false, identification (several accepted answers, separated by /), fill in the blank (`___` marks each blank), each with its answer key; and short answer (a short essay the teacher scores, default 5 points, with an optional guide for checking only the teacher sees). Each question has points. Reorder and delete sections and questions, save (Ctrl+S; the page warns about unsaved changes), preview it as students will see it (no answers), delete a sheet. A sheet belongs to the teacher, so it can later be given to several classes
- Assign (teacher): from the activity editor, give a sheet to one or more classes — to everyone in the class (also students added later) or to selected students — with an optional due date. Late work will still be accepted, marked late. The class page lists its activities; sheets show Assigned or Draft
- Students: My activities (To do / Submitted, with due dates, overdue and late), answer page for all question types (answers save automatically as they go), submit and see the score right away — short answers wait for the teacher. The teacher sets how many submissions are allowed per activity (1–10 or unlimited); with tries left, Try again starts a new attempt with the last answers, and the latest submission counts. Checking: identification and fill in the blank ignore capitals and extra spaces; fill in the blank gives part of the points per right blank. Once a student submits, the teacher can no longer edit that sheet
- Results (teacher): per class and activity — submitted / not started / late / average / points to check, and a table of every student with their score and a score per activity section (e.g. pre-test vs post-test), with search and filters. Tap a student to see their answers next to the answer key, score short answers, change any question's points (e.g. accept another spelling), look at earlier attempts, or give them another try. For a student who answered on paper, enter a paper score (the total, optional late and note); it counts like a submission and can be edited or removed. After a paper score the student can't answer online unless the teacher gives them another try
- Export results to Excel or PDF from the results page: summary and one row per student with status, submitted time, score, percent and a score per activity section (Excel for computing grades, PDF to print or send)

### Planned

Matching type, tables in text sections, import from Word, export results.

## Getting started

Requires Python 3.10+.

```bash
./run.sh          # http://127.0.0.1:5000
./run.sh lan      # also reachable from other devices on the same Wi-Fi
```

Log in with `admin` / `admin` and set a new password.

### Sample data

```bash
.venv/bin/flask --app app seed
```

Adds 6 sample teachers (e.g. `ecruz`) and 48 sample students: Grades 9 to 12, two sections each, 6 students per section (e.g. `jdelacruz01`, Grade 9 - Rizal). All sample accounts use the password `1234`. They can log in right away. Safe to run again: existing usernames are skipped.

## Code structure

```
app.py                  entry point (flask --app app ...): app = create_app()
myguro/
  __init__.py           create_app(): config, database, blueprints, CLI commands
  config.py             database path, secret key, school time zone
  errors.py             ValidationError / NotFoundError / ... -> JSON {"error": ...}
  database.py           connection per request, init-db, default admin
  migrations.py         upgrading databases made by older versions
  schema.sql            the tables
  seed.py               flask --app app seed (sample accounts)
  exports.py            results to Excel / PDF
  imports.py            reading students from an Excel file, and its template
  domain/               rules with no Flask or SQL: cleaning input, sheets and questions,
                        checking answers, adding up scores, due dates and tries
  repositories/         all SQL, one class per kind of data (users, classes, activities,
                        assignments, submissions); they never commit
  services/             use cases, one class per area (auth, accounts, classes, activities,
                        assignments, student work, results, dashboard); they commit
  web/                  Flask blueprints, one per area (pages + JSON API), login/role checks
  templates/, static/, fonts/
tests/                  pytest suite
```

Each layer only uses the ones below it: web → services → repositories / domain.
A route reads the request, calls a service, and returns JSON; a service raises
`ValidationError("...")` (or `NotFoundError`, ...) and the error becomes `{"error": "..."}`
with the right status, with nothing saved.

## Tests

```bash
.venv/bin/pip install -r requirements-dev.txt   # once
.venv/bin/pytest
```

Every test starts from a fresh throwaway database with the sample accounts.

