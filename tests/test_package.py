"""Smoke tests for package layout."""

import geogrid


def test_version_defined():
    assert hasattr(geogrid, "__version__")
    assert isinstance(geogrid.__version__, str)
