"""Tests for loading raw grid JSON into SQLite tables."""

from __future__ import annotations

from pathlib import Path

import pytest

from geogrid.grid_loader import load_grid_json, open_and_init


MINIMAL_GRID = {
    "grid_id": "99",
    "rows": [
        {"id": "row_cat", "name": "Row A", "variantId": 1},
        {"id": "row_cat", "name": "Row B", "variantId": 2},
        {"id": "row_cat", "name": "Row C", "variantId": 3},
    ],
    "columns": [
        {"id": "col_cat", "name": "Col X", "variantId": 10},
        {"id": "col_cat", "name": "Col Y", "variantId": None},
        {"id": "col_cat", "name": "Col Z", "variantId": 12},
    ],
    "answers": {"match_box_1": []},
}


def test_load_grid_populates_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    conn = open_and_init(db_path)
    load_grid_json(conn, MINIMAL_GRID)

    grid = conn.execute("SELECT grid_id FROM grids WHERE grid_id = ?", ("99",)).fetchone()
    assert grid is not None

    cats = conn.execute(
        "SELECT axis, position, cat_id, variant_id, name FROM grid_cats WHERE grid_id = ? ORDER BY axis DESC, position",
        ("99",),
    ).fetchall()
    assert len(cats) == 6
    assert cats[0]["axis"] == "row"
    assert cats[0]["position"] == 1
    assert cats[0]["cat_id"] == "row_cat"
    assert cats[0]["variant_id"] == 1
    assert cats[0]["name"] == "Row A"
    assert cats[4]["axis"] == "column"
    assert cats[4]["position"] == 2
    assert cats[4]["variant_id"] is None

    squares = conn.execute(
        """
        SELECT square_id, row_position, column_position,
               row_category_id, row_variant_id,
               column_category_id, column_variant_id
        FROM squares WHERE grid_id = ? ORDER BY square_id
        """,
        ("99",),
    ).fetchall()
    assert len(squares) == 9
    assert squares[0]["square_id"] == 1
    assert squares[0]["row_position"] == 1
    assert squares[0]["column_position"] == 1
    assert squares[0]["row_variant_id"] == 1
    assert squares[0]["column_variant_id"] == 10
    assert squares[8]["square_id"] == 9
    assert squares[8]["row_position"] == 3
    assert squares[8]["column_position"] == 3

    conn.close()


def test_load_grid_rejects_wrong_category_count(tmp_path: Path) -> None:
    conn = open_and_init(tmp_path / "test.db")
    bad = {**MINIMAL_GRID, "rows": MINIMAL_GRID["rows"][:2]}
    with pytest.raises(ValueError, match="expected 3 row"):
        load_grid_json(conn, bad)
