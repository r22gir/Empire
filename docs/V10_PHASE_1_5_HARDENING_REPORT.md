# EmpireBox v10 Phase 1.5 Hardening Report
**Date:** 2026-04-29
**Branch:** feature/v10.0-test-lane
**Worktree:** ~/empire-repo-v10
**Port:** 3010 (test-studio.empirebox.store)

---

## Phase 1.5 Scope

Frontend-only hardening for TranscriptForge v10 and ArchiveForge v10.
No backend changes. No Phase 2 implementation. No stable production changes.

---

## Files Changed

### New Files
| File | Purpose | TF/AF |
|------|---------|-------|
| `app/hooks/useUIPhase.ts` | Shared UI phase constants (TF-1) | Both |
| `app/hooks/useTranscriptForgeAPI.ts` | Phase 2 backend swap point stubs (TF-3) | TF |
| `app/lib/transcriptforge/audio.ts` | Audio validation helper (TF-6) | TF |

### Modified Files
| File | Changes | TF/AF |
|------|---------|-------|
| `app/hooks/useTranscriptForgeProofreading.tsx` | Added EditPatch export, Speaker Index, Confidence Calibration (TF-2, TF-4, TF-5) | TF |
| `app/schemas/transcriptforge-schemas.ts` | Added EditPatch, SpeakerIndexEntry, ConfidenceCalibrationEntry, AudioValidationResult interfaces | TF |
| `app/components/screens/TranscriptExportPanel.tsx` | Added Edit Patch JSON download button (TF-2) | TF |
| `app/hooks/useArchiveForgePrototype.ts` | Re-export PHASE from useUIPhase for backward compatibility | AF |
| `app/components/screens/ConditionGradingWizard.tsx` | Added skip link, result disclaimer (AF-1, AF-2) | AF |
| `app/schemas/archiveforge-schemas.ts` | Added comment on ConditionGradeResult output contract (AF-2) | AF |

### Documentation
| File | Purpose |
|------|---------|
| `docs/V10_PHASE_1_5_HARDENING_REPORT.md` | This report |

---

## TranscriptForge Enhancements

### TF-1: Shared UI Phase Hook
- **File:** `app/hooks/useUIPhase.ts`
- **Exports:** `TRANSCRIPTFORGE_PHASE`, `ARCHIVEFORGE_PHASE`, `PHASE` (alias), `isPrototypePhase()`, `getPrototypeBanner()`
- **Used by:** `useArchiveForgePrototype.ts` (PHASE re-export for backward compatibility)

### TF-2: Edit Patch Export
- **Files:** `transcriptforge-schemas.ts`, `useTranscriptForgeProofreading.tsx`, `TranscriptExportPanel.tsx`
- **Interface:** `EditPatch` with `jobId`, `exportedAt`, `source: 'localStorage'`, `edits[]`
- **Storage:** No new localStorage — uses existing `transcriptforge_local_edits`
- **Download button:** "Edit Patch JSON" in Export panel, filename: `{jobId}_transcriptforge_edit_patch.json`
- **Label:** "Local edit patch — for backup / future backend sync. Does not save to backend."
- **data-max-task:** inherited from panel context

### TF-3: Phase 2 API Hook Stub
- **File:** `app/hooks/useTranscriptForgeAPI.ts`
- **Functions:** `fetchJob`, `saveSegmentEdit`, `syncSpeakerLabels`, `markSegmentsReviewed`, `fetchJobAudio`, `fetchAudioBundle`, `fetchTranscriptExport`, `sendConfidenceFeedback`
- **All stubs:** `console.warn('[TranscriptForge] [API] {fn} not implemented — Phase 2 endpoint')` + TODO comment
- **No real fetch calls in Phase 1**

### TF-4: Confidence Calibration Queue
- **File:** `useTranscriptForgeProofreading.tsx` (context + localStorage)
- **Storage key:** `transcriptforge_confidence_calibration`
- **Entry:** `ConfidenceCalibrationEntry` — `jobId`, `chunkId`, `confidence`, `verdict` ('looks_good' | 'needs_correction' | 'unclear'), `note`, `reviewedAt`
- **Helpers:** `getCalibration()`, `setCalibration()`, `getLowConfidenceSegments()`
- **Label:** "Prototype confidence calibration — stored locally only."
- **Phase 2 TODO:** `sendConfidenceFeedback()` stub with `POST /api/v1/transcriptforge/jobs/{job_id}/confidence-feedback`

