-- myguro tables. Safe to run again: existing tables and data are kept.

-- All accounts. There is no sign-up: the admin creates teachers, students and supervisors
-- (a supervisor can only read the activity log).
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
    role TEXT NOT NULL CHECK (role IN ('admin', 'teacher', 'student', 'supervisor')),
    must_change_password INTEGER NOT NULL DEFAULT 1,
    active INTEGER NOT NULL DEFAULT 1,
    -- 0 = never enabled (a fresh student: can still be deleted); set to 1 the first time
    -- the account is enabled and never goes back, even if it is deactivated later
    activated INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    -- Students only, both optional (an irregular student may have no section): "Grade 6", "Rizal"
    grade TEXT NOT NULL DEFAULT '',
    section TEXT NOT NULL DEFAULT '',
    -- The school year this person is looking at; NULL = the current one (see school_years)
    view_year_id INTEGER REFERENCES school_years (id)
);

-- School years, like "2026-2027". Which one is the current year is a setting
-- (current_school_year). Classes and assignments belong to one year; a past year is read-only.
CREATE TABLE IF NOT EXISTS school_years (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users (id),
    school_year_id INTEGER REFERENCES school_years (id),
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
    -- Set when the teacher deletes a sheet that was given to students: it is hidden from the teacher's
    -- list and from students, with its assignments and answers kept, so it can be restored.
    deleted_at TEXT,
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
-- class_id NULL = a direct assignment: given to the students in assignment_students only, who
-- need not be in any class (everyone is ignored). One per activity (see the index below).
CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY,
    activity_id INTEGER NOT NULL REFERENCES activities (id),
    class_id INTEGER REFERENCES classes (id),
    -- The year of the class; for a direct assignment, the year it was given in
    school_year_id INTEGER REFERENCES school_years (id),
    everyone INTEGER NOT NULL DEFAULT 1,
    due_date TEXT,
    -- 0 = students don't see their scores yet (so answers can't be passed around); the teacher releases them
    scores_released INTEGER NOT NULL DEFAULT 0,
    -- not_started: students given the sheet don't see it yet. open: they can answer it. closed: final, every
    -- unfinished attempt was submitted; students can only read it. The teacher can re-open it. Each class or
    -- group has its own status, so one sheet can be open for one class and closed for another
    status TEXT NOT NULL DEFAULT 'not_started' CHECK (status IN ('not_started', 'open', 'closed')),
    assigned_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (activity_id, class_id)
);

-- UNIQUE treats NULLs as different, so "one direct assignment per activity and school year"
-- needs its own index (made in migrations.py, after the school_year_id column exists).

CREATE TABLE IF NOT EXISTS assignment_students (
    assignment_id INTEGER NOT NULL REFERENCES assignments (id),
    student_id INTEGER NOT NULL REFERENCES users (id),
    PRIMARY KEY (assignment_id, student_id)
);

-- A student the teacher excluded from one assignment (for example absent): they don't see it and
-- can't answer it until added back. Their saved answers are kept.
CREATE TABLE IF NOT EXISTS assignment_exclusions (
    assignment_id INTEGER NOT NULL REFERENCES assignments (id),
    student_id INTEGER NOT NULL REFERENCES users (id),
    excluded_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (assignment_id, student_id)
);

-- The questions of an activity section, in position order.
-- type: multiple_choice, true_false, identification, fill_blank, matching, short_answer (checked in app.py, so new
-- types can be added without rebuilding the table). choices and answer are JSON:
--   multiple_choice: choices ["Hinduism", ...], answer 1 (the index of the correct choice)
--   true_false:      answer true / false
--   identification:  answer ["Taoism", "Daoism"] (any of them is correct)
--   fill_blank:      prompt has ___ for each blank, answer [["Buddhism"], ["China"]] (per blank)
--   matching:        choices = Column B texts, answer [{"item": "Hinduism", "match": 2}, ...] (Column A item +
--                    index of its Column B choice); prompt = the instruction line
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
    -- 1 = submitted by the teacher closing the assignment, not by the student; re-opening puts it back to in progress
    auto_submitted INTEGER NOT NULL DEFAULT 0,
    UNIQUE (assignment_id, student_id, attempt)
);

-- One answer per question. answer is JSON, like the question's answer key: a choice index,
-- true/false, text, or a list of texts (one per blank).
-- is_correct and points are set when submitted; both stay NULL for a short answer until
-- the teacher scores it. feedback is the teacher's remark on this answer (empty = none).
CREATE TABLE IF NOT EXISTS submission_answers (
    submission_id INTEGER NOT NULL REFERENCES submissions (id),
    question_id INTEGER NOT NULL REFERENCES questions (id),
    answer TEXT NOT NULL,
    is_correct INTEGER,
    points INTEGER,
    feedback TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (submission_id, question_id)
);

-- School-wide settings the admin can change (key -> value as text). A missing key means the
-- default, so the table can start empty.
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- The activity log: who did what, newest last. Nothing edits a row; the oldest are deleted when the
-- log passes MAX_LOG_ENTRIES (domain/log.py), so it cannot grow without end.
-- The names are copied in as they were at that time, and there are no foreign keys, so renaming
-- or deleting a person or an activity later never changes or loses its history.
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY,
    at TEXT NOT NULL DEFAULT (datetime('now')),
    actor_id INTEGER,                  -- NULL for a failed login with a username nobody has
    actor_name TEXT NOT NULL,
    actor_username TEXT NOT NULL,
    actor_role TEXT NOT NULL,          -- "" for a failed login with an unknown username
    action TEXT NOT NULL,              -- a code, like 'assignment.opened'
    category TEXT NOT NULL,            -- see domain/log.py CATEGORIES
    target_type TEXT NOT NULL DEFAULT '',
    target_id INTEGER,
    target_name TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL,             -- one short sentence for people to read
    address TEXT NOT NULL DEFAULT ''   -- device address, sign-in actions only
);
CREATE INDEX IF NOT EXISTS activity_log_at ON activity_log (at);
CREATE INDEX IF NOT EXISTS activity_log_actor ON activity_log (actor_id, at);
CREATE INDEX IF NOT EXISTS activity_log_category ON activity_log (category, at);
