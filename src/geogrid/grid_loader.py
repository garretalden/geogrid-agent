"""Load raw grid JSON files into normalized SQLite tables."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from geogrid.db import connect, init_db


def _category_axis_entries(
    grid_id: str,
    axis: str,
    categories: list[dict[str, Any]],
) -> list[tuple[str, str, int, str, int | None, str]]:
    if len(categories) != 3:
        raise ValueError(f"grid {grid_id}: expected 3 {axis} categories, got {len(categories)}")
    rows: list[tuple[str, str, int, str, int | None, str]] = []
    for index, cat in enumerate(categories, start=1):
        cat_id = cat["id"]
        name = cat["name"]
        variant_id = cat.get("variantId")
        if variant_id is not None and not isinstance(variant_id, int):
            variant_id = int(variant_id)
        rows.append((grid_id, axis, index, cat_id, variant_id, name))
    return rows


def _square_entries(
    grid_id: str,
    row_categories: list[dict[str, Any]],
    column_categories: list[dict[str, Any]],
) -> list[tuple[str, int, int, int, str, int | None, str, int | None]]:
    squares: list[tuple[str, int, int, int, str, int | None, str, int | None]] = []
    for row_pos, row_cat in enumerate(row_categories, start=1):
        row_cat_id = row_cat["id"]
        row_variant = row_cat.get("variantId")
        if row_variant is not None and not isinstance(row_variant, int):
            row_variant = int(row_variant)
        for col_pos, col_cat in enumerate(column_categories, start=1):
            col_cat_id = col_cat["id"]
            col_variant = col_cat.get("variantId")
            if col_variant is not None and not isinstance(col_variant, int):
                col_variant = int(col_variant)
            square_id = (row_pos - 1) * 3 + col_pos
            squares.append(
                (
                    grid_id,
                    square_id,
                    row_pos,
                    col_pos,
                    row_cat_id,
                    row_variant,
                    col_cat_id,
                    col_variant,
                )
            )
    return squares


def load_grid_json(conn: sqlite3.Connection, payload: dict[str, Any]) -> str:
    """Upsert one grid's metadata into grids, grid_cats, and squares."""
    grid_id = str(payload.get("grid_id") or payload.get("gridId") or "").strip()
    if not grid_id:
        raise ValueError("grid JSON missing grid_id")

    row_categories = payload.get("rows")
    column_categories = payload.get("columns")
    if not isinstance(row_categories, list) or not isinstance(column_categories, list):
        raise ValueError(f"grid {grid_id}: rows and columns must be lists")

    conn.execute("INSERT OR REPLACE INTO grids (grid_id) VALUES (?)", (grid_id,))

    cat_rows = _category_axis_entries(grid_id, "row", row_categories)
    cat_rows.extend(_category_axis_entries(grid_id, "column", column_categories))
    conn.executemany(
        """
        INSERT OR REPLACE INTO grid_cats
            (grid_id, axis, position, cat_id, variant_id, name)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        cat_rows,
    )

    square_rows = _square_entries(grid_id, row_categories, column_categories)
    conn.executemany(
        """
        INSERT OR REPLACE INTO squares (
            grid_id,
            square_id,
            row_position,
            column_position,
            row_category_id,
            row_variant_id,
            column_category_id,
            column_variant_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        square_rows,
    )
    conn.commit()
    return grid_id


def load_grid_file(conn: sqlite3.Connection, path: Path) -> str:
    with path.open(encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return load_grid_json(conn, payload)


def load_grids_from_directory(
    conn: sqlite3.Connection,
    grids_dir: Path,
    *,
    grid_ids: Iterable[str] | None = None,
) -> list[str]:
    """Load all ``*.json`` files in *grids_dir* (or only *grid_ids* if given)."""
    if not grids_dir.is_dir():
        raise FileNotFoundError(f"grids directory not found: {grids_dir}")

    paths = sorted(grids_dir.glob("*.json"))
    if grid_ids is not None:
        wanted = {str(g) for g in grid_ids}
        paths = [p for p in paths if p.stem in wanted]

    loaded: list[str] = []
    for path in paths:
        loaded.append(load_grid_file(conn, path))
    return loaded


def open_and_init(db_path: Path | str) -> sqlite3.Connection:
    conn = connect(db_path)
    init_db(conn)
    return conn
