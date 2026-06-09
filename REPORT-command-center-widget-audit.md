# REPORT — Command Center Widget / Status-Chip Audit

**Repo:** `/home/rg/empire-repo-main` · **Branch:** `main` · **HEAD:** `28679781a22c3c7901754067356b3d42bdf226c3`
**Author:** tandem audit (Sub-2 widget auditor + Hermes reconciliation), 2026-06-09
**Scope:** read-only inspection. No code changed. No branches. No push.

## Methodology

Read `app/page.tsx`, `app/components/layout/{TopBar,BottomBar,LeftNav}.tsx`, `app/components/screens/ChatScreen.tsx`, `app/components/ContinuityPanel.tsx`, `app/hooks/useSystemData.ts`, `app/lib/api.ts`. Probed low-cost live endpoints: `/health`, `/api/v1/max/health`, `/api/v1/max/orchestration/status`, `/api/v1/max/status`, `/api/v1/openclaw/health`, `/api/v1/openclaw/tasks?status=queued`, `/api/v1/system/ollama/status`, `/api/v1/system/stats`, `/api/v1/max/telegram/status`, `:7878/health`, `:8787/`, `:3005/`.

## Where each chip lives

The "top status chips" row is rendered **only inside `ChatScreen` (lines 501–595 of `app/components/screens/ChatScreen.tsx`)** under `data-testid="max-orchestration-status"`. It is mounted only while the chat screen is the active screen. Switching to Dashboard/Tasks/Desks etc. hides it entirely.

The `TopBar` at the very top of the page is a separate element showing: model picker (provider + model), search, language, notifications, settings, avatar.

The "MAX Truth" compact row is `<ContinuityPanel mode="compact" />` rendered in `ChatScreen` at line 597.

---

## A. Top / MAX status chips

