# MiniMax CLI Integration — v10

**Branch:** `feature/v10.0-test-lane`
**Status:** ACTIVE

---

## Confirmed Working Capabilities

| Capability | Status | Access Path | Endpoint/Command |
|-----------|--------|-------------|-----------------|
| Text/Chat | ✅ available | OpenAI-compatible API | `https://api.minimax.io/v1/chat/completions` |
| HTML Artifacts | ✅ available | OpenAI-compatible API | Same as text |
| Image Generation | ✅ available | mmx CLI | `mmx image generate --prompt "..." --n <num>` |
| Vision/Image Description | ✅ available | mmx CLI | `mmx vision describe --image <path> --prompt "..."` |
| Web Search | ✅ available | mmx CLI | `mmx search query --q "..."` |
| TTS/Speech Synthesis | ✅ available | mmx CLI | `mmx speech synthesize --text "..." --voice <voice>` |
| STT/Transcription | ❌ unavailable | — | MiniMax STT not verified — existing provider remains active |
| Video Generation | ⚠️ quota_exceeded | mmx CLI | `mmx video generate` — weekly limit reached on current plan |
| Music Generation | ✅ available | mmx CLI | `mmx music generate --prompt "..." --lyrics-optimizer` |

---

## Routing Policy (v10)

### Text / Chat / Artifact Generation
- **Provider:** `MiniMaxTextClient` (OpenAI-compatible `/v1/chat/completions`)
- **Model:** MiniMax-M2.7
- **Image input:** BLOCKED — MiniMax Anthropic endpoint returns 404; use Gemini/OpenAI for vision

### Image Generation
- **Provider:** `MiniMaxImageGenerationClient` via mmx CLI (`mmx image generate`)
- **Fallback:** None configured (direct API returns 404 for this key)

### Vision / Image Understanding
- **Provider:** `MiniMaxVisionClient` via mmx CLI (`mmx vision describe`)
- **Fallback:** Gemini or OpenAI if mmx fails
- **Important:** Do NOT send images to MiniMax text endpoint — it does not support `type="image"`

### Web Search
- **Provider:** `MiniMaxSearchClient` via mmx CLI (`mmx search query`)
- **Scope:** Inside MAX tool mode only

### TTS
- **Provider:** `MiniMaxSpeechClient` via mmx CLI (`mmx speech synthesize`)
- **Fallback:** Existing TTS provider if mmx fails
- **Voice:** Default `english_expressive_narrator` (other verified voices: `english_radiant_girl`, `english_magnetic_voiced_man`, `english_upbeat_woman`, `english_trustworth_man`, `english_calmwoman`)

### STT
- **Provider:** Existing provider unchanged
- **Status:** MiniMax STT not verified; do not switch

### Video Generation
- **Provider:** `MiniMaxVideoClient` via mmx CLI (`mmx video generate`)
- **Status:** Weekly usage limit exceeded on Token Plan Hs_plus — resets 2026-05-18
- **Fallback:** None configured

### Music Generation
- **Provider:** `MiniMaxMusicClient` via mmx CLI (`mmx music generate --lyrics-optimizer`)
- **Note:** `--lyrics-optimizer` is used by default (auto-generates lyrics). Pure instrumental requires music-2.5+/2.6 plan

---

## Critical: Endpoint Routing

### What works for this key
```
POST https://api.minimax.io/v1/chat/completions     → 200 ✅ (text/chat/artifact)
POST https://api.minimax.io/v1/image_generation      → 404 ❌
POST https://api.minimax.io/v1/t2a_v2                → 404 ❌
POST https://api.minimax.io/anthropic/chat/completions → 404 ❌
mmx CLI (speech, vision, search, image)             → 200 ✅
mmx CLI (music with --lyrics-optimizer)             → 200 ✅
mmx CLI (video)                                     → 429/quota exceeded ⚠️
```

### What doesn't work for this key
- Direct API calls for TTS, image generation, speech (return 404/401)
- Anthropic-compatible endpoint (`https://api.minimax.io/anthropic/*`) — 404
- Video generation — weekly quota exhausted

### mmx CLI vs Direct API
The mmx CLI works because it uses its own key resolution from `~/.mmx/config.json` and routes internally. The direct API calls fail because `MINIMAX_BASE_URL=/v1` causes double-path URLs (`/v1/v1/...`).

---

## Feature Flags (v10)

