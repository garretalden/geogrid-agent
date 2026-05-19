"""Tests for loading raw guess JSON into raw_guess_records."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from geogrid.grid_loader import load_grid_json, open_and_init
from geogrid.guess_loader import load_guess_file, load_guess_json


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _minimal_grid(grid_id: str) -> dict:
    return {
        "grid_id": grid_id,
        "rows": [
            {"id": "r", "name": "R1", "variantId": 1},
            {"id": "r", "name": "R2", "variantId": 2},
            {"id": "r", "name": "R3", "variantId": 3},
        ],
        "columns": [
            {"id": "c", "name": "C1", "variantId": 1},
            {"id": "c", "name": "C2", "variantId": 2},
            {"id": "c", "name": "C3", "variantId": 3},
        ],
        "answers": {f"match_box_{n}": [f"Valid-{n}"] for n in range(1, 10)},
    }


def _minimal_guesses(grid_id: str) -> dict:
    payload: dict = {"grid_id": grid_id}
    for n in range(1, 10):
        payload[f"match_box_{n}"] = {f"Valid-{n}": 10, "Wrong": 1, "total": 11}
    return payload


def test_load_guess_records_validity_flags(tmp_path: Path) -> None:
    grids_dir = tmp_path / "grids"
    guesses_dir = tmp_path / "guesses"
    grids_dir.mkdir()
    guesses_dir.mkdir()

    grid = _minimal_grid("42")
    guesses = _minimal_guesses("42")
    _write_json(grids_dir / "42.json", grid)
    _write_json(guesses_dir / "42.json", guesses)

    conn = open_and_init(tmp_path / "test.db")
    load_grid_json(conn, grid)
    load_guess_file(conn, guesses_dir / "42.json", grids_dir=grids_dir)

    rows = conn.execute(
        """
        SELECT raw_answer_text, guess_count, is_valid_answer
        FROM raw_guess_records
        WHERE grid_id = 42 AND square_id = 1
        ORDER BY raw_answer_text
        """
    ).fetchall()
    assert len(rows) == 2
    assert rows[0]["raw_answer_text"] == "Valid-1"
    assert rows[0]["guess_count"] == 10
    assert rows[0]["is_valid_answer"] == 1
    assert rows[1]["raw_answer_text"] == "Wrong"
    assert rows[1]["is_valid_answer"] == 0
    conn.close()


def test_load_guess_records_skips_total_key(tmp_path: Path) -> None:
    conn = open_and_init(tmp_path / "test.db")
    conn.execute("INSERT OR REPLACE INTO grids (grid_id) VALUES (?)", ("1",))

    valid = {n: {"X"} for n in range(1, 10)}
    guesses = {"grid_id": "1"}
    for n in range(1, 10):
        guesses[f"match_box_{n}"] = {"X": 5, "total": 99, "Total": 1}

    load_guess_json(conn, guesses, valid_by_square=valid)

    totals = conn.execute(
        "SELECT raw_answer_text FROM raw_guess_records WHERE grid_id = 1 AND lower(raw_answer_text) = 'total'"
    ).fetchall()
    assert totals == []
    count = conn.execute("SELECT COUNT(*) FROM raw_guess_records WHERE grid_id = 1").fetchone()[0]
    assert count == 9
    conn.close()


def test_load_guess_json_flags_invalid_country(tmp_path: Path) -> None:
    conn = open_and_init(tmp_path / "test.db")
    conn.execute("INSERT OR REPLACE INTO grids (grid_id) VALUES (?)", ("7",))

    valid = {n: {"Spain"} if n == 1 else {"X"} for n in range(1, 10)}
    guesses = {"grid_id": "7"}
    for n in range(1, 10):
        guesses[f"match_box_{n}"] = (
            {"Spain": 100, "Italy": 1, "total": 101} if n == 1 else {"X": 1, "total": 1}
        )

    load_guess_json(conn, guesses, valid_by_square=valid)

    italy = conn.execute(
        "SELECT is_valid_answer FROM raw_guess_records WHERE grid_id = 7 AND raw_answer_text = 'Italy'"
    ).fetchone()
    assert italy["is_valid_answer"] == 0
    spain = conn.execute(
        "SELECT is_valid_answer FROM raw_guess_records WHERE grid_id = 7 AND raw_answer_text = 'Spain'"
    ).fetchone()
    assert spain["is_valid_answer"] == 1
    conn.close()
