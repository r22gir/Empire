# MiniMax `</mm:think>` + `[Tool call:]` leak — before / after (Max-e / Juan)

**Instance:** Max-e (Juan) · branch `family/amp-live-20261014`  
**Seen:** 2026-10-21 11:21 AM ET (tool markup) and 11:26 AM ET (reasoning leak)  
**Night Lab:** 2026-10-22 RED-1 / FP-1 + FP-8  
**Fix:** `thinking.py` drops namespaced + orphan `</mm:think>` and untagged internal-rule preambles. `parse_tool_blocks` executes literal `[Tool call: name]` and `strip_tool_blocks` never shows that markup. `Resúmeme el día` prelooks up agenda tools. Family tool failure is Spanish.

No live data. No real sends. No real contacts.

---

## Exact Night Lab strings

Offline probe (all three instances leaked):

```
secret plan</mm:think>Hola
```

Oct 21 11:26 AM ET assistant shape (internal rules + orphan close + Spanish):

```
The assistant reviewed the request. The developer says not ask tokens/secrets. Tools absent from current prompt. I should answer without exposing internal rules.
</mm:think>
Claro, Juan. Aquí tienes lo que pediste.
```

Oct 21 11:21 AM ET for **Resúmeme el día** (printed, tools did not run):

```
[Tool call: get_today_agenda] [Tool call: list_schedule] [Tool call: get_tasks]
```

## After

- `secret plan</mm:think>Hola` → `Hola`
- Oct 21 reasoning payload → `Claro, Juan. Aquí tienes lo que pediste.`
- `[Tool call: get_today_agenda] …` is executed, never shown
- `Resúmeme el día` runs `get_today_agenda`, `list_schedule`, `get_tasks`
- Agenda tool failure → `No pude consultar la agenda ahora. Inténtalo de nuevo en un momento.`

## Paths

| Path | Gate |
|---|---|
| Reply | `strip_thinking` + `_sanitize_internal_leakage_text` + `sanitize_output` |
| Stream | buffered `ThinkingStreamFilter` then the same sanitizer (chunks split on `</mm:think>`) |
| Tool markup | `parse_tool_blocks` / `strip_tool_blocks` |
| Agenda ask | `is_today_agenda_ask("Resúmeme el día")` + prelookup |
| Family fail | `_family_graceful_visible_reply` |

## Chat endpoints (the UI path)

`POST /api/v1/max/chat` and `POST /api/v1/max/chat/stream` — same doors `useChat.ts` hits.

## Test output (no live model, no real sends)

```
python3 -m pytest tests/test_mm_think_toolcall_leak.py \
  tests/test_minimax_thinking_strip.py \
  tests/test_today_agenda.py \
  tests/test_tool_block_parser_hotfix.py -q

65 passed, 9 warnings
```

## Real chat-path capture (same doors as Command Center)

`POST /api/v1/max/chat` with the Oct 21 `</mm:think>` payload:

```
Claro, Juan. Aquí tienes lo que pediste.
```

See `reports/2026-10-22_mm_think_chat_path.json`.

`POST /api/v1/max/chat/stream` decoded text:

```
Claro, Juan. Aquí tienes lo que pediste.
```

See `reports/2026-10-22_mm_think_stream_path.txt`.

`POST /api/v1/max/chat` for **Resúmeme el día** — tools executed
`get_today_agenda`, `list_schedule`, `get_tasks`; visible reply:

```
Hoy tienes: Sesión AMP a las 10am.
```

No `[Tool call:` text. See `reports/2026-10-22_mm_think_resumeme_chat.json`.
