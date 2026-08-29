"""Isolation the whole suite needs, and nothing else.

**This is not texastoast's `conftest.py`**, which AGENTS.md says must never be
copied here: that one is entirely tkinter fixtures and would give this package
a GUI dependency to run its tests. Nothing below imports anything outside the
standard library and pytest.

There is one fixture, and it exists because the arcade grew a reason to read
the filesystem. `ArcadeApp` loads every cabinet's best score when it opens, so
without this the suite reads whoever-is-running-it's real scoreboards — a
suite that passes on a fresh machine and fails on the developer's, or the
reverse, for reasons nothing in the test says.
"""

import pytest

from magmacrunch.engine.scores import DATA_DIR_ENV


@pytest.fixture(autouse=True)
def isolated_scores(tmp_path, monkeypatch):
    """Point every score read and write at a per-test temporary directory.

    Autouse rather than opt-in: the risk is a test that touches real scores
    *without meaning to*, so the default has to be the safe one. A test that
    wants scores on disk writes them under this directory, which `tmp_path`
    hands out fresh each time.
    """
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path / "data"))
    return tmp_path / "data"
