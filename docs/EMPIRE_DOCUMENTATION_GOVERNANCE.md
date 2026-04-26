# EmpireBox Documentation Governance

> Effective: 2026-04-26
> Applies to: All documentation in `~/empire-repo/docs/`
> Authority: Repo/runtime truth > old prose

---

## Core Principles

1. **Repo truth beats prose** — If code and docs conflict, code is authoritative. Update docs to match reality, not the other way around.
2. **Every module needs a doc section** — New modules must document themselves in EMPIRE_MASTER_DOCUMENT_CURRENT.md or a module-specific doc.
3. **Implementation is not complete until docs updated** — "It's done when the docs reflect it."
4. **Old docs must be deprecated, not deleted** — Mark with `**DEPRECATED – superseded by X**` header so historical context survives.

---

## Required Documentation Standards

### For Every Module/Product

Each module must have (at minimum):
- Current status: **live / partial / stub / deprecated / unknown**
- Purpose (one sentence)
- Key frontend files (3–5 paths)
- Key backend files (3–5 paths)
- Data: tables, storage paths, approximate row counts
- AI integration: which desk, model routing if special
- Known gaps (bullet list)
- Last verified: commit hash or date

### For Major Features

Features that cross multiple modules must have:
- Flow description (current state)
- Data touched (tables, files)
- AI/MAX involvement
- Related docs (cross-reference)
- Gaps or TODOs

---

## Document Hierarchy

| Level | Document | Authority | Update Frequency |
|-------|----------|-----------|-----------------|
| **Master** | `EMPIRE_MASTER_DOCUMENT_CURRENT.md` | This is the current truth | On every major release |
| **Module** | `EMPIRE_MODULE_REGISTRY.md` | Detail for each module | Monthly or on feature changes |
| **Changelog** | `EMPIRE_CHANGELOG_RECENT.md` | Post-baseline commit log | On every session |
| **Architecture** | `EMPIRE_ARCHITECTURE_CURRENT.md` | System design | On architectural changes |
| **Governance** | `EMPIRE_DOCUMENTATION_GOVERNANCE.md` | This file | Only when governance changes |
| **Module-specific** | `docs/MODULE_SPECIFIC.md` | Per-module deep dives | As needed |
| **Historical** | `EMPIRE_MASTER_DOCUMENT_2026.pdf` | Old baseline (April 1–2, 2026) | Never — archive only |

---

## Naming Conventions

- Master: `EMPIRE_MASTER_DOCUMENT_CURRENT.md`
- Module: `EMPIRE_MODULE_REGISTRY.md`
- Changelog: `EMPIRE_CHANGELOG_RECENT.md`
- Architecture: `EMPIRE_ARCHITECTURE_CURRENT.md`
- Governance: `EMPIRE_DOCUMENTATION_GOVERNANCE.md`
- Module-specific: `docs/MODULE_NAME_SPEC.md` or `docs/MODULE_NAME_STATUS.md`
- Deprecated: prefix with `DEPRECATED_` or mark with `[DEPRECATED]` in filename

---

## Update Triggers

| Event | Action |
|-------|--------|
| New module shipped | Add to EMPIRE_MASTER_DOCUMENT_CURRENT.md + EMPIRE_MODULE_REGISTRY.md |
| Module status change | Update status in both master + module registry |
| New AI provider/model | Update AI routing table in module doc |
| New desk created | Add to MAX section in module registry |
| New backend router | Add to module's backend list |
| Major refactor | Update architecture doc + re-document flows |
| Module deprecated | Mark as **[DEPRECATED]** in title, add supersession note |
| Old PDF baseline | Never modify — archive as-is |

---

## Deprecation Protocol

When a document is superseded:
1. Add `**DEPRECATED – superseded by [new doc] (YYYY-MM-DD)**` to the top
2. Keep the content intact (historical record)
3. Update the new doc's "supersedes" field
4. Do NOT delete old docs — they preserve history and reasoning

Example header:
```markdown
# Old Module Doc
**DEPRECATED – superseded by EMPIRE_MASTER_DOCUMENT_CURRENT.md (2026-04-26)**
```

---

## Version References

When documenting version state:
- Always cite commit hash, not date, for precision
- For multi-commit features, cite the most recent relevant commit
- For "needs verification" items, do NOT guess — mark explicitly

---

## Sources of Truth (Priority Order)

1. **Live code** — `.py` files, `.tsx` files, routers, services
2. **Git history** — `git log --oneline` shows what actually shipped
3. **Running services** — ports, endpoints via health checks
4. **Databases** — schema, row counts via direct query
5. **New documentation** — this repo's docs/ directory
6. **Old documentation** — historical only, must be verified
7. **Memory** — `.claude-context/` only for session context, not architectural truth

---

*Governance established 2026-04-26 — applies to all current and future EmpireBox documentation*