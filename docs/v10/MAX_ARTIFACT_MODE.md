# EmpireBox v10 — MAX Artifact Mode

## Overview

MAX Artifact Mode allows MAX to generate structured, reviewable artifacts alongside a visible text response. Artifacts are parsed server-side, validated, sanitized, streamed via SSE, rendered in a sandboxed browser viewer, and can be optionally persisted into the Hermes Knowledge Artifact Layer.

This is a v10-only feature (`feature/v10.0-test-lane`, port 8010).

---

## Artifact Types

| Type | Description |
|------|-------------|
| `plain_text` | Simple text block — no approval needed |
| `markdown_report` | Multi-section text/markdown report |
| `html_artifact` | Static HTML card/page — requires approval, scripts disabled |
| `react_component_proposal` | React/TSX component proposal — requires approval |

---

## Output Format

MAX emits artifacts as fenced JSON blocks in its text response:

```
MAX_VISIBLE_RESPONSE: [summary text]

MAX_ARTIFACT_JSON:
```json
{
  "id": "unique-id",
  "artifact_type": "html_artifact",
  "title": "Artifact Title",
  "description": "Short description",
  "content_format": "html",
  "content": "<!DOCTYPE html>...",
  "source": "max",
  "mode": "review_only"
}
```
```

MAX decides when to emit an artifact based on complexity and review utility (dashboards, reports, component proposals, etc.) — not on a fixed category whitelist.

---

## Backend Contract

### Artifact Parser (`artifact_parser.py`)

- Extracts `MAX_ARTIFACT_JSON:` and plain ````json` blocks via regex
- Validates via Pydantic `ArtifactPayload`
- Applies safety defaults per artifact type:
  - `html_artifact`: `scripts_allowed=false`, `external_network_allowed=false`, `sandboxed=true`, `sanitized=true`, `requires_approval=true`
- Backend sanitizes: strips `<script>`, event handlers, `javascript:` URLs, external href/src, `<link>`, `<iframe>`, `<form>`
- Invalid JSON → silently skipped, plain text fallback

### ChatResponse

```python
artifacts: Optional[List[ArtifactPayload]] = None
```

Populated via `parse_max_artifact_blocks()` after model call in non-streaming `/api/v1/max/chat`.

### Streaming SSE

Streamed via `/api/v1/max/chat/stream` — emits `{"type": "artifact", "artifact": {...}}` events before the `done` event.

### Safety Flags (html_artifact)

```python
safety: {
    "scripts_allowed": False,
    "external_network_allowed": False,
    "sandboxed": True,
    "sanitized": True,
}
requires_approval: True
```

---

## Frontend Contract

### Types (`lib/types.ts`)

```typescript
export type ArtifactType = 'plain_text' | 'markdown_report' | 'html_artifact' | 'react_component_proposal';
export interface MaxArtifact {
  id, artifact_type, title, description, content_format, content,
  source, mode, requires_approval, allowed_actions, safety, metadata
}
```

### Message Type

```typescript
interface Message { ..., artifacts?: MaxArtifact[] }
```

### Components

| Component | Purpose |
|-----------|---------|
| `ArtifactCard` | Inline card below chat bubble |
| `ArtifactViewer` | Full modal with Preview/Source/Actions tabs |
| `SafeHtmlPreview` | Sandboxed iframe renderer |
| `ArtifactSourcePanel` | Escaped source code view |
| `ArtifactActions` | Approve/Reject/Request Changes + Save to Hermes Memory |

### SafeHtmlPreview Sandboxing

```tsx
<iframe
  srcDoc={htmlDoc}
  sandbox=""  // NO allow-scripts, NO allow-same-origin, NO allow-forms
  title={artifact.title}
/>
```

**Rules enforced:**
- `sandbox=""` — no allow-scripts, no allow-same-origin, no allow-forms
- `<script>` tags stripped server-side and client-side
- Event handlers (`onclick`, `onerror`, etc.) stripped
- `javascript:` URLs stripped
- External `href`/`src` URLs stripped
- `<link>` tags stripped
- `<iframe>`, `<form>`, `<object>`, `<embed>` stripped

### Review State vs Persistence

- Approve/reject/request-changes state is still local UI state by default.
- "Save to Hermes Memory" now calls backend persistence (`/api/v1/hermes/artifacts/write`) and returns a durable artifact id.
- Local review state and backend persisted status are separate until full workflow merge is implemented.

### Copy/Export

- **Copy Source**: `navigator.clipboard.writeText(artifact.content)`
- **Export HTML**: Creates a `Blob` download of the sanitized artifact content as a standalone HTML file

---

## Sanitizer Coverage

| Threat | Backend | Frontend |
|--------|---------|----------|
| `<script>` tags | ✅ stripped | ✅ stripped |
| Event handlers (`onclick`, etc.) | ✅ stripped | ✅ stripped |
| `javascript:` URLs | ✅ stripped | ✅ stripped |
| External href/src | ✅ stripped | ✅ stripped |
| `<link>` tags | ✅ stripped | ✅ stripped |
| `<iframe>` | ✅ stripped | ✅ stripped |
| `<form>` | ✅ stripped | ✅ stripped |
| `<meta http-equiv="refresh">` | N/A (not present) | N/A |

---

## System Prompt Instructions

The MAX system prompt instructs:

- Emit artifacts for complex structured outputs
- Use `MAX_ARTIFACT_JSON:` fence blocks
- `html_artifact` and `react_component_proposal` always `requires_approval=true`
- Static HTML only — no arbitrary JavaScript
- No external scripts/CSS, no auto-submit forms
- If artifact JSON is invalid → display `MAX_VISIBLE_RESPONSE` as plain text

---

## Known Limitations

- **Non-streaming**: `ChatResponse.artifacts` only populated in non-streaming mode. Streaming route emits artifacts via SSE events but the final HTTP response body does not contain an `artifacts` field.
- **Model tool use**: When MAX calls a tool instead of responding inline, artifact blocks may not be emitted. Instruct MAX to "reply only with text, do not use any tools" if artifacts are needed.
- **\<link> sanitizer gap**: Previously, external stylesheet `<link>` tags were not stripped. Fixed in backend `artifact_parser.py` and frontend `artifacts.ts`.
- **Split review model**: Approval button state remains local UI state; durable approval lifecycle lives in Hermes artifact metadata APIs and is not yet automatically synchronized with UI state.

---

## Last Updated

2026-05-13
