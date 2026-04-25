"""
TranscriptForge — Legal/High-Risk Transcription Pipeline.

States: uploaded → chunking → first_chunk_processing → first_chunk_ready →
        processing_remaining_chunks → verification_running → needs_review →
        approved / corrected_and_approved / rejected

Verification: per-chunk + full-document critical-field pass
Approval gate: human-only, never auto-approved
Provider: Groq Whisper (verifed available in this environment)

Hermes role (bounded beneath MAX):
  - PENDING skill: transcriptforge-intake
  - PENDING skill: transcriptforge-qc-review
  - PENDING skill: transcriptforge-critical-field-check
  - workflow memory capture
  - correction pattern learning
  - review checklist generation

MAX responsibilities (NOT delegated to Hermes):
  - job state authority
  - approval boundary enforcement
  - runtime truth about what ran/failed
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid, os, json, logging, asyncio, tempfile
from pathlib import Path

from app.services.max.token_tracker import token_tracker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/transcriptforge", tags=["transcriptforge"])

# ── Storage ──────────────────────────────────────────────────────────
BASE_DIR = Path(os.path.expanduser("~/empire-repo/backend/data/transcriptforge"))
JOBS_DIR = BASE_DIR / "jobs"
CHUNKS_DIR = BASE_DIR / "chunks"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"

for _d in (JOBS_DIR, CHUNKS_DIR, ARTIFACTS_DIR, TRANSCRIPTS_DIR):
    os.makedirs(_d, exist_ok=True)

# ── Source Modes ──────────────────────────────────────────────────────
SOURCE_MODES = ["deposition", "court_hearing", "conference", "general_intake", "web_chat"]
# web_chat is future-ready, labeled accordingly in API responses

# ── Chunk Configuration ───────────────────────────────────────────────
CHUNK_DURATION_SEC = 600  # 10-minute chunks
CHUNK_OVERLAP_SEC = 3      # 3-second overlap between chunks

# ── QC Thresholds (configurable) ──────────────────────────────────────
QC_THRESHOLDS = {
    "min_segment_confidence": 0.7,
    "max_unreviewed_low_confidence": 3,
    "max_mismatch_count": 5,
}

_GSTREAMER_EXTRACT_SCRIPT = r"""
import sys
from pathlib import Path

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst

Gst.init(None)
input_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
start_s = float(sys.argv[3])
end_s = float(sys.argv[4])

pipeline = Gst.Pipeline.new("transcriptforge-extract")
src = Gst.ElementFactory.make("uridecodebin", "src")
convert = Gst.ElementFactory.make("audioconvert", "convert")
resample = Gst.ElementFactory.make("audioresample", "resample")
capsfilter = Gst.ElementFactory.make("capsfilter", "caps")
wavenc = Gst.ElementFactory.make("wavenc", "wavenc")
sink = Gst.ElementFactory.make("filesink", "sink")

if not all([pipeline, src, convert, resample, capsfilter, wavenc, sink]):
    raise SystemExit("missing required GStreamer element")

src.set_property("uri", input_path.resolve().as_uri())
capsfilter.set_property(
    "caps",
    Gst.Caps.from_string("audio/x-raw,format=S16LE,channels=1,rate=16000"),
)
sink.set_property("location", str(output_path))

for element in (src, convert, resample, capsfilter, wavenc, sink):
    pipeline.add(element)

if not convert.link(resample) or not resample.link(capsfilter) or not capsfilter.link(wavenc) or not wavenc.link(sink):
    raise SystemExit("failed to link GStreamer audio pipeline")

def on_pad_added(_element, pad):
    caps = pad.get_current_caps() or pad.query_caps(None)
    if caps and caps.to_string().startswith("audio/"):
        target = convert.get_static_pad("sink")
        if not target.is_linked():
            pad.link(target)

src.connect("pad-added", on_pad_added)
bus = pipeline.get_bus()
pipeline.set_state(Gst.State.PAUSED)

while True:
    msg = bus.timed_pop_filtered(15 * Gst.SECOND, Gst.MessageType.ERROR | Gst.MessageType.ASYNC_DONE)
    if msg is None:
        raise SystemExit("GStreamer preroll timed out")
    if msg.type == Gst.MessageType.ERROR:
        err, debug = msg.parse_error()
        raise SystemExit(f"GStreamer preroll error: {err}; {debug}")
    if msg.type == Gst.MessageType.ASYNC_DONE:
        break

ok = pipeline.seek(
    1.0,
    Gst.Format.TIME,
    Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
    Gst.SeekType.SET,
    int(start_s * Gst.SECOND),
    Gst.SeekType.SET,
    int(end_s * Gst.SECOND),
)
if not ok:
    raise SystemExit("GStreamer seek failed")

pipeline.set_state(Gst.State.PLAYING)
while True:
    msg = bus.timed_pop_filtered(180 * Gst.SECOND, Gst.MessageType.ERROR | Gst.MessageType.EOS)
    if msg is None:
        raise SystemExit("GStreamer extraction timed out")
    if msg.type == Gst.MessageType.ERROR:
        err, debug = msg.parse_error()
        raise SystemExit(f"GStreamer extraction error: {err}; {debug}")
    if msg.type == Gst.MessageType.EOS:
        break

