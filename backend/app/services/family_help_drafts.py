"""On-demand Max drafts for family requests.

Nothing here sends, saves, or writes help.db. Generate is founder-tap only.
Uses Max's included MiniMax path — never on-demand billed models
(Claude / Grok / OpenAI / Cursor).
"""
from __future__ import annotations

import os
import re
from typing import Awaitable, Callable, Optional

from app.services.family_help_store import EDITION_WHO, HELP_EDITIONS
from app.services.max.ui_map import (
    UiFeature,
    feature_href,
    feature_markdown_link,
    feature_open_label,
    feature_where,
    features_for_edition,
    lookup_feature,
    render_ui_map_section,
)

INCLUDED_PROVIDER = "minimax"
BILLED_ON_DEMAND = ("claude", "anthropic", "grok", "xai", "openai", "gpt-4", "gpt-5", "cursor")
FORBIDDEN_NAMES = re.compile(r"\b(juan|juancito|camilo|cami)\b", re.I)
STEP_RE = re.compile(r"^\s*(?:\d+[.)]|[-*•])\s+(.*)$")

# Extra Spanish family words → family-safe ui-map ids (PR #116).
FAMILY_HINTS: dict[str, tuple[str, ...]] = {
    "perfil": ("owner", "ai-face", "search"),
    "profile": ("owner", "ai-face", "search"),
    "recado": ("organizer", "tasks"),
    "recados": ("organizer", "tasks"),
    "tarea": ("tasks", "organizer"),
    "tareas": ("tasks", "organizer"),
    "recordatorio": ("organizer", "tasks", "scheduler"),
    "foto": ("organizer", "search"),
    "fotos": ("organizer", "search"),
    "voz": ("talk", "ai-face"),
    "hablar": ("talk", "ai-face"),
    "cara": ("ai-face", "talk"),
    "presentacion": ("presentation-mode", "max-avatar"),
    "presentación": ("presentation-mode", "max-avatar"),
    "ayuda": ("family-help",),
    "buscar": ("search",),
    "memoria": ("memory-bank",),
}

GenerateFn = Callable[[str, str], Awaitable[dict]]


def _under_test() -> bool:
    return bool(
        os.getenv("PYTEST_CURRENT_TEST")
        or os.getenv("EMPIRE_TEST_GUARD_LOG")
        or os.getenv("EMPIRE_TEST_GUARD")
    )


def edition_product(edition: str) -> dict:
    who = EDITION_WHO.get(edition, {"who": "Family", "assistant": edition, "label": edition})
    return {
        "edition": edition,
        "assistant": who["assistant"],
        "who_label": who["label"],
    }


def related_features(text: str, *, limit: int = 6) -> list[UiFeature]:
    """Family-edition screens from the live ui-map that match the request."""
    family_feats = features_for_edition(True)
    by_id = {f.id: f for f in family_feats}
    found: dict[str, UiFeature] = {}

    blob = text or ""
    hit = lookup_feature(blob, family=True)
    if hit:
        found[hit.id] = hit

    lowered = blob.lower()
    for feat in family_feats:
        names = [feat.name, feat.id.replace("-", " "), *feat.aliases_en, *feat.aliases_es]
        for alias in names:
            alias_n = (alias or "").lower().strip()
            if len(alias_n) >= 4 and alias_n in lowered:
                found[feat.id] = feat
                break

    for word, ids in FAMILY_HINTS.items():
        if word in lowered:
            for fid in ids:
                if fid in by_id:
                    found[fid] = by_id[fid]

    if not found and "owner" in by_id:
        found["owner"] = by_id["owner"]
    if "search" in by_id and len(found) < 2:
        found["search"] = by_id["search"]
    return list(found.values())[:limit]


def serialize_feature(feat: UiFeature) -> dict:
    href = feature_href(feat, family=True)
    return {
        "id": feat.id,
        "name": feat.name,
        "href": href,
        "where": feature_where(feat, family=True),
        "label": feature_open_label(feat),
        "link": feature_markdown_link(feat, channel="web", family=True) or f"[{feature_open_label(feat)}]({href})",
    }


def ui_map_for_manual() -> str:
    return render_ui_map_section(family=True)


def strip_family_names(text: str) -> str:
    cleaned = FORBIDDEN_NAMES.sub("manito", text or "")
    cleaned = re.sub(r"(manito)(\s+\1)+", r"\1", cleaned, flags=re.I)
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip()


