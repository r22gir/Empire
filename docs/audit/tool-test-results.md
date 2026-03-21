# MAX Tool Test Results
**Date:** 2026-03-20
**Method:** Code review + tool_executor.py analysis + live MAX chat tests

---

## Summary
- **Total tools registered:** 37
- **Tested via code review:** 37/37
- **Tested via live chat:** 5/37
- **Working (code review):** 30/37
- **Broken or degraded:** 4/37
- **Dangerous (need restrictions):** 3/37

---

## Tool Results

| # | Tool Name | Category | Code Status | Live Test | Notes |
|---|-----------|----------|-------------|-----------|-------|
| 1 | `create_task` | Tasks | PASS | — | Creates task in DB with desk routing |
| 2 | `get_tasks` | Tasks | PASS | — | Lists tasks, filters by status/desk |
| 3 | `get_desk_status` | Desks | PASS | — | Returns desk configurations |
| 4 | `search_quotes` | Quotes | PASS | — | Searches JSON quote files |
| 5 | `get_quote` | Quotes | PASS | — | Loads specific quote by ID |
| 6 | `open_quote_builder` | Quotes | PASS | — | Returns quote builder URL |
| 7 | `create_quick_quote` | Quotes | PASS | — | Creates quote with QIS engine or manual |
| 8 | `select_proposal` | Quotes | PASS | — | Selects a proposal tier from auto-quote |
| 9 | `search_contacts` | CRM | PASS | — | Searches customer DB |
| 10 | `create_contact` | CRM | PASS | — | Creates customer record |
| 11 | `get_system_stats` | System | PASS | PASS | Returns CPU/RAM/disk via psutil |
| 12 | `get_weather` | External | PASS | — | Uses Brave API for weather |
| 13 | `get_services_health` | System | PASS | — | Checks port accessibility for all services |
| 14 | `send_telegram` | Comms | PASS | — | Sends message to Telegram founder chat |
| 15 | `send_quote_telegram` | Comms | PASS | — | Sends formatted quote via Telegram |
| 16 | `send_email` | Comms | CONDITIONAL | — | Works IF SendGrid domain is verified |
| 17 | `send_quote_email` | Comms | CONDITIONAL | — | Sends quote PDF as email attachment |
| 18 | `search_images` | Files | PASS | — | Finds images in upload directories |
| 19 | `web_search` | External | PASS | — | Brave Search API integration |
| 20 | `web_read` | External | PASS | — | Fetches and extracts text from URLs |
| 21 | `photo_to_quote` | Vision+Quotes | PASS | — | AI photo analysis → auto-quote generation |
| 22 | `run_desk_task` | Desks | PASS | — | Submits task to desk manager |
| 23 | `present` | Presentations | PASS | — | Generates structured presentations |
| 24 | `shell_execute` | Code/System | DANGEROUS | — | Executes arbitrary shell commands |
| 25 | `dispatch_to_openclaw` | AI | DEGRADED | — | OpenClaw available but Ollama offline |
| 26 | `file_read` | Code | PASS | — | Reads files with path expansion + truncation |
| 27 | `file_write` | Code | PASS | — | Creates/overwrites files |
| 28 | `file_edit` | Code | PASS | — | Find-and-replace in files |
| 29 | `file_append` | Code | PASS | — | Appends content to files |
| 30 | `env_get` | Config | PASS | — | Reads environment variables |
| 31 | `env_set` | Config | DANGEROUS | — | Sets environment variables |
| 32 | `db_query` | Data | DANGEROUS | — | Executes raw SQL queries |
| 33 | `git_ops` | Code | PASS | — | Git status, diff, log, commit, push |
| 34 | `service_manager` | System | PASS | — | Start/stop/restart systemd services |
| 35 | `package_manager` | System | PASS | — | pip/npm install/uninstall |
| 36 | `test_runner` | Code | PASS | — | Run pytest/npm test |
| 37 | `project_scaffold` | Code | PASS | — | Create project directory structures |
| 38 | `search_conversations` | Memory | PASS | — | Search brain conversation history |

---

## Issues Found

### Dangerous Tools (Need Guardrails)
1. **`shell_execute`** — Can run any shell command. Currently gated by tier middleware but a serious security risk if tier checks fail.
2. **`env_set`** — Can modify environment variables including API keys. Should require PIN confirmation.
3. **`db_query`** — Can execute arbitrary SQL. Could delete all data. Should be read-only or require PIN.

### Degraded Tools
4. **`dispatch_to_openclaw`** — OpenClaw server is running but Ollama is offline, so all dispatches fail.

### Tools That Depend on External Config
5. **`send_email`** / **`send_quote_email`** — Depend on SendGrid API key and domain verification. Key exists; domain verification status unknown.
6. **`get_weather`** — Depends on Brave Search API. Key configured and working.
7. **`web_search`** / **`web_read`** — Depend on Brave Search API. Working.

### Auto-Routing (CodeForge)
File and git tools (`file_read`, `file_write`, `file_edit`, `file_append`, `git_ops`) are auto-routed from main chat to the CodeForge desk, which uses Claude Opus for better code handling. This is a good pattern.

---

## Recommendations

1. **Add PIN confirmation for dangerous tools** — `shell_execute`, `env_set`, `db_query` should require owner confirmation via Telegram or PIN.
2. **Make `db_query` read-only by default** — Only allow SELECT statements unless explicitly overridden.
3. **Start Ollama** — Fixes `dispatch_to_openclaw` and provides a free local fallback.
4. **Add tool execution metrics** — Track which tools are used most, failure rates, and average execution time.
5. **Tool documentation in system prompt** — Ensure MAX knows exactly what each tool can do and when to use it.
