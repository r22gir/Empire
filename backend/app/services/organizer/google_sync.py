"""Google Calendar sync status. No connector exists in this repo — stub only."""

GOOGLE_SYNC_STATUS = {
    "available": False,
    "connected": False,
    "provider": "google_calendar",
    "note": (
        "No Google Calendar connector exists in this repository. "
        "Use ICS export or the subscribe feed instead. "
        "This endpoint is a stub so the Organizer can show a clear status "
        "instead of pretending a sync ran."
    ),
    "use_instead": ["ics_export", "ics_subscribe"],
}


def google_sync_status() -> dict:
    return dict(GOOGLE_SYNC_STATUS)


def google_sync_push(_items) -> dict:
    status = google_sync_status()
    status["pushed"] = 0
    status["error"] = "google_calendar_not_configured"
    return status
