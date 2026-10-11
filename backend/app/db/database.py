"""
Empire Task Engine — SQLite connection helper.
Standalone sqlite3 (no ORM). Separate from the main SQLAlchemy database.
"""
import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager

_FAMILY_DATA_ROOTS = ("/data/amp", "/data/maxine")


def _norm(p: str) -> str:
    try:
        return str(Path(p).expanduser().resolve())
    except Exception:
        return os.path.expanduser(p)


def _is_family_data_dir(data_dir: str) -> bool:
    if not data_dir:
        return False
    n = _norm(data_dir)
    for root in _FAMILY_DATA_ROOTS:
        if n == root or n.startswith(root + os.sep):
            return True
    return False


def resolve_task_db_path() -> str:
    """Resolve the task/engine SQLite path.

    Preference:
      1. EMPIRE_TASK_DB when set (and, for family editions, only if it stays
         under EMPIRE_DATA_DIR — otherwise derive from EMPIRE_DATA_DIR).
      2. For family editions (EMPIRE_DATA_DIR under /data/amp or /data/maxine,
         or EMPIRE_EDITION in {amp,maxine}): always ``{EMPIRE_DATA_DIR}/empire.db``.
         Never fall back to ~/empire-data.
      3. Workroom default: ~/empire-data/empire.db.
    """
    data_dir = (os.getenv("EMPIRE_DATA_DIR") or "").strip()
    explicit = (os.getenv("EMPIRE_TASK_DB") or "").strip()
    edition = (os.getenv("EMPIRE_EDITION") or "").strip().lower()
    family = _is_family_data_dir(data_dir) or edition in ("amp", "maxine")

    if family:
        if not data_dir:
            data_dir = "/data/amp" if edition == "amp" else "/data/maxine" if edition == "maxine" else ""
        if data_dir:
            derived = str(Path(data_dir).expanduser() / "empire.db")
            if explicit:
                exp_n = _norm(explicit)
                root_n = _norm(data_dir)
                if exp_n == root_n or exp_n.startswith(root_n + os.sep):
                    return explicit
                # Explicit path escapes the family data root — ignore it.
            return derived
        # Family edition without a usable data dir: refuse Workroom fallback.
        raise RuntimeError(
            "Family edition requires EMPIRE_DATA_DIR under /data/amp or /data/maxine "
            "(refusing ~/empire-data fallback)"
        )

    if explicit:
        return explicit
    return str(Path.home() / "empire-data" / "empire.db")


# Backward-compatible module attribute. Prefer resolve_task_db_path() at call
# time — import-time capture was the isolation footgun for family editions.
DB_PATH = resolve_task_db_path()


def get_db_path() -> str:
    """Call-time task DB path (always re-resolves from env)."""
    return resolve_task_db_path()


def get_connection() -> sqlite3.Connection:
    """Get a new SQLite connection with row factory enabled."""
    path = resolve_task_db_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    """Context manager that yields a connection and auto-commits/rollbacks."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def dict_row(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain dict."""
    return dict(row) if row else None


def dict_rows(rows: list) -> list:
    """Convert a list of sqlite3.Row to a list of dicts."""
    return [dict(r) for r in rows]
