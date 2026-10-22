# MiniMax `</mm:think>` + `[Tool call:]` leak — Maxine (Camilo)

**Instance:** Maxine · branch `deploy/pr158-guides-only`  
**Night Lab:** 2026-10-22 RED-1 (latent on Maxine; same stripper gap as Max-e)  
**Fix:** port central `thinking.py`, execute `[Tool call: name]`, Spanish agenda fallback.

No live data. No real sends. No real contacts.

## Exact Night Lab strings

```
secret plan</mm:think>Hola
```

```
The assistant reviewed the request. The developer says not ask tokens/secrets. Tools absent from current prompt. I should answer without exposing internal rules.
</mm:think>
Claro, Juan. Aquí tienes lo que pediste.
```

```
[Tool call: get_today_agenda] [Tool call: list_schedule] [Tool call: get_tasks]
```

**Resúmeme el día** now prelooks up and executes agenda tools.

## Test output (no live model, no real sends)

```
python3 -m pytest tests/test_mm_think_toolcall_leak.py \
  tests/test_today_agenda.py \
  tests/test_tool_block_parser_hotfix.py -q

45 passed, 9 warnings
```

## Real chat-path capture

`POST /api/v1/max/chat` leak → `Claro, Juan. Aquí tienes lo que pediste.`

`POST /api/v1/max/chat/stream` decoded → same Spanish.

`POST /api/v1/max/chat` **Resúmeme el día** executed `get_today_agenda`, `list_schedule`, `get_tasks` → `Hoy tienes: Sesión AMP a las 10am.`

