# H81 Phase 2B · Task C · PIN path map (no implementation)

**Date:** 2026-09-01
**Repo:** `~/empire-repo-main` · branch `feature/drawing-standard` · HEAD `dd72de8`
**Constraint (binding):** the PIN value must not travel in the chat message body. The H50 enforcer catches MAX asking for a PIN, and a path that puts the PIN in `request.message` lands it in the conversation store, the SSE stream, and the journal. The three options below all keep the value out of `request.message`.

**Pre-existing infrastructure that any option can build on:**

- **`/api/v1/auth/founder-token`** at `backend/app/routers/auth.py:175-209` already issues a JWT after `FOUNDER_PIN` verification. The PIN travels in the body of THIS POST only — once, at session start. JWT lives in the client, not in chat.
- **`obtainFounderToken(pin)`** at `empire-command-center/app/lib/api.ts:66-74` calls that endpoint.
- **`relistFetch` with `Authorization: Bearer <token>`** at `empire-command-center/app/lib/api.ts:53-64` is the established Bearer-header pattern. Used today by `RelistAppPage.tsx:1152,1159,1169,1179`.
- **`create_access_token` / `create_refresh_token`** at `auth.py` (imported into the route) issue HS256 JWTs against a backend secret.
- **`access_controller.create_pending_session`** at `backend/app/services/max/access_control.py:161-176` and **`authorize_pin_session`** at `:264-276` exist. The dispatch asks whether these are usable — see C3.

---

## C1 · Portal-side field (Bearer token in Authorization header)

**Shape:** Portal obtains a JWT once via `/auth/founder-token`, stores it in localStorage (parallel to `RELIST_TOKEN_KEY` pattern), threads it as `Authorization: Bearer <token>` into the `/max/chat` and `/max/chat/stream` fetches. The chat handler reads the header, verifies the JWT, and on success populates `access_context["pin"]` from `os.getenv("FOUNDER_PIN", "")` so the existing dangerous-tools gate accepts it.

### What changes

**Frontend — `empire-command-center/app/lib/api.ts` and `app/hooks/useChat.ts`:**

- `api.ts:66-74` already has `obtainFounderToken(pin)`. No change needed there.
- New helper `getFounderToken()` / `setFounderToken(token)` parallel to `getRelistToken()` / `setRelistToken()` at `api.ts:41-51` (different localStorage key).
- `useChat.ts:124-138` builds the body and posts to `/max/chat/stream`. Add `headers: { Authorization: \`Bearer \${token}\` }` when a token is present; thread through a parameter or read from localStorage at fetch time.
- `ChatScreen.tsx`: a "Sign in" affordance — a small modal/button that calls `obtainFounderToken(pin)`, stores the token, and re-fetches. UX matches the existing `/auth/founder-token` flow used by RelistAppPage (`RelistAppPage.tsx:1159`).

**Frontend — `empire-command-center/app/hooks/useChat.ts`:** signature of `sendMessage` doesn't need to change. Token reading happens inside the fetch.

**Backend — `backend/app/routers/max/router.py`:**

- `chat_with_max` (line 2162) and `chat_stream` (line 3308) gain a single helper, e.g. `_verified_founder_bearer(request: Request) -> Optional[dict]`, that:
  - Reads `request.headers.get("Authorization")`.
  - Strips `Bearer ` prefix.
  - Calls `decode_access_token(token)` (already exists in `auth.py`).
  - Returns `{"user_id": ..., "email": ...}` on success, `None` otherwise.
- For the founder path (after `is_founder_message(msg_ctx)` already returned True via the canonical channel), if the bearer verifies, additionally set `access_context["pin"] = os.getenv("FOUNDER_PIN", "")` so the dangerous-tools gate (`tool_executor.py:523`) reads a matching PIN. The PIN itself never leaves the env; the JWT just attests "this caller has proven FOUNDER_PIN".
- For the stream endpoint specifically, this would close the H81 H81 body-channel vector too: a non-founder reaching `/chat/stream` with body `channel="web_cc"` still gets `founder=True` from the predicate (Task 2B A confirmed the stream endpoint remains body-driven for privilege), but without a valid Bearer token the access_context won't have a PIN and the dangerous-tools gate refuses uniformly.

**Backend — `tool_executor.py:512-535`:** no change. The dangerous-tools PIN gate already accepts any caller whose `access_context["pin"]` matches `FOUNDER_PIN`. C1 just feeds that path from a verified JWT instead of from message-body extraction.