def ensure_manito(text: str) -> str:
    body = (text or "").strip()
    if not body:
        return "Manito,"
    if re.search(r"\bmanito\b", body, re.I):
        return body
    return f"Manito, {body[0].lower() + body[1:] if body[0].isupper() and not body.startswith('¿') else body}"


def polish_draft(text: str) -> str:
    return ensure_manito(strip_family_names(text))


def inject_screen_links(body: str, features: list[UiFeature]) -> str:
    text = body or ""
    missing = []
    for feat in features:
        href = feature_href(feat, family=True)
        if href and href in text:
            continue
        missing.append(feat)
    if not missing:
        return text
    lines = [text.rstrip(), "", "Pantallas en tu edición:", ""]
    for feat in missing:
        link = feature_markdown_link(feat, channel="web", family=True)
        where = feature_where(feat, family=True)
        lines.append(f"- {feat.name}: {where} {link}".rstrip())
    return "\n".join(lines).strip()


def parse_steps(body: str, features: list[UiFeature]) -> list[dict]:
    steps: list[dict] = []
    for raw in (body or "").splitlines():
        m = STEP_RE.match(raw)
        if not m:
            continue
        line = m.group(1).strip()
        href = None
        label = None
        link_m = re.search(r"\[([^\]]+)\]\((/[^)]+)\)", line)
        if link_m:
            label, href = link_m.group(1), link_m.group(2)
        elif features:
            feat = features[min(len(steps), len(features) - 1)]
            href = feature_href(feat, family=True)
            label = feature_open_label(feat)
        steps.append({"n": len(steps) + 1, "text": line, "href": href, "label": label})
    if steps:
        return steps
    for i, feat in enumerate(features, 1):
        steps.append({
            "n": i,
            "text": f"Abre {feat.name} — {feature_where(feat, family=True)}",
            "href": feature_href(feat, family=True),
            "label": feature_open_label(feat),
        })
    return steps


def _attachment_note(ticket: dict) -> str:
    atts = ticket.get("attachments") or []
    if not atts:
        return "Sin adjuntos."
    parts = []
    for att in atts:
        kind = att.get("kind") or "file"
        name = att.get("filename") or att.get("id") or "adjunto"
        parts.append(f"{kind}: {name}")
    return "; ".join(parts)


def _ticket_context(ticket: dict) -> str:
    product = edition_product(ticket.get("edition") or "")
    return (
        f"Edición: {product['assistant']} ({ticket.get('edition')})\n"
        f"Pedido: {ticket.get('message') or ticket.get('transcript') or ''}\n"
        f"Transcripción: {ticket.get('transcript') or '(ninguna)'}\n"
        f"Adjuntos: {_attachment_note(ticket)}\n"
        f"Tipo: {ticket.get('request_type') or ticket.get('type') or 'adjust'}\n"
    )


def reply_prompts(ticket: dict) -> tuple[str, str]:
    product = edition_product(ticket.get("edition") or "")
    system = (
        "Eres Max, el asistente de Rafael. Redactas un borrador de respuesta "
        "en español para el chat familiar. Reglas estrictas:\n"
        "- Saluda con 'manito'. Nunca uses sus nombres (ni Juan ni Camilo).\n"
        f"- Habla como si escribieras en {product['assistant']}.\n"
        "- Tono cálido, claro, de hermano. 4 a 8 frases.\n"
        "- Basa la respuesta en el pedido, los adjuntos y la edición.\n"
        "- No digas que ya se envió. Esto es solo un borrador.\n"
        "- No uses modelos ni menciones costos."
    )
    user = (
        "Redacta el borrador de respuesta.\n\n"
        + _ticket_context(ticket)
    )
    return system, user


def manual_prompts(ticket: dict, features: list[UiFeature]) -> tuple[str, str]:
    product = edition_product(ticket.get("edition") or "")
    screens = "\n".join(
        f"- {serialize_feature(f)['name']}: {serialize_feature(f)['where']} {serialize_feature(f)['link']}"
        for f in features
    ) or "(usa el mapa vivo de abajo)"
    system = (
        "Eres Max. Redactas un manual paso a paso (how-to) en español para el "
        f"hermano en {product['assistant']}. Reglas:\n"
        "- Empieza saludando con 'manito'. Nunca uses Juan ni Camilo.\n"
        "- Cada paso debe incluir un enlace markdown tocable a la pantalla "
        "correcta de SU edición, tomado SOLO del mapa de pantallas.\n"
        "- No inventes pantallas que no estén en el mapa. No uses "
        "studio.empirebox.store.\n"
        "- Enlaces relativos /?screen=… o /?product=…\n"
        "- Esto es un borrador. No se envía ni se guarda todavía."
    )
    user = (
        "Redacta el manual.\n\n"
        + _ticket_context(ticket)
        + "\nPantallas relacionadas (ui-map):\n"
        + screens
        + "\n\nMapa vivo de la edición familiar:\n"
        + ui_map_for_manual()
    )
    return system, user