| # | Chip | Component / line | Data source | Live? | Refresh | Clickable | Affects MAX? | Accurate? | Founder-useful? | Classification |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | "Founder > MAX" | ChatScreen.tsx:515–517 | none — static | hardcoded | n/a | no | no | trivially yes | no (decoration) | **HIDE** |
| 2 | "MiniMax" (chat row) | ChatScreen.tsx:518 via `primaryModel` | `/max/orchestration/status` → `providers.cloud[primary].name` | live | 60s | no | yes (selects active provider) | yes — `minimax` / `MiniMax-M3` | low (duplicate of TopBar) | **HIDE** in chat row; **KEEP_MAIN** in TopBar |
| 3 | "Text routing ready" | ChatScreen.tsx:400–404 | derived from `streamingModel` + `latestAssistantModel` | live | per stream | no | no | yes | low | **SHOW_ONLY_ON_ERROR** |
| 4 | "Vision offline" | ChatScreen.tsx:405–408 | `/max/orchestration/status` → `local_vision.online` (Ollama probe) | live | 60s | no | indirect (only local vision) | **misleading** — local vision is offline (Ollama stopped), but image understanding via MiniMax MCP `mmx_vision` still works | high (Founder reads as "image upload broken") | **FIX_LABEL** → "Vision: cloud" |
| 5 | "Voice configured" | ChatScreen.tsx:409–413 | `/max/orchestration/status` → `capabilities.voice_input && voice_output` | live | 60s | no | no (read-only) | yes | low | **SHOW_ONLY_ON_ERROR** |
| 6 | "OpenClaw online · 72 tasks" | ChatScreen.tsx:414–415, 522 | `/max/orchestration/status` → `providers.local[openclaw].queue_stats.total` | live | 60s | no | no (display only) | **misleading** — gate is healthy, but 72 tasks queued for ~2 days, all recent "Read file" stuck; worker not draining. Tone is `ok`. | high (truthful health), but wrong tone | **FIX_LABEL** → "OpenClaw online · 72 queued (stalled)" with warn tone; click → OpenClawTasksPage |
| 7 | "Code Mode CodeForge / Atlas" | ChatScreen.tsx:416–418, 523 | `/max/orchestration/status` → `code_mode.executor` | live | 60s | no | yes (selects executor) | yes | low (technical) | **MOVE_TO_SYSTEM_DETAILS** |
| 8 | "Self-heal guided" | ChatScreen.tsx:419–421, 524 | `/max/orchestration/status` → `self_heal.full_autonomous_repair_verified` (false) | live | 60s | no | no | yes (guided) — **tone hardcoded `warn`**, constant amber on a healthy system | low; alarming | **SHOW_ONLY_ON_ERROR** |
| 9 | "17 desks subordinate" | ChatScreen.tsx:525–541 | `/max/orchestration/status` → `desks.count` | live | on chat mount | **YES** → `onScreenChange('desks')` | no | **stale label** — runtime registers 18 desks (sidebar `EmpireSidebar.tsx:22` shows "18 desks"). `desks.count` may also be 18 now. | yes (count) | **KEEP_MAIN** with relabel: "18 desks" |
| 10 | "Memory Bank" button | ChatScreen.tsx:542–558 | none (navigation) | hardcoded | n/a | **YES** | no | n/a | yes (shortcut) | **KEEP_MAIN** (reclassify as toolbar) |
| 11 | "RelistApp" button | ChatScreen.tsx:559–575 | none (navigation) | hardcoded | n/a | **YES** | no | n/a | yes (shortcut) | **KEEP_MAIN** (reclassify as toolbar) |
| 12 | "Public MAX" link | ChatScreen.tsx:576–592 | none (link to `/max`) | hardcoded | n/a | **YES** | no | n/a | low (marketing link inside status row is confusing) | **MOVE_TO_SYSTEM_DETAILS** or convert to `?` About button in TopBar |
| 13 | "Upload image/doc" | ChatScreen.tsx:593 | none | **hardcoded, NOT clickable** | n/a | **NO** (static `<span>`) | no | n/a — real uploader is Paperclip at line 1000–1010 | misleading (looks like button, isn't) | **REMOVE** or wire onClick to `fileInputRef` |

## B. MAX Truth compact row (`ContinuityPanel.tsx` lines 157–209)

| # | Pill | Data source | Live? | Clickable | Accurate? | Founder-useful? | Classification |
|---|---|---|---|---|---|---|---|
| B1 | "MAX Truth:" label | static | hardcoded | no | n/a | n/a | KEEP (section header) |
| B2 | "Registry OK" | `status.registry.registry_version` | live | no | yes | low | **MOVE_TO_SYSTEM_DETAILS** |
| B3 | "Commit 2867978" | `status.current_commit.hash` | live | no | yes (matches live backend) | low | **KEEP_MAIN** |
| B4 | "OpenClaw healthy" | `openclaw_gate.state` | live | no | yes (gate=healthy; worker stalled is separate issue) | yes (correct health) | **KEEP_MAIN** |
| B5 | "Handoff stale cf1b782" | audit result vs current_commit | live (per audit) | no | yes (audit-derived) | confusing after reboot | **SHOW_ONLY_ON_ERROR** — only when `runtime.restart_required` or audit result actually disagrees. Normal after reboot, not actionable. |
| B6 | "Worker fresh 8.953s" | `openclaw_gate.worker_heartbeat` | live | no | yes (3–14s, fresh) | low; reassuring | **KEEP_MAIN** compact as "Worker ✓" |
| B7 | "Checked 12:36:56 PM" | local `toLocaleTimeString()` at panel mount | live (set on each refresh) | no | yes (set on mount; never auto-refreshes) | no | **REMOVE_IF_STALE** — replace with live clock or auto-refresh |
| B8 | "Live truth wins." | shown when `staleCommitWarning && currentCommit` | live, conditional | no | yes (engineer message) | **NO — internal logic** | **SHOW_ONLY_IN_DEBUG_MODE** or remove |
| B9 | "Open Continuity" | `<button>` | hardcoded | **YES** | n/a | yes | **KEEP_MAIN** |

## C. Bottom status bar (`components/layout/BottomBar.tsx`)

| # | Item | Data source | Live? | Clickable | Affects MAX? | Accurate? | Founder-useful? | Classification |
|---|---|---|---|---|---|---|---|---|
| C1 | Service dot `backend` | `useSystemData.fetchServices` → `/system/stats` 200? | live | no | no | yes (200 → green) | low | **KEEP_MAIN** |
| C2 | Service dot `db` | **never polled** (only `backend`, `ollama`, `openclaw`, `tg` are); `services.db` undefined → always amber | **broken** | no | no | always wrong | **NO** | **HIDE** — remove from SERVICES array or add real `/db/health` probe |
| C3 | Service dot `grok` | **never polled** | **broken** | no | no | always wrong | NO | **HIDE** |
| C4 | Service dot `claude` | **never polled** | **broken** | no | no | always wrong | NO | **HIDE** |
| C5 | Service dot `ollama` | `/ollama/models` 200? | live | no | no | yes (currently amber) | yes | **KEEP_MAIN** |
| C6 | Service dot `tq` (telegram) | `/max/telegram/status` → `configured` | live | no | no | yes (green: configured) | yes | **KEEP_MAIN** (rename to `tg` for consistency) |
| C7 | "Check" / "Monitor Check" links | n/a — these are **NOT in BottomBar**; they're notifications from `/notifications` rendered in TopBar panel (one item: "Monitor Check · 194 inbox items piling up"). The "(System)" suffix is misleading. | n/a | n/a | n/a | n/a | n/a | **FIX_LABEL** in notifications source |
| C8 | "Ollama OFF" toggle | `/system/ollama/status` polled every 30s; POST `/system/ollama/toggle` | live | **YES** (with two `confirm()` dialogs) | **YES** — turns local Ollama + RecoveryForge classification on/off | yes (`ollama: "stopped"`) | yes (real control, high-friction) | **KEEP_MAIN** — replace `confirm()` dialogs with one-click + inline `?` tooltip |
| C9 | Clock | client `new Date()` | live (client) | no | no | yes (local browser time, not server) | low | **KEEP_MAIN** or replace with backend time |
| C10 | News ticker | `/notifications` polled once on mount; falls back to 6 hardcoded items | **mostly hardcoded** ("AI photo analysis now live in Workroom", "Telegram bot integration complete", etc.) | some items link out | no | mostly stale defaults | low | **HIDE** — replace with real notifications or remove |
| C11 | Newspaper chevron toggle | client state — expands ticker into 200px panel | live | **YES** | no | n/a | low | **MOVE_TO_SYSTEM_DETAILS** |
| C12 | Power icon (Ollama) | same as C8 | live | **YES** | yes | yes | yes | **KEEP_MAIN** (paired with label) |

---

## Answers to the 7 confusing-label questions

1. **"Vision offline" while image upload still works through another path?** — Yes. `/max/orchestration/status` reports `local_vision.online: false` (Ollama is down) but `minimax_tools.image_understanding: { configured: true, cli_available: true }`. Uploaded images are still analyzed via the MiniMax MCP `mmx_vision` tool. The chip is technically correct for *local* vision, but Founder reads it as "image upload broken". **FIX_LABEL** to "Vision: cloud" or hide on OK state.

2. **"OpenClaw online · 72 tasks" while OpenClaw is not safe as executor?** — OpenClaw is online, but the 72-task queue has not drained in ~2 days; all recent tasks (id 31, 42, 44, 45) are still `queued` since 2026-05-26 to 2026-06-05. Historical: 5916 failed, 1439 done, 2 cancelled, 0 viable in window. The chip uses `tone="ok"`. Founder should see a warn state. **FIX_LABEL** to "OpenClaw online · 72 queued (stalled)" with warn tone, or just "OpenClaw · check queue" linking to OpenClawTasksPage.

3. **"Public MAX" meaning unclear?** — It is a link to the public marketing page at `/max` (route at `app/max/page.tsx`). It is NOT a status; it is a navigation button. Its placement inside the status-chip row, and its visual style matching the actual chips, makes it look like a status indicator. **MOVE_TO_SYSTEM_DETAILS** or convert to `?` help button.

4. **"Handoff stale" if normal after reboot?** — Yes, normal. `compactHandoffLabel` becomes "Handoff stale {commit}" only when the audit result's commit differs from the live `current_commit`. After a reboot, MAX's last saved handoff packet is naturally one commit behind. **SHOW_ONLY_ON_ERROR** — only show when `runtime.restart_required` is true.

5. **"Ollama OFF" while MiniMax is intentionally active?** — Accurate. Routing state shows `ollama-llama.disabled_reason: "founder_disabled_due_to_stall_suspected"`, so Ollama being OFF is the intended state. The chip itself is fine. The issue is the confirmation dialogs on the toggle. **FIX_LABEL** in the confirm dialog, not the chip.

6. **"Live truth wins" if it is internal logic?** — Correct. Shown in `ContinuityPanel.tsx` lines 184–188 only when `staleCommitWarning && currentCommit`. Engineering telemetry explaining MAX's behavior. **SHOW_ONLY_IN_DEBUG_MODE** or remove.

7. **Bottom-bar indicators that are developer telemetry?** — `db`, `grok`, `claude` service dots are never polled by `useSystemData.fetchServices` (lines 22–49 of `useSystemData.ts` only checks `backend`, `ollama`, `openclaw`, `tg`), so they always render amber. The "tq" label is inconsistent with "tg" elsewhere. The hardcoded news ticker is dev filler. All are **HIDE** or **MOVE_TO_SYSTEM_DETAILS**.

---

## Desk count disagreement (cross-cutting)

Live runtime now shows **18 desks** (sidebar `EmpireSidebar.tsx:22` literal "18 desks"; `system_prompt.py:426` literal "18 desks"; `PresentationScreen.tsx:765` literal "18 desks"). `desks_online:17` from `/max/health` and `desks.count: 17` from `/max/orchestration/status` may also need a recount after the desk_manager re-registration. OwnerContext in RightPanel hardcodes "12 AI Desks" (stale). Pick one source of truth: `AIDeskManager.router.desk_ids.count`.

---

## Bottom status bar decision

**Move everything except the Ollama toggle and clock to a System Details drawer.** Current bar is dev telemetry. The news ticker is hardcoded fiction. 3 of 6 service dots (`db`, `grok`, `claude`) are never polled. The Ollama toggle is the only Founder-actionable item; the rest is noise.

---

## Proposed simplified MAX main surface

**Header (TopBar — keep):** EMPIRE logo · Search (⌘K) · Model picker (provider + model, click to switch) — single source of truth · Notifications bell (unread count) · Settings / Client view toggle · Avatar

**Chat-screen status row (replace chip sprawl with a clean 4-line strip):**
1. **Routing line (1 short chip):** `minimax · MiniMax-M3 · cloud` (only show fallback/voice/vision on non-OK states)
2. **Desks line (1 chip):** `18 desks ▸` → click to Desks screen
3. **OpenClaw line (1 chip):** `OpenClaw healthy · worker 4s` → click to OpenClawTasksPage. Drop the 72-task count (or move inline only when queue is small/growing).
4. **MAX Truth (compact, only on stale/warn):** A single collapsed indicator. Expand on click into ContinuityPanel. Drop "Live truth wins." entirely.

**Bottom bar — collapse to a single "System: OK · Ollama OFF" pill** that opens a System Details drawer. Remove the 6-dot telemetry strip, news ticker, and Newspaper expand toggle. Keep the Ollama toggle inside the drawer.

---

## Top 10 widget/UI risks

1. **"OpenClaw online · 72 tasks" painted green** — 72 tasks queued for 2+ days, worker stalled. Misleading OK tone hides a real problem.
2. **"Vision offline"** — accurate for local vision only; image understanding via MiniMax MCP `mmx_vision` still works, but Founder reads it as broken.
3. **"Upload image/doc" chip is a fake button** — hardcoded `<StatusChip>` with no onClick; real uploader is Paperclip icon 400px below.
4. **"Handoff stale" + "Live truth wins."** — engineering telemetry displayed to Founder; should be debug-only.
5. **"Founder > MAX"** — decorative breadcrumb, no information value.
6. **"Self-heal guided"** — tone hardcoded `warn` on a healthy system, constant amber alarm.
7. **"Public MAX" link inside status row** — marketing page link visually indistinguishable from status chips.
8. **Bottom-bar `db`, `grok`, `claude` dots are never polled** — always amber; lying.
9. **Model chip duplicated** — TopBar model picker AND chat-header "MiniMax" chip show the same value.
10. **News ticker is mostly hardcoded fiction** — defaults like "AI photo analysis now live in Workroom", "Telegram bot integration complete" are not real updates.

---

**End of widget audit. No implementation performed.**