### What breaks

- **H50 compliance:** PIN travels in body of `/auth/founder-token` POST ONCE at session start, then travels only as a Bearer header. Never in chat message body, never in conversation store, never in SSE stream. The H50 enforcer (whatever its current state) is undisturbed because MAX never asks for the PIN in chat — the portal prompts for it before the chat session begins, via a dedicated endpoint with no enforcer attached.
- **Token lifecycle:** no refresh path exists today; `auth.py:158-162` has the refresh-token machinery but no client-side plumb. JWT expiry would force re-PIN. For a single-founder system this is acceptable; documented limitation.
- **Portal UX:** a Sign-in modal must be added to `ChatScreen.tsx`. Without it, the existing `/chat` calls work for safe tools but dangerous tools refuse with the same "Please provide your founder PIN" message as today. UX regression for dangerous tools only; safe tools unchanged.
- **No CSRF risk:** Bearer header in `Authorization` is not auto-attached by browsers (unlike cookies). CSRF applies to cookie auth; Bearer is bearer-of-the-token. Safe.

### Phase 3 interaction

C1 is **the prototype for Phase 3's identity credential.** Whatever Phase 3 specifies — header token, mTLS, hardware key, session cookie — the frontend plumbing (sign-in modal → store token → send on each request) and the backend plumbing (read header → verify → mark identity verified) are the same shape. C1 may be replaced wholesale, or may become the foundation that Phase 3 strengthens. Either way it is not wasted work.

---

## C2 · Pre-authorized session (grant table)

**Shape:** Founder hits `/api/v1/auth/dangerous-tools-grant` (new endpoint) once with FOUNDER_PIN; backend creates a row in a new `dangerous_tool_grants(user_id, expires_at)` table with a TTL; returns a `grant_id`. Chat handler reads `X-Dangerous-Tools-Grant: <grant_id>` header, looks up the row, checks TTL. If valid, `access_context["pin"]` is populated from env; dangerous tools run.

### What changes

- **New schema:** `dangerous_tool_grants(id, user_id, expires_at, scope)`. Migration via the existing `init_db()` or `get_db()` pattern.
- **New endpoint** at `auth.py` or a new router: `POST /api/v1/auth/dangerous-tools-grant` with `FounderPinRequest` body (PIN in body, like `/founder-token`). Validates FOUNDER_PIN, inserts grant row, returns `{"grant_id": "...", "expires_at": "..."}`.
- **Chat handler** at `router.py:2162` and `:3308` gains a helper that reads `X-Dangerous-Tools-Grant` header, queries `dangerous_tool_grants` for `id=? AND expires_at > now()`, deletes expired rows lazily or via a sweeper.
- **Dangerous-tools gate** at `tool_executor.py:512-535`: unchanged structurally — `access_context["pin"]` is populated by the chat handler when the grant is valid; the gate then matches against FOUNDER_PIN as today.

### What breaks

- **H50 compliance:** same as C1 — PIN only in `/auth/dangerous-tools-grant` POST body, once.
- **New schema + table sweeper:** DB maintenance; small but new.
- **Two-factor model:** identity (who is calling) + grant (is this dangerous-tools call authorized). The grant sits between identity and tool call. If identity is solid, the grant is redundant; if grants are short, the surface area is bounded.
- **Phase 3 interaction:** if Phase 3 introduces real identity per-request, the grant becomes redundant — every request is already identity-verified. The grant table would still work but adds nothing.

### Is `create_pending_session` usable here?

**No, different shape.** `create_pending_session` (`access_control.py:161-176`) ties to a **specific tool call**: it persists `tool_name`, `tool_params`, `desk`, and TTL of 60s (confirm) or 120s (PIN). A pre-authorized session is **scope-wide** ("I authorize all dangerous tools for the next 10 minutes"), not per-call. Reusing `create_pending_session` would either:
- Pass `tool_name="*"` and `tool_params={}` — abusing the type, breaking consumers of the pending session.
- Create one pending session per dangerous-tool call the founder expects to make — defeats the "authorize once" goal.

A separate grants table is the right shape if C2 is chosen.

---

## C3 · Out-of-band confirm (re-use `access_controller` / `/access/confirm` + `/access/pin`)

