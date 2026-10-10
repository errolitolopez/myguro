"""Bringing a database made by an older version of schema.sql up to date. Existing data is kept.

CREATE TABLE IF NOT EXISTS (schema.sql) skips tables that already exist, so changed tables
are handled here: upgrade_old_tables() runs before schema.sql, add_missing_columns() after.
"""

from myguro.domain.accounts import display_name, guess_name_parts

# Tables from before students became accounts (when they joined with a class code + PIN).
OLD_CLASS_TABLES = ["submission_answers", "submissions", "questions", "activities", "students", "classes"]


# Tables from before activities belonged to the teacher (they had a class_id).
OLD_ACTIVITY_TABLES = ["submission_answers", "submissions", "questions", "activities"]


def upgrade_old_tables(db):
    """Update a database made by an older version of schema.sql. Accounts are kept.

    CREATE TABLE IF NOT EXISTS skips tables that already exist, so changed tables are
    handled here. Returns the tables renamed to <table>_old to be rebuilt: init_db() copies
    their rows into the new tables made by schema.sql.
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

    # activity_classes was replaced by assignments before anything could be assigned,
    # so it is only dropped when empty. (Old databases also keep an unused activities.status.)
    if "activity_classes" in tables:
        if db.execute("SELECT COUNT(*) FROM activity_classes").fetchone()[0]:
            raise RuntimeError("Can't upgrade: the old activity_classes table has data.")
        db.execute("DROP TABLE activity_classes")
        db.commit()

    # Submissions now belong to an assignment and can be saved before submitting.
    # Nothing could be submitted before, so the old tables are only dropped when empty.
    if "submissions" in tables:
        submission_columns = [row["name"] for row in db.execute("PRAGMA table_info(submissions)")]
        if submission_columns and "assignment_id" not in submission_columns:
            for table in ("submission_answers", "submissions"):
                if db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]:
                    raise RuntimeError(f"Can't upgrade: the old {table} table has data.")
            db.execute("DROP TABLE submission_answers")
            db.execute("DROP TABLE submissions")
            db.commit()

    # users allowed only admin and teacher. SQLite can't change a CHECK, so the table is rebuilt.
    rebuilt = []
    users = db.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'").fetchone()
    if users and "'student'" not in users["sql"]:
        rename_for_rebuild(db, "users")
        rebuilt.append("users")

    # A student can now submit more than once (attempt 1, 2, ...): the one-per-student
    # UNIQUE rule changed, so the table is rebuilt. Existing work becomes attempt 1.
    submission_columns = [row["name"] for row in db.execute("PRAGMA table_info(submissions)")]
    if submission_columns and "attempt" not in submission_columns:
        rename_for_rebuild(db, "submissions")
        rebuilt.append("submissions")
    return rebuilt


def rename_for_rebuild(db, table):
    """Rename table to <table>_old; schema.sql then makes the new table and init_db() copies
    the rows back (copy_old_rows).

    Other tables' REFERENCES <table> must keep that name so they point to the new table.
    SQLite rewrites them on rename unless legacy_alter_table is ON *and* foreign_keys is OFF
    (foreign_keys can only be switched outside a transaction, hence the commit first).
    """
    db.commit()
    db.execute("PRAGMA foreign_keys = OFF")
    db.execute("PRAGMA legacy_alter_table = ON")
    db.execute(f"ALTER TABLE {table} RENAME TO {table}_old")
    db.execute("PRAGMA legacy_alter_table = OFF")
    db.execute("PRAGMA foreign_keys = ON")


def copy_old_rows(db, table):
    """Copy the rows of <table>_old into the new <table> (the columns both have), then drop it."""
    new_columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
    columns = ", ".join(row["name"] for row in db.execute(f"PRAGMA table_info({table}_old)")
                        if row["name"] in new_columns)
    db.execute(f"INSERT INTO {table} ({columns}) SELECT {columns} FROM {table}_old")
    db.execute(f"DROP TABLE {table}_old")
    db.commit()


def add_missing_columns(db):
    """CREATE TABLE IF NOT EXISTS skips tables that already exist, so new columns are
    added here for databases created before the column existed."""
    user_columns = [row["name"] for row in db.execute("PRAGMA table_info(users)")]
    if "grade" not in user_columns:
        db.execute("ALTER TABLE users ADD COLUMN grade TEXT NOT NULL DEFAULT ''")
    if "section" not in user_columns:
        db.execute("ALTER TABLE users ADD COLUMN section TEXT NOT NULL DEFAULT ''")
    if "activated" not in user_columns:
        db.execute("ALTER TABLE users ADD COLUMN activated INTEGER NOT NULL DEFAULT 1")
        # Disabled students with no class and no work were never used: still fresh.
        db.execute(
            "UPDATE users SET activated = 0 WHERE role = 'student' AND active = 0 "
            "AND id NOT IN (SELECT student_id FROM class_students) "
            "AND id NOT IN (SELECT student_id FROM submissions)"
        )
    if "last_name" not in user_columns:
        db.execute("ALTER TABLE users ADD COLUMN last_name TEXT NOT NULL DEFAULT ''")
        db.execute("ALTER TABLE users ADD COLUMN first_name TEXT NOT NULL DEFAULT ''")
        db.execute("ALTER TABLE users ADD COLUMN middle_initial TEXT NOT NULL DEFAULT ''")
        split_old_names(db)

    activity_columns = [row["name"] for row in db.execute("PRAGMA table_info(activities)")]
    if "max_attempts" not in activity_columns:
        db.execute("ALTER TABLE activities ADD COLUMN max_attempts INTEGER DEFAULT 1")

    assignment_columns = [row["name"] for row in db.execute("PRAGMA table_info(assignments)")]
    if "scores_released" not in assignment_columns:
        db.execute("ALTER TABLE assignments ADD COLUMN scores_released INTEGER NOT NULL DEFAULT 0")

    submission_columns = [row["name"] for row in db.execute("PRAGMA table_info(submissions)")]
    if "paper" not in submission_columns:
        db.execute("ALTER TABLE submissions ADD COLUMN paper INTEGER NOT NULL DEFAULT 0")
        db.execute("ALTER TABLE submissions ADD COLUMN paper_score INTEGER")
        db.execute("ALTER TABLE submissions ADD COLUMN note TEXT NOT NULL DEFAULT ''")

    section_columns = [row["name"] for row in db.execute("PRAGMA table_info(activity_sections)")]
    if "kind" not in section_columns:
        db.execute(
            "ALTER TABLE activity_sections ADD COLUMN kind TEXT NOT NULL DEFAULT 'text' "
            "CHECK (kind IN ('text', 'activity'))"
        )
    if "description_format" not in section_columns:
        db.execute(
            "ALTER TABLE activity_sections ADD COLUMN description_format TEXT NOT NULL DEFAULT 'plain' "
            "CHECK (description_format IN ('plain', 'rich'))"
        )
    db.commit()


def split_old_names(db):
    """Teachers and students saved with one name ("Juan Dela Cruz") get Last, First, M.I.
    (a guess: commas if any, else the last word is the last name; the admin can fix it)."""
    for row in db.execute("SELECT id, name FROM users WHERE role IN ('teacher', 'student')").fetchall():
        last, first, middle = guess_name_parts(row["name"])
        db.execute("UPDATE users SET last_name = ?, first_name = ?, middle_initial = ?, name = ? WHERE id = ?",
                   (last, first, middle, display_name(last, first, middle), row["id"]))

