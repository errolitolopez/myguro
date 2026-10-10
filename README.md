# myguro

A learning activity sheet web app: teachers write learning activities with questions, students read them and answer online.

Built with Python (Flask), SQLite, vanilla JavaScript and Bootstrap 5.

## Features

- One login page for admin, teachers and students (no sign-up; 5 wrong tries locks that device + username for 5 minutes; the login ends when the browser is closed)
- Default admin account `admin` / `admin`, created on first start — the password must be changed at first login
- Change password (forced while using a temporary password)
- Teachers and Students pages (admin only): the admin makes every account — one account per student for the whole school. Students have an optional grade (Kinder, Grade 1–12) and section (empty for irregular students); the Students page filters by grade. Create with a temporary password (shown once, with a Copy button), search, rename, reset a password, deactivate or activate. Deactivated accounts can't log in; their classes are kept
- Dashboard: admin sees totals (teachers, classes, students, activities); teachers see their students, activities, answers submitted, and their classes; students see their classes and teachers
- Classes (teacher): create classes (name + optional subject), edit them
- Students in a class (teacher): search the school's student list (filter by grade and section) and add them one by one or a whole section with "Add all", search the class, remove a student from the class (account kept). Several teachers add the same student account to their own classes
- Learning activity sheets (teacher, Activities tab): start a sheet with a title and optional subject, then build it section by section (like the LAS parts I–XI). Each section is either **text** (a title + description, for reading) or an **activity** (a title + directions + questions). Question types: multiple choice, true or false, identification (several accepted answers, separated by /), fill in the blank (`___` marks each blank), each with its answer key; and short answer (a short essay the teacher scores, default 5 points, with an optional guide for checking only the teacher sees). Each question has points. Reorder and delete sections and questions, save (Ctrl+S; the page warns about unsaved changes), preview it as students will see it (no answers), delete a sheet. A sheet belongs to the teacher, so it can later be given to several classes

### Planned

Matching type, giving sheets to classes, answering and scoring, results.

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

Adds 6 sample teachers (e.g. `ecruz`, password `teacher123`) and 48 sample students: Grades 9 to 12, two sections each, 6 students per section (e.g. `jdelacruz01`, Grade 9 - Rizal, password `student123`). They can log in right away. Safe to run again: existing usernames are skipped.
