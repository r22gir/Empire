"""Per-edition Organizer usage caps. Family editions stay smaller."""

from __future__ import annotations

from datetime import date

from app.services.organizer.edition import process_edition, usage_caps
from app.services.organizer.store import now_iso


class UsageCapExceeded(Exception):
    def __init__(self, bucket: str, used: int, cap: int):
        self.bucket = bucket
        self.used = used
        self.cap = cap
        super().__init__(f"{bucket} cap reached for this edition ({used}/{cap}).")


def _today() -> str:
    return date.today().isoformat()


def snapshot(conn, edition: str | None = None) -> dict:
    ed = edition or process_edition()
    caps = usage_caps(ed)
    row = conn.execute(
        "SELECT items, captures, actions FROM organizer_usage WHERE edition = ? AND day = ?",
        (ed, _today()),
    ).fetchone()
    used = dict(row) if row else {"items": 0, "captures": 0, "actions": 0}
    return {
        "edition": ed,
        "day": _today(),
        "used": used,
        "caps": caps,
        "remaining": {k: max(0, caps[k] - int(used.get(k) or 0)) for k in caps},
    }


def consume(conn, bucket: str, n: int = 1, edition: str | None = None) -> dict:
    ed = edition or process_edition()
    caps = usage_caps(ed)
    if bucket not in caps:
        return snapshot(conn, ed)
    day = _today()
    conn.execute(
        """
        INSERT INTO organizer_usage (edition, day, items, captures, actions)
        VALUES (?, ?, 0, 0, 0)
        ON CONFLICT(edition, day) DO NOTHING
        """,
        (ed, day),
    )
    row = conn.execute(
        f"SELECT {bucket} FROM organizer_usage WHERE edition = ? AND day = ?",
        (ed, day),
    ).fetchone()
    used = int((dict(row) if row else {}).get(bucket) or 0)
    cap = int(caps[bucket])
    if used + n > cap:
        raise UsageCapExceeded(bucket, used, cap)
    conn.execute(
        f"UPDATE organizer_usage SET {bucket} = {bucket} + ? WHERE edition = ? AND day = ?",
        (n, ed, day),
    )
    try:
        conn.commit()
    except Exception:
        pass
    return snapshot(conn, ed)


def bump_or_raise(conn, bucket: str, n: int = 1):
    """Consume or raise HTTP-friendly dict."""
    try:
        return consume(conn, bucket, n)
    except UsageCapExceeded as exc:
        raise UsageCapExceeded(exc.bucket, exc.used, exc.cap) from exc
