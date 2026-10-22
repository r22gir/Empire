# MiniMax thinking leak — before / after (Max-e / Juan)

**Instance:** Max-e (Juan) · branch `family/amp-live-20261014`  
**Seen:** 2026-10-21 ~11:27 AM ET  
**Complaint:** «¿por qué en inglés?»  
**Fix:** central strip in `backend/app/services/max/thinking.py` before reply, saved history, or web_search / tool queries. Streaming uses `ThinkingStreamFilter` so split `<think>` tags cannot leak.

No live data. No real sends. Sample below is a reconstructed transcript of the leak shape (English hidden reasoning + Spanish user-facing reply).

---

## User

```
qué pasó hoy en Colombia
```

## Before (what Juan saw / what was saved / what was searched)

Visible reply **and** saved assistant turn (the English block also appeared a second time when `reasoning_content` was concatenated with tagged content):

```
<think>
The user asked "qué pasó hoy en Colombia" in Spanish. I should search in English for better results about current Colombian news and then summarize.
</think>

Hoy en Colombia hay varias noticias: te resumo lo principal en español, Juan.
```

`web_search` query built from that assistant text / tool field:

```
The user asked "qué pasó hoy en Colombia" in Spanish. I should search in English for better results about current Colombian news and then summarize.
```

That is why the search ran in English.

## After (strip, then show / save / search)

Visible reply and saved assistant turn (once):

```
Hoy en Colombia hay varias noticias: te resumo lo principal en español, Juan.
```

`web_search` query (from the Spanish user turn, thinking stripped from history and tool fields):

```
qué pasó hoy en Colombia
```

Reply stays Spanish for Juan. English self-talk never reaches the transcript, the JSON chat file, or DuckDuckGo / Brave.

---

## Test output (no live model, no real sends)

```
python3 -m pytest tests/test_minimax_thinking_strip.py \
  tests/test_max_whitespace_streaming.py \
  tests/test_search_context_carry_forward.py \
  tests/test_max_image_vision_routing.py::test_minimax_response_sanitizer_strips_think_tags \
  tests/test_family_chat_history.py::test_persist_exchange_uses_full_id_and_new_york_zone \
  tests/test_tool_block_parser_hotfix.py -q -k "not TestRouterParseErrorSynthetic"

48 passed, 2 deselected, 3 warnings
```

New file `tests/test_minimax_thinking_strip.py` covers reply, saved history (no double English block), search-query, streaming split tags, and Spanish keep.

## Paths covered

| Path | Gate |
|---|---|
| Reply | `visible_text_from_provider_payload` + `strip_thinking` in MiniMax chat / `sanitize_output` |
| Saved history | `persist_exchange` / `upsert_chat` strip assistant content; reasoning fields dropped |
| Search query | `build_search_query` + `parse_tool_blocks` + `_web_search` |
| Streaming | `ThinkingStreamFilter` (partial `<th` / `ink>` tags) |