### TF-5: Speaker Index with Fingerprinting
- **File:** `useTranscriptForgeProofreading.tsx` (context + localStorage)
- **Storage key:** `transcriptforge_speaker_index`
- **Limit:** 100 entries, evict oldest by `lastSeenAt` when exceeded
- **Fingerprint:** Non-sensitive, text-based (first 3 chars + length + simple hash). NO audio/biometric data.
- **Eviction log:** `[TranscriptForge] [SpeakerIndex] index full — evicted oldest entry for {fingerprintHash}`
- **Helpers:** `getSpeakerSuggestions(text)`, `recordSpeakerUsage(label, jobId)`
- **Behavior:** Suggest on focus, do not auto-apply
- **Label:** "Local speaker suggestions — not automatic diarization."

### TF-6: Audio Validation Helper
- **File:** `app/lib/transcriptforge/audio.ts`
- **Interfaces:** `AudioValidationResult`, `AudioSource`, `AudioRisk`
- **Functions:** `validateAudioAvailability()`, `validateAudioChunk()`
- **Risk levels:** 'low' (chunk audio), 'medium' (full-job audio), 'high' (no audio)
- **M4A note:** "If playback fails, convert to MP3/WAV." — codec detection requires Phase 2 backend endpoint
- **Codec detection:** Extension-based only, not binary header parsing

---

## ArchiveForge Enhancements

### AF-1: Wizard Skip Link + Gating Polish
- **File:** `ConditionGradingWizard.tsx`
- **Skip link:** "Skip for now (prototype only)" — text-xs, text-slate-500, hover underline, left-aligned below disabled Next button
- **Visible only when:** Not all wear assessment dimensions are answered
- **data-max-task:** `data-max-task="condition-grading-skip-prototype"`
- **No backend action implied by skip**

### AF-2: Condition Grading Output Contract
- **File:** `archiveforge-schemas.ts` + `ConditionGradingWizard.tsx`
- **Added comment to `ConditionGradeResult`:** "Draft Phase 2 request body for backend condition grading endpoint. Not persisted to backend in Phase 1.5."
- **Added result screen label:** "Prototype grading — output is local and not validated by a certified grader"
- **Disclaimer in wizard header:** "Prototype grading — output is not validated by a certified grader"

### AF-3: Comparable Sales Sparkline
- **Status:** Already correctly implemented at `app/components/screens/ComparableSalesSparkline.tsx`
- **Uses Recharts:** via dynamic import with CSS fallback if recharts unavailable
- **Fallback:** CSS-based sparkline when recharts import fails
- **Empty state:** "No comparable sales yet" in styled fallback div

### AF-4: Prototype Disclaimers — Already Present
Verified all panels have clear prototype labels:

| Panel | Disclaimer | Status |
|-------|------------|--------|
| ValuationPanel | "Prototype data — not live valuation yet" | ✅ |
| MarketIntelligencePanel | "Prototype data — not live valuation yet" | ✅ |
| PlatformRecommendations | "Prototype recommendation — not connected to live marketplace data" | ✅ |
| FounderReviewQueue | "Prototype queue — flagging writes to localStorage only" | ✅ |
| ConditionGradingWizard | "Prototype grading — output not validated by a certified grader" | ✅ (improved) |
| BundleIntelligencePanel | "Prototype bundle intelligence — backend integration pending" | ✅ |

All panels have `data-max-task` attributes correctly pointing to Phase 2 backend integration tasks.

---

## localStorage Keys Reference

| Key | Module | Purpose | Max Entries |
|-----|--------|---------|-------------|
| `transcriptforge_speaker_labels` | TF | Speaker label per job/chunk | none |
| `transcriptforge_local_edits` | TF | Local transcript edits per job/chunk | none |
| `transcriptforge_reviewed_segments` | TF | Reviewed chunk IDs per job | none |
| `transcriptforge_speaker_index` | TF | Speaker suggestions with fingerprint | 100 |
| `transcriptforge_confidence_calibration` | TF | Confidence calibration verdicts | none |
| `archiveforge_flagged_items` | AF | Flagged founder review items | none |

---

## New or Changed data-max-task Attributes