def fallback_reply(ticket: dict) -> str:
    product = edition_product(ticket.get("edition") or "")
    ask = (ticket.get("message") or ticket.get("transcript") or "lo que me pediste").strip()
    atts = _attachment_note(ticket)
    extra = "" if atts.startswith("Sin") else f" Vi el adjunto ({atts})."
    return (
        f"Manito, ya vi lo que me pediste en {product['assistant']}: {ask}.{extra} "
        "Lo reviso y te dejo el siguiente paso aquí mismo."
    )


def fallback_manual(ticket: dict, features: list[UiFeature]) -> str:
    product = edition_product(ticket.get("edition") or "")
    ask = (ticket.get("message") or ticket.get("transcript") or "eso que me pediste").strip()
    lines = [
        f"Manito, te dejo el paso a paso en {product['assistant']} para: {ask}",
        "",
    ]
    if not features:
        features = related_features(ask)
    for i, feat in enumerate(features, 1):
        link = feature_markdown_link(feat, channel="web", family=True)
        lines.append(f"{i}. Abre {feat.name} {link}")
        lines.append(f"   {feature_where(feat, family=True)}")
    return "\n".join(lines).strip()


async def call_max_included_model(system: str, user: str) -> dict:
    """Max included MiniMax path. Refuses live calls under test. Never billed models."""
    if _under_test() and not os.getenv("FAMILY_HELP_ALLOW_LIVE_MODEL"):
        raise RuntimeError("included model must be mocked in tests; refusing live call")
    from app.services.max.ai_router import AIMessage, AIModel, ai_router

    resp = await ai_router.chat(
        messages=[AIMessage(role="user", content=user)],
        model=AIModel.MINIMAX,
        system_prompt=system,
        source="family-help-draft",
        tenant_id="founder",
    )
    used = (resp.model_used or "").lower()
    if any(tag in used for tag in BILLED_ON_DEMAND):
        raise RuntimeError(f"refusing on-demand billed model {resp.model_used}")
    if resp.provider_unavailable:
        raise RuntimeError("included model unavailable")
    return {
        "text": resp.content or "",
        "model_used": resp.model_used or INCLUDED_PROVIDER,
        "included": True,
    }


async def generate_reply(ticket: dict, *, generate_fn: Optional[GenerateFn] = None) -> dict:
    system, user = reply_prompts(ticket)
    fn = generate_fn or call_max_included_model
    raw = await fn(system, user)
    text = polish_draft((raw or {}).get("text") or fallback_reply(ticket))
    return {
        "kind": "reply",
        "title": None,
        "body": text,
        "steps": [],
        "screens": [],
        "edition": ticket.get("edition"),
        "ticket_id": ticket.get("id"),
        "model_used": (raw or {}).get("model_used") or INCLUDED_PROVIDER,
        "included_model": True,
        "would_send": False,
        "saved": False,
    }


async def generate_manual(ticket: dict, *, generate_fn: Optional[GenerateFn] = None) -> dict:
    features = related_features(
        " ".join(
            [
                ticket.get("message") or "",
                ticket.get("transcript") or "",
                ticket.get("summary") or "",
            ]
        )
    )
    system, user = manual_prompts(ticket, features)
    fn = generate_fn or call_max_included_model
    raw = await fn(system, user)
    body = polish_draft((raw or {}).get("text") or fallback_manual(ticket, features))
    body = inject_screen_links(body, features)
    steps = parse_steps(body, features)
    ask = (ticket.get("summary") or ticket.get("message") or "Manual").strip()
    title = ask[:80]
    return {
        "kind": "manual",
        "title": title,
        "body": body,
        "steps": steps,
        "screens": [serialize_feature(f) for f in features],
        "edition": ticket.get("edition"),
        "ticket_id": ticket.get("id"),
        "model_used": (raw or {}).get("model_used") or INCLUDED_PROVIDER,
        "included_model": True,
        "would_send": False,
        "saved": False,
    }
