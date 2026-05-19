#!/usr/bin/env python3
"""Load raw grid JSON from data/raw/grids into SQLite tables."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from geogrid.db import DEFAULT_DB_PATH
from geogrid.grid_loader import load_grids_from_directory, open_and_init


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load raw grid JSON files into grids, grid_cats, and squares tables.",
    )
    parser.add_argument(
        "--grids-dir",
        type=Path,
        default=_ROOT / "data" / "raw" / "grids",
        help="Directory of raw grid JSON files (default: data/raw/grids)",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"SQLite database path (default: {DEFAULT_DB_PATH.relative_to(_ROOT)})",
    )
    parser.add_argument(
        "grid_ids",
        nargs="*",
        help="Optional grid ids to load; default loads every *.json in grids-dir",
    )
    args = parser.parse_args()

    try:
        conn = open_and_init(args.db)
        loaded = load_grids_from_directory(
            conn,
            args.grids_dir,
            grid_ids=args.grid_ids or None,
        )
        conn.close()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not loaded:
        print("No grid files loaded.", file=sys.stderr)
        return 1

    for grid_id in loaded:
        print(f"loaded grid {grid_id}")
    print(f"database: {args.db.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
