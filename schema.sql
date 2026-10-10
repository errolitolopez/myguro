-- myguro tables. Safe to run again: existing tables and data are kept.

-- Admin and teacher accounts. There is no sign-up: the admin creates teachers.
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'teacher')),
    must_change_password INTEGER NOT NULL DEFAULT 1,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users (id),
    name TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY,
    class_id INTEGER NOT NULL REFERENCES classes (id),
    name TEXT NOT NULL COLLATE NOCASE,
    pin_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (class_id, name)
);

CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY,
    class_id INTEGER NOT NULL REFERENCES classes (id),
    title TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published')),
    due_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY,
    activity_id INTEGER NOT NULL REFERENCES activities (id),
    position INTEGER NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('multiple_choice', 'true_false', 'short_answer')),
    prompt TEXT NOT NULL,
    choices TEXT,  -- JSON list, for multiple choice
    answer TEXT NOT NULL,
    points INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY,
    activity_id INTEGER NOT NULL REFERENCES activities (id),
    student_id INTEGER NOT NULL REFERENCES students (id),
    submitted_at TEXT NOT NULL DEFAULT (datetime('now')),
    score INTEGER NOT NULL DEFAULT 0,
    UNIQUE (activity_id, student_id)
);

CREATE TABLE IF NOT EXISTS submission_answers (
    id INTEGER PRIMARY KEY,
    submission_id INTEGER NOT NULL REFERENCES submissions (id),
    question_id INTEGER NOT NULL REFERENCES questions (id),
    answer TEXT NOT NULL,
    is_correct INTEGER NOT NULL DEFAULT 0,
    points INTEGER NOT NULL DEFAULT 0
);
