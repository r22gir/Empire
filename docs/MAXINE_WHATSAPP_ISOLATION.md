# Maxine WhatsApp isolation findings (Phase 0, post-port)

**Audit + code already on this PR.** No merge, no deploy, no client sends.

Written after TASK C/D for Camilo’s edition. Complements the Phase 0 audit
([PR #96](https://github.com/r22gir/Empire/pull/96)) with what the Maxine
process actually gets on this branch.

## Edition git branch (searched, not assumed)

Every remote branch name on `r22gir/Empire` was listed. There is **no**
`feature/maxine-edition` (or any Maxine-only edition line).

| Candidate | Why it is not Maxine’s edition tree |
|-----------|-------------------------------------|
| `feature/amp-edition` | Shared family codebase. Dell Maxine unit (`/home/rg/empire-maxine`) runs this tree with `EMPIRE_EDITION=maxine`. |
| `cursor/amp-whatsapp-family-8454` (PR #98) | Max-e WhatsApp port. Same engine; Amp-e copy. |
| `cursor/family-whatsapp-isolation-audit-8454` (PR #96) | Docs-only audit. |
| `deploy/pr82-84-85` | Workroom WhatsApp channel. Must not merge. |

**This PR** (`cursor/maxine-whatsapp-family-8454`) is cut from `feature/amp-edition`
and stacked on #98 **because that is the only edition tree Maxine has**.
Saying otherwise would invent a branch.

## Isolation matrix (Maxine vs Workroom vs Max-e)

| Store | Maxine | Separate from Rafael? | Separate from Max-e? |
|-------|--------|------------------------|----------------------|
| Process | uvicorn `127.0.0.1:8012` | Yes (Workroom 8000) | Yes (8011) |
| UI | `maxine.empirebox.store` :3012 | Yes | Yes (`amp.empirebox.store`) |
| Data | `/data/maxine` | Yes if env is set | Yes (`/data/amp`) |
| Env file | `/home/rg/empire-maxine.env` | Yes | Yes |
| WhatsApp DB / chat log / media / jobs | `$EMPIRE_DATA_DIR/whatsapp*`, `/jobs` | Yes | Yes |
| Allowlist | `WHATSAPP_OWNER_NUMBERS` in Maxine env only | Yes if Rafael does not copy Workroom numbers | Yes if Camilo’s number only |
| Meta | Camilo’s **own new** app + Meta test number | Must not share Rafael’s token | Must not share Juan Diego’s |
| Labels | `/data/maxine/whatsapp/labels.json` | Yes | Yes |
| Usage / model | 20%, MiniMax M3 | Yes | Same cap, own `usage.db` |
| Draft / send | `documents_auto_send: false` | No client sends | Same |

Webhook path name is shared (`/api/v1/whatsapp/webhook`). Host and port differ.
Rafael must confirm cloudflared `https://maxine.empirebox.store/api/v1/*` → `127.0.0.1:8012`.

## Can Maxine see Rafael’s chats, jobs, clients, quotes?

**No**, when `EMPIRE_EDITION=maxine`, `EMPIRE_DATA_DIR` is a tmp/test root or
`/data/maxine`, and this PR’s gates are loaded:

- Inbox / legacy chats / uploads resolve under the Maxine data root, not
  `~/empire-repo/backend/data/*`.
- Repo `client_aliases.json` and `business.json` are founder-only
  (`is_founder_edition()`). `dahlia` / Nehal do not resolve.
- Docs hub (`_hub_base`, `find_docs`) is disabled.
- File-finder roots stay inside the Maxine data dir.
- Drawings / Craft / Luxe stay disabled (Willard / McLean are not family defaults).
- Fail-closed: unset/`workroom` edition + data-dir basename `maxine` is still Maxine.

Mocks in `backend/tests/test_maxine_whatsapp_isolation.py` assert this. They never
write `/data/maxine` or call live Graph.

## Spanish guide

Route (same Next app, Maxine host): `/amp/whatsapp` and `/ayuda/whatsapp`.
Copy is Camilo / inmuebles / construcción / desarrollo. Checkpoints: own Meta
account (not Rafael, not Workroom, not Max-e), Meta test number, webhook
`https://maxine.empirebox.store/api/v1/whatsapp/webhook`, secrets only via the
secure request into `/home/rg/empire-maxine.env`.

## Confidentiality

Construction and sales wording only. No legal-entity file is added here.
Owner digits are not committed; they belong only in the Dell env file.

## Hand-work

See the PR body. Nothing here is a deploy or a send.
