# MAX Brain — Technical Specification
## Portable Persistent Memory System

**Version:** 1.0
**Date:** February 27, 2026
**Status:** Phase 1 Implemented
**Parent:** Empire Box / MAX AI Director

---

## 1. Overview

MAX Brain is a hybrid memory and intelligence system that gives MAX persistent knowledge across all conversations, sessions, and devices. The brain runs locally on Ollama (free, private, offline-capable) stored on a portable 1TB external drive, while cloud LLMs (Grok, Claude) handle complex reasoning. Plug the drive into any machine and MAX's full knowledge comes with it.

**Core Principle:** Ollama is the memory. Grok/Claude is the intelligence. The external drive is the portable brain.

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────┐
│                    MAX AI Director                     │
│                                                        │
│  ┌─────────────────┐     ┌──────────────────────────┐ │
│  │  LOCAL BRAIN     │     │  CLOUD INTELLIGENCE      │ │
│  │  (Ollama on      │     │                          │ │
│  │   BACKUP11)      │     │  Grok (xAI) — MAX voice  │ │
│  │                  │     │  Claude — heavy tasks     │ │
│  │  Mistral 7B      │     │                          │ │
│  │  - Summarize     │────▶│  Receives enriched       │ │
│  │  - Classify      │     │  context from local      │ │
│  │  - Triage        │     │  brain before every      │ │
│  │                  │     │  response                │ │
│  │  Nomic Embed     │     │                          │ │
│  │  - Embeddings    │     └──────────────────────────┘ │
│  │  - Semantic      │                                  │
│  │    search        │     ┌──────────────────────────┐ │
│  │                  │     │  STORAGE (BACKUP11)      │ │
│  │  Memory Store    │────▶│  /ollama/models/         │ │
│  │  - Save          │     │  /ollama/brain/          │ │
│  │  - Retrieve      │     │    memories.db           │ │
│  │  - Search        │     │    embeddings.db         │ │
│  │                  │     │    customers/            │ │
│  └─────────────────┘     │    conversations/        │ │
│                           │    knowledge/            │ │
│                           └──────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

---

## 3. External Drive Structure

```
/media/rg/BACKUP11/ollama/
├── models/                      ← Ollama model weights
│   ├── manifests/
│   └── blobs/
└── brain/                       ← MAX's persistent knowledge
    ├── memories.db              ← SQLite — all memories
    ├── embeddings.db            ← SQLite-vec — vector embeddings (future)
    ├── founder/
    ├── customers/
    ├── conversations/
    ├── knowledge/
    │   ├── workroomforge/
    │   ├── amp/
    │   ├── socialforge/
    │   ├── marketforge/
    │   ├── craftforge/
    │   └── empire/
    └── operational/
```

---

## 4. Models

| Model | Size | RAM Usage | Purpose |
|-------|------|-----------|---------|
| `nomic-embed-text` | 274MB | ~500MB | Embeddings for semantic search |
| `mistral:7b` | 4.1GB | ~6GB | Summarization, classification, triage |
| `llama3:latest` | 4.7GB | ~7GB | Fallback/alternative |

---

## 5. Backend Services

Located at: `~/Empire/backend/app/services/max/brain/`

| File | Purpose |
|------|---------|
| `brain_config.py` | Paths, models, limits, drive detection |
| `memory_store.py` | SQLite CRUD for memories, customers, knowledge, tasks |
| `embeddings.py` | Ollama embedding generation + cosine similarity search |
| `local_llm.py` | Ollama client for summarize, classify, triage |
| `context_builder.py` | Assembles memory context for cloud LLM calls |
| `conversation_tracker.py` | Auto-summarize conversations after threshold |

---

## 6. Implementation Phases

### Phase 1 — Foundation ✅
- Install Ollama, pull models to external drive
- Create brain directory structure on BACKUP11
- Create startup script (start_brain.sh)
- Build all brain service Python modules
- Seed foundational knowledge (27 memories + 10 knowledge entries)

### Phase 2 — Context Integration
- Wire context_builder into MAX chat endpoint
- Auto-summarize conversations after 10 messages
- Semantic search with nomic-embed-text embeddings

### Phase 3 — Intelligence
- Task extraction from conversations
- Telegram message triage via local LLM
- Customer memory auto-tracking
- Morning briefing from brain

### Phase 4 — Advanced
- sqlite-vec for fast vector search
- Memory importance decay
- Cross-conversation learning
- Proactive suggestions
