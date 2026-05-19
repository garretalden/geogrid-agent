"""SQLite schema and connection helpers for normalized grid tables."""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Resolved from package location so cwd never creates ./geogrid.db at repo root.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = _PROJECT_ROOT / "data" / "processed" / "geogrid.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS grids (
    grid_id TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS grid_cats (
    grid_id TEXT NOT NULL,
    axis TEXT NOT NULL CHECK (axis IN ('row', 'column')),
    position INTEGER NOT NULL CHECK (position BETWEEN 1 AND 3),
    cat_id TEXT NOT NULL,
    variant_id INTEGER,
    name TEXT NOT NULL,
    PRIMARY KEY (grid_id, axis, position),
    FOREIGN KEY (grid_id) REFERENCES grids (grid_id)
);

CREATE TABLE IF NOT EXISTS squares (
    grid_id TEXT NOT NULL,
    square_id INTEGER NOT NULL CHECK (square_id BETWEEN 1 AND 9),
    row_position INTEGER NOT NULL CHECK (row_position BETWEEN 1 AND 3),
    column_position INTEGER NOT NULL CHECK (column_position BETWEEN 1 AND 3),
    row_category_id TEXT NOT NULL,
    row_variant_id INTEGER,
    column_category_id TEXT NOT NULL,
    column_variant_id INTEGER,
    PRIMARY KEY (grid_id, square_id),
    FOREIGN KEY (grid_id) REFERENCES grids (grid_id)
);

CREATE TABLE IF NOT EXISTS raw_guess_records (
    grid_id INTEGER NOT NULL,
    square_id INTEGER NOT NULL CHECK (square_id BETWEEN 1 AND 9),
    raw_answer_text TEXT NOT NULL,
    guess_count INTEGER NOT NULL,
    is_valid_answer INTEGER NOT NULL CHECK (is_valid_answer IN (0, 1)),
    PRIMARY KEY (grid_id, square_id, raw_answer_text),
    FOREIGN KEY (grid_id) REFERENCES grids (grid_id)
);
"""


def connect(db_path: Path | str) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()
