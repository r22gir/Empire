# WhatsApp guide: explicit intent only

**Instance:** Max-e (amp) + Maxine on this tree  
**Base:** `family/amp-live-20261014` @ a3250d4b  
**Branch:** `cursor/whatsapp-guide-intent-ae32`  
**PR:** https://github.com/r22gir/Empire/pull/224  
**Live send:** no · **Keys in chat:** no

## Root cause

`maybe_resume_whatsapp_guide` treated any first turn / empty history / greeting
as WhatsApp resume when `facts.json` had `pendiente_*whatsapp` and the channel
was disabled. Post-deploy isolation chats send `"history": []`, so every
question got the Meta onboarding script.

## Tests

```
python -m pytest backend/tests/test_whatsapp_guide_intent.py \
  backend/tests/test_maxe_whatsapp_resume.py \
  backend/tests/test_maxe_guides.py -q
```

44 passed.

## Real chat (local backend)

Pending WhatsApp fact, channel disabled, empty history.
`POST /api/v1/max/chat` via TestClient and via uvicorn on 127.0.0.1:18011 (amp)
and :18012 (maxine). Edition env only inside those processes.

### Before (amp)

| Q | model | A |
|---|---|---|
| Qué es el Workroom | whatsapp-setup-guide | Vamos a crear TU cuenta de Meta y TU número de WhatsApp Business... |
| Quién es Rafael Giraldo | whatsapp-setup-guide | Vamos a crear TU cuenta de Meta y TU número de WhatsApp Business... |
| cómo activo WhatsApp | whatsapp-setup-guide | Vamos a crear TU cuenta de Meta y TU número de WhatsApp Business... |

### Before (maxine)

Maxine live branch has no first-turn resume. On this tree before the gate:

| Q | model | A |
|---|---|---|
| Qué es el Workroom | empire-module-knowledge | No conozco el Workroom. Esta instancia no es ese taller y no tiene sus datos. |
| Quién es Rafael Giraldo | usage-cap | token_plan/remains unread (no MiniMax meter in this env) — not the WhatsApp script |
| cómo activo WhatsApp | usage-cap | same — guide did not fire |

### After (amp, uvicorn :18011)

| Q | model | A |
|---|---|---|
| Qué es el Workroom | empire-module-knowledge | No conozco el Workroom. Esta instancia no es ese taller y no tiene sus datos. |
| Quién es Rafael Giraldo | usage-cap | token_plan/remains unread — **not** the WhatsApp script |
| cómo activo WhatsApp | whatsapp-setup-guide | Vamos a crear TU cuenta de Meta... Pantalla segura: /amp/whatsapp. |

### After (maxine, uvicorn :18012)

| Q | model | A |
|---|---|---|
| Qué es el Workroom | empire-module-knowledge | No conozco el Workroom. Esta instancia no es ese taller y no tiene sus datos. |
| Quién es Rafael Giraldo | usage-cap | token_plan/remains unread — **not** the WhatsApp script |
| cómo activo WhatsApp | whatsapp-setup-guide | Vamos a crear TU cuenta de Meta... Pantalla segura: /ayuda/whatsapp. |

Rafael isolation would normally go to the model. This environment has no
family token-plan remainder, so usage-cap answers first. The defect was the
WhatsApp script; that no longer appears on those prompts.
