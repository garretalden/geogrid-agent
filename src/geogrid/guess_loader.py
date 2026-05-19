"""Load raw guess/rarity JSON into raw_guess_records."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from geogrid.grid_loader import open_and_init

_MATCH_BOX_RE = re.compile(r"^match_box_(\d+)$")


def _parse_grid_id(value: Any) -> int:
    if value is None or value == "":
        raise ValueError("missing grid_id")
    return int(value)


def _valid_answers_by_square(grid_payload: dict[str, Any]) -> dict[int, set[str]]:
    answers = grid_payload.get("answers")
    if not isinstance(answers, dict):
        raise ValueError(f"grid {grid_payload.get('grid_id')}: missing answers object")
    by_square: dict[int, set[str]] = {}
    for key, countries in answers.items():
        match = _MATCH_BOX_RE.match(key)
        if not match:
            continue
        square_id = int(match.group(1))
        if not 1 <= square_id <= 9:
            raise ValueError(f"grid {grid_payload.get('grid_id')}: invalid {key}")
        if not isinstance(countries, list):
            raise ValueError(f"grid {grid_payload.get('grid_id')}: {key} must be a list")
        by_square[square_id] = set(countries)
    if len(by_square) != 9:
        raise ValueError(
            f"grid {grid_payload.get('grid_id')}: expected 9 match_box answer lists, got {len(by_square)}"
        )
    return by_square


def _guess_rows_from_payload(
    grid_id: int,
    guesses_payload: dict[str, Any],
    valid_by_square: dict[int, set[str]],
) -> list[tuple[int, int, str, int, int]]:
    if _parse_grid_id(guesses_payload.get("grid_id")) != grid_id:
        raise ValueError(
            f"guesses grid_id {guesses_payload.get('grid_id')!r} does not match expected {grid_id}"
        )

    rows: list[tuple[int, int, str, int, int]] = []
    for key, box in guesses_payload.items():
        match = _MATCH_BOX_RE.match(key)
        if not match:
            continue
        square_id = int(match.group(1))
        if not isinstance(box, dict):
            raise ValueError(f"grid {grid_id}: {key} must be an object")
        valid = valid_by_square.get(square_id)
        if valid is None:
            raise ValueError(f"grid {grid_id}: no valid answers for square {square_id}")

        for country, count in box.items():
            if country.lower() == "total":
                continue
            if not isinstance(count, (int, float)) or isinstance(count, bool):
                raise ValueError(f"grid {grid_id} {key}: non-numeric count for {country!r}")
            is_valid = 1 if country in valid else 0
            rows.append((grid_id, square_id, country, int(count), is_valid))
    return rows


def load_guess_json(
    conn: sqlite3.Connection,
    guesses_payload: dict[str, Any],
    *,
    valid_by_square: dict[int, set[str]],
) -> int:
    """Replace all guess rows for one grid. Returns grid_id."""
    grid_id = _parse_grid_id(guesses_payload.get("grid_id"))
    rows = _guess_rows_from_payload(grid_id, guesses_payload, valid_by_square)

    conn.execute("DELETE FROM raw_guess_records WHERE grid_id = ?", (grid_id,))
    if rows:
        conn.executemany(
            """
            INSERT INTO raw_guess_records (
                grid_id, square_id, raw_answer_text, guess_count, is_valid_answer
            ) VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
    conn.commit()
    return grid_id


def load_guess_file(
    conn: sqlite3.Connection,
    guesses_path: Path,
    *,
    grids_dir: Path,
) -> int:
    grid_id = int(guesses_path.stem)
    grid_path = grids_dir / f"{grid_id}.json"
    if not grid_path.is_file():
        raise FileNotFoundError(f"grid answers required for validation: {grid_path}")

    with guesses_path.open(encoding="utf-8") as f:
        guesses_payload = json.load(f)
    with grid_path.open(encoding="utf-8") as f:
        grid_payload = json.load(f)

    if not isinstance(guesses_payload, dict) or not isinstance(grid_payload, dict):
        raise ValueError(f"{guesses_path}: expected JSON objects")

    valid_by_square = _valid_answers_by_square(grid_payload)
    return load_guess_json(conn, guesses_payload, valid_by_square=valid_by_square)


def load_guesses_from_directory(
    conn: sqlite3.Connection,
    guesses_dir: Path,
    *,
    grids_dir: Path,
    grid_ids: Iterable[str] | None = None,
) -> list[int]:
    if not guesses_dir.is_dir():
        raise FileNotFoundError(f"guesses directory not found: {guesses_dir}")

    paths = sorted(guesses_dir.glob("*.json"))
    if grid_ids is not None:
        wanted = {str(g) for g in grid_ids}
        paths = [p for p in paths if p.stem in wanted]

    loaded: list[int] = []
    for path in paths:
        loaded.append(load_guess_file(conn, path, grids_dir=grids_dir))
    return loaded
