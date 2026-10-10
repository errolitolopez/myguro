-- myguro tables. Safe to run again: existing tables and data are kept.

-- All accounts. There is no sign-up: the admin creates teachers, teachers create students.
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    -- Shown and sorted as "Last, First M." (built from the three parts below; the admin
    -- account has only this)
    name TEXT NOT NULL,
    last_name TEXT NOT NULL DEFAULT '',
    first_name TEXT NOT NULL DEFAULT '',
    middle_initial TEXT NOT NULL DEFAULT '',
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'teacher', 'student')),
    must_change_password INTEGER NOT NULL DEFAULT 1,
    active INTEGER NOT NULL DEFAULT 1,
    -- 0 = never enabled (a fresh student: can still be deleted); set to 1 the first time
    -- the account is enabled and never goes back, even if it is deactivated later
    activated INTEGER NOT NULL DEFAULT 1,
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
-- can be given to several classes (assignments). A sheet with no assignments is a draft.
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users (id),
    title TEXT NOT NULL,
    subject TEXT NOT NULL DEFAULT '',
    max_attempts INTEGER DEFAULT 1,  -- how many times a student may submit; NULL = unlimited
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
    description TEXT NOT NULL DEFAULT '',  -- the text, or the directions of an activity
    -- 'plain' = typed text; 'rich' = HTML (bold, italic, lists) cleaned by domain/richtext.py
    description_format TEXT NOT NULL DEFAULT 'plain' CHECK (description_format IN ('plain', 'rich'))
);

-- A sheet given to a class: to everyone in it (also students added later), or only to the
-- students in assignment_students. due_date is optional ("2026-10-15", Philippine time);
-- students can still submit after it, marked late.
CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY,
    activity_id INTEGER NOT NULL REFERENCES activities (id),
    class_id INTEGER NOT NULL REFERENCES classes (id),
    everyone INTEGER NOT NULL DEFAULT 1,
    due_date TEXT,
    -- 0 = students don't see their scores yet (so answers can't be passed around); the teacher releases them
    scores_released INTEGER NOT NULL DEFAULT 0,
    assigned_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (activity_id, class_id)
);

CREATE TABLE IF NOT EXISTS assignment_students (
    assignment_id INTEGER NOT NULL REFERENCES assignments (id),
    student_id INTEGER NOT NULL REFERENCES users (id),
    PRIMARY KEY (assignment_id, student_id)
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

-- A student's work on an assignment, one row per attempt (1, 2, ... up to the activity's
-- max_attempts). Answers are saved while they work (submitted_at is NULL); submitting sets
-- submitted_at, checks the answers, and marks it late if it was after the due date.
-- The latest submitted attempt is the one that counts (a paper score is an attempt too).
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY,
    assignment_id INTEGER NOT NULL REFERENCES assignments (id),
    student_id INTEGER NOT NULL REFERENCES users (id),
    attempt INTEGER NOT NULL DEFAULT 1,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    submitted_at TEXT,
    late INTEGER NOT NULL DEFAULT 0,
    -- Paper: the student answered on paper and the teacher typed in the total score.
    paper INTEGER NOT NULL DEFAULT 0,
    paper_score INTEGER,
    note TEXT NOT NULL DEFAULT '',
    UNIQUE (assignment_id, student_id, attempt)
);

-- One answer per question. answer is JSON, like the question's answer key: a choice index,
-- true/false, text, or a list of texts (one per blank).
-- is_correct and points are set when submitted; both stay NULL for a short answer until
-- the teacher scores it.
CREATE TABLE IF NOT EXISTS submission_answers (
    submission_id INTEGER NOT NULL REFERENCES submissions (id),
    question_id INTEGER NOT NULL REFERENCES questions (id),
    answer TEXT NOT NULL,
    is_correct INTEGER,
    points INTEGER,
    PRIMARY KEY (submission_id, question_id)
);
