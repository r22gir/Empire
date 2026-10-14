"""Founder Studio email aliases + safe password set.

FOUNDER_ACCESS_EMAILS is a comma list of addresses that authenticate as
the founder row (the live founder user has an empty email column).
This module does not send mail and does not write unless the operator
script is invoked with an explicit database path or EMPIRE_TASK_DB.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


def parse_founder_access_emails(raw: Optional[str] = None) -> list[str]:
    text = raw if raw is not None else os.getenv("FOUNDER_ACCESS_EMAILS", "")
    out: list[str] = []
    seen: set[str] = set()
    for part in text.split(","):
        email = part.strip().lower()
        if email and email not in seen:
            seen.add(email)
            out.append(email)
    return out


def email_is_founder_alias(email: Optional[str]) -> bool:
    if not email:
        return False
    return str(email).strip().lower() in set(parse_founder_access_emails())


def resolve_db_path(explicit: Optional[str] = None) -> Path:
    """Same default as app.db.database: EMPIRE_TASK_DB or ~/empire-data/empire.db."""
    if explicit:
        return Path(explicit).expanduser().resolve()
    return Path(
        os.getenv("EMPIRE_TASK_DB", str(Path.home() / "empire-data" / "empire.db"))
    ).expanduser().resolve()


def backup_sqlite(db_path: Path) -> Path:
    if not db_path.is_file():
        raise FileNotFoundError(f"database not found: {db_path}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = db_path.with_name(f"{db_path.name}.bak-{stamp}")
    shutil.copy2(db_path, dest)
    return dest


def set_founder_password(
    db_path: Path | str,
    password: str,
    emails: Optional[Iterable[str]] = None,
) -> int:
    """Hash `password` onto the active founder row only. Returns rows updated.

    If the founder email is empty, fills it with the first FOUNDER_ACCESS_EMAILS
    entry (or `emails`). Never logs the password.
    """
    if not password:
        raise ValueError("password cannot be empty")
    from app.utils.security import get_password_hash

    hashed = get_password_hash(password)
    aliases = list(emails) if emails is not None else parse_founder_access_emails()
    fill_email = aliases[0] if aliases else None
    path = Path(db_path)
    conn = sqlite3.connect(str(path))
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(access_users)")}
        cur = conn.execute(
            "SELECT id, email FROM access_users WHERE role = 'founder' AND is_active = 1 LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            return 0
        founder_id, current_email = row
        assignments = ["password_hash = ?"]
        values: list = [hashed]
        if (not current_email or not str(current_email).strip()) and fill_email and "email" in cols:
            assignments.append("email = ?")
            values.append(fill_email)
        if "updated_at" in cols:
            assignments.append("updated_at = datetime('now')")
        values.append(founder_id)
        updated = conn.execute(
            f"UPDATE access_users SET {', '.join(assignments)} "
            "WHERE role = 'founder' AND is_active = 1 AND id = ?",
            values,
        ).rowcount
        conn.commit()
        return int(updated or 0)
    finally:
        conn.close()