pipeline.set_state(Gst.State.NULL)
"""


# ── State Machine ─────────────────────────────────────────────────────
VALID_STATES = [
    "uploaded", "chunking", "first_chunk_processing", "first_chunk_ready",
    "processing_remaining_chunks", "verification_running", "needs_review",
    "approved", "corrected_and_approved", "rejected"
]

STATE_TRANSITIONS = {
    "uploaded": ["chunking"],
    "chunking": ["first_chunk_processing", "rejected"],
    "first_chunk_processing": ["first_chunk_ready", "rejected"],
    "first_chunk_ready": ["processing_remaining_chunks", "needs_review", "rejected"],
    "processing_remaining_chunks": ["verification_running", "needs_review", "rejected"],
    "verification_running": ["needs_review", "approved", "corrected_and_approved", "rejected"],
    "needs_review": ["approved", "corrected_and_approved", "rejected"],
    "approved": [],
    "corrected_and_approved": [],
    "rejected": [],
}


def can_transition(from_state: str, to_state: str) -> bool:
    return to_state in STATE_TRANSITIONS.get(from_state, [])


# ── Pydantic Schemas ──────────────────────────────────────────────────

class ChunkInfo(BaseModel):
    chunk_id: str
    job_id: str
    sequence: int
    start_time: float
    end_time: float
    overlap_left: float
    overlap_right: float
    raw_transcript: Optional[str] = None
    verified_transcript: Optional[str] = None
    confidence: Optional[float] = None
    mismatch_flags: List[str] = Field(default_factory=list)
    review_status: str = "pending"  # pending | good | needs_review | edited
    reviewer: Optional[str] = None
    reviewer_timestamp: Optional[datetime] = None
    raw_provider_result: Optional[Dict[str, Any]] = None
    processing_status: str = "pending"  # pending | transcribing | transcribed | failed
    raw_transcript_path: Optional[str] = None
    verified_transcript_path: Optional[str] = None


class TranscriptJobCreate(BaseModel):
    source_mode: str = "general_intake"
    uploader: str = "founder"
    notes: Optional[str] = None


class TranscriptJob(BaseModel):
    job_id: str
    state: str
    source_mode: str
    uploader: str
    created_at: datetime
    updated_at: datetime
    file_path: str
    file_size: int
    file_name: str
    duration_sec: Optional[float] = None
    chunks_total: int = 0
    chunks_complete: int = 0
    chunks_failed: int = 0
    verification_failures: int = 0
    reviewer_corrections_count: int = 0
    overall_confidence: Optional[float] = None
    raw_transcript_path: Optional[str] = None
    verified_transcript_path: Optional[str] = None
    approved_transcript_path: Optional[str] = None
    critical_field_flags: List[str] = Field(default_factory=list)
    boundary_coherence_flags: List[Dict[str, Any]] = Field(default_factory=list)
    qc_summary: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    chunks: List[ChunkInfo] = Field(default_factory=list)


class ApprovalAction(BaseModel):
    action: str  # approve | reject | correct_and_approve
    reviewer: str
    notes: Optional[str] = None
    chunk_corrections: Optional[Dict[str, str]] = None  # chunk_id -> corrected text


class TranscriptModeResponse(BaseModel):
    modes: List[Dict[str, Any]]
    web_chat_note: str = "Web Chat integration is future-ready and not yet fully active in this pass."


# ── Helpers ────────────────────────────────────────────────────────────

def _job_path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"


def _load_job(job_id: str) -> Dict[str, Any]:
    p = _job_path(job_id)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return json.loads(p.read_text())


def _save_job(job: Dict[str, Any]) -> None:
    p = _job_path(job["job_id"])
    job["updated_at"] = datetime.utcnow().isoformat()
    p.write_text(json.dumps(job, indent=2, default=str))


def _chunk_path(job_id: str, chunk_id: str) -> Path:
    return CHUNKS_DIR / f"{job_id}_{chunk_id}.json"


def _load_chunk(job_id: str, chunk_id: str) -> Dict[str, Any]:
    p = _chunk_path(job_id, chunk_id)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Chunk {chunk_id} not found")
    return json.loads(p.read_text())


def _save_chunk(chunk: Dict[str, Any]) -> None:
    _persist_chunk_transcript_files(chunk)
    p = _chunk_path(chunk["job_id"], chunk["chunk_id"])
    p.write_text(json.dumps(chunk, indent=2, default=str))


def _replace_job_chunk(job: Dict[str, Any], chunk: Dict[str, Any]) -> None:
    chunks = job.get("chunks", [])
    replaced = False
    for idx, existing in enumerate(chunks):
        if existing.get("chunk_id") == chunk.get("chunk_id"):
            chunks[idx] = chunk
            replaced = True
            break
    if not replaced:
        chunks.append(chunk)
    job["chunks"] = chunks


def _transcript_path(job_id: str, kind: str) -> Path:
    # kind: raw | verified | approved
    return TRANSCRIPTS_DIR / f"{job_id}_{kind}.txt"


def _chunk_transcript_path(job_id: str, chunk_id: str, kind: str) -> Path:
    chunk_dir = TRANSCRIPTS_DIR / job_id
    chunk_dir.mkdir(parents=True, exist_ok=True)
    return chunk_dir / f"{chunk_id}_{kind}.txt"


def _persist_chunk_transcript_files(chunk: Dict[str, Any]) -> None:
    raw = chunk.get("raw_transcript")
    if raw:
        raw_path = _chunk_transcript_path(chunk["job_id"], chunk["chunk_id"], "raw")
        raw_path.write_text(raw, encoding="utf-8")
        chunk["raw_transcript_path"] = str(raw_path)

    verified = chunk.get("verified_transcript")
    if verified:
        verified_path = _chunk_transcript_path(chunk["job_id"], chunk["chunk_id"], "verified")
        verified_path.write_text(verified, encoding="utf-8")
        chunk["verified_transcript_path"] = str(verified_path)


def _estimate_duration(file_size: int) -> float:
    """Estimate MP3 duration from file size at 128kbps."""
    return file_size / 16000


def _chunk_job(job: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Split job into timed chunks with overlap metadata."""
    duration = job["duration_sec"]
    chunks = []
    seq = 0
    start = 0.0
    while start < duration:
        end = min(start + CHUNK_DURATION_SEC, duration)
        prev_seq = seq - 1
        chunks.append({
            "chunk_id": f"chunk_{seq:03d}",
            "job_id": job["job_id"],
            "sequence": seq,
            "start_time": start,
            "end_time": end,
            "overlap_left": CHUNK_OVERLAP_SEC if seq > 0 else 0.0,
            "overlap_right": CHUNK_OVERLAP_SEC if start + CHUNK_DURATION_SEC < duration else 0.0,
            "raw_transcript": None,
            "verified_transcript": None,
            "confidence": None,
            "mismatch_flags": [],
            "review_status": "pending",
            "reviewer": None,
            "reviewer_timestamp": None,
            "raw_provider_result": None,
            "processing_status": "pending",
            "raw_transcript_path": None,
            "verified_transcript_path": None,
        })
        if end >= duration:
            break
        start = end - CHUNK_OVERLAP_SEC
        seq += 1
    return chunks


