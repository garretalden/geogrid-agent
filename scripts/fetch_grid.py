#!/usr/bin/env python3
"""CLI to download GeoGrid raw JSON (answers and/or rarity XHR payload)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from geogrid.fetch import (
    DEFAULT_API_BASE,
    DEFAULT_CDN_DATA_BASE,
    fetch_grid_answers,
    fetch_grid_guesses,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch GeoGrid board JSON into data/raw/")
    parser.add_argument("grid_number", type=int, help="Board / grid id (e.g. 766)")
    parser.add_argument(
        "--kind",
        choices=("answers", "guesses", "both"),
        default="both",
        help="Which payload to download",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Root for raw files (default: ./data/raw)",
    )
    parser.add_argument(
        "--cdn-data-base-url",
        default=DEFAULT_CDN_DATA_BASE,
        help="CDN base including trailing path to data/ (default: Teuteuf CDN)",
    )
    parser.add_argument(
        "--api-base-url",
        default=DEFAULT_API_BASE,
        help="API base (default: https://api.geogridgame.com/api)",
    )
    parser.add_argument(
        "--region",
        choices=("world", "usa"),
        default="world",
        help="Board set for answers JSON (world vs USA boards on CDN)",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout seconds")

    args = parser.parse_args()
    out: Path | None = args.output_dir

    try:
        if args.kind in ("answers", "both"):
            p = fetch_grid_answers(
                args.grid_number,
                output_dir=out,
                cdn_data_base_url=args.cdn_data_base_url,
                region=args.region,
                timeout=args.timeout,
            )
            print(f"answers -> {p.resolve()}")
        if args.kind in ("guesses", "both"):
            p = fetch_grid_guesses(
                args.grid_number,
                output_dir=out,
                api_base_url=args.api_base_url,
                timeout=args.timeout,
            )
            print(f"guesses -> {p.resolve()}")
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
