"""Database helpers: open/close the SQLite connection and CLI setup commands."""

import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin"


def get_db():
    """Return the database connection for the current request (opened once per request)."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row  # rows behave like dicts: row["name"]
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the tables and the default admin (safe to run again, existing data is kept)."""
    db = get_db()
    rebuild_users = upgrade_old_tables(db)
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf8"))
    if rebuild_users:
        db.execute(
            "INSERT INTO users (id, name, username, password_hash, role, must_change_password, active, created_at) "
            "SELECT id, name, username, password_hash, role, must_change_password, active, created_at "
            "FROM users_old"
        )
        db.execute("DROP TABLE users_old")
        db.commit()
    add_missing_columns(db)
    create_default_admin(db)


def add_missing_columns(db):
    """CREATE TABLE IF NOT EXISTS skips tables that already exist, so new columns are
    added here for databases created before the column existed."""
    user_columns = [row["name"] for row in db.execute("PRAGMA table_info(users)")]
    if "grade" not in user_columns:
        db.execute("ALTER TABLE users ADD COLUMN grade TEXT NOT NULL DEFAULT ''")
    if "section" not in user_columns:
        db.execute("ALTER TABLE users ADD COLUMN section TEXT NOT NULL DEFAULT ''")

    section_columns = [row["name"] for row in db.execute("PRAGMA table_info(activity_sections)")]
    if "kind" not in section_columns:
        db.execute(
            "ALTER TABLE activity_sections ADD COLUMN kind TEXT NOT NULL DEFAULT 'text' "
            "CHECK (kind IN ('text', 'activity'))"
        )
    db.commit()


# Tables from before students became accounts (when they joined with a class code + PIN).
OLD_CLASS_TABLES = ["submission_answers", "submissions", "questions", "activities", "students", "classes"]


# Tables from before activities belonged to the teacher (they had a class_id).
OLD_ACTIVITY_TABLES = ["submission_answers", "submissions", "questions", "activities"]


def upgrade_old_tables(db):
    """Update a database made by an older version of schema.sql. Accounts are kept.

    CREATE TABLE IF NOT EXISTS skips tables that already exist, so changed tables are
    handled here. Returns True when users was renamed to users_old: init_db() then
    copies the accounts into the new users table.
    """
    tables = {row["name"] for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}

    # Old class tables: there was no page to fill them yet, so they are only dropped when empty.
    if "students" in tables:
        for table in OLD_CLASS_TABLES:
            if db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]:
                raise RuntimeError(f"Can't upgrade: the old {table} table has data.")
        for table in OLD_CLASS_TABLES:
            db.execute(f"DROP TABLE {table}")
        db.commit()

    # Activities used to belong to one class (class_id); now they belong to the teacher.
    # There was no page to make activities yet, so these are only dropped when empty.
    if "activities" in tables:
        activity_columns = [row["name"] for row in db.execute("PRAGMA table_info(activities)")]
        if "class_id" in activity_columns:
            for table in OLD_ACTIVITY_TABLES:
                if db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]:
                    raise RuntimeError(f"Can't upgrade: the old {table} table has data.")
            for table in OLD_ACTIVITY_TABLES:
                db.execute(f"DROP TABLE {table}")
            db.commit()

    # Questions now belong to a section (section_id). There was no page to make questions
    # yet, so the old table is only dropped when empty.
    if "questions" in tables:
        question_columns = [row["name"] for row in db.execute("PRAGMA table_info(questions)")]
        if question_columns and "section_id" not in question_columns:
            if db.execute("SELECT COUNT(*) FROM questions").fetchone()[0]:
                raise RuntimeError("Can't upgrade: the old questions table has data.")
            db.execute("DROP TABLE questions")
            db.commit()

    # users allowed only admin and teacher. SQLite can't change a CHECK, so the table is rebuilt.
    users = db.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'").fetchone()
    if users and "'student'" not in users["sql"]:
        db.execute("ALTER TABLE users RENAME TO users_old")
        db.commit()
        return True
    return False


def create_default_admin(db):
    """Add the admin/admin account if there is no admin yet. Its password must be changed on first login."""
    has_admin = db.execute("SELECT 1 FROM users WHERE role = 'admin'").fetchone()
    if has_admin:
        return
    db.execute(
        "INSERT INTO users (name, username, password_hash, role, must_change_password) "
        "VALUES ('Administrator', ?, ?, 'admin', 1)",
        (DEFAULT_ADMIN_USERNAME, generate_password_hash(DEFAULT_ADMIN_PASSWORD)),
    )
    db.commit()


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Create the tables (safe to run again, existing data is kept)."""
    init_db()
    click.echo("Database ready.")


def init_app(app):
    """Register the database helpers with the Flask app."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    # Make sure the tables and the default admin exist before the first request.
    with app.app_context():
        init_db()
