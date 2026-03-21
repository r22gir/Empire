# MAX Communications Diagnosis Report
**Date**: 2026-03-21
**Scope**: All MAX communication paths — Web, Telegram, Code Mode, Cross-channel, Voice

---

## 1. Web MAX Chat (Command Center — port 3005)

### Architecture
- **Frontend**: `ChatScreen.tsx` → `useChat.ts` hook → SSE streaming
- **Backend**: `POST /api/v1/max/chat/stream` → security checks → system prompt build → ai_router → SSE events
- **AI Provider Chain**: Grok → Claude → Groq → OpenClaw → Ollama
- **Tool Loop**: Max 3 rounds of tool execution per message
- **Conversation Storage**: JSON files in `backend/data/chats/{user_id}/`

### Status: MOSTLY WORKING
- SSE streaming works correctly
- Tool execution + results display works
- Multi-turn conversation tracking works
- Token tracking works

### Issues Found
1. **CRITICAL — STT silently fails**: `ChatScreen.tsx:176` checks `data.success` but backend `/api/transcribe` returns `{text, language, filename}` — no `success` field. Mic records audio, sends it, gets valid transcript back, then DROPS it.
2. **No auto-play TTS**: Speaker button exists per-message but user must click each one manually. No option for auto-voice responses.
3. **No push-to-talk / continuous voice mode**: Single-click record only.
4. **Incomplete tool block recovery**: If stream cuts mid-tool-block, partial JSON is lost with no recovery.
5. **Context-pack only on first message**: Later brain updates not reflected mid-conversation.

---

## 2. Telegram MAX (@Empire_Max_Bot)

### Architecture
- **Protocol**: Long-polling (NOT webhooks) via python-telegram-bot
- **Bot startup**: `telegram_bot.py` — registers handlers, starts polling loop
- **Message flow**: User message → founder verify → same `ai_router` as Web → response → reply
- **Voice flow**: Voice message → voiceprint verify → Groq Whisper STT → chat → xAI TTS → voice reply

### Status: WORKING
- Text chat works through same AI router + system prompt
- Full tool access (same 38 tools as Web)
- Voice input → STT → chat → TTS → voice reply (full pipeline)
- Cross-channel context injection works
- Founder detection via chat_id

### Issues Found
1. **Single-worker requirement**: `--workers 4` spawns duplicate bot instances (duplicate polling). Must run single worker.
2. **No graceful shutdown**: Bot polling doesn't always clean up on restart.
3. **Channel format**: Telegram gets ultra-short format directive but sometimes still gets long responses.

---

## 3. Code Mode (Atlas / CodeForge)

### Architecture
- **Frontend**: Code Mode toggle in ChatScreen → `POST /max/code-task` → poll status
- **Backend**: `code_task_runner.py` → background async task → Atlas (Claude Opus 4.6)
- **Tool whitelist**: file_read, file_write, file_edit, file_append, git_ops, test_runner (6 tools)
- **Max iterations**: 15 (vs 3 for regular chat)
- **Storage**: In-memory dict (not persisted)

### Status: WORKING (underutilized)
- Full async execution pipeline functional
- Activity logging with live polling
- Multi-iteration tool chaining works
- Error handling with retry support

### Issues Found
1. **Tasks lost on restart**: In-memory storage only — no persistence.
2. **No SSE streaming**: Uses polling (2s interval) — less responsive than regular chat.
3. **System prompt doesn't advertise Code Mode**: Regular MAX doesn't know to suggest it.

---

## 4. Cross-Channel Context

### Architecture
- **Bridge method**: System prompt injection — last 4 messages from each channel (2-hour window)
- **Shared brain**: SQLite MemoryStore tagged by source channel
- **Chat storage**: Separate systems — `data/chats/founder/` (Web) vs `data/chats/telegram/` (Telegram)

### Status: WORKING
- System prompt includes recent cross-channel messages
- Memory learning from both channels feeds same store
- Conversation tracker maintains per-channel history

### Issues Found
1. **Two separate storage systems**: Web uses JSON files, Telegram uses its own tracker. No unified search.
2. **2-hour window**: Context injection only covers recent 2 hours. Older cross-channel context lost.
3. **No real-time sync**: If user chats on Telegram, Web chat doesn't update until next message triggers prompt rebuild.

---

## 5. Voice Support

### Infrastructure Built
| Component | Backend | Frontend | Status |
|-----------|---------|----------|--------|
| STT (Speech-to-Text) | `POST /api/transcribe` — Groq Whisper | Mic button + MediaRecorder | Backend OK, Frontend BROKEN (success check) |
| STT alt endpoint | `POST /api/v1/max/stt` | Not used | Available |
| TTS (Text-to-Speech) | `POST /api/v1/max/tts` — xAI Grok Rex | Per-message speaker button | Working (manual click only) |
| Telegram Voice In | python-telegram-bot voice handler | N/A | Working |
| Telegram Voice Out | xAI TTS → send voice message | N/A | Working |

### What's Missing for Full Voice
1. **Fix STT silent failure** (line 176 — remove `data.success` check)
2. **Auto-play TTS toggle** — auto-speak all AI responses when enabled
3. **Push-to-talk mode** — hold spacebar or button to record
4. **Voice mode indicator** — show when voice is active
5. **Continuous conversation** — auto-listen after TTS finishes for hands-free flow

---

## 6. Infrastructure Issues

### Concurrency Limit (CRITICAL)
- `--limit-concurrency 20` in uvicorn config is far too low
- Cloudflared tunnel holds 12+ persistent HTTP/2 connections
- Command Center dashboard polls 15+ endpoints simultaneously
- Result: Chat requests get **503 Service Unavailable** when dashboard is open
- **Fixed**: Increased to `--limit-concurrency 100` in systemd service

### Code Mode Path Bug
- Atlas (Claude Opus) doesn't know the actual home directory `/home/rg/`
- System prompt used generic `/absolute/path` examples
- Atlas guesses `/root/empire-repo/` which fails path validation
- **Fixed**: Injected actual `repo_root` path into Code Mode prompt

### Quality Checks Missing from Streaming Path
- Non-streaming `/chat` endpoint runs `verify_web_response()`, `quality_engine.validate()`, `accuracy_monitor`
- Streaming `/chat/stream` has **none of these** — and frontend exclusively uses streaming
- Impact: No hallucination detection, no quality validation on web chat

---

## Summary of Critical Fixes Needed

| Priority | Issue | Location | Fix |
|----------|-------|----------|-----|
| P0 | STT silently fails | ChatScreen.tsx:176 | Change `data.success && data.text` to `data.text` |
| P1 | No auto-play TTS | ChatScreen.tsx + useChat.ts | Add voice mode toggle, auto-call playTTS on new messages |
| P1 | No push-to-talk | ChatScreen.tsx | Add spacebar hold-to-record |
| P2 | No continuous voice | ChatScreen.tsx | Auto-listen after TTS playback ends |
| P3 | Code tasks lost on restart | code_task_runner.py | Add file persistence |
| P0 | Concurrency limit 503s | systemd/empire-backend.service | Increase to 100 (was 20) |
| P1 | Code Mode wrong paths | code_task_runner.py | Inject actual repo_root in prompt |
| P2 | No quality checks on streaming | max/router.py | Add grounding + quality to stream path |
| P3 | Cross-channel storage split | chats/ directory | Unify or add cross-search |
