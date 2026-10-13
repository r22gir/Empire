"""Simli / avatar lip-sync timing.

Simli Compose expects PCM16 mono at 16 kHz and internally buffers
``PREFERRED_CHUNK_SAMPLES`` (3000) samples — 6000 bytes, 187.5 ms — before
the face moves. Live voice is 24 kHz. If we play TTS locally at t=0 and
forward PCM to Simli, the mouth lands ~200 ms late. That is the "lip
syncing is kinda off" report, not a Simli defect.

This module is the single source of truth for:
- the playback delay the client must apply to local audio
- resampling 24 kHz live-voice PCM to Simli's 16 kHz
- 6000-byte chunking
- word-timestamp alignment (TalkingHead / spoken documents)
- safe Int16Array → bytes slicing (do not send the whole ArrayBuffer)
"""
from __future__ import annotations

from typing import Any, Iterable, Sequence

SIMLI_SAMPLE_RATE = 16000
LIVE_VOICE_SAMPLE_RATE = 24000
PCM16_BYTES_PER_SAMPLE = 2
PREFERRED_CHUNK_SAMPLES = 3000  # Simli JS default audioBufferSize
PREFERRED_CHUNK_BYTES = PREFERRED_CHUNK_SAMPLES * PCM16_BYTES_PER_SAMPLE  # 6000
BUFFER_OFFSET_MS = 188  # 3000 / 16000 * 1000, rounded
WEBRTC_JITTER_MS = 32
# Delay local playback so heard speech matches the Simli (or TalkingHead) mouth.
LIP_SYNC_OFFSET_MS = BUFFER_OFFSET_MS + WEBRTC_JITTER_MS  # 220
AUDIO_FORMAT = "pcm16"


def playback_delay_ms(offset_ms: int | None = None) -> int:
    value = LIP_SYNC_OFFSET_MS if offset_ms is None else int(offset_ms)
    return max(0, value)


def pcm16_view_slice(byte_offset: int, byte_length: int, buffer_nbytes: int) -> tuple[int, int]:
    """Byte range for an Int16Array view.

    Sending ``int16.buffer`` (the whole backing store) prepends leftover
    samples and makes the mouth lag. Clients must send ``buffer.slice(start, end)``.
    """
    start = max(0, int(byte_offset))
    end = start + max(0, int(byte_length))
    cap = max(0, int(buffer_nbytes))
    if start > cap:
        return cap, cap
    return start, min(end, cap)


def resample_pcm16_mono(
    pcm: bytes,
    from_rate: int,
    to_rate: int = SIMLI_SAMPLE_RATE,
) -> bytes:
    """Linear-resample little-endian PCM16 mono. Duration is preserved."""
    if not pcm:
        return b""
    src_rate = int(from_rate or to_rate)
    dst_rate = int(to_rate or SIMLI_SAMPLE_RATE)
    if src_rate <= 0 or dst_rate <= 0:
        return b""
    n = len(pcm) // PCM16_BYTES_PER_SAMPLE
    if n == 0:
        return b""
    if src_rate == dst_rate:
        return pcm[: n * PCM16_BYTES_PER_SAMPLE]

    import array

    src = array.array("h")
    src.frombytes(pcm[: n * PCM16_BYTES_PER_SAMPLE])
    out_n = max(1, int(round(n * dst_rate / src_rate)))
    dst = array.array("h", [0] * out_n)
    last = n - 1
    for i in range(out_n):
        pos = i * src_rate / dst_rate
        i0 = int(pos)
        if i0 >= last:
            dst[i] = src[last]
            continue
        frac = pos - i0
        dst[i] = int(src[i0] * (1.0 - frac) + src[i0 + 1] * frac)
    return dst.tobytes()


def chunk_pcm16(pcm: bytes, chunk_bytes: int = PREFERRED_CHUNK_BYTES) -> list[bytes]:
    """Split PCM into Simli-sized frames. Last frame is short; no silence pad."""
    size = max(PCM16_BYTES_PER_SAMPLE, int(chunk_bytes))
    size -= size % PCM16_BYTES_PER_SAMPLE
    if not pcm:
        return []
    return [pcm[i : i + size] for i in range(0, len(pcm), size)]


def pcm_duration_ms(pcm: bytes, sample_rate: int = SIMLI_SAMPLE_RATE) -> float:
    if sample_rate <= 0 or not pcm:
        return 0.0
    samples = len(pcm) // PCM16_BYTES_PER_SAMPLE
    return round(1000.0 * samples / sample_rate, 3)


