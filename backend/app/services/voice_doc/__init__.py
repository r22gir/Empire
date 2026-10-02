"""Voice-to-document borrador shared by Max, Max-e, and Maxine."""
from app.services.voice_doc.pipeline import (
    channel_report,
    close_session,
    format_session_reply,
    ingest_structured,
    ingest_transcript,
)
from app.services.voice_doc.store import approve_draft, get_draft, send_draft

__all__ = [
    "approve_draft",
    "channel_report",
    "close_session",
    "format_session_reply",
    "get_draft",
    "ingest_structured",
    "ingest_transcript",
    "send_draft",
]
