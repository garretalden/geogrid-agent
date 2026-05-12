"""Tests for geogrid.fetch with mocked HTTP."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from geogrid.fetch import fetch_grid_answers, fetch_grid_guesses


class _FakeResp:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResp:
        return self

    def __exit__(self, *args: object) -> None:
        return None


@patch("geogrid.fetch.urlopen")
def test_fetch_grid_answers_writes_raw_json(mock_urlopen: MagicMock, tmp_path: Path) -> None:
    payload = {"grid_id": "1", "meta": {"n": 1}, "rows": []}
    body = json.dumps(payload, separators=(",", ":"))
    mock_urlopen.return_value = _FakeResp(body.encode("utf-8"))

    out = fetch_grid_answers(1, output_dir=tmp_path, timeout=1.0)

    assert out == tmp_path / "grids" / "1.json"
    saved = out.read_text(encoding="utf-8")
    assert json.loads(saved) == json.loads(body)
    assert "\n" in saved
    assert "  " in saved
    mock_urlopen.assert_called_once()


@patch("geogrid.fetch.urlopen")
def test_fetch_grid_guesses_writes_raw_json(mock_urlopen: MagicMock, tmp_path: Path) -> None:
    payload = {
        "grid_id": "2",
        "match_box_1": {"aa": 2, "zz": 1, "total": 3},
        "plays": 0,
    }
    body = json.dumps(payload, separators=(",", ":"))
    mock_urlopen.return_value = _FakeResp(body.encode("utf-8"))

    out = fetch_grid_guesses(2, output_dir=tmp_path, timeout=1.0)

    assert out == tmp_path / "guesses" / "2.json"
    saved = out.read_text(encoding="utf-8")
    assert json.loads(saved) == json.loads(body)
    assert "\n" in saved
    assert "  " in saved
    assert list(json.loads(saved)["match_box_1"].keys()) == ["aa", "zz", "total"]


@patch("geogrid.fetch.urlopen")
def test_fetch_grid_guesses_sorts_ties_alphabetically(mock_urlopen: MagicMock, tmp_path: Path) -> None:
    payload = {
        "_id": "x",
        "match_box_1": {"m": 5, "a": 5, "total": 10},
    }
    body = json.dumps(payload, separators=(",", ":"))
    mock_urlopen.return_value = _FakeResp(body.encode("utf-8"))

    out = fetch_grid_guesses(99, output_dir=tmp_path, timeout=1.0)
    keys = list(json.loads(out.read_text(encoding="utf-8"))["match_box_1"].keys())
    assert keys == ["a", "m", "total"]


@patch("geogrid.fetch.urlopen")
def test_fetch_rejects_invalid_json(mock_urlopen: MagicMock, tmp_path: Path) -> None:
    mock_urlopen.return_value = _FakeResp(b"not json")
    try:
        fetch_grid_answers(3, output_dir=tmp_path, timeout=1.0)
    except ValueError as exc:
        assert "not valid JSON" in str(exc)
    else:
        raise AssertionError("expected ValueError")