**Shape:** Founder's chat call to a dangerous tool triggers the access_controller permission flow (instead of skipping it). Access controller returns `__ACCESS_PENDING__pin__{session_id}__{summary}` — exactly as it does today for non-founder callers at level 3. Chat response carries the `session_id`. Portal surfaces a "Confirm" dialog; user POSTs `/api/v1/access/pin` with the `session_id` and PIN. Backend verifies, re-runs the tool.

### What changes

**Backend — `router.py` chat handlers:** the `if founder:` skip of `access_controller` must be conditional on tool level. Today `tool_executor.py:465-495` skips the entire access_controller block for any founder call. The change:

- For founder calls where `TOOL_LEVELS[tool_name] == 3` (dangerous): do NOT skip access_controller. Let it emit `__ACCESS_PENDING__pin__` for level-3 tools.
- For founder calls where level ≤ 2: keep the skip (level 1 = auto, level 2 = confirm — both already behave correctly for founder; level 0 = founder-only auto).

**Backend — `tool_executor.py:465-535`:** the founder branch (`if founder:`) currently sets `tool_call["_founder"] = True` and skips access_controller AND skips the dangerous-tools PIN gate. Post-Task-1, the dangerous-tools PIN gate runs anyway. C3 needs a third adjustment: for level-3 tools, founder should NOT bypass the access_controller's "pin" action — only bypass the permission flow that doesn't end in pin (deny/locked/confirm). Practically: pass founder into `access_controller.check_permission` and trust its return for level 3 only.

**Backend — `/access/pin` at `router.py:5009-5018`:** currently calls `execute_tool({...}, desk=...)` with no `founder` or `access_context`. So when the tool is `shell_execute`, the dangerous-tools PIN gate fires and refuses. Fix: pass `access_context={"pin": <the verified pin>}` AND `founder=True` (or just the access_context). The pin the user just verified IS the FOUNDER_APPROVAL_PIN or the per-user pin_hash — neither matches FOUNDER_PIN. So /access/pin's verify_pin checks against `access_users.pin_hash`, not against `FOUNDER_PIN`. After C3 fix, /access/pin would need to ALSO know to populate `access_context["pin"]` to `FOUNDER_PIN` when the verified user is the founder. That last step is where C3 implicitly relies on identity (the verified user is founder) — which is the Phase 3 problem.

### What breaks

- **H50 compliance:** same as C1/C2 — PIN only in `/access/pin` POST body, never in chat.
- **UX regression for ALL founder tools:** today the founder's chat returns immediately for safe tools. With C3, every level-3 tool call requires an out-of-band confirm via portal. UX cost is a per-dangerous-action click, not a one-time sign-in.
- **`access_controller` per-user PIN vs `FOUNDER_PIN`:** these are three different values today:
  - `FOUNDER_PIN` (env var, plain text) — used by `tool_executor.py:88` dangerous-tools gate
  - `FOUNDER_APPROVAL_PIN` (env var, plain text) — used by `verify_founder_approval` at `access_control.py:37`
  - `access_users.pin_hash` (per-user, bcrypt/sha256) — verified by `verify_pin` at `access_control.py:221`
  `/access/pin` verifies the third value, but the dangerous-tools gate matches the first. They are not interchangeable. To make C3 work end-to-end, either the founder's `pin_hash` must equal `FOUNDER_PIN` (one-time setup, undocumented), OR /access/pin must be extended to also verify against `FOUNDER_PIN` AND `FOUNDER_APPROVAL_PIN`. The latter is the natural path but adds yet another branch to the existing pin-handling surface.

### Is `create_pending_session` usable here?

**Yes — this is the exact machinery C3 re-uses.** `create_pending_session` already does:
- Persists `tool_name`, `tool_params`, `desk`, `user_id`, `channel`, `chat_id`, `level`, `status='pending'`, `expires_at` (60s for level 2 confirm, 120s for level 3 PIN)
- Returns `session_id`
- `confirm_session(session_id)` transitions to `confirmed` and returns the persisted payload for re-execution

`/access/confirm` (`router.py:4997-5006`) and `/access/pin` (`router.py:5009-5018`) already wire this up for non-founder. C3 is "let the founder take the same path." The machinery fits.

The hole is the FOUNDER_PIN mismatch above (per-user `pin_hash` ≠ `FOUNDER_PIN`), and the gate re-fire on re-execution (no `access_context["pin"]` passed by `/access/pin`). Both are fixable; neither is a structural obstacle.

