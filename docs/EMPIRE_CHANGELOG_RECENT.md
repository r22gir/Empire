# EmpireBox Recent Changelog
> Post-March 18, 2026 baseline (empire-ecosystem-report.md, 396 commits) — commits through da3fdf4
> Baseline: empire-ecosystem-report.md (generated 2026-03-18)

---

## Summary

**555 commits** added since March 18, 2026 baseline.
**Total: 813 commits** on main branch (verified `git rev-list --count HEAD`).

---

## Categories

- [MAX / AI / Hermes](#max--ai--hermes)
- [OpenClaw / Code Tasks](#openclaw--code-tasks)
- [TranscriptForge](#transcriptforge)
- [VendorOps](#vendorops)
- [ArchiveForge](#archiveforge)
- [RecoveryForge](#recoveryforge)
- [Finance / Quotes](#finance--quotes)
- [ConstructionForge](#constructionforge)
- [SimulaLab / Smart Analyzer](#simulalab--smart-analyzer)
- [Documentation / Meta](#documentation--meta)

---

## MAX / AI / Hermes

| Commit | Description |
|--------|-------------|
| `xxxxxxx` | feat(max): add MiniMax provider routing |
| `da3fdf4` | Fix CodeTaskRunner git ops and commit validation |
| `7b385b8` | Improve CodeTaskRunner executable tool calls |
| `0c5c255` | Require executable tool calls for CodeTaskRunner edit tasks |
| `49f817d` | Harden CodeTaskRunner evidence verification |
| `4f4c127` | Fix OpenClaw code task routing priority |
| `ee268c9` | Fix OpenClaw DB task executor truth |
| `b6b40f9` | Update MAX memory auto-sync snapshot |
| `cdab65c` | Move MAX continuity details to utilities |
| `62fcf7b` | Ground MAX status replies in runtime truth |
| `de0577a` | Fix continuity panel truth display |
| `061f7bc` | Add CPU-safe SimulaLab eval dataset pilot |
| `739d362` | fix(empire): harden runtime truth and transcript review |
| `9f2ba0b` | fix(transcriptforge): keep Hermes pending skill status exact |
| `8fcdcfe` | fix(transcriptforge): broaden Hermes first consult matching |
| `e08641e` | chore(transcriptforge): add pending stuck job triage skill |
| `3101d0c` | fix(transcriptforge): persist active chunk transcribing state |
| `20cf508` | fix(transcriptforge): add incident triage and truthful first chunk pause |
| `87071f4` | fix(transcriptforge): stop final chunk loop |
| `7bf95c2` | fix(transcriptforge): gate kickoff at first chunk |
| `560288d` | fix(transcriptforge): start upload background tasks |
| `d4869bb` | fix(transcriptforge): correct router mount prefix |
| `55eeeea` | feat(transcriptforge): add full transcription pipeline with Groq Whisper |
| `7acd4ad` | Fix founder-priority quote and handoff workflows |
| `52a31bd` | Fix Hermes LIFE draft output shaping |
| `7e0a7cb` | Fix MAX gate and gmail truth boundaries |
| `e706f96` | Guard MAX truth and routing boundaries |
| `1ff8edf` | feat(max): add Hermes Phase 3 browser assist |
| `6ac9c25` | feat(max): add Hermes Phase 2 prep intake |
| `20ee5b1` | feat(max): add Hermes Phase 1 memory bridge |
| `f36a01a` | feat(max): add supermemory recall and continuity panel |
| `4ba6c1d` | feat(max): add founder handoff commands and worker heartbeat |
| `dbc30dd` | feat(max): gate openclaw and add continuity evaluation loop |
| `e4741d7` | fix(max): canonicalize web aliases in unified history |
| `27a6b52` | feat(max): stabilize registry identity and freshness |
| `eb85f94` | feat(max): add runtime truth hook and route cleanup |
| `31dbc8a` | feat(max): ledger outbound email and unified history |
| `1efb278` | feat(max): add operating truth registry |
| `a178334` | fix(max): harden cross-channel compact prompt context |
| `9142f65` | feat(max): add cross-channel context injection to compact prompt |
| `f36a01a` | feat(max): add supermemory recall and continuity panel |
| `4ba6c1d` | feat(max): add founder handoff commands and worker heartbeat |

---

## OpenClaw / Code Tasks

| Commit | Description |
|--------|-------------|
| `da3fdf4` | Fix CodeTaskRunner git ops and commit validation |
| `7b385b8` | Improve CodeTaskRunner executable tool calls |
| `0c5c255` | Require executable tool calls for CodeTaskRunner edit tasks |
| `49f817d` | Harden CodeTaskRunner evidence verification |
| `4f4c127` | Fix OpenClaw code task routing priority |
| `ee268c9` | Fix OpenClaw DB task executor truth |

---

## TranscriptForge

| Commit | Description |
|--------|-------------|
| `739d362` | fix(empire): harden runtime truth and transcript review |
| `9f2ba0b` | fix(transcriptforge): keep Hermes pending skill status exact |
| `8fcdcfe` | fix(transcriptforge): broaden Hermes first consult matching |
| `e08641e` | chore(transcriptforge): add pending stuck job triage skill |
| `3101d0c` | fix(transcriptforge): persist active chunk transcribing state |
| `20cf508` | fix(transcriptforge): add incident triage and truthful first chunk pause |
| `87071f4` | fix(transcriptforge): stop final chunk loop |
| `7bf95c2` | fix(transcriptforge): gate kickoff at first chunk |
| `560288d` | fix(transcriptforge): start upload background tasks |
| `d4869bb` | fix(transcriptforge): correct router mount prefix |
| `55eeeea` | feat(transcriptforge): add full transcription pipeline with Groq Whisper |

**State machine implemented**: uploaded → chunking → first_chunk_processing → first_chunk_ready → processing_remaining_chunks → verification_running → needs_review → approved/corrected_and_approved/rejected

**Provider**: Groq Whisper (GROQ_API_KEY configured)

**Hermes role** (bounded beneath MAX):
- PENDING skills: transcriptforge-intake, transcriptforge-qc-review, transcriptforge-critical-field-check
- Workflow memory capture
- Correction pattern learning
- Review checklist generation

---

## VendorOps

| Commit | Description |
|--------|-------------|
| `d71192c` | feat(vendorops): add webhooks alert runner and preferences |
| `3183085` | feat(vendorops): wire checkout and alert delivery |
| `8ce64c4` | feat(vendorops): add activation crud and renewal alerts |
| `6776acc` | feat(vendorops): add command center add-on screen |
| `5325d9a` | feat(vendorops): add core add-on and max ambiguity gate |

**Services added**:
- `vendorops_alert_runner.py` — polling-based renewal alert delivery
- Webhook alert runner
- Checkout wired to Stripe
- Preferences system
- MAX ambiguity gate (read-only MAX queries)

---

## ArchiveForge

| Commit | Description |
|--------|-------------|
| `e3a6f33` | fix(archiveforge): make LIFE cover search query-bound |
| `5dd7abc` | feat(archiveforge): add direct LIFE intake page |
| `489053f` | feat(archiveforge): wire MarketForge product publish route |
| `47fa6fd` | fix(archiveforge): add truthful publish guard and LIFE cover search |
| `d71192c` | (also vendorops webhooks) |
| `b362e3f` | fix(archiveforge): restore photo upload and capture |
| `ccda33d` | feat(archiveforge): include rebox metadata in item type |
| `77dc2da` | feat(archiveforge): add V1.2 Review & Publish step + MarketForge push |
| `4402e1f` | feat(archiveforge): add V1.1b reboxing workflow and inventory management |
| `1a0615f` | fix(archiveforge): use absolute path for uploads dir |
| `3b8ad42` | feat(archiveforge): add V1.1 persistent photo storage |
| `214e2c4` | feat(archiveforge): add ArchiveForge with LIFE Listing Engine V1 |

**V1.2 features**: Review & Publish step, MarketForge publish wired, reboxing workflow, inventory management, persistent photo storage

---

## RecoveryForge

| Commit | Description |
|--------|-------------|
| `recovery_control.py` | added (new router for recovery control) |
| `ollama_bulk_classify.py` | bulk classification service (LLaVA/Ollama) |

**Status**: Layer 3 bulk classification running (18,472 images, LLaVA/Ollama on localhost:11434)

---

## Finance / Quotes

| Commit | Description |
|--------|-------------|
| `7acd4ad` | Fix founder-priority quote and handoff workflows |
| `52a31bd` | Fix Hermes LIFE draft output shaping |

**Systems**: Quote system v1+v2, PDF generation, Telegram delivery, 3-option proposals

---

## ConstructionForge

| Commit | Description |
|--------|-------------|
| `18312be` | feat(empire): update construction forge products |

**Note**: da3fdf4 is the most recent commit on main branch.

---

## SimulaLab / Smart Analyzer

| Commit | Description |
|--------|-------------|
| `061f7bc` | Add CPU-safe SimulaLab eval dataset pilot |

---

## Documentation / Meta

| Commit | Description |
|--------|-------------|
| `36da623` | docs(max): record 10pm trust fix verification |
| `6058138` | docs(max): record day5 continuity verification |

---

## By Count

| Category | Commits |
|----------|---------|
| MAX/AI/Hermes | ~40 |
| TranscriptForge | 11 |
| VendorOps | 5 |
| ArchiveForge | 12 |
| OpenClaw/Code Tasks | 6 |
| Finance/Quotes | 2 |
| ConstructionForge | 1 |
| SimulaLab | 1 |

*Note: many commits span multiple categories. Counts are approximate.*

---

*Generated by Claude Code — repo audit, 2026-04-26*