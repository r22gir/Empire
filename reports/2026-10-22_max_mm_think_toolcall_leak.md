# MiniMax `</mm:think>` + `[Tool call:]` leak — before / after (Max / Rafael)

**Instance:** Max (Rafael) · branch `dell/studio-batch-1014`  
**Night Lab:** 2026-10-22 RED-1 (latent on Max; same stripper gap as Max-e)  
**Fix:** port `thinking.py`, execute `[Tool call: name]`, treat **Resúmeme el día** as an agenda ask.

No live data. No real sends. No real contacts. Does not merge amp or maxine.

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
- English user-facing answers are kept (Max / workroom)

## Paths

| Path | Gate |
|---|---|
| Reply | `strip_thinking` + `_sanitize_internal_leakage_text` + `sanitize_output` |
| Stream | buffered `ThinkingStreamFilter` then the same sanitizer (chunks split on `</mm:think>`) |
| Tool markup | `parse_tool_blocks` / `strip_tool_blocks` |
| Agenda ask | `answer_policy.is_today_agenda_ask("Resúmeme el día")` + prelookup |

## Chat endpoints (the UI path)

`POST /api/v1/max/chat` and `POST /api/v1/max/chat/stream` — same doors Command Center hits.

## Test output (no live model, no real sends)

```
python3 -m pytest tests/test_mm_think_toolcall_leak.py \
  tests/test_today_agenda.py \
  tests/test_tool_block_parser_hotfix.py -q

45 passed, 29 warnings in 2.46s
```

Live-data firewall: 3 connect(s) to live services blocked (not failures):
`127.0.0.1:8000`, `127.0.0.1:3005`, `127.0.0.1:7878`.

## Real chat-path capture (same doors as Command Center)

`POST /api/v1/max/chat` with the Oct 21 `</mm:think>` payload:

```
Claro, Juan. Aquí tienes lo que pediste.
```

See `reports/2026-10-22_max_mm_think_chat_path.json`.

`POST /api/v1/max/chat/stream` decoded text:

```
Claro, Juan. Aquí tienes lo que pediste.
```

See `reports/2026-10-22_max_mm_think_stream_path.txt`.

`POST /api/v1/max/chat` for **Resúmeme el día** — tools executed
`get_today_agenda`, `list_schedule`, `get_tasks`; visible reply:

```
Hoy tienes: Sesión AMP a las 10am.
```

No `[Tool call:` text. See `reports/2026-10-22_max_mm_think_resumeme_chat.json`.
