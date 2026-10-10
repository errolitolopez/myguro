-- myguro tables. Safe to run again: existing tables and data are kept.

-- All accounts. There is no sign-up: the admin creates teachers, teachers create students.
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'teacher', 'student')),
    must_change_password INTEGER NOT NULL DEFAULT 1,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    -- Students only, both optional (an irregular student may have no section): "Grade 6", "Rizal"
    grade TEXT NOT NULL DEFAULT '',
    section TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users (id),
    name TEXT NOT NULL,
    subject TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Which students are in which class. A student can be in several classes (one per subject).
CREATE TABLE IF NOT EXISTS class_students (
    class_id INTEGER NOT NULL REFERENCES classes (id),
    student_id INTEGER NOT NULL REFERENCES users (id),
    added_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (class_id, student_id)
);

-- A learning activity sheet. It belongs to the teacher who wrote it, so the same sheet
-- can be given to several classes (activity_classes).
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users (id),
    title TEXT NOT NULL,
    subject TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- The parts of a sheet (like "I. Title of the Lesson", "III. Pre-test"), in position order.
-- kind: 'text' = a title + description only; 'activity' = a title + directions + questions.
CREATE TABLE IF NOT EXISTS activity_sections (
    id INTEGER PRIMARY KEY,
    activity_id INTEGER NOT NULL REFERENCES activities (id),
    position INTEGER NOT NULL,
    kind TEXT NOT NULL DEFAULT 'text' CHECK (kind IN ('text', 'activity')),
    title TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT ''  -- the text, or the directions of an activity
);

-- Which classes a sheet is given to.
CREATE TABLE IF NOT EXISTS activity_classes (
    activity_id INTEGER NOT NULL REFERENCES activities (id),
    class_id INTEGER NOT NULL REFERENCES classes (id),
    assigned_at TEXT NOT NULL DEFAULT (datetime('now')),
    due_at TEXT,
    PRIMARY KEY (activity_id, class_id)
);

-- The questions of an activity section, in position order.
-- type: multiple_choice, true_false, identification, fill_blank, short_answer (checked in app.py, so new
-- types can be added without rebuilding the table). choices and answer are JSON:
--   multiple_choice: choices ["Hinduism", ...], answer 1 (the index of the correct choice)
--   true_false:      answer true / false
--   identification:  answer ["Taoism", "Daoism"] (any of them is correct)
--   fill_blank:      prompt has ___ for each blank, answer [["Buddhism"], ["China"]] (per blank)
--   short_answer:    a short essay the teacher scores; answer "key points..." (optional guide, may be "")
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY,
    activity_id INTEGER NOT NULL REFERENCES activities (id),
    section_id INTEGER NOT NULL REFERENCES activity_sections (id),
    position INTEGER NOT NULL,
    type TEXT NOT NULL,
    prompt TEXT NOT NULL,
    choices TEXT,
    answer TEXT NOT NULL,
    points INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY,
    activity_id INTEGER NOT NULL REFERENCES activities (id),
    student_id INTEGER NOT NULL REFERENCES users (id),
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
