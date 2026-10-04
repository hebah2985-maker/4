"""FR-50: every visitor gets a private data directory and cached source."""

from __future__ import annotations

import os
import time

from streamlit.testing.v1 import AppTest

from app._shared import _purge_stale_sessions

_SCRIPT = """
import streamlit as st
from app._shared import db_path
st.write(str(db_path()))
"""


def test_purge_removes_only_stale_sessions_of_others(tmp_path):
    old = tmp_path / "old"
    fresh = tmp_path / "fresh"
    mine = tmp_path / "mine"
    for folder in (old, fresh, mine):
        folder.mkdir()
    ancient = time.time() - 24 * 3600
    os.utime(old, (ancient, ancient))
    os.utime(mine, (ancient, ancient))
    _purge_stale_sessions(tmp_path, keep="mine")
    assert not old.exists()
    assert fresh.exists()
    assert mine.exists()


def test_two_sessions_get_different_db_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("NAQL_DATA_DIR", str(tmp_path))
    first = AppTest.from_string(_SCRIPT).run()
    second = AppTest.from_string(_SCRIPT).run()
    path_a = first.markdown[0].value
    path_b = second.markdown[0].value
    assert path_a != path_b
    assert "sessions" in path_a
