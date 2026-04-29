# TranscriptForge v10 Phase 1 — Export & Proofreading UI Implementation Plan

**Created:** 2026-04-29
**Status:** Phase 1 IN PROGRESS
**Lane:** v10 test (port 3010) — `~/empire-repo-v10` on `feature/v10.0-test-lane`

---

## PHASE 0 TRUTH (VERIFIED)

### Route / File Locations
- Frontend: `~/empire-repo-v10/empire-command-center/app/components/screens/TranscriptForgePage.tsx`
- Backend router: `~/empire-repo-v10/backend/app/routers/transcriptforge.py`
- STT service: `~/empire-repo-v10/backend/app/services/max/stt_service.py`

### Backend Routes (all under `/api/v1/transcriptforge/`)
Job workflow: `uploaded → chunking → first_chunk_processing → first_chunk_ready → processing_remaining_chunks → verification_running → needs_review → approved / corrected_and_approved / rejected`

Core endpoints: POST/GET `/jobs`, PUT `/jobs/{id}/upload`, GET `/jobs/{id}`, POST `/jobs/{id}/chunks/{id}/review`, POST `/jobs/{id}/continue`, POST `/jobs/{id}/approve`, GET `/jobs/{id}/transcript/{kind}`, GET `/jobs/{id}/chunks/{id}/audio`, POST `/transcribe-direct`

### Data Model
- `ChunkInfo`: chunk_id, job_id, sequence, start_time, end_time, raw_transcript, verified_transcript, confidence, mismatch_flags, review_status, reviewer, reviewer_timestamp, processing_status, raw_transcript_path, verified_transcript_path
- `TranscriptJob`: job_id, state, source_mode, uploader, created_at, updated_at, file_name, file_size, duration_sec, chunks_total/complete/failed, chunks[], qc_summary, audit_trail[]
- Transcript text served as plain JSON: `{"text": "...", "kind": "...", "state": "..."}`

### Speaker / Diarization
**Groq Whisper does NOT return speaker diarization.** Speaker labels must be manually assigned.

### Timestamps
- Chunk start_time / end_time exist per chunk (in seconds, float).
- Timestamps are NOT embedded in served transcript text.
- SRT/VTT export can only use chunk-level timing, not word-level.

### Audio
- Source audio at: `artifacts/{job_id}/source{suffix}`
- Per-chunk audio extraction via GStreamer (`_GSTREAMER_EXTRACT_SCRIPT`).
- Per-chunk audio URL in frontend: `` `${API}/transcriptforge/jobs/${job_id}/chunks/${chunk_id}/audio#t=${start},${end}` ``
- **No full-job audio export endpoint exists (Phase 2 item).**

---

## PHASE 1 SCOPE

### What Is Being Built
Frontend-only upgrade to TranscriptForgePage.tsx:
- Structured transcript segment building from job.chunks[]
- Manual speaker label assignment + localStorage persistence
- Local proofreading edits with localStorage persistence
- Export tools: TXT, MD, JSON, HTML, SRT, VTT
- Export preview modal with toggle options
- Audio sync / chunk-level playback highlight
- No new backend changes

### Files to Create
| File | Purpose |
|------|---------|
| `app/schemas/transcriptforge-schemas.ts` | TypeScript interfaces |
| `app/lib/transcriptforge/time.ts` | Timestamp formatting helpers |
| `app/lib/transcriptforge/exporters.ts` | Export format utilities |
| `app/hooks/useTranscriptForgeProofreading.ts` | React Context for proofreading state |
| `app/components/screens/TranscriptExportPanel.tsx` | Export panel UI |
| `app/components/screens/TranscriptExportPreviewModal.tsx` | Export preview modal |

### Files to Modify
| File | Purpose |
|------|---------|
| `app/components/screens/TranscriptForgePage.tsx` | Integrate proofreading panel + export tools |

---

## LOCAL STORAGE KEYS

| Key | Content |
|-----|---------|
| `transcriptforge_speaker_labels` | `{ [jobId]: { [chunkId]: string } }` |
| `transcriptforge_local_edits` | `{ [jobId]: { [chunkId]: string } }` |
| `transcriptforge_reviewed_segments` | `{ [jobId]: Set<chunkId> }` |

---

## EXPORT FORMAT BEHAVIOR

### TXT
Plain text, optionally with timestamps `[HH:MM:SS]` and speaker labels.

### Markdown
Markdown-formatted with optional metadata header, speaker labels, timestamps.

### JSON
Structured export with segments array containing id, start, end, speaker, text, confidence, reviewed, edited fields.

### HTML / Printable
Styled HTML with proper formatting, print media query, segment blocks.

### SRT / VTT
- Enabled only when all chunks have valid (positive, end > start) start_time/end_time.
- If any chunk lacks valid timestamps: disable SRT/VTT and show notice.
- Format: chunk-level timing, not word-level.
- SRT: sequential index + timestamp line + text
- VTT: WEBVTT header + cue format with speaker

---

## AUDIO SYNC BEHAVIOR

- Per-chunk audio playback already exists in TranscriptForgePage.tsx (`<audio controls src={...}/chunks/{chunk_id}/audio#t=...>`).
- Highlight active chunk when its audio is playing.
- "Full-transcript audio sync" requires a Phase 2 full-job audio endpoint — not available.
- Show informational notice about chunk-level vs full-sync mode.
- Audio export: no backend endpoint → disabled button with Phase 2 notice.

---

## REVISED STATE TRACKING

Per-segment reviewed state tracked in localStorage, independent of backend review_status.
A segment is "reviewed" when user clicks "Mark Reviewed" or "Good" in proofreading mode.
Export options can include/exclude non-reviewed segments.

---

## LIMITATIONS (DOCUMENTED)

1. **No diarization** — Groq Whisper doesn't provide speaker diarization; all labels are manual
2. **No word-level timestamps** — SRT/VTT use chunk-level timing only
3. **No full audio export** — Phase 2 backend endpoint needed
4. **No backend save for edits** — localStorage-only proofreading until Phase 2 save endpoint
5. **No undo/redo for exports** — only for local edit sessions

---

## PHASE 2 BACKEND ENDPOINTS (PROPOSED)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/transcriptforge/jobs/{job_id}/audio` | Full job audio stream |
| GET | `/api/v1/transcriptforge/jobs/{job_id}/export/audio-bundle` | ZIP with all chunk audio |
| POST | `/api/v1/transcriptforge/jobs/{job_id}/segments/{chunk_id}` | Save proofreading edits |
| POST | `/api/v1/transcriptforge/jobs/{job_id}/speaker-labels` | Save speaker label assignments |
| GET | `/api/v1/transcriptforge/jobs/{job_id}/export/{format}` | Server-side export (progressive enhancement) |

---

## BUILD VERIFICATION

- `npm run build` — zero errors
- `curl localhost:3010/transcriptforge` — 200
- Stable regression: `curl localhost:3005` — 200, no /transcriptforge route on stable

---

## COMMIT HISTORY

| Commit | Description |
|--------|-------------|
| (pending) | Phase 1 — export tools + proofreading UI + speaker labels |
