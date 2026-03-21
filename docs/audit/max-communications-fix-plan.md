# MAX Communications Fix Plan
**Date**: 2026-03-21
**Based on**: max-communications-diagnosis.md

---

## Phase 1: Critical STT Fix (5 min)

**File**: `empire-command-center/app/components/screens/ChatScreen.tsx`

**Change**: Line 176 — `if (data.success && data.text)` → `if (data.text)`

Backend returns `{text, language, filename}` — no `success` field. This one-line fix restores voice input.

---

## Phase 2: Full Voice Mode (30 min)

### 2a. Voice Mode Toggle
- Add `voiceMode` state to ChatScreen
- Toggle button next to mic button (headphones icon)
- When enabled: auto-play TTS on every new AI response

### 2b. Auto-Play TTS
- In useChat.ts or ChatScreen: detect new assistant message completion
- If voiceMode enabled, automatically call `playTTS(message.content)`
- Strip markdown/tool blocks before sending to TTS
- Add audio queue to prevent overlapping playback

### 2c. Push-to-Talk
- Spacebar held = recording (when textarea not focused)
- Visual indicator: pulsing mic icon + "Listening..." label
- On release: stop recording → transcribe → auto-send if voiceMode
- Mobile: hold mic button for same behavior

### 2d. Continuous Voice Loop
- When voiceMode ON + TTS finishes playing → auto-start recording
- Creates hands-free conversation flow: speak → AI responds (voice) → auto-listen → speak again
- "Stop" button or Escape key to exit loop

---

## Phase 3: Voice Mode UI

### Visual States
1. **Off** (default): Text input + manual mic button
2. **Voice Mode**:
   - Large pulsing mic indicator when listening
   - Speaker animation when TTS playing
   - "Voice Mode" badge in header
   - Auto-send after transcription (no manual send needed)

### Controls
- Toggle: Click headphones icon or keyboard shortcut (V when textarea not focused)
- Interrupt: Click anywhere or press Escape to stop TTS + cancel recording
- Manual override: Can still type while in voice mode

---

## Phase 4: Backend Voice Resilience

### STT Fallback
- Primary: Groq Whisper (`whisper-large-v3-turbo`)
- Fallback: If Groq fails, try OpenAI Whisper API (if key available)
- Error response: Return `{text: "", error: "transcription_failed"}` instead of 500

### TTS Resilience
- Primary: xAI Grok TTS (Rex voice)
- Timeout: 10s max for TTS generation
- Fallback: Browser's built-in `speechSynthesis` API as last resort
- Cache: Don't re-generate TTS for same text within session

---

## Implementation Order

1. Fix STT bug (P0 — immediate)
2. Add voiceMode state + toggle UI
3. Wire auto-play TTS on message completion
4. Add push-to-talk (spacebar + button hold)
5. Add continuous voice loop
6. Add backend TTS/STT fallbacks
7. Test full flow: Web voice in → AI response → auto TTS → auto listen → repeat

---

## Files to Modify

| File | Changes |
|------|---------|
| `ChatScreen.tsx` | STT fix, voice mode toggle, push-to-talk UI, continuous loop |
| `useChat.ts` | Callback for message completion (voice auto-play trigger) |
| `stt_service.py` | Fallback provider, better error responses |
| `tts_service.py` | Timeout, caching |