### Phase 3 interaction

C3 survives Phase 3 only if Phase 3's identity check does NOT eliminate the need for an out-of-band confirm. If Phase 3 says "founder's identity is established per-request, dangerous tools run if identity verified," C3 is redundant — there's no separate "confirm" UX needed. If Phase 3 says "founder's identity is established per-session, dangerous tools still need explicit confirmation per call," C3 is the right shape. The phase 3 ruling will settle this.

---

## My recommendation

**C1.** Reasons:

1. **The infrastructure already exists.** `obtainFounderToken`, `relistFetch` with Bearer, `/auth/founder-token`, `create_access_token` / `decode_access_token` — all written, all working for RelistApp. The portal already has the localStorage-token pattern (`RELIST_TOKEN_KEY`). C1 is threading that pattern into `ChatScreen.tsx` and adding a verifier in the chat handler. ~50 lines of code total, split across 3 files.
2. **It is the prototype for Phase 3.** Whatever credential Phase 3 specifies — stronger JWT, mTLS, hardware key — the front-end UX (sign in once, send on every request) and the back-end seam (read header, verify, mark identity confirmed) are identical. C1 is not wasted work even if Phase 3 supersedes it.
3. **C2 introduces a new concept (grants) that sits between identity and tool.** Adding grants means reasoning about grant lifecycle, TTL races, and "what happens when an identity check ALSO succeeds." It's a second source of truth. If Phase 3 is "identity per request is enough," C2 is dead weight.
4. **C3 is invasive and triply-PIN-coupled.** It requires conditionalizing the founder-skip in the chat handler (UX cost for safe tools too — every level-3 needs out-of-band confirm), it surfaces the three-PIN-mismatch problem (per-user `pin_hash` vs `FOUNDER_APPROVAL_PIN` vs `FOUNDER_PIN`), and it depends on whatever Phase 3 says about confirmation policy. Most surface area, most unknowns.

**If the founder rules against C1** — say because the existing RelistApp token is short-lived, or because Phase 3 is known to be a different credential shape — **C3 is the fallback.** The machinery is already there, the per-call UX is more conservative (every dangerous action gets a confirm click), and it doesn't require deciding what Phase 3 looks like.

**C2 only wins if** Phase 3 turns out to require grant-style delegation (e.g. "the founder authorizes an assistant to run dangerous tools for 10 minutes while the founder is away"). For the single-founder-on-this-machine case, that's not the shape.

---

## Founder ruling 2026-09-01

**Chosen shape: C1. Deferred into Phase 3 proper. Not implemented now.**

C1 is the identity credential wearing a PIN-path hat. Shipping it as a quick unlock means committing to the credential design without ruling on it. Nothing is exposed by waiting: the dangerous tools are locked, and Task 0a found zero firings in 30 days.

### What goes into Phase 3 from this map

- **C1 is the chosen shape.** `/api/v1/auth/founder-token` at `backend/app/routers/auth.py:175-209`, `obtainFounderToken(pin)` at `empire-command-center/app/lib/api.ts:66-74`, and the `relistFetch` Bearer pattern at `app/lib/api.ts:53-64` already exist and already work. Phase 3 threads them into `useChat.ts` and the two chat handlers (`/chat` and `/chat/stream`). See C1's "What changes" sections above for the specific files and lines.
- **C2 and C3 are not chosen.** The map's reasoning stands: `create_pending_session` is per-call and wrong for a scope-wide grant (C2); C3 surfaces the three-PIN mismatch (`FOUNDER_PIN` env vs `FOUNDER_APPROVAL_PIN` env vs `access_users.pin_hash` per-user bcrypt/sha256) and costs a click per level-3 call.

### OPEN, must be answered before any Phase 3 code

1. **What does `/auth/founder-token` actually put in the JWT?** This map cited the endpoint and its FOUNDER_PIN verification (`auth.py:175-209`), but not the token's claims, lifetime, or signing secret. Specifically:
   - What is in the JWT payload (claims)?
   - What is the expiry (minutes? hours? days?)?
   - Is the signing secret a real value from the environment, or a fallback default? If it has a default, the whole chain rests on that default — a Phase 3 attacker who knows the default can forge a token.
   - **Decision required from the founder before Phase 3 code:** the secret and the lifetime must be reviewed. If the secret is a fallback default, it must be hardened before C1 ships.
