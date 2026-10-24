# Max-e Night Lab RED — `<mm:think>` leak (2026-10-23)

**Edition:** Max-e (Juan)  
**Base:** `family/amp-live-20261014`  
**Do not merge into Studio / main.**

## Found

MiniMax still leaked English hidden reasoning into Juan's chat when tags were
nested (`<mm:think>…<think>…</think> leftover</mm:think>`), unclosed, or split
across stream chunks. One-pass `.*?` closed the outer open on the inner
`</think>`, then the orphan-close rule ate the visible prefix. The stream
filter exited thinking on the first close. Email drafts/sends skipped the
shared sanitizer.

## Changed

Single layer: `sanitize_output` → `strip_thinking` in `thinking.py`.

- Innermost-first complete-block peel (nested tags keep "Hola Juan").
- Stream filter holds namespaced / split tags and tracks nest depth.
- Orphan `</mm:think>` still drops the reasoning prefix (`secret plan</mm:think>Hola`).
- Email draft + `EmailService.send`, WhatsApp `send_session_text` / `send_reply`,
  and Telegram `_chat_with_max` all call `sanitize_output`. No real sends.

## Tests

```
PYTHONPATH=backend python -m pytest \
  tests/test_maxe_think_tag_variants.py \
  tests/test_mm_think_toolcall_leak.py \
  tests/test_minimax_thinking_strip.py -q
# 51 passed
```

Covers closed, unclosed, nested, split-across-chunks, and variants
(`mm:think`, `minimax:think`, fences, special tokens). WhatsApp / Telegram /
email mocked only.

## Chat-path proof

`POST /api/v1/max/chat` and `POST /api/v1/max/chat/stream` with the nested
payload → `Hola.` + `Claro, Juan. Aquí tienes lo que pediste.`  
No `secret plan`, no `developer says`, no `mm:think`.

Files: `reports/2026-10-23_maxe_think_tag_chat_path.{json,html,png}`
