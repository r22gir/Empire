"""IMP-0010: Simli / avatar lip-sync offset is not "just how it is"."""
from __future__ import annotations

import base64
import struct

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.avatar import _estimate_word_timestamps
from app.routers.simli_avatar import router as simli_router
from app.routers.voice_documents import router as voice_docs_router
from app.routers.voice_documents import spoken_document_lipsync
from app.services.simli_lipsync import (
    LIP_SYNC_OFFSET_MS,
    LIVE_VOICE_SAMPLE_RATE,
    PREFERRED_CHUNK_BYTES,
    SIMLI_SAMPLE_RATE,
    align_pcm_for_simli,
    apply_lip_sync_offset,
    chunk_pcm16,
    estimate_word_timestamps,
    lipsync_payload,
    pcm16_view_slice,
    pcm_duration_ms,
    resample_pcm16_mono,
)

_app = FastAPI()
_app.include_router(simli_router, prefix="/api/v1")
_app.include_router(voice_docs_router, prefix="/api/v1")
client = TestClient(_app)


def _pcm16(samples: int, value: int = 1200) -> bytes:
    return struct.pack("<" + "h" * samples, *([value] * samples))


def test_lipsync_offset_is_the_simli_buffer_plus_jitter():
    cfg = lipsync_payload()
    assert cfg["lip_sync_offset_ms"] == 220
    assert cfg["playback_delay_ms"] == 220
    assert cfg["sample_rate"] == 16000
    assert cfg["chunk_bytes"] == 6000
    assert cfg["send_backing_buffer"] is False
    assert cfg["play_simli_remote_audio"] is True
    assert LIP_SYNC_OFFSET_MS == 220


def test_24k_live_voice_resamples_to_16k_without_stretching_duration():
    # 240 ms of 24 kHz speech → 5760 samples. After 16 kHz: 3840 samples, still 240 ms.
    src = _pcm16(5760, 8000)
    out = resample_pcm16_mono(src, LIVE_VOICE_SAMPLE_RATE, SIMLI_SAMPLE_RATE)
    assert pcm_duration_ms(src, LIVE_VOICE_SAMPLE_RATE) == 240.0
    assert pcm_duration_ms(out, SIMLI_SAMPLE_RATE) == 240.0
    assert len(out) == 3840 * 2


def test_pcm_is_chunked_to_simli_6000_byte_frames():
    # 400 ms at 16 kHz = 6400 samples = 12800 bytes → 6000 + 6000 + 800
    pcm = _pcm16(6400)
    chunks = chunk_pcm16(pcm)
    assert [len(c) for c in chunks] == [6000, 6000, 800]
    aligned = align_pcm_for_simli(pcm, SIMLI_SAMPLE_RATE)
    assert aligned["chunk_count"] == 3
    assert aligned["playback_delay_ms"] == LIP_SYNC_OFFSET_MS


def test_int16_view_does_not_send_the_whole_backing_buffer():
    # 16 leftover prefix samples + 100 real samples in a 200-sample buffer.
    start, end = pcm16_view_slice(byte_offset=32, byte_length=200, buffer_nbytes=400)
    assert (start, end) == (32, 232)
    leaked = pcm16_view_slice(0, 400, 400)
    assert leaked == (0, 400)
    assert leaked[1] - leaked[0] != 200  # whole buffer would be wrong


def test_word_timestamps_shift_by_offset_so_mouth_matches_speech():
    raw = estimate_word_timestamps("hello there", 1.0, offset_seconds=0.0)
    assert raw[0]["start"] == 0.0
    assert raw[0]["end"] == 0.5
    shifted = apply_lip_sync_offset(raw)
    assert shifted[0]["start"] == 0.220
    assert shifted[0]["end"] == 0.720
    assert shifted[1]["start"] == 0.720
    assert shifted[1]["end"] == 1.220


def test_avatar_speak_timestamps_include_lip_sync_offset():
    rows = _estimate_word_timestamps("one two", b"x" * 4000)
    assert rows[0]["start"] == 0.220
    assert rows[-1]["end"] > 1.0


def test_spoken_document_uses_same_offset_as_simli():
    spoken = spoken_document_lipsync("draft quote ready", duration_seconds=1.5)
    assert spoken["surface"] == "voice_documents"
    assert spoken["lip_sync_offset_ms"] == LIP_SYNC_OFFSET_MS
    assert spoken["timestamps"][0]["start"] == 0.220
    assert spoken["playback_delay_ms"] == 220


def test_simli_lipsync_route_is_public_and_has_no_secrets():
    res = client.get("/api/v1/avatar/simli/lipsync")
    assert res.status_code == 200
    body = res.json()
    assert body["playback_delay_ms"] == 220
    assert body["chunk_bytes"] == PREFERRED_CHUNK_BYTES
    blob = res.text.lower()
    assert "api_key" not in blob
    assert "simli_api_key" not in blob


def test_simli_align_route_resamples_and_shifts_words():
    pcm = _pcm16(4800, 400)  # 200 ms at 24 kHz
    res = client.post("/api/v1/avatar/simli/align", json={
        "pcm_b64": base64.b64encode(pcm).decode("ascii"),
        "from_rate": 24000,
        "text": "hi there",
        "apply_offset_to_timestamps": True,
    })
    assert res.status_code == 200
    body = res.json()
    assert body["sample_rate"] == 16000
    assert body["duration_ms"] == 200.0
    assert "chunks" not in body
    assert body["timestamps"][0]["start"] == 0.220
    assert body["lipsync"]["playback_delay_ms"] == 220


def test_voice_documents_lipsync_route():
    res = client.get("/api/v1/voice/documents/lipsync")
    assert res.status_code == 200
    assert res.json()["surface"] == "voice_documents"
    assert res.json()["lip_sync_offset_ms"] == 220

    spoken = client.post("/api/v1/voice/documents/spoken", json={
        "text": "send the quote",
        "duration_seconds": 1.0,
    })
    assert spoken.status_code == 200
    assert spoken.json()["timestamps"][0]["start"] == 0.220