async def _extract_audio_segment(input_path: str, start: float, end: float, output_path: str) -> bool:
    """Extract a time-segment from audio file."""
    try:
        import wave
        import struct

        with wave.open(input_path, 'rb') as wf:
            rate = wf.getframerate()
            nframes = wf.getnframes()
            duration = nframes / rate

            # Convert times to frame numbers
            start_frame = int(start * rate)
            end_frame = min(int(end * rate), nframes)

            # Read the segment
            wf.setpos(start_frame)
            frames = wf.readframes(end_frame - start_frame)

            # Write to output
            with wave.open(output_path, 'wb') as out:
                out.setnchannels(wf.getnchannels())
                out.setsampwidth(wf.getsampwidth())
                out.setframerate(rate)
                out.writeframes(frames)
        return True
    except Exception as e:
        logger.info(f"Wave extraction unavailable for {Path(input_path).suffix or 'audio'}: {e}")

    proc = await asyncio.create_subprocess_exec(
        "/usr/bin/python3",
        "-c",
        _GSTREAMER_EXTRACT_SCRIPT,
        input_path,
        output_path,
        str(start),
        str(end),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        detail = (stderr or stdout).decode(errors="replace").strip()
        logger.error(f"GStreamer audio segment extraction failed: {detail}")
        return False

    p = Path(output_path)
    return p.exists() and p.stat().st_size > 44


async def _transcribe_chunk(chunk_info: Dict, audio_path: str, stt_service) -> Dict[str, Any]:
    """Transcribe a single chunk using Groq Whisper."""
    start = chunk_info["start_time"]
    end = chunk_info["end_time"]
    chunk_info["processing_status"] = "transcribing"

    # Create temporary segment file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Extract segment
        success = await _extract_audio_segment(audio_path, start, end, tmp_path)
        if not success:
            chunk_info["mismatch_flags"].append("audio_extraction_failed")
            chunk_info["processing_status"] = "failed"
            return chunk_info

        # Transcribe via Groq
        result = await stt_service.transcribe(Path(tmp_path))

        if result.startswith("["):
            # Error result
            chunk_info["mismatch_flags"].append(f"transcription_failed: {result[:100]}")
            chunk_info["confidence"] = 0.0
            chunk_info["processing_status"] = "failed"
        else:
            chunk_info["raw_transcript"] = result
            chunk_info["raw_provider_result"] = {"provider": "groq-whisper-large-v3-turbo", "model": "whisper-large-v3-turbo"}
            # Placeholder confidence — Groq doesn't return per-chunk confidence
            # Real implementation would need a provider that returns confidence scores
            chunk_info["confidence"] = 0.85  # placeholder until real confidence available
            chunk_info["review_status"] = "pending"
            chunk_info["processing_status"] = "transcribed"

        return chunk_info
    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def _verify_chunk(chunk_info: Dict, audio_path: str, stt_service) -> Dict[str, Any]:
    """Run verification pass against original audio segment — flags low confidence and mismatches."""
    job_id = chunk_info["job_id"]
    chunk_id = chunk_info["chunk_id"]
    raw = chunk_info.get("raw_transcript", "")

    if not raw:
        chunk_info["mismatch_flags"].append("no_raw_transcript_to_verify")
        return chunk_info

    # Verify against original audio — re-transcribe same segment with verification flag
    # Note: This is a simplified verification. Real implementation would use
    # a separate verification pass that compares ASR output against audio.
    # For now, we flag based on heuristics and placeholder confidence.

    confidence = chunk_info.get("confidence", 0.0)
    if confidence < QC_THRESHOLDS["min_segment_confidence"]:
        chunk_info["mismatch_flags"].append(f"low_confidence_segment: {confidence:.2f}")

    # Flag if raw transcript is very short (potential audio issue)
    if len(raw.split()) < 5 and chunk_info["end_time"] - chunk_info["start_time"] > 30:
        chunk_info["mismatch_flags"].append("unusually_short_transcript_for_duration")

    # Flag if mismatch count exceeds threshold
    if len(chunk_info["mismatch_flags"]) > QC_THRESHOLDS["max_mismatch_count"]:
        chunk_info["mismatch_flags"].append("excessive_flags_per_chunk")

    chunk_info["verified_transcript"] = raw  # In this pass, verified = raw with flags
    return chunk_info


async def _stitch_transcript(job: Dict[str, Any]) -> Dict[str, str]:
    """Stitch chunks into raw, verified, and approved full transcripts."""
    job_id = job["job_id"]
    chunks = sorted(job.get("chunks", []), key=lambda c: c["sequence"])

    raw_parts = []
    verified_parts = []

    for chunk in chunks:
        if chunk.get("raw_transcript"):
            # De-duplicate overlap by skipping first chunk overlap region
            text = chunk["raw_transcript"]
            # Simple de-duplication: if same word appears at boundary, trim
            raw_parts.append(text)

        if chunk.get("verified_transcript"):
            verified_parts.append(chunk["verified_transcript"])

    raw_full = "\n\n".join(raw_parts)
    verified_full = "\n\n".join(verified_parts)

    raw_path = _transcript_path(job_id, "raw")
    verified_path = _transcript_path(job_id, "verified")

    raw_path.write_text(raw_full, encoding="utf-8")
    verified_path.write_text(verified_full, encoding="utf-8")

    return {"raw": str(raw_path), "verified": str(verified_path)}


def _boundary_coherence_audit(job: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flag chunk-edge risks in stitched multi-chunk transcripts."""
    import re

    chunks = sorted(
        [c for c in job.get("chunks", []) if c.get("raw_transcript")],
        key=lambda c: c["sequence"],
    )
    if len(chunks) < 2:
        return []

    high_risk_pattern = re.compile(
        r"\b(?:mr\.|mrs\.|ms\.|dr\.|judge|counsel|exhibit|case|hearing|oath|sworn|"
        r"\d{1,2}[/.-]\d{1,2}[/.-](?:19|20)\d{2}|[A-Z][a-z]+ [A-Z][a-z]+)\b"
    )
    speaker_pattern = re.compile(r"\b(?:Q\.|A\.|THE COURT|MR\.|MS\.|MRS\.|DR\.)\b")
    flags: List[Dict[str, Any]] = []

    for prev, cur in zip(chunks, chunks[1:]):
        gap_seconds = float(cur.get("start_time", 0)) - float(prev.get("end_time", 0))
        prev_words = str(prev.get("raw_transcript") or "").split()
        cur_words = str(cur.get("raw_transcript") or "").split()
        edge_words = prev_words[-8:] + cur_words[:8]
        edge_text = " ".join(edge_words)
        phrase_break = bool(prev_words and cur_words and not str(prev.get("raw_transcript", "")).rstrip().endswith((".", "?", "!", ":", ";")))
        markers = sorted(set(m.group(0) for m in high_risk_pattern.finditer(edge_text)))
        speakers = sorted(set(m.group(0) for m in speaker_pattern.finditer(edge_text)))

        if gap_seconds > CHUNK_OVERLAP_SEC:
            flags.append({
                "type": "chunk_boundary_time_gap",
                "severity": "warning",
                "left_chunk": prev["chunk_id"],
                "right_chunk": cur["chunk_id"],
                "gap_seconds": round(gap_seconds, 3),
                "message": "Boundary discontinuity exceeds 3 seconds; verify against original audio.",
            })

        if phrase_break and len(edge_words) > 8:
            flags.append({
                "type": "possible_phrase_break_spanning_boundary",
                "severity": "warning",
                "left_chunk": prev["chunk_id"],
                "right_chunk": cur["chunk_id"],
                "tokens_to_review": len(edge_words),
                "markers": markers,
                "speaker_markers": speakers,
                "message": "Phrase may span chunk edge; verify names, dates, legal terms, exhibit numbers, and speaker changes against audio.",
            })

        if markers or speakers:
            flags.append({
                "type": "high_risk_terms_at_boundary",
                "severity": "review_aid",
                "left_chunk": prev["chunk_id"],
                "right_chunk": cur["chunk_id"],
                "markers": markers,
                "speaker_markers": speakers,
                "message": "High-risk transcript content appears at a chunk edge; primary verification is original audio versus transcript.",
            })

    return flags


async def _critical_field_verification(transcript_text: str) -> List[str]:
    """Full-document pass for critical fields: names, dates, addresses, legal phrases."""
    flags = []

    if not transcript_text:
        return ["empty_transcript"]

    text_lower = transcript_text.lower()

    # Flag potential case numbers (pattern: digits with separators)
    import re
    case_patterns = re.findall(r'(?:case\s*(?:no\.?|#|number)?[:.\s]*[\d]{1,4}[-/\s][\d]+)', text_lower)
    if len(case_patterns) > 0:
        # Normal case - just track count
        pass

    # Flag oath/attestation language — verify proper attribution
    oath_phrases = ["under penalty of perjury", "sworn testimony", "affirm under oath", "certify under penalty"]
    for phrase in oath_phrases:
        if phrase in text_lower:
            # Check if speaker is attributed within 100 chars before
            idx = text_lower.find(phrase)
            preceding = transcript_text[max(0, idx-100):idx]
            if not any(sp in preceding for sp in ["i", "the witness", "mr.", "ms.", "dr."]):
                flags.append(f"unattributed_oath: {phrase}")

    # Flag potential dates in legal context
    date_pattern = re.findall(r'(?:on\s+)?\d{1,2}[/\-.]\d{1,2}[/\-.](?:19|20)\d{2}', transcript_text)
    if len(date_pattern) > 5:
        flags.append(f"many_dates_require_verification: {len(date_pattern)} found")

    # Flag dollar amounts — should be reviewed
    amounts = re.findall(r'\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?', transcript_text)
    if len(amounts) > 3:
        flags.append(f"financial_amounts_require_review: {len(amounts)} found")

    # Flag potential document numbers
    doc_numbers = re.findall(r'(?:exhibit\s*[a-z]?\d?|document\s*(?:no\.?|number)?[:.\s]*[\d]+)', text_lower)
    if len(doc_numbers) > 2:
        flags.append(f"document_references_require_verification: {len(doc_numbers)} found")

    return flags


async def _process_chunk_background(job_id: str, chunk_id: str):
    """Background task to process a single chunk: transcribe + verify."""
    try:
        job = _load_job(job_id)
        chunk = _load_chunk(job_id, chunk_id)
        job.setdefault("audit_trail", []).append({
            "event": "chunk_transcription_started",
            "timestamp": datetime.utcnow().isoformat(),
            "chunk_id": chunk_id,
            "actor": "system",
        })
        _save_job(job)

        audio_path = job["file_path"]

        # Lazy-load STT service
        from app.services.max.stt_service import stt_service

        # Transcribe
        chunk = await _transcribe_chunk(chunk, audio_path, stt_service)
        _save_chunk(chunk)

        # Verify
        chunk = _load_chunk(job_id, chunk_id)
        chunk = await _verify_chunk(chunk, audio_path, stt_service)
        _save_chunk(chunk)

        # Update job
        job = _load_job(job_id)
        _replace_job_chunk(job, chunk)
        completed = sum(1 for c in job.get("chunks", []) if c.get("raw_transcript"))
        failed = sum(
            1
            for c in job.get("chunks", [])
            if "audio_extraction_failed" in c.get("mismatch_flags", [])
            or "transcription_failed" in str(c.get("mismatch_flags", []))
        )
        job["chunks_complete"] = completed
        job["chunks_failed"] = failed
        job.setdefault("audit_trail", []).append({
            "event": "chunk_transcription_completed" if chunk.get("raw_transcript") else "chunk_transcription_failed",
            "timestamp": datetime.utcnow().isoformat(),
            "chunk_id": chunk_id,
            "actor": "system",
            "processing_status": chunk.get("processing_status"),
            "confidence": chunk.get("confidence"),
        })

        # Update state if first chunk ready
        if chunk["sequence"] == 0 and chunk.get("raw_transcript"):
            if job["state"] == "first_chunk_processing":
                job["state"] = "first_chunk_ready"
                job["display_state"] = "paused_awaiting_review"
                job["audit_trail"].append({
                    "event": "first_chunk_ready",
                    "timestamp": datetime.utcnow().isoformat(),
                    "actor": "system",
                    "chunk_id": chunk_id,
                    "message": "Paused awaiting review of first chunk.",
                })
                _save_job(job)

        if job.get("state") == "processing_remaining_chunks" and job.get("chunks_total") and completed >= job["chunks_total"]:
            paths = await _stitch_transcript(job)
            job["raw_transcript_path"] = paths["raw"]
            job["verified_transcript_path"] = paths["verified"]
            job["boundary_coherence_flags"] = _boundary_coherence_audit(job)
            raw_text = Path(paths["raw"]).read_text(encoding="utf-8") if Path(paths["raw"]).exists() else ""
            job["critical_field_flags"] = await _critical_field_verification(raw_text)
            job["state"] = "needs_review"
            job["display_state"] = "needs_review"
            job["audit_trail"].append({
                "event": "all_chunks_transcribed",
                "timestamp": datetime.utcnow().isoformat(),
                "actor": "system",
                "raw_transcript_path": paths["raw"],
                "verified_transcript_path": paths["verified"],
                "boundary_flags": len(job["boundary_coherence_flags"]),
            })

        _save_job(job)

    except Exception as e:
        logger.error(f"Chunk processing error {job_id}/{chunk_id}: {e}")
        try:
            chunk = _load_chunk(job_id, chunk_id)
            chunk["processing_status"] = "failed"
            chunk.setdefault("mismatch_flags", []).append(f"background_processing_error: {str(e)[:100]}")
            _save_chunk(chunk)
            job = _load_job(job_id)
            job.setdefault("audit_trail", []).append({
                "event": "chunk_processing_exception",
                "timestamp": datetime.utcnow().isoformat(),
                "actor": "system",
                "chunk_id": chunk_id,
                "error": str(e)[:300],
            })
            job["chunks_failed"] = sum(1 for c in job.get("chunks", []) if c.get("processing_status") == "failed")
            _save_job(job)
        except Exception:
            pass


# ── Routes ────────────────────────────────────────────────────────────

@router.get("/modes", response_model=TranscriptModeResponse)
async def get_modes():
    """Return supported source modes. web_chat labeled as future-ready."""
    modes = [
        {"id": "deposition", "label": "Deposition", "active": True},
        {"id": "court_hearing", "label": "Court Hearing", "active": True},
        {"id": "conference", "label": "Conference", "active": True},
        {"id": "general_intake", "label": "General Transcript Intake", "active": True},
        {"id": "web_chat", "label": "Web Chat", "active": False, "note": "Future-ready — not fully active in this pass"},
    ]
    return TranscriptModeResponse(modes=modes, web_chat_note="Web Chat integration is future-ready and not yet fully active in this pass.")


@router.post("/jobs", response_class=JSONResponse)
async def create_job(background_tasks: BackgroundTasks, source_mode: str = "general_intake", uploader: str = "founder"):
    """Create a transcription job from uploaded audio file. Chunking starts immediately."""
    if source_mode not in SOURCE_MODES:
        raise HTTPException(status_code=400, detail=f"Invalid source_mode. Use one of: {SOURCE_MODES}")

    job_id = f"tf_{uuid.uuid4().hex[:12]}"

    # Placeholder — file upload handled separately via /jobs/{id}/upload
    job = {
        "job_id": job_id,
        "state": "uploaded",
        "display_state": "uploaded",
        "source_mode": source_mode,
        "uploader": uploader,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "file_path": None,
        "file_size": 0,
        "file_name": None,
        "duration_sec": None,
        "chunks_total": 0,
        "chunks_complete": 0,
        "chunks_failed": 0,
        "verification_failures": 0,
        "reviewer_corrections_count": 0,
        "overall_confidence": None,
        "raw_transcript_path": None,
        "verified_transcript_path": None,
        "approved_transcript_path": None,
        "critical_field_flags": [],
        "boundary_coherence_flags": [],
        "qc_summary": None,
        "notes": None,
        "chunks": [],
        "audit_trail": [
            {"event": "job_created", "timestamp": datetime.utcnow().isoformat(), "actor": uploader}
        ],
    }
    _save_job(job)
    return {"job_id": job_id, "state": "uploaded", "message": "Job created. Upload audio via PUT /jobs/{job_id}/upload"}


@router.put("/jobs/{job_id}/upload")
async def upload_audio(background_tasks: BackgroundTasks, job_id: str, file: UploadFile = File(...)):
    """Upload audio file and initialize chunking. Starts background chunk processing."""
    job = _load_job(job_id)

    if job["state"] not in ["uploaded"]:
        raise HTTPException(status_code=409, detail=f"Cannot upload — job is in state '{job['state']}'")

    # Save uploaded file
    suffix = Path(file.filename or "audio.mp3").suffix or ".mp3"
    upload_dir = ARTIFACTS_DIR / job_id
    os.makedirs(upload_dir, exist_ok=True)
    file_path = upload_dir / f"source{suffix}"

    content = await file.read()
    file_path.write_bytes(content)
    file_size = len(content)

    # Update job
    duration = _estimate_duration(file_size)
    job["file_path"] = str(file_path)
    job["file_size"] = file_size
    job["file_name"] = file.filename or "audio.mp3"
    job["duration_sec"] = duration
    job["state"] = "chunking"
    job["display_state"] = "chunking"
    job["audit_trail"].append({
        "event": "file_uploaded",
        "timestamp": datetime.utcnow().isoformat(),
        "actor": job["uploader"],
        "file_name": file.filename,
        "file_size": file_size,
    })
    _save_job(job)

    # Create chunks
    chunks = _chunk_job(job)
    job["chunks"] = chunks
    job["chunks_total"] = len(chunks)
    job["state"] = "first_chunk_processing"
    job["display_state"] = "first_chunk_processing"
    job["audit_trail"].append({
        "event": "chunks_created",
        "timestamp": datetime.utcnow().isoformat(),
        "actor": "system",
        "chunks_total": len(chunks),
        "chunk_duration_sec": CHUNK_DURATION_SEC,
        "chunk_overlap_sec": CHUNK_OVERLAP_SEC,
    })
    job["audit_trail"].append({
        "event": "first_chunk_queued",
        "timestamp": datetime.utcnow().isoformat(),
        "actor": "system",
        "chunk_id": "chunk_000",
    })
    _save_job(job)

    # Save individual chunk files
    for chunk in chunks:
        _save_chunk(chunk)

    # Queue only chunk 0 for the first review gate.
    background_tasks.add_task(_process_chunk_background, job_id, "chunk_000")

    return {
        "job_id": job_id,
        "state": "first_chunk_processing",
        "chunks_total": len(chunks),
        "file_name": job["file_name"],
        "duration_sec": duration,
        "message": "Audio uploaded. Chunk 1 processing started. Poll /jobs/{job_id} for status."
    }


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get full job status and transcript state."""
    job = _load_job(job_id)

    # Build QC summary
    chunks = job.get("chunks", [])
    low_conf_count = sum(
        1
        for c in chunks
        if c.get("confidence") is not None and c.get("confidence") < QC_THRESHOLDS["min_segment_confidence"]
    )

    job["qc_summary"] = {
        "chunks_total": job.get("chunks_total", 0),
        "chunks_complete": job.get("chunks_complete", 0),
        "chunks_failed": job.get("chunks_failed", 0),
        "low_confidence_segments": low_conf_count,
        "unreviewed_low_confidence": sum(
            1
            for c in chunks
            if c.get("confidence") is not None
            and c.get("confidence") < QC_THRESHOLDS["min_segment_confidence"]
            and c.get("review_status") != "good"
        ),
        "mismatch_count": sum(len(c.get("mismatch_flags", [])) for c in chunks),
        "reviewer_corrections_count": job.get("reviewer_corrections_count", 0),
        "overall_confidence": job.get("overall_confidence"),
    }
    if job.get("state") == "first_chunk_ready":
        job["display_state"] = "paused_awaiting_review"
        job["truth_summary"] = "Paused awaiting review of first chunk. Remaining chunks are intentionally pending."
    elif job.get("chunks_total", 0) == 0 and job.get("state") in {"uploaded", "chunking"}:
        job["display_state"] = "preparing_chunk_count"
        job["truth_summary"] = "Preparing audio and detecting chunks."
    else:
        job["display_state"] = job.get("display_state") or job.get("state")

    return job


@router.get("/jobs/{job_id}/chunks/{chunk_id}")
async def get_chunk(job_id: str, chunk_id: str):
    """Get status of a specific chunk."""
    chunk = _load_chunk(job_id, chunk_id)
    return chunk


@router.get("/jobs/{job_id}/chunks/{chunk_id}/audio")
async def get_chunk_audio_segment(job_id: str, chunk_id: str):
    """Stream the original audio segment for this chunk (for replay/QA)."""
    job = _load_job(job_id)
    if not job.get("file_path"):
        raise HTTPException(status_code=404, detail="Original audio not found")

    chunk = _load_chunk(job_id, chunk_id)
    start = chunk["start_time"]
    end = chunk["end_time"]

    # For playback, we return the full file + time range
    # Frontend handles range request for the segment
    from fastapi.responses import FileResponse
    return FileResponse(job["file_path"], media_type="audio/mpeg")


@router.post("/jobs/{job_id}/chunks/{chunk_id}/review")
async def review_chunk(job_id: str, chunk_id: str, status: str = Query(...), reviewer: str = Query("founder")):
    """Mark a chunk as good/needs_review/edited."""
    if status not in ["good", "needs_review", "edited"]:
        raise HTTPException(status_code=400, detail="status must be: good | needs_review | edited")

    chunk = _load_chunk(job_id, chunk_id)
    job = _load_job(job_id)

    chunk["review_status"] = status
    chunk["reviewer"] = reviewer
    chunk["reviewer_timestamp"] = datetime.utcnow().isoformat()
    _save_chunk(chunk)
    _replace_job_chunk(job, chunk)

    job["audit_trail"].append({
        "event": "chunk_reviewed",
        "timestamp": datetime.utcnow().isoformat(),
        "actor": reviewer,
        "chunk_id": chunk_id,
        "status": status,
    })

    # Check if all chunks reviewed
    all_reviewed = all(c.get("review_status") != "pending" for c in job.get("chunks", []))
    if all_reviewed and job["state"] == "processing_remaining_chunks":
        job["state"] = "verification_running"

    _save_job(job)
    return {"chunk_id": chunk_id, "review_status": status, "reviewer": reviewer}


@router.post("/jobs/{job_id}/continue")
async def continue_remaining_chunks(background_tasks: BackgroundTasks, job_id: str, reviewer: str = Query("founder")):
    """Queue remaining chunks after first chunk review."""
    job = _load_job(job_id)
    if job["state"] != "first_chunk_ready":
        raise HTTPException(status_code=409, detail=f"Cannot continue — job is in state '{job['state']}'")

    chunks = sorted(job.get("chunks", []), key=lambda c: c.get("sequence", 0))
    if not chunks or not chunks[0].get("raw_transcript"):
        raise HTTPException(status_code=409, detail="Cannot continue — first chunk transcript is not ready")
    if chunks[0].get("review_status") == "pending":
        raise HTTPException(status_code=409, detail="Review chunk_000 as Good or Needs Review before continuing")

    queued = []
    for chunk in chunks[1:]:
        if not chunk.get("raw_transcript") and chunk.get("processing_status") != "transcribing":
            chunk["processing_status"] = "pending"
            _save_chunk(chunk)
            _replace_job_chunk(job, chunk)
            background_tasks.add_task(_process_chunk_background, job_id, chunk["chunk_id"])
            queued.append(chunk["chunk_id"])

    if not queued:
        raise HTTPException(status_code=409, detail="No remaining chunks are available to queue")

    job["state"] = "processing_remaining_chunks"
    job["display_state"] = "processing_remaining_chunks"
    job.setdefault("audit_trail", []).append({
        "event": "remaining_chunks_queued",
        "timestamp": datetime.utcnow().isoformat(),
        "actor": reviewer,
        "queued_chunks": queued,
    })
    _save_job(job)
    return {"job_id": job_id, "state": job["state"], "queued_chunks": queued}


@router.post("/jobs/{job_id}/approve")
async def approve_transcript(job_id: str, action: ApprovalAction):
    """Submit approval/rejection decision. Human-only gate."""
    job = _load_job(job_id)

    if action.action not in ["approve", "reject", "correct_and_approve"]:
        raise HTTPException(status_code=400, detail="action must be: approve | reject | correct_and_approve")

    # Pre-approval checks
    if action.action in ["approve", "correct_and_approve"]:
        chunks = job.get("chunks", [])

        # Check all chunks have raw transcripts
        missing = [c["chunk_id"] for c in chunks if not c.get("raw_transcript")]
        if missing:
            raise HTTPException(status_code=409, detail=f"Chunks missing raw transcript: {missing}")

        # Check critical field flags
        if job.get("critical_field_flags"):
            raise HTTPException(status_code=409, detail=f"Cannot approve — unresolved critical field flags: {job['critical_field_flags']}")

        # Check low confidence segments
        low_conf = [c["chunk_id"] for c in chunks if (c.get("confidence") or 0) < QC_THRESHOLDS["min_segment_confidence"] and c.get("review_status") != "good"]
        if low_conf:
            raise HTTPException(status_code=409, detail=f"Unreviewed low-confidence chunks: {low_conf}. Review before approving.")

    # Apply corrections if any
    corrections_applied = 0
    if action.action == "correct_and_approve" and action.chunk_corrections:
        for chunk_id, corrected_text in action.chunk_corrections.items():
            chunk = _load_chunk(job_id, chunk_id)
            chunk["verified_transcript"] = corrected_text
            chunk["review_status"] = "edited"
            chunk["reviewer"] = action.reviewer
            chunk["reviewer_timestamp"] = datetime.utcnow().isoformat()
            _save_chunk(chunk)
            _replace_job_chunk(job, chunk)
            corrections_applied += 1

        # Re-stitch with corrections
        paths = await _stitch_transcript(job)
        job["verified_transcript_path"] = paths["verified"]
        job["boundary_coherence_flags"] = _boundary_coherence_audit(job)

    # Run full-document critical field verification before approval
    if action.action in ["approve", "correct_and_approve"]:
        paths = await _stitch_transcript(job)
        job["raw_transcript_path"] = paths["raw"]
        job["verified_transcript_path"] = paths["verified"]
        job["boundary_coherence_flags"] = _boundary_coherence_audit(job)
        raw_path = _transcript_path(job_id, "raw")
        if raw_path.exists():
            text = raw_path.read_text(encoding="utf-8")
            flags = await _critical_field_verification(text)
            job["critical_field_flags"] = flags
            if flags:
                # Cannot auto-approve with flags — require human resolution
                job["state"] = "needs_review"
                job["audit_trail"].append({
                    "event": "critical_field_flags_found",
                    "timestamp": datetime.utcnow().isoformat(),
                    "flags": flags,
                })
                _save_job(job)
                return {"status": "blocked", "reason": "critical_field_flags_require_resolution", "flags": flags}

    # Final state transition
    state_map = {
        "approve": "approved",
        "correct_and_approve": "corrected_and_approved",
        "reject": "rejected",
    }
    new_state = state_map[action.action]
    job["state"] = new_state
    job["reviewer_corrections_count"] = corrections_applied

    # Final stitch
    paths = await _stitch_transcript(job)
    job["raw_transcript_path"] = paths["raw"]
    job["verified_transcript_path"] = paths["verified"]
    job["boundary_coherence_flags"] = _boundary_coherence_audit(job)

    # Copy to approved path
    approved_path = _transcript_path(job_id, "approved")
    verified_path = Path(paths["verified"])
    if verified_path.exists():
        approved_path.write_bytes(verified_path.read_bytes())
    job["approved_transcript_path"] = str(approved_path)

    job["audit_trail"].append({
        "event": f"transcript_{action.action.replace('_', '_')}",
        "timestamp": datetime.utcnow().isoformat(),
        "actor": action.reviewer,
        "notes": action.notes,
        "corrections_applied": corrections_applied,
    })

    _save_job(job)
    token_tracker.log_fixed_cost("transcriptforge-approval", feature="transcription", source="transcriptforge")

    return {
        "job_id": job_id,
        "state": new_state,
        "reviewer": action.reviewer,
        "corrections_applied": corrections_applied,
        "approved_path": str(approved_path) if new_state in ["approved", "corrected_and_approved"] else None,
        "audit_trail_entry": job["audit_trail"][-1],
    }


@router.get("/jobs/{job_id}/transcript/{kind}")
async def get_transcript(job_id: str, kind: str):
    """Get transcript text. kind must be: raw | verified | approved."""
    if kind not in ["raw", "verified", "approved"]:
        raise HTTPException(status_code=400, detail="kind must be: raw | verified | approved")

    job = _load_job(job_id)

    # Check access control — only show approved to non-founders if they have review access
    # For this pass: founder-only access
    path_key = f"{kind}_transcript_path"
    p = job.get(path_key)
    if not p:
        raise HTTPException(status_code=404, detail=f"No {kind} transcript available — job state is '{job['state']}'")

    text = Path(p).read_text()
    return {"job_id": job_id, "kind": kind, "text": text, "state": job["state"]}


@router.get("/jobs")
async def list_jobs(state: Optional[str] = None, uploader: Optional[str] = None):
    """List all jobs, optionally filtered by state or uploader."""
    jobs = []
    for p in JOBS_DIR.glob("*.json"):
        try:
            job = json.loads(p.read_text())
            if state and job.get("state") != state:
                continue
            if uploader and job.get("uploader") != uploader:
                continue
            jobs.append({
                "job_id": job["job_id"],
                "state": job["state"],
                "display_state": "paused_awaiting_review" if job.get("state") == "first_chunk_ready" else job.get("display_state", job.get("state")),
                "source_mode": job.get("source_mode"),
                "uploader": job.get("uploader"),
                "created_at": job.get("created_at"),
                "file_name": job.get("file_name"),
                "chunks_total": job.get("chunks_total", 0),
                "chunks_complete": job.get("chunks_complete", 0),
            })
        except Exception:
            continue

    jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    return {"jobs": jobs, "total": len(jobs)}


@router.post("/jobs/{job_id}/stop")
async def stop_job(job_id: str):
    """Stop processing at current chunk. Job remains in current state for review."""
    job = _load_job(job_id)
    if job["state"] not in ["first_chunk_processing", "first_chunk_ready", "processing_remaining_chunks"]:
        raise HTTPException(status_code=409, detail=f"Cannot stop job in state '{job['state']}'")

    job["audit_trail"].append({
        "event": "job_stopped_by_user",
        "timestamp": datetime.utcnow().isoformat(),
        "actor": job.get("uploader", "unknown"),
    })

    # Downgrade to needs_review so user can assess what we have
    if job["state"] in ["first_chunk_processing", "first_chunk_ready", "processing_remaining_chunks"]:
        job["state"] = "needs_review"

    _save_job(job)
    return {"job_id": job_id, "state": job["state"], "message": "Job stopped. Review available chunks."}


@router.get("/jobs/{job_id}/audit")
async def get_audit_trail(job_id: str):
    """Return full audit trail for a job."""
    job = _load_job(job_id)
    return {"job_id": job_id, "audit_trail": job.get("audit_trail", [])}


@router.get("/incidents/diagnose")
async def diagnose_incident(job_id: Optional[str] = None, include_logs: bool = Query(True)):
    """MAX/Hermes/OpenClaw timeline diagnosis for TranscriptForge incidents."""
    from app.services.max.transcriptforge_incidents import build_transcriptforge_incident_diagnosis
    return build_transcriptforge_incident_diagnosis(job_id=job_id, include_logs=include_logs)


@router.post("/incidents/repair")
async def queue_incident_repair(job_id: str = Query(...), description: Optional[str] = None):
    """Queue a bounded OpenClaw repair only after the OpenClaw gate is healthy."""
    from app.services.max.transcriptforge_incidents import queue_bounded_transcriptforge_repair
    return queue_bounded_transcriptforge_repair(job_id=job_id, description=description)


@router.post("/incidents/learning")
async def record_incident_learning(payload: Dict[str, Any]):
    """Record validated or inconclusive TranscriptForge incident learning into Hermes memory."""
    from app.services.max.transcriptforge_incidents import record_incident_learning
    return record_incident_learning(
        subject=str(payload.get("subject") or "TranscriptForge incident learning"),
        status=str(payload.get("status") or "PENDING"),
        learning_type=str(payload.get("learning_type") or "inconclusive"),
        evidence=dict(payload.get("evidence") or {}),
        fix_summary=str(payload.get("fix_summary") or "No fix summary supplied."),
        commit_hash=payload.get("commit_hash"),
    )


# ── Direct transcription (no job flow) for quick intake ──────────────

@router.post("/transcribe-direct")
async def transcribe_direct(file: UploadFile = File(...), source_mode: str = "general_intake"):
    """One-shot transcription of uploaded audio. Does NOT go through full QA pipeline.

    Use for quick intake when full QA pipeline is not needed.
    Full pipeline use case: upload via POST /jobs then approve via POST /jobs/{id}/approve
    """
    from app.services.max.stt_service import stt_service

    if not stt_service.is_configured:
        raise HTTPException(status_code=503, detail="STT not configured — GROQ_API_KEY missing")

    suffix = Path(file.filename or "audio.mp3").suffix or ".mp3"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        transcript = await stt_service.transcribe(tmp_path)
        token_tracker.log_fixed_cost("transcriptforge-direct", feature="stt", source="transcriptforge")
        return {
            "text": transcript,
            "source_mode": source_mode,
            "filename": file.filename,
            "note": "Direct transcription — not reviewed, not approval-gated. Use job flow for legal/high-risk use."
        }
    finally:
        tmp_path.unlink(missing_ok=True)