```bash
MINIMAX_CLI_ENABLED=true              # Enable mmx CLI multimodal tools
MAX_ENABLE_MINIMAX_CLI_TOOLS=true     # Register tools in MAX registry
MAX_ENABLE_MINIMAX_IMAGE=true        # Image generation via mmx CLI
MAX_ENABLE_MINIMAX_VISION=true        # Vision via mmx CLI first
MAX_ENABLE_MINIMAX_WEB_SEARCH=true    # Web search via mmx CLI
MAX_ENABLE_MINIMAX_TTS=true           # TTS via mmx CLI
MAX_ENABLE_MINIMAX_STT=false          # STT NOT switched — keep existing provider
MAX_ENABLE_MINIMAX_VIDEO=false        # Video disabled — quota exhausted
MAX_ENABLE_MINIMAX_MUSIC=false        # Music NOT yet enabled by default
```

---

## MAX Tool Registry (v10)

Registered tools (when `MAX_ENABLE_MINIMAX_CLI_TOOLS=true`):

| Tool Name | Function | Access Path |
|-----------|----------|-------------|
| `minimax_image_generate` | Image generation via mmx CLI | `minimax_cli` |
| `minimax_vision_describe` | Image understanding via mmx CLI | `minimax_cli` |
| `minimax_web_search` | Web search via mmx CLI | `minimax_cli` |
| `minimax_tts_synthesize` | TTS via mmx CLI | `minimax_cli` |

---

## Security Controls

- No `shell=True` in subprocess calls
- Strict command allowlist (only mmx with specific subcommands)
- Timeout handling on all CLI calls (15-300s configurable)
- Secrets never exposed in logs (redacted via regex)
- Output files go to `backend/data/minimax-output/` (gitignored)
- `env={}` passed to subprocess to prevent mmx from inheriting `MINIMAX_BASE_URL=/v1`
  - Without this, mmx constructs URLs like `/v1/v1/t2a_v2` → 404

---

## Smoke Test Commands

```bash
# Backend health
curl -s http://localhost:8010/max/health

# MiniMax capability status
curl -s http://localhost:8010/api/v1/minimax/status | python3 -m json.tool

# Direct mmx CLI tests
mmx speech synthesize --text "test" --voice "English_expressive_narrator" --output json
mmx vision describe --image /tmp/test.png --prompt "what" --output json
mmx search query --q "test" --output json
mmx image generate --prompt "red square" --n 1 --output json
mmx music generate --prompt "calm chime" --lyrics-optimizer --output json
```

---

## Files Changed

- `backend/app/services/max/minimax_adapter.py` — split clients + `_cli_env()` fix + music lyrics-optimizer
- `backend/app/services/max/ai_router.py` — image blocking + Anthropic comment
- `backend/app/routers/max/router.py` — capability router + minimax_cli_tools in status
- `backend/app/routers/minimax.py` — capability router (existing)
- `backend/.env.example` — feature flags added
- `backend/app/services/max/tool_executor.py` — tool registry entries + handlers + params nesting fix
- `docs/v10/MINIMAX_CLI_INTEGRATION.md` — this file

---

## Known Limitations

1. **Video:** Weekly quota exhausted on Token Plan Hs_plus — resets 2026-05-18
2. **STT:** Not available through MiniMax — existing provider remains active
3. **Anthropic endpoint:** Returns 404 for this key — not usable
4. **Direct API image/TTS:** Returns 404 — only mmx CLI works for multimodal
5. **Image input in chat:** MiniMax text endpoint does NOT support `type="image"` — blocked with ValueError
6. **Music instrumental:** Requires music-2.5+/2.6 plan; `--lyrics-optimizer` used as fallback

---

## Workflow Routing Summary

v10 MAX uses MiniMax for:
- **Text/Chat:** MiniMax `/v1/chat/completions` (MiniMax-M2.7)
- **HTML Artifacts:** MiniMax via text endpoint
- **Image Generation:** `minimax_image_generate` → mmx CLI → `image_*.jpg`
- **Vision:** `minimax_vision_describe` → mmx CLI → text description
- **Web Search:** `minimax_web_search` → mmx CLI → 10 results
- **TTS:** `minimax_tts_synthesize` → mmx CLI → `speech_*.mp3`
- **Video:** Disabled — quota exhausted
- **Music:** Available via `MiniMaxMusicClient` with `--lyrics-optimizer`

v10 MAX does NOT use MiniMax for:
- **STT:** Existing provider (not MiniMax)
- **Ollama:** Disabled and not required
- **xAI Grok:** Disabled (credits unavailable)