"""Persist owner-stated facts for Max-e / Maxine across conversations.

Main Max recalls Workroom memory via the brain store. Family editions must
not read that file. Owner facts (business name, preferences) go under
``EMPIRE_DATA_DIR`` — ``assistant/memory.md`` and ``facts.json`` — and are
injected into the family system prompt so a new ``conversation_id`` still
sees them.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from app.edition import assistant_memory_path, is_family_edition


_RECALL_QUESTION_RE = re.compile(
    r"(?is)^\s*(?:nueva\s+sesi[oó]n[.\s]*)?"
    r"(?:cu[aá]l|c[oó]mo|what|what'?s)\s+"
    r"(?:es|se\s+llama|is|was)\b"
)

_SECRETISH_RE = re.compile(
    r"(?i)\b("
    r"password|passwd|contrase[nñ]a|pin\b|token|api[_-]?key|secret|bearer"
    r"|postdeploy|remember\s+this\s+code"
    r")\b"
)

_COMPANY_RE = re.compile(
    r"(?i)(?:mi|nuestra|nuestro)\s+"
    r"(?:empresa|negocio|compa[nñ][ií]a|company)\s+"
    r"se\s+llama\s+[:\s]*([^\n.]+)"
)
_COMPANY_EN_RE = re.compile(
    r"(?i)(?:my|our)\s+company\s+(?:is\s+called|is\s+named)\s+[:\s]*([^\n.]+)"
)
_REMEMBER_RE = re.compile(
    r"(?i)(?:recuerd[ae]|remember(?:\s+that)?|ten\s+en\s+cuenta\s+que|"
    r"guarda(?:\s+que)?)\s*:?\s+(.+)"
)
_PREF_RE = re.compile(
    r"(?i)(?:prefiero|mi\s+preferencia\s+es|siempre\s+(?:responde|usa|habla)|"
    r"nunca\s+(?:env[ií]es|uses|publica))\s+(.+)"
)


def _clean_value(raw: str) -> str:
    value = (raw or "").strip().strip(" \"'«»“”")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[.。]+$", "", value).strip()
    return value[:200]


def _looks_secret(text: str) -> bool:
    return bool(_SECRETISH_RE.search(text or ""))


def extract_user_stated_facts(message: str) -> list[dict]:
    """Pull business-name / remember-that / preference facts from one turn."""
    raw = (message or "").strip()
    if not raw or _RECALL_QUESTION_RE.search(raw) or _looks_secret(raw):
        return []
    found: list[dict] = []
    seen: set[str] = set()

    def add(key: str, label: str, value: str) -> None:
        cleaned = _clean_value(value)
        if len(cleaned) < 2 or key in seen:
            return
        if _looks_secret(cleaned):
            return
        seen.add(key)
        found.append({
            "key": key,
            "label": label,
            "value": cleaned,
            "text": f"{label}: {cleaned}",
        })

    company = _COMPANY_RE.search(raw) or _COMPANY_EN_RE.search(raw)
    if company:
        add("trade_name", "Nombre comercial", company.group(1))

    remember = _REMEMBER_RE.search(raw)
    if remember:
        clause = remember.group(1).strip()
        nested = _COMPANY_RE.search(clause) or _COMPANY_EN_RE.search(clause)
        if nested:
            add("trade_name", "Nombre comercial", nested.group(1))
        elif not company:
            slug = re.sub(r"[^a-z0-9]+", "-", clause.casefold())[:40].strip("-") or "note"
            add(f"note:{slug}", "Dato del dueño", clause)

    pref = _PREF_RE.search(raw)
    if pref:
        add("preference", "Preferencia", pref.group(1))

    return found


def _append_memory_md(lines: list[str]) -> None:
    path = assistant_memory_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    additions = []
    for line in lines:
        if line and line not in existing:
            additions.append(f"- {stamp}: {line}")
    if not additions:
        return
    prefix = existing.rstrip() + "\n\n" if existing.strip() else "# Memoria\n\n"
    path.write_text(prefix + "\n".join(additions) + "\n", encoding="utf-8")


def invalidate_family_prompt_cache() -> None:
    try:
        from app.services.max.system_prompt import _prompt_cache

        _prompt_cache["prompt"] = None
        _prompt_cache["expires"] = 0
        _prompt_cache["_brain_ctx"] = None
        _prompt_cache["_brain_expires"] = 0
    except Exception:
        pass


def persist_user_stated_facts(message: str) -> list[dict]:
    """Write owner facts under this edition's data root. No-op on Workroom."""
    try:
        if not is_family_edition():
            return []
    except Exception:
        return []
    facts = extract_user_stated_facts(message)
    if not facts:
        return []
    from app.services.edition_facts import upsert_fact

    saved = []
    texts = []
    for item in facts:
        row = upsert_fact(
            key=item["key"],
            text=item["text"],
            value=item["value"],
            label=item["label"],
            source="chat",
            visibility="confidential",
        )
        saved.append(row)
        texts.append(item["text"])
    _append_memory_md(texts)
    invalidate_family_prompt_cache()
    return saved


def family_memory_prompt_block() -> str:
    """Facts + memory.md for the family system prompt (this instance only)."""
    try:
        if not is_family_edition():
            return ""
    except Exception:
        return ""
    lines: list[str] = []
    try:
        from app.services.edition_facts import list_facts

        for fact in list_facts():
            text = (fact.get("text") or "").strip()
            if text and text not in lines:
                lines.append(f"- {text}")
    except Exception:
        pass
    try:
        path = assistant_memory_path()
        if path.is_file():
            body = path.read_text(encoding="utf-8").strip()
            if body:
                lines.append(body[:2500])
    except Exception:
        pass
    if not lines:
        return ""
    return (
        "=== MEMORIA PERSISTENTE (todas las conversaciones) ===\n"
        "Estos hechos los dijo el dueño y viven en la memoria de esta instancia. "
        "Úsalos en conversaciones nuevas. Nunca digas que los guardarás solo "
        "para esta conversación o que no hay memoria persistente.\n"
        + "\n".join(lines)
    )


def persist_last_user_message(messages) -> None:
    """Best-effort persist from a chat message list (router / ai_router)."""
    if not messages:
        return
    text = ""
    if isinstance(messages, str):
        text = messages
    else:
        for item in reversed(list(messages)):
            role = getattr(item, "role", None)
            if role is None and isinstance(item, dict):
                role = item.get("role")
            content = getattr(item, "content", None)
            if content is None and isinstance(item, dict):
                content = item.get("content")
            if (role or "") == "user" and content:
                text = str(content)
                break
    if text:
        persist_user_stated_facts(text)