2. **The dangerous-tools gate stops being a PIN gate when C1 lands.** The proposed C1 path is: chat handler verifies the JWT, then sets `access_context["pin"] = os.getenv("FOUNDER_PIN", "")`. The dangerous-tools PIN gate then matches the env var and the call proceeds. **The gate is then not checking a PIN — it is checking that the code handed it one.** The JWT becomes the real gate. That may be correct (the JWT is a stronger credential than the PIN), but it must be an explicit decision, and the gate's comment at `tool_executor.py:497-512` must say what it actually checks. **Decision required from the founder before Phase 3 code.**
3. **Token storage.** localStorage matches the existing Relist pattern (`api.ts:41-51`), but a token that unlocks `shell_execute` is not the same asset as a Relist token. Relist's token is a per-service subscription credential; the C1 token grants shell-equivalent authority. The blast radius of an XSS-compromised localStorage is different. **Decision required from the founder before Phase 3 code:** is localStorage acceptable, or does C1 require httpOnly cookies / WebCrypto-wrapped key / a different store?

### What does NOT change in Phase 3 from this map

- H50 enforcement — unchanged. PIN travels in body of `/auth/founder-token` POST ONCE at session start; never in chat body, never in conversation store, never in SSE stream. The H50 enforcer is undisturbed because MAX never asks for the PIN in chat.
- The dangerous-tools PIN gate semantics — unchanged. The gate still matches `access_context["pin"]` against `FOUNDER_PIN`. The path that fills `access_context["pin"]` changes (JWT verification instead of body regex); the gate itself does not.

### What MUST change in Phase 3 from this map (founder ruling 2026-09-01)

**The channel-alone-grants-founder path is the load-bearing thing Phase 3 reverses.** The previous version of this section said "`is_founder_message` predicate — unchanged ... The JWT adds a second layer on top, not a replacement." That contradicted the standing ruling: web/CC must prove identity; channel name alone must stop granting founder. Corrected here.

Phase 3 must decide:

1. **The five-name allow-list** in `is_founder_message` (`guardrails.py:110`): `("web", "web_cc", "cc", "command_center", "command-center")` returns True unconditionally today. The web entries must be removed (or the predicate inverted) so that no channel name alone grants founder. Telegram's chat_id match (the existing `_FOUNDER_CHAT_ID` path) is the template — web/CC needs the equivalent: identity proven by something other than a string in the body.
2. **`canonical_channel = "web_cc"` in the chat handlers** (`router.py:2187`, `:5293`): today the handlers hard-code web_cc and feed it into the predicate, so founder is granted before the JWT is even read. If the predicate stops returning True for web/web_cc, this declaration becomes a misdirection — the handler must instead build the predicate input from the verified JWT (user_id, role, etc.), not from a string literal. The shape of the chat handler changes from "declare the channel; ask the predicate" to "verify the credential; ask the predicate."

Phase 3 has not done the thing that was ruled if either of those two is left untouched. The C1 path (Bearer-token credential) is what replaces the channel grant, not what supplements it.

### H84 coupling — must land together, not in sequence

Once channel alone stops granting founder, **unidentified callers become normal rather than impossible.** Today every chat-handler caller reaches `founder=True` via the canonical-channel declaration, so the access-controller flow's "unresolvable user" path (`if user:` gate at `tool_executor.py:470`) is silently bypassed for everyone — and the dangerous-tools PIN gate catches the consequence for non-founder-callable tools only because `founder=True` actually means "founder" today, not "whoever the controller couldn't classify." With the credential change, an unidentified caller (one without a valid JWT) lands in `is_founder_message`'s deny path AND in the access-controller flow's "unresolvable user" path simultaneously. H84 (`memory/project_h84_access_control_skip.md`) stops being theoretical.

**H84 and the credential change must land together, not in sequence.** Sequencing them — credential change first, H84 fix later — leaves a window where unidentified callers reach the executor and the `if user:` skip lets them through to the PIN gate alone. That window is exactly the H81 body-channel vector widened by the new vector of "no credential at all." H84 closes the second vector; the credential change closes the first. Both must be in the same Phase 3 dispatch.

---

*Map only, no implementation. Saved to `reports/2026-09-01_h81_phase2b_task_c_pin_path_map.md`. Document joined Task D's documentation commit; Phase 2B founder correction committed separately.*