| Attribute | File | Phase 2 Endpoint |
|-----------|------|-----------------|
| `transcriptforge-backend-edit-sync` | (TF-2 via ExportPanel) | `PATCH /api/v1/transcriptforge/jobs/{job_id}/segments/{chunk_id}` |
| `transcriptforge-audio-export-backend` | useTranscriptForgeAPI.ts | `GET /api/v1/transcriptforge/jobs/{job_id}/export/audio-bundle` |
| `transcriptforge-confidence-feedback` | useTranscriptForgeAPI.ts | `POST /api/v1/transcriptforge/jobs/{job_id}/confidence-feedback` |
| `condition-grading-backend-integration` | ConditionGradingWizard.tsx | `POST /api/v1/condition/grade` |
| `condition-grading-skip-prototype` | ConditionGradingWizard.tsx (skip link) | N/A — prototype only |
| `archiveforge-condition-grading-backend` | (existing) | `POST /api/v1/condition/grade` |

---

## Import Path Convention

- All new imports use relative paths from hook/schema location
- Example: `import { TRANSCRIPTFORGE_PHASE } from '../../hooks/useUIPhase'`
- No `~` alias used (not confirmed in tsconfig.json for this path pattern)
- `useUIPhase.ts` exports verified to match expected import locations

---

## Error Logging Prefix Standard

All new warnings/errors use `[Module] [Component]` prefix:

- `[TranscriptForge] [ProofreadingProvider] localStorage parse failed — using defaults`
- `[TranscriptForge] [SpeakerIndex] localStorage quota exceeded — index will not persist`
- `[TranscriptForge] [SpeakerIndex] index full — evicted oldest entry for {fingerprintHash}`
- `[TranscriptForge] [ConfidenceCalibration] localStorage quota exceeded — calibration will not persist`
- `[TranscriptForge] [API] fetchJob not implemented — Phase 2 endpoint` (repeated for all 8 stubs)

---

## Audio Validator Limitation Note

**Included in `app/lib/transcriptforge/audio.ts`:**
> Client-side MIME type check is extension-based only.
> For M4A: assumes AAC codec — mark as low risk with playback warning.
> True codec detection requires backend file inspection — Phase 2 endpoint needed.

---

## Speaker Index Limit

- **Limit:** 100 entries enforced in `recordSpeakerUsage()`
- **Eviction:** Oldest entry by `lastSeenAt` when limit exceeded
- **Log:** `[TranscriptForge] [SpeakerIndex] index full — evicted oldest entry for {fingerprintHash}`
- **Fingerprint:** Non-sensitive, text-based — no raw audio, no biometric data

---

## Skip Link Visual Spec

- **Font:** text-xs
- **Color:** text-slate-500 / hover:text-slate-400
- **Hover:** underline
- **Position:** Below disabled Next button, left-aligned (w-full center)
- **Label:** "Skip for now (prototype only)"
- **data-max-task:** `condition-grading-skip-prototype`

---

## Backend Untouched Confirmation

- ✅ No edits to `backend/app/routers/transcriptforge.py`
- ✅ No edits to `backend/app/routers/archiveforge.py`
- ✅ No database schema changes
- ✅ No new backend endpoints
- ✅ `useTranscriptForgeAPI.ts` contains only TODO stubs with `console.warn`

---

## Stable Untouched Confirmation

- ✅ `~/empire-repo-stable` not modified
- ✅ `stable/production` branch not touched
- ✅ Port 3005 (stable) not restarted
- ✅ `studio.empirebox.store` Cloudflare route not modified

---

## Build Result

[To be filled after `npm run build` verification]

---

## Verification Results

### v10 Local Routes
| Route | Expected | Command |
|-------|----------|---------|
| `/transcriptforge` | 200 | `curl -I http://localhost:3010/transcriptforge` |
| `/transcriptforge-review` | 200 | `curl -I http://localhost:3010/transcriptforge-review` |
| `/archiveforge` | 200 | `curl -I http://localhost:3010/archiveforge` |
| `/archiveforge-life` | 200 | `curl -I http://localhost:3010/archiveforge-life` |

### v10 External Routes
| Route | Expected | Command |
|-------|----------|---------|
| `https://test-studio.empirebox.store/transcriptforge` | 200 | `curl -Ik` |
| `https://test-studio.empirebox.store/archiveforge` | 200 | `curl -Ik` |

### Stable Regression
| Route | Expected | Command |
|-------|----------|---------|
| `http://localhost:3005` | 200 | `curl -I` |
| `https://studio.empirebox.store` | 200 | `curl -Ik` |
| `https://luxe.empirebox.store` | 200 | `curl -Ik` |

