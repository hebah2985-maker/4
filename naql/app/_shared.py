"""Shared app-level helpers: per-session storage, cached source loading (UI4, FR-50)."""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import streamlit as st

from app import state
from naql_core import db
from naql_core.config import load_config
from naql_core.match import JoinedSource, build_joined_source

_SESSIONS_DIR = "sessions"
_STALE_SESSION_SECONDS = 6 * 60 * 60  # idle sessions are purged after 6 hours


def session_data_dir() -> Path:
    """Return this visitor's private data directory (FR-50, NFR-07).

    Every visitor gets ``data/sessions/<uuid>/`` so no one can see another
    visitor's uploaded sources. Idle sessions of other visitors are purged.
    """
    root = load_config().data_dir / _SESSIONS_DIR
    root.mkdir(parents=True, exist_ok=True)
    _purge_stale_sessions(root, keep=state.get_session_id())
    path = root / state.get_session_id()
    path.mkdir(parents=True, exist_ok=True)
    path.touch()  # refresh mtime: marks the session as active
    return path


def _purge_stale_sessions(root: Path, *, keep: str) -> None:
    """Delete session folders untouched for longer than the stale threshold."""
    now = time.time()
    for child in root.iterdir():
        if child.name == keep or not child.is_dir():
            continue
        if now - child.stat().st_mtime > _STALE_SESSION_SECONDS:
            shutil.rmtree(child, ignore_errors=True)


def db_path() -> Path:
    """Resolve this session's SQLite file and make sure it is initialised."""
    path = session_data_dir() / "naql.sqlite"
    db.init_db(path)
    return path


@st.cache_data(show_spinner=False)
def load_joined_source(db_file: str, doc_id: int) -> JoinedSource:
    """Load and join all pages of a document (cached heavy operation, UI4).

    ``db_file`` is part of the cache key on purpose: it contains the session
    id, so two visitors can never share a cached source (FR-50).
    """
    import sqlite3

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    try:
        pages = db.get_pages(conn, doc_id)
    finally:
        conn.close()
    return build_joined_source([(p.pdf_page, p.printed_page, p.text_raw) for p in pages])
