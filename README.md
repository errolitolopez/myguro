# myguro

A learning activity sheet web app: teachers write learning activities with questions, students read them and answer online.

Built with Python (Flask), SQLite, vanilla JavaScript and Bootstrap 5.

## Features

- Login for admin and teachers (no sign-up; 5 wrong tries locks that device + username for 5 minutes; the login ends when the browser is closed)
- Default admin account `admin` / `admin`, created on first start — the password must be changed at first login
- Change password (forced while using a temporary password)
- Dashboard: admin sees totals (teachers, classes, students, activities); teachers see their students, activities, answers submitted, and their classes with class codes

### Planned

Classes, student join with class code, activities with questions, answering and scoring.

## Getting started

Requires Python 3.10+.

```bash
./run.sh          # http://127.0.0.1:5000
./run.sh lan      # also reachable from other devices on the same Wi-Fi
```

Log in with `admin` / `admin` and set a new password.
