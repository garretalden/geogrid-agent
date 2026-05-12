"""HTTP fetch helpers for GeoGrid raw JSON (answers + rarity / guess popularity)."""

from __future__ import annotations

import json
import ssl
from pathlib import Path
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_CDN_DATA_BASE = "https://cdn-assets.teuteuf.fr/data/"
DEFAULT_API_BASE = "https://api.geogridgame.com/api"


def _default_raw_root() -> Path:
    return Path.cwd() / "data" / "raw"


def _normalize_base(url: str) -> str:
    u = url.strip()
    return u if u.endswith("/") else f"{u}/"


def _http_get_text(url: str, *, timeout: float) -> tuple[str, int]:
    req = Request(url, headers={"User-Agent": "geogrid-agent/0.1 (+https://github.com/) "})
    ctx = ssl.create_default_context()
    with urlopen(req, timeout=timeout, context=ctx) as resp:
        status = getattr(resp, "status", 200)
        raw = resp.read()
    text = raw.decode("utf-8")
    return text, int(status)


def _guess_count_value(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    return float(value)


def _sort_match_box_by_guess_count(box: dict[str, Any]) -> dict[str, Any]:
    """Country/answer entries sorted by guess count descending; ``total`` last if present."""
    pairs = [(k, v) for k, v in box.items() if k != "total"]
    pairs.sort(key=lambda kv: (-_guess_count_value(kv[1]), kv[0]))
    out: dict[str, Any] = {k: v for k, v in pairs}
    if "total" in box:
        out["total"] = box["total"]
    return out


def _prepare_guesses_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Top-level keys sorted like ``sort_keys=True``; each ``match_box_*`` ordered by count desc."""
    prepared: dict[str, Any] = {}
    for key in sorted(data.keys()):
        val = data[key]
        if key.startswith("match_box_") and isinstance(val, dict):
            prepared[key] = _sort_match_box_by_guess_count(val)
        else:
            prepared[key] = val
    return prepared


def _validate_and_write_json(body: str, dest: Path) -> Path:
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError(f"response is not valid JSON: {exc}") from exc
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    return dest


def _validate_and_write_guesses_json(body: str, dest: Path) -> Path:
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError(f"response is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("guesses response must be a JSON object")
    prepared = _prepare_guesses_payload(data)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as f:
        json.dump(prepared, f, indent=2, sort_keys=False)
    return dest


def fetch_grid_answers(
    grid_number: int,
    *,
    output_dir: Path | str | None = None,
    cdn_data_base_url: str = DEFAULT_CDN_DATA_BASE,
    region: Literal["world", "usa"] = "world",
    timeout: float = 30.0,
) -> Path:
    """
    Download all valid answers for a board and save raw JSON to
    ``data/raw/grids/{grid_number}.json`` (under *output_dir* if given).

    Source matches the site CDN: ``geogrid/boards/{n}.json`` or USA boards.
    """
    if grid_number < 0:
        raise ValueError("grid_number must be non-negative")
    root = Path(output_dir) if output_dir is not None else _default_raw_root()
    dest = root / "grids" / f"{grid_number}.json"
    prefix = "geogrid/boards" if region == "world" else "geogrid-usa/boards"
    url = f"{_normalize_base(cdn_data_base_url)}{prefix}/{grid_number}.json"

    try:
        body, status = _http_get_text(url, timeout=timeout)
    except HTTPError as exc:
        raise RuntimeError(f"failed to fetch answers ({exc.code}): {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"failed to fetch answers: {url}: {exc.reason}") from exc

    if status != 200:
        raise RuntimeError(f"unexpected status {status} for {url}")

    return _validate_and_write_json(body, dest)


def fetch_grid_guesses(
    grid_number: int,
    *,
    output_dir: Path | str | None = None,
    api_base_url: str = DEFAULT_API_BASE,
    timeout: float = 30.0,
) -> Path:
    """
    Download guess / popularity data (same XHR as the site: ``game/rarity``) and
    save raw JSON to ``data/raw/guesses/{grid_number}.json``.

    Each ``match_box_*`` object is written with answer keys sorted by guess count
    descending (``total`` remains last). Source: ``GET {api}/game/rarity/{grid_number}``.
    """
    if grid_number < 0:
        raise ValueError("grid_number must be non-negative")
    root = Path(output_dir) if output_dir is not None else _default_raw_root()
    dest = root / "guesses" / f"{grid_number}.json"
    base = _normalize_base(api_base_url).rstrip("/")
    url = f"{base}/game/rarity/{grid_number}"

    try:
        body, status = _http_get_text(url, timeout=timeout)
    except HTTPError as exc:
        raise RuntimeError(f"failed to fetch guesses ({exc.code}): {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"failed to fetch guesses: {url}: {exc.reason}") from exc

    if status != 200:
        raise RuntimeError(f"unexpected status {status} for {url}")

    return _validate_and_write_guesses_json(body, dest)
