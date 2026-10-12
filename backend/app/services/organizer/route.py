"""Today's stops + estimated drive times + a one-tap maps URL.

No Google connector lives in this repo. Drive minutes are a conservative
estimate from address changes (not live traffic).
"""

from __future__ import annotations

from urllib.parse import quote

from app.services.organizer.dayplan import FIELD_KINDS, order_field_stops

SHOP_ADDRESS = "Hyattsville, MD"
DEFAULT_LEG_MINUTES = 22
SAME_PLACE_MINUTES = 5


def _addr(item: dict) -> str:
    return (item.get("location_address") or "").strip()


def estimate_leg_minutes(prev: str, nxt: str) -> int:
    a, b = prev.lower().strip(), nxt.lower().strip()
    if not a or not b:
        return DEFAULT_LEG_MINUTES
    if a == b:
        return SAME_PLACE_MINUTES
    # Same first token (street/city) → shorter hop.
    if a.split(",")[0][:12] == b.split(",")[0][:12]:
        return 12
    return DEFAULT_LEG_MINUTES


def build_route(items: list[dict], *, origin: str = SHOP_ADDRESS) -> dict:
    stops = [i for i in order_field_stops(items) if _addr(i) or i.get("start_time")]
    legs = []
    prev = origin
    total = 0
    ordered = []
    for i, stop in enumerate(stops, start=1):
        dest = _addr(stop) or origin
        minutes = estimate_leg_minutes(prev, dest)
        total += minutes
        legs.append({
            "from": prev,
            "to": dest,
            "minutes": minutes,
            "stop": i,
        })
        ordered.append({
            **stop,
            "stop_index": i,
            "drive_minutes_from_previous": minutes,
            "maps_stop_url": f"https://maps.google.com/?q={quote(dest)}" if dest else None,
        })
        prev = dest
    waypoints = [_addr(s) for s in ordered if _addr(s)]
    maps_url = None
    if waypoints:
        dest = waypoints[-1]
        mid = waypoints[:-1]
        maps_url = (
            "https://www.google.com/maps/dir/?api=1"
            f"&origin={quote(origin)}"
            f"&destination={quote(dest)}"
        )
        if mid:
            maps_url += f"&waypoints={quote('|'.join(mid))}"
    return {
        "origin": origin,
        "stops": ordered,
        "legs": legs,
        "total_drive_minutes": total,
        "maps_url": maps_url,
        "live_traffic": False,
        "note": (
            "Drive times are estimates from address changes (no maps API in this repo). "
            "Open the maps link on the phone for turn-by-turn."
        ),
    }
