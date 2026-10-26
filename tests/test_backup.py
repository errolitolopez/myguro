"""Backups: a complete copy of the data, the download, the console command and the reminder."""

import os
import sqlite3
from datetime import datetime, timedelta, timezone

from conftest import flask_app, login, make_class


def open_copy(tmp_path, data):
    path = tmp_path / "copy.db"
    path.write_bytes(data)
    return sqlite3.connect(path)


def set_last_backup(text):
    connection = sqlite3.connect(os.environ["MYGURO_DATABASE"])
    connection.execute("INSERT INTO settings (key, value) VALUES ('last_backup_at', ?) "
                       "ON CONFLICT (key) DO UPDATE SET value = excluded.value", (text,))
    connection.commit()
    connection.close()


def test_the_download_is_a_complete_valid_copy(admin, teacher, tmp_path):
    make_class(teacher)
    response = admin.get("/backup/download")
    assert response.status_code == 200
    assert response.mimetype == "application/vnd.sqlite3"
    assert 'filename="myguro-backup-' in response.headers["Content-Disposition"]
    assert response.headers["Cache-Control"] == "no-store"
    copy = open_copy(tmp_path, response.data)
    assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert copy.execute("SELECT name FROM classes").fetchall() == [("Grade 9 - Rizal",)]
    assert ("admin",) in copy.execute("SELECT username FROM users").fetchall()


def test_the_download_is_for_the_admin_only(admin, teacher, supervisor):
    assert teacher.get("/backup/download").status_code == 403
    assert supervisor.get("/backup/download").status_code == 403
    assert flask_app.test_client().get("/backup/download").status_code == 401


def test_the_download_is_in_the_activity_log(admin):
    admin.get("/backup/download")
    entries = admin.get("/api/log?q=backup").get_json()["entries"]
    assert any(entry["action"] == "backup.downloaded" for entry in entries)


def test_the_dashboard_says_there_was_never_a_backup_then_today(admin):
    html = admin.get("/dashboard").get_data(as_text=True)
    assert "Last backup: never" in html and "backup-warning" in html
    admin.get("/backup/download")
    html = admin.get("/dashboard").get_data(as_text=True)
    assert "Last backup: today" in html and "backup-warning" not in html


def test_the_dashboard_warns_when_the_last_backup_is_old(admin):
    set_last_backup((datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S"))
    html = admin.get("/dashboard").get_data(as_text=True)
    assert "Last backup: 10 days ago" in html and "backup-warning" in html
    set_last_backup((datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"))
    html = admin.get("/dashboard").get_data(as_text=True)
    assert "Last backup: 3 days ago" in html and "backup-warning" not in html


def test_teachers_do_not_see_the_backup_card(teacher):
    assert "Download backup" not in teacher.get("/dashboard").get_data(as_text=True)


def test_the_console_command_writes_a_copy_and_keeps_only_the_newest(tmp_path):
    runner = flask_app.test_cli_runner()
    for _ in range(3):
        result = runner.invoke(args=["backup", "--to", str(tmp_path), "--keep", "2"])
        assert result.exit_code == 0, result.output
    names = sorted(os.listdir(tmp_path))
    assert len(names) == 2 and all(name.startswith("myguro-") and name.endswith(".db") for name in names)
    assert sqlite3.connect(tmp_path / names[-1]).execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert runner.invoke(args=["backup", "--to", str(tmp_path), "--keep", "0"]).exit_code != 0
