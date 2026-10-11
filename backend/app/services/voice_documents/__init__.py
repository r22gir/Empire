"""Voice-to-document engine.

Generic core (extract, session, send gate, pipeline) is edition-config
driven. Workroom quote/drawing output lives in adapters.workroom.
Max-e and Maxine register the same kinds with an unported adapter so
the family editions can swap outputs without a second engine.

Port unchanged: extract.py, session.py, send_gate.py, pipeline.py,
kinds.py, email_format.py, routers/voice_documents.py.
Swap per edition: edition.py config, adapters/workroom.py.
"""

from app.services.voice_documents.pipeline import (
    dispatch_confirmed_send,
    ingest_audio,
    ingest_telegram_voice_transcript,
    ingest_transcript,
    prepare_send,
)

__all__ = [
    "dispatch_confirmed_send",
    "ingest_audio",
    "ingest_telegram_voice_transcript",
    "ingest_transcript",
    "prepare_send",
]
