"""Shop / drawing calendar date.

Sheets stamp the workroom's local day (America/New_York), never UTC
`date.today()`. Early-morning UTC can still be the previous evening in ET.
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

SHOP_TZ_NAME = "America/New_York"
SHOP_TZ = ZoneInfo(SHOP_TZ_NAME)


def shop_today(now: datetime | None = None) -> str:
    """YYYY-MM-DD in America/New_York."""
    if now is None:
        now = datetime.now(SHOP_TZ)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc).astimezone(SHOP_TZ)
    else:
        now = now.astimezone(SHOP_TZ)
    return now.date().isoformat()
