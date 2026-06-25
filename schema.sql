-- GSP (Generational Story Preserver) — Database Schema
-- SQLite. Kept deliberately simple (no ORM) so it is easy to read,
-- inspect with the `sqlite3` CLI, and explain to an examiner.

PRAGMA foreign_keys = ON;

-- One row per storyteller.
CREATE TABLE IF NOT EXISTS user (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    birth_year   TEXT,
    birth_place  TEXT,
    gender       TEXT,
    occupation   TEXT,
    is_demo      INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- One row per story (a user could, in theory, restart a story; we
-- keep the relationship one-to-many even though the UI drives one-to-one).
CREATE TABLE IF NOT EXISTS story (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    story_title       TEXT,

    -- Chapters --------------------------------------------------------
    childhood         TEXT,
    education         TEXT,
    career            TEXT,
    wisdom            TEXT,        -- raw "story that changed your life"

    -- Family chapter fields --------------------------------------------
    father_name       TEXT,
    mother_name       TEXT,
    spouse_name       TEXT,
    children          TEXT,        -- comma separated names
    siblings          TEXT,        -- comma separated names
    family_notes      TEXT,

    -- AI-derived content -------------------------------------------------
    wisdom_corrected  TEXT,        -- grammar-polished version of `wisdom`
    q_friend             TEXT,
    q_game               TEXT,
    q_festival           TEXT,
    q_nickname           TEXT,
    q_school             TEXT,
    q_teacher            TEXT,
    q_subject            TEXT,
    q_achievement        TEXT,
    q_firstjob           TEXT,
    q_career_achievement TEXT,
    q_advice             TEXT,
    q_future_advice      TEXT,
    q_learned_late       TEXT,
    wisdom_emotions   TEXT,        -- JSON list, e.g. ["Love","Wonder"]
    life_lesson       TEXT,
    wisdom_summary    TEXT,
    biography         TEXT,
    timeline_json     TEXT,        -- JSON list of {year, title, icon, detail}

    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Uploaded keepsake photographs.
CREATE TABLE IF NOT EXISTS photo (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    image_path  TEXT NOT NULL,     -- relative to /static
    category    TEXT NOT NULL,     -- childhood | education | career | family
    caption     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Uploaded / recorded voice keepsakes.
CREATE TABLE IF NOT EXISTS audio (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    audio_path  TEXT NOT NULL,     -- relative to /static
    category    TEXT NOT NULL,     -- childhood | education | career | family | wisdom
    transcript  TEXT,              -- captured client-side via Web Speech API
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_story_user ON story(user_id);
CREATE INDEX IF NOT EXISTS idx_photo_user ON photo(user_id);
CREATE INDEX IF NOT EXISTS idx_audio_user ON audio(user_id);