def estimate_word_timestamps(
    text: str,
    duration_seconds: float,
    *,
    offset_seconds: float = 0.0,
) -> list[dict[str, Any]]:
    """Evenly space words across known audio duration, then apply lip-sync offset."""
    words = [w for w in (text or "").split() if w]
    if not words:
        return []
    try:
        duration = float(duration_seconds)
    except (TypeError, ValueError):
        duration = 0.0
    if duration < 0.08:
        duration = max(0.08, len(words) * 0.35)
    gap = duration / len(words)
    try:
        shift = max(0.0, float(offset_seconds))
    except (TypeError, ValueError):
        shift = 0.0
    out: list[dict[str, Any]] = []
    for i, word in enumerate(words):
        out.append({
            "word": word,
            "start": round(shift + i * gap, 3),
            "end": round(shift + (i + 1) * gap, 3),
        })
    return out


def apply_lip_sync_offset(
    timestamps: Sequence[dict[str, Any]] | None,
    offset_ms: int | None = None,
) -> list[dict[str, Any]]:
    """Shift word/viseme times later so they line up with delayed playback.

    Used when the client plays audio immediately (no delay). When the client
    applies ``playback_delay_ms``, leave timestamps unshifted relative to the
    delayed clock (offset 0).
    """
    shift = playback_delay_ms(offset_ms) / 1000.0
    rows: list[dict[str, Any]] = []
    for raw in timestamps or []:
        if not isinstance(raw, dict):
            continue
        row = dict(raw)
        for key in ("start", "end", "time"):
            if key not in row:
                continue
            try:
                row[key] = round(float(row[key]) + shift, 3)
            except (TypeError, ValueError):
                pass
        rows.append(row)
    return rows


def align_pcm_for_simli(
    pcm: bytes,
    from_rate: int = LIVE_VOICE_SAMPLE_RATE,
    *,
    offset_ms: int | None = None,
) -> dict[str, Any]:
    """Resample live-voice PCM and emit Simli-ready chunks + timing."""
    aligned = resample_pcm16_mono(pcm, from_rate, SIMLI_SAMPLE_RATE)
    chunks = chunk_pcm16(aligned)
    delay = playback_delay_ms(offset_ms)
    return {
        "sample_rate": SIMLI_SAMPLE_RATE,
        "audio_format": AUDIO_FORMAT,
        "bytes": len(aligned),
        "samples": len(aligned) // PCM16_BYTES_PER_SAMPLE,
        "duration_ms": pcm_duration_ms(aligned, SIMLI_SAMPLE_RATE),
        "chunk_bytes": PREFERRED_CHUNK_BYTES,
        "chunk_count": len(chunks),
        "chunks": chunks,
        "playback_delay_ms": delay,
        "lip_sync_offset_ms": delay,
    }


def lipsync_payload(*, surface: str = "simli") -> dict[str, Any]:
    """Public config the browser (and spoken-document playback) consume."""
    delay = playback_delay_ms()
    return {
        "surface": surface,
        "audio_format": AUDIO_FORMAT,
        "sample_rate": SIMLI_SAMPLE_RATE,
        "live_voice_sample_rate": LIVE_VOICE_SAMPLE_RATE,
        "chunk_samples": PREFERRED_CHUNK_SAMPLES,
        "chunk_bytes": PREFERRED_CHUNK_BYTES,
        "buffer_offset_ms": BUFFER_OFFSET_MS,
        "webrtc_jitter_ms": WEBRTC_JITTER_MS,
        "lip_sync_offset_ms": delay,
        "playback_delay_ms": delay,
        "play_simli_remote_audio": True,
        "send_backing_buffer": False,
        "reason": (
            "Local TTS/live-voice audio leads the Simli mouth by the 3000-sample "
            f"compose buffer ({BUFFER_OFFSET_MS} ms) plus WebRTC jitter "
            f"({WEBRTC_JITTER_MS} ms). Delay local playback by {delay} ms, "
            "or play the Simli remote audio track (already locked to video) "
            "and mute the local copy. Feed PCM16 mono 16 kHz in 6000-byte "
            "chunks; slice Int16Array by byteOffset/byteLength."
        ),
    }


def attach_lipsync(payload: dict[str, Any] | None, *, surface: str = "simli") -> dict[str, Any]:
    data = dict(payload or {})
    data["lipsync"] = lipsync_payload(surface=surface)
    return data


def first_chunk_sizes(chunks: Iterable[bytes]) -> list[int]:
    return [len(c) for c in chunks]