---

## Phase 2 Priority Recommendation

### High Priority (next sprint)
1. **TranscriptForge edit persistence:** `PATCH /api/v1/transcriptforge/jobs/{job_id}/segments/{chunk_id}` — enables save of proofreading edits to backend
2. **ArchiveForge valuation endpoint:** `POST /api/v1/archiveforge/valuation/estimate` — replaces mock data with live valuation

### Medium Priority
3. **TranscriptForge speaker sync:** `POST /api/v1/transcriptforge/jobs/{job_id}/speaker-labels` — sync manual labels to backend
4. **ArchiveForge condition grading:** `POST /api/v1/archiveforge/condition/grade` — real grading algorithm
5. **TranscriptForge full-job audio:** `GET /api/v1/transcriptforge/jobs/{job_id}/audio` — unified audio playback

### Lower Priority
6. **TranscriptForge confidence feedback:** `POST /api/v1/transcriptforge/jobs/{job_id}/confidence-feedback` — model improvement data
7. **ArchiveForge bundle suggestions backend:** `POST /api/v1/archiveforge/bundle/suggest`
8. **ArchiveForge market trends API:** `GET /api/v1/archiveforge/market/trends`

---

## Phase 3 Cross-Module Spec (Documentation Only)

**Do NOT implement cross-module data pipe in Phase 1.5.**

### Conceptual Pipeline

```
ArchiveForge item
    → TranscriptForge notes/audio attachment if item has recorded description
    → Hermes memory context for related historical events

TranscriptForge transcript
    → ArchiveForge reference notes if transcript references specific items/issues
    → Drawing Studio treatment areas if measurements mentioned

Photo/reference analysis (via WorkroomForge / Vision analysis)
    → Quote/Drawing Studio handoff for formal treatment plan
    → MarketForge listing draft with extracted metadata

MAX/OpenClaw task markers
    → Backend integration backlog (Hermes memory note)
    → Task queue for human review before action

LIFE reference (ArchiveForge)
    → Drawing Studio reference image import
    → Quote builder fabric reference

Hermes memory note
    → Supporting context only, NOT source of truth for any module
    → Read-only reference for cross-module enrichment
```

### Integration Constraints
- No automatic data handoff without user confirmation
- Each module owns its data; cross-module references are pointers, not copies
- Phase 3 implementation requires backend API design for each cross-module path

---

## Promotion Rule

**No v10 Phase 1.5 feature may be promoted to stable, port 3005, or studio.empirebox.store without explicit founder approval.**

Features requiring founder approval for promotion:
- `useUIPhase.ts` — shared phase constants (verify no stable import conflicts)
- `transcriptforge_speaker_index` localStorage — ensure 100-entry limit acceptable
- `transcriptforge_confidence_calibration` localStorage — new storage key
- `ConditionGradingWizard` skip link — changes UX flow

---

## Commit

**Message:** `fix(v10): harden prototype workflows and local state`
**Branch:** `feature/v10.0-test-lane`
**Push:** `git push origin feature/v10.0-test-lane`

---

## Remaining Backlog

### TranscriptForge
- [ ] Backend edit persistence endpoint
- [ ] Full-job audio playback + export endpoint
- [ ] Automatic speaker diarization (requires Groq + diarization model)
- [ ] Word-level timestamps
- [ ] `POST /api/v1/transcriptforge/jobs/{job_id}/speaker-labels` sync endpoint
- [ ] `POST /api/v1/transcriptforge/jobs/{job_id}/confidence-feedback` endpoint
- [ ] Confidence calibration queue UI in Proofread tab

### ArchiveForge
- [ ] `POST /api/v1/archiveforge/valuation/estimate` — real valuation API
- [ ] `GET /api/v1/archiveforge/market/trends` — real market data
- [ ] `POST /api/v1/archiveforge/condition/grade` — real grading algorithm
- [ ] `POST /api/v1/archiveforge/bundle/suggest` — bundle intelligence backend
- [ ] `GET /api/v1/archiveforge/collection/comparables` — real comparable sales
- [ ] LIFE Google Books PDF legal download link verification
- [ ] `archiveforge_prototype_skipped_steps` localStorage (not needed yet — skip is ephemeral)

---

*Report generated: 2026-04-29*
*Phase 1.5 hardening — TranscriptForge + ArchiveForge v10*