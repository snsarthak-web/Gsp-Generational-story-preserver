"""
db.py — tiny data-access layer for GSP.

We use Python's built-in ``sqlite3`` module instead of an ORM
(SQLAlchemy, etc.) on purpose: it keeps the dependency list to just
Flask + ReportLab, and it makes every query visible and explainable
in a viva / project demo. Rows are returned as ``sqlite3.Row`` so
they can be used like dictionaries in templates (``story['career']``).
"""
import sqlite3
from pathlib import Path
from flask import g, current_app

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_db():
    """Return a request-scoped SQLite connection (created once per request)."""
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE_PATH"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """Create tables if they do not already exist. Safe to call every boot."""
    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA_PATH.read_text())
        db.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
    init_db(app)
