# MAX Self-Heal Handoff — April 3, 2026

## What Was Wrong (37 chat exchanges)
1. MAX jumped to quoting when user asked for drawing (no conversation mode tracking)
2. PIN 7777 demanded on web_cc even though guardrails already had founder bypass
3. MAX claimed "I sent the PDF" without proof (no transport validation)
4. Drawings sent to email/Telegram instead of inline on web chat (wrong default)
5. MAX argued it can't show drawings inline — right after doing it (no capability registry)

## What Was Fixed

### New Infrastructure (6 files):
- **capability_registry.json**: 10 capabilities with channel scope and proof requirements
- **capability_loader.py**: generates system prompt from registry (not static claims)
- **transport_matrix.py**: defines default delivery per output type + channel
- **conversation_mode.py**: persistent mode tracking (design/quote/code/review/general)
- **founder_auth.py**: centralized founder detection (web_cc = always founder)
- **self_heal.py**: incident logging, canary tests, scope limits

### Modified Files:
- **system_prompt.py**: anti-hallucination rules, inline drawing default, capability injection
- **router.py**: /max/self-heal-status endpoint (10 capabilities, incident log)

## Self-Heal Scope
**Allowed**: backend/app/services/max/, vision/, empire-command-center/app/
**Blocked**: .env, auth.py, payments, stripe, main.py, migrations

## Founder Commands
- "MAX, show self-heal status" → returns capability registry + incident log
- Endpoint: GET /max/self-heal-status

## Test Commands
```bash
curl localhost:8000/max/self-heal-status | python3 -m json.tool
```
