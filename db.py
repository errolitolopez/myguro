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
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf8"))
    create_default_admin(db)


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
