# Claude Context Bridge — Reference

## What It Does
Makes claude.ai and Claude Code share the same context, so you never start a session cold.

## Files (all in `~/.claude-context/`)
| File | Purpose | Updated By |
|------|---------|------------|
| `master_context.md` | Architecture, tech stack, file map | You (manually, when things change) |
| `project_brief.md` | Current priorities, P0/P1 tasks | You or Claude (when priorities shift) |
| `last_chat_summary.md` | What happened last session | Auto (bridge commands) |
| `session_log.md` | Running log of all sessions | Auto (every push/pull/end) |

## Daily Workflow

### Starting a claude.ai session:
```
claude-context push          # copies context block to clipboard
```
Paste into claude.ai as your first message. Claude picks up exactly where you left off.

### Ending a claude.ai session:
Ask Claude: *"Generate an end-of-session context update."*
Then:
```
claude-context pull          # paste Claude's output, Ctrl+D
```

### Starting a Claude Code session:
Just start it. Claude Code reads `CLAUDE.md` → reads all context files automatically.

### Ending a Claude Code session:
```
claude-end                   # prompts you to paste Claude Code's summary
```
Or ask Claude Code to write directly to `~/.claude-context/last_chat_summary.md`.

## Install on EmpireDell
```bash
tar xzf claude-context-bridge.tar.gz
cd claude-context-bridge
./install.sh
source ~/.bashrc
```

## The Flow
```
┌─────────────┐     push      ┌──────────────┐
│ Claude Code  │───────────────│  claude.ai   │
│ (terminal)   │               │  (browser)   │
│              │◄──────────────│              │
└──────┬───────┘     pull      └──────┬───────┘
       │                              │
       └──────────┬───────────────────┘
                  │
        ┌─────────▼──────────┐
        │ ~/.claude-context/ │
        │                    │
        │  master_context    │
        │  project_brief     │
        │  last_chat_summary │
        │  session_log       │
        └────────────────────┘
```
