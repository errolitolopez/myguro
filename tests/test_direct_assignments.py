"""Teacher: giving a sheet directly to individual students, with no class."""

from conftest import assign, error, login, make_activity, make_class

OLD_ASSIGNMENTS_TABLE = """
    CREATE TABLE assignments (
        id INTEGER PRIMARY KEY,
        activity_id INTEGER NOT NULL REFERENCES activities (id),
        class_id INTEGER NOT NULL REFERENCES classes (id),
        everyone INTEGER NOT NULL DEFAULT 1,
        due_date TEXT,
        scores_released INTEGER NOT NULL DEFAULT 0,
        assigned_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE (activity_id, class_id)
    )
"""


def test_migration_makes_class_optional_and_keeps_rows(app, teacher):
    from myguro.database import get_db, init_db

    class_id, students = make_class(teacher)
    activity_id, _ = make_activity(teacher)
    assignment_id = assign(teacher, activity_id, class_id, everyone=False,
                           student_ids=[students[0]["id"]], due_date="2026-10-15")
    student = login(students[0]["username"])
    student.put(f"/api/my-activities/{assignment_id}/answers", json={"answers": {}})
    student.post(f"/api/my-activities/{assignment_id}/submit", json={"answers": {}})

    with app.app_context():
        db = get_db()
        # Put the table back into its old shape (class_id NOT NULL), keeping the rows.
        rows = [dict(row) for row in db.execute("SELECT * FROM assignments")]
        db.commit()
        db.execute("PRAGMA foreign_keys = OFF")
        db.execute("DROP INDEX IF EXISTS one_direct_assignment_per_activity")
        db.execute("DROP TABLE assignments")
        db.execute(OLD_ASSIGNMENTS_TABLE)
        for row in rows:
            db.execute(
                "INSERT INTO assignments (id, activity_id, class_id, everyone, due_date, scores_released, "
                "assigned_at) VALUES (:id, :activity_id, :class_id, :everyone, :due_date, :scores_released, "
                ":assigned_at)", row)
        db.commit()
        db.execute("PRAGMA foreign_keys = ON")

        init_db()  # the upgrade under test

        info = {row["name"]: row for row in db.execute("PRAGMA table_info(assignments)")}
        assert info["class_id"]["notnull"] == 0
        kept = db.execute("SELECT * FROM assignments").fetchall()
        assert [(row["id"], row["class_id"], row["due_date"]) for row in kept] == \
            [(assignment_id, class_id, "2026-10-15")]
        assert db.execute("SELECT COUNT(*) FROM assignment_students WHERE assignment_id = ?",
                          (assignment_id,)).fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM submissions WHERE assignment_id = ? AND submitted_at IS NOT NULL",
                          (assignment_id,)).fetchone()[0] == 1
        # A direct assignment (no class) can now be stored, but only one per activity.
        db.execute("INSERT INTO assignments (activity_id, class_id) VALUES (?, NULL)", (activity_id,))
        try:
            db.execute("INSERT INTO assignments (activity_id, class_id) VALUES (?, NULL)", (activity_id,))
        except Exception as problem:
            assert "UNIQUE" in str(problem)
        else:
            raise AssertionError("a second direct assignment was accepted")
        db.rollback()
