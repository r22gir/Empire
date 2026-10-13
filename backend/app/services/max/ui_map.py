"""Live Command Center screen-path map — single source of truth for 'where is X'.

Built from the real IDs in:
  empire-command-center/app/components/layout/LeftNav.tsx
  empire-command-center/app/components/layout/QuickSwitch.tsx
  empire-command-center/app/page.tsx
  empire-command-center/app/lib/types.ts

Max answers "where is X / how do I open X" from this map. Never grep the
repo, and never read stale build folders (.next, .next.prev, node_modules).

Every web reply includes a markdown deep link so ChatScreen can make it tappable.
"""
from __future__ import annotations

import re
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Set for the duration of a chat turn so shell_execute can see the question.
_CURRENT_USER_MESSAGE: ContextVar[str] = ContextVar("max_ui_map_user_message", default="")

REPO_ROOT = Path(__file__).resolve().parents[4]
CC_APP = REPO_ROOT / "empire-command-center" / "app"
LEFT_NAV_PATH = CC_APP / "components" / "layout" / "LeftNav.tsx"
QUICK_SWITCH_PATH = CC_APP / "components" / "layout" / "QuickSwitch.tsx"
PAGE_PATH = CC_APP / "page.tsx"
TYPES_PATH = CC_APP / "lib" / "types.ts"

BUILD_DIR_RE = re.compile(
    r"(?:^|[/'\"\s])(?:\.next(?:\.prev)?|node_modules)(?:[/'\"\s]|$)",
    re.I,
)
SEARCH_CMD_RE = re.compile(
    r"(?:^|[;&|]\s*)(?:grep|rg|ag|ack|find)\b",
    re.I,
)

_FIND_CUE = re.compile(
    r"\b(?:"
    r"where(?:'s| is| are| do i| can i)?|"
    r"wheres|"
    r"how do i (?:open|find|get(?: to)?|reach|see|start|use)|"
    r"how (?:can|do) i (?:open|find|get(?: to)?|reach)|"
    r"d[oó]nde(?: est[aá]| queda| encuentro| abro| est[aá]n)?|"
    r"donde(?: esta| queda| encuentro| abro| estan)?|"
    r"c[oó]mo (?:abro|encuentro|llego|abir|abrir|encuentro)|"
    r"como (?:abro|encuentro|llego|abrir)|"
    r"show me (?:how to open|where)|"
    r"link to"
    r")\b",
    re.I,
)
# Named/record lookups ("where is Marley's last quote") are not screen questions.
_RECORD_LOOKUP = re.compile(
    r"\b(?:last|latest|recent|newest|previous)\b.+\b(?:quote|quotes|estimate|invoice|job)s?\b"
    r"|\b(?:quote|estimate|invoice|job)s?\b.+\b(?:for|from|of)\s+[A-Za-z]"
    r"|\best-\d+"
    r"|\b(?:nelma|dahlia|marley)\b",
    re.I,
)
_DOC_WORDS = re.compile(r"\b(?:docs|documents|document|finals|paperwork)\b", re.I)


@dataclass(frozen=True)
class UiFeature:
    id: str
    name: str
    where: str
    href: str
    aliases_en: tuple[str, ...] = ()
    aliases_es: tuple[str, ...] = ()
    workroom_only: bool = False
    group: str = ""
    source_ids: tuple[str, ...] = ()
    extra: str = ""
    where_family: str = ""


@dataclass
class NavItem:
    id: str
    name: str
    group: str
    screen: str = ""
    kind: str = "product"


def set_current_user_message(message: str | None):
    return _CURRENT_USER_MESSAGE.set(message or "")


def reset_current_user_message(token) -> None:
    try:
        _CURRENT_USER_MESSAGE.reset(token)
    except Exception:
        pass


def current_user_message() -> str:
    return _CURRENT_USER_MESSAGE.get() or ""


def is_family_edition() -> bool:
    try:
        from app.services.max.chat_style import _is_family
        return bool(_is_family())
    except Exception:
        try:
            from app.services.max.founder_session import is_family_edition as _fe
            return bool(_fe())
        except Exception:
            edition = ( __import__("os").getenv("EMPIRE_EDITION") or "").strip().lower()
            return edition in {"amp", "max-e", "maxe", "maxine", "family"}


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def parse_left_nav(source: str | None = None) -> list[NavItem]:
    text = source if source is not None else _read(LEFT_NAV_PATH)
    items: list[NavItem] = []
    group = ""
    for raw in text.splitlines():
        g = re.search(r"key:\s*'([^']+)'", raw)
        if g and "label:" not in raw:
            group = g.group(1)
        m = re.search(r"id:\s*'([^']+)'\s*,\s*name:\s*['\"]([^'\"]+)['\"]", raw)
        if not m:
            continue
        screen_m = re.search(r"screen:\s*'([^']+)'", raw)
        kind_m = re.search(r"kind:\s*'([^']+)'", raw)
        items.append(NavItem(
            id=m.group(1),
            name=m.group(2),
            group=group or "nav",
            screen=(screen_m.group(1) if screen_m else ""),
            kind=(kind_m.group(1) if kind_m else "product"),
        ))
    return items


def parse_quick_switch(source: str | None = None) -> list[dict[str, str]]:
    text = source if source is not None else _read(QUICK_SWITCH_PATH)
    out: list[dict[str, str]] = []
    for m in re.finditer(
        r"label:\s*'([^']+)'\s*,\s*shortcut:\s*'([^']+)'\s*,\s*screen:\s*'([^']+)'",
        text,
    ):
        out.append({"label": m.group(1), "shortcut": m.group(2), "screen": m.group(3)})
    return out


def parse_screen_modes(source: str | None = None) -> set[str]:
    text = source if source is not None else _read(TYPES_PATH)
    block = re.search(r"export type ScreenMode = ([^;]+);", text)
    if not block:
        return set()
    return set(re.findall(r"'([^']+)'", block.group(1)))


def parse_product_ids(source: str | None = None) -> set[str]:
    text = source if source is not None else _read(TYPES_PATH)
    block = re.search(r"export type EcosystemProduct = ([^;]+);", text)
    if not block:
        return set()
    return set(re.findall(r"'([^']+)'", block.group(1)))


def parse_deep_link_keys(source: str | None = None) -> set[str]:
    """Keys declared in page.tsx SCREEN_DEEP_LINKS / PRODUCT_DEEP_LINKS."""
    text = source if source is not None else _read(PAGE_PATH)
    keys: set[str] = set()
    for const_name in ("SCREEN_DEEP_LINKS", "PRODUCT_DEEP_LINKS"):
        block = re.search(rf"{const_name}[^=]*=\s*\{{([\s\S]*?)\}};", text)
        if not block:
            continue
        keys.update(re.findall(r"'([^']+)'\s*:", block.group(1)))
        keys.update(re.findall(r"^\s*([A-Za-z][\w-]*)\s*:", block.group(1), re.M))
    return keys


def _href_for_nav(item: NavItem) -> str:
    if item.kind == "daily-summary":
        return "/?product=owner"
    if item.kind == "screen" and item.screen:
        return f"/?screen={item.screen}"
    return f"/?product={item.id}"


def _default_where(item: NavItem) -> str:
    group = item.group.replace("-", " ").title() if item.group else "left nav"
    if item.kind == "daily-summary":
        return (
            f"Left nav → Command → {item.name}. It opens the Daily Summary side panel "
            f"(not a separate page)."
        )
    return f"Left nav → {group} → {item.name}."


# Rich directions + EN/ES aliases layered on top of the live nav/quick-switch IDs.
_OVERLAYS: dict[str, dict] = {
    "presentation-mode": {
        "name": "Presentation mode",
        "where": (
            "Open Quick Switch (⌘K / Ctrl+K) and choose MAX Avatar (shortcut M), "
            "or tap [Open Presentation](/?screen=presentation&mode=presentation). "
            "That opens the MAX Avatar / Presentation screen. "
            "On that screen the Presentation / Compact / Text toggle is at the top. "
            "Do not use the stale .next.prev talkinghead answer (a gold corner button "
            "that is not on this checkout)."
        ),
        "href": "/?screen=presentation&mode=presentation",
        "aliases_en": (
            "presentation mode", "presentation", "present mode",
            "presentation button", "max avatar", "avatar mode",
            "ai face", "the ai face", "simli", "talking head",
        ),
        "aliases_es": (
            "modo presentacion", "modo presentación", "presentacion",
            "presentación", "boton de presentacion", "botón de presentación",
            "avatar de max",
        ),
        "workroom_only": False,
        "source_ids": ("presentation-mode", "presentation", "max-avatar"),
    },
    "organizer": {
        "name": "Organizer",
        "where": (
            "Left nav → Command → Organizer. Founder task/planner "
            "(spaces, today board, follow-ups) at /api/v1/organizer/*. "
            "Screen route is /?screen=calendar. Themes switch with "
            "?orgTheme=a|b|c. This is not the AI Vision photo queue."
        ),
        "href": "/?screen=calendar",
        "aliases_en": (
            "organizer", "organiser", "founder organizer",
            "planner", "life organizer",
        ),
        "aliases_es": (
            "organizador", "planificador",
        ),
        "workroom_only": False,
        "source_ids": ("organizer", "schedule", "calendar"),
    },
    "schedule": {
        "name": "Organizer",
        "where": (
            "Left nav → Command → Organizer. Opens /?screen=calendar "
            "(founder planner; /api/v1/organizer/*; orgTheme a|b|c)."
        ),
        "href": "/?screen=calendar",
        "aliases_en": ("schedule", "calendar", "organizer screen"),
        "aliases_es": ("agenda", "calendario"),
        "workroom_only": False,
        "source_ids": ("schedule", "calendar", "organizer"),
    },
    "quotes": {
        "name": "Quotes",
        "where": (
            "Left nav → Command → Empire Workroom → Quotes (New Quote / Open Quotes). "
            "Daily Summary also has a Quotes row. "
            "Quote Review (read existing quotes) is Quick Switch → Quote Review (Q). "
            "Open [Open Quotes](/?product=workroom&section=quotes)."
        ),
        "href": "/?product=workroom&section=quotes",
        "aliases_en": (
            "quotes", "quote builder", "quote page", "workroom quotes",
            "new quote", "open quotes", "estimates", "estimate builder",
        ),
        "aliases_es": (
            "cotizaciones", "cotizacion", "cotización", "presupuestos",
            "constructor de cotizaciones",
        ),
        "workroom_only": True,
        "source_ids": ("quotes", "workroom"),
    },
    "quote-review": {
        "name": "Quote Review",
        "where": (
            "Quick Switch (⌘K) → Quote Review (shortcut Q). "
            "Open [Open Quote Review](/?screen=quote)."
        ),
        "href": "/?screen=quote",
        "aliases_en": ("quote review", "review quotes"),
        "aliases_es": ("revision de cotizaciones", "revisión de cotizaciones"),
        "workroom_only": True,
        "source_ids": ("quote-review", "quote"),
    },
    "tasks": {
        "name": "Tasks",
        "where": "Quick Switch (⌘K) → Tasks (K), or [Open Tasks](/?screen=tasks).",
        "href": "/?screen=tasks",
        "aliases_en": ("tasks", "to-dos", "todo", "task list"),
        "aliases_es": ("tareas", "pendientes"),
        "workroom_only": False,
    },
    "owner": {
        "name": "Owner's Desk / Max chat",
        "where": "Left nav → Command → Owner's Desk. Opens Max chat. [Open Chat](/?product=owner).",
        "href": "/?product=owner",
        "aliases_en": ("max chat", "owner's desk", "chat", "ask max"),
        "aliases_es": ("chat de max", "escritorio del dueño", "preguntar a max"),
        "workroom_only": False,
    },
    "vision": {
        "name": "AI Vision",
        "where": (
            "Left nav → Tools → AI Vision. Photo Analyzer and the photo "
            "queue (Add Photos) live on that page — not the founder Organizer. "
            "[Open AI Vision](/?product=vision)."
        ),
        "href": "/?product=vision",
        "aliases_en": (
            "ai vision", "vision", "photo analyzer",
            "photo organizer", "photo gallery", "photo queue",
        ),
        "aliases_es": ("vision ia", "visión ia", "galeria de fotos", "galería de fotos"),
        "workroom_only": False,
    },
    "workroom": {
        "name": "Empire Workroom",
        "where": "Left nav → Command → Empire Workroom. [Open Workroom](/?product=workroom).",
        "href": "/?product=workroom",
        "aliases_en": ("empire workroom", "workroom"),
        "aliases_es": ("taller", "workroom"),
        "workroom_only": True,
    },
    "search": {
        "name": "Header search",
        "where": (
            "On Command Center screens the top bar has Search anything… (⌘K). "
            "Click it or press Ctrl/⌘+K to open Quick Switch and jump to a screen "
            "(Chat, MAX Avatar, Dashboard, Tasks, Quote Review, Documents, …). "
            "[Open Command Center](/?product=owner)."
        ),
        "href": "/?product=owner",
        "aliases_en": (
            "search", "search bar", "search anything", "quick switch",
            "command k", "cmd k", "ctrl k", "header search",
        ),
        "aliases_es": (
            "buscador", "barra de busqueda", "barra de búsqueda", "buscar",
        ),
        "workroom_only": False,
        "source_ids": ("search",),
    },
    "tokens": {
        "name": "Tokens & Costs",
        "where": "Left nav → System → Tokens & Costs. [Open Tokens](/?product=tokens).",
        "href": "/?product=tokens",
        "aliases_en": ("tokens & costs", "tokens and costs", "cost tracker", "minimax usage"),
        "aliases_es": ("tokens y costos", "costos"),
        "workroom_only": False,
    },
}


def _merge_overlay(base: UiFeature, overlay: dict) -> UiFeature:
    return UiFeature(
        id=base.id,
        name=overlay.get("name", base.name),
        where=overlay.get("where", base.where),
        href=overlay.get("href", base.href),
        aliases_en=tuple(overlay.get("aliases_en", base.aliases_en)),
        aliases_es=tuple(overlay.get("aliases_es", base.aliases_es)),
        workroom_only=bool(overlay.get("workroom_only", base.workroom_only)),
        group=base.group,
        source_ids=tuple(overlay.get("source_ids", base.source_ids)),
        extra=overlay.get("extra", base.extra),
        where_family=overlay.get("where_family", base.where_family),
    )


def _quick_href(screen: str) -> str:
    if screen == "presentation":
        return "/?screen=presentation&mode=presentation"
    if screen == "workroom-page":
        return "/?product=workroom"
    if screen == "craft-page":
        return "/?product=craft"
    if screen == "platform-page":
        return "/?product=platform"
    if screen in {"recovery", "relist"}:
        return f"/?product={screen}"
    if screen == "apostapp":
        return "/?screen=apostapp"
    return f"/?screen={screen}"


def build_ui_map(
    nav_items: list[NavItem] | None = None,
    quick_items: list[dict[str, str]] | None = None,
) -> list[UiFeature]:
    """Build the live map from current LeftNav + QuickSwitch, plus overlays."""
    nav_items = nav_items if nav_items is not None else parse_left_nav()
    quick_items = quick_items if quick_items is not None else parse_quick_switch()
    features: list[UiFeature] = []
    seen: set[str] = set()

    for item in nav_items:
        feat = UiFeature(
            id=item.id,
            name=item.name,
            where=_default_where(item),
            href=_href_for_nav(item),
            aliases_en=(item.name.lower(), item.id.replace("-", " ")),
            aliases_es=(),
            workroom_only=item.id not in {
                "owner", "amp", "tokens", "system", "openclaw",
                "max-continuity", "daily-summary",
            },
            group=item.group,
            source_ids=(item.id, item.screen) if item.screen else (item.id,),
        )
        if item.id in _OVERLAYS:
            feat = _merge_overlay(feat, _OVERLAYS[item.id])
        features.append(feat)
        seen.add(item.id)

    extras = [
        "presentation-mode", "organizer", "quotes", "quote-review",
        "search", "tasks",
    ]
    for key in extras:
        if key in seen:
            continue
        ov = _OVERLAYS[key]
        features.append(UiFeature(
            id=key,
            name=ov["name"],
            where=ov["where"],
            href=ov["href"],
            aliases_en=tuple(ov.get("aliases_en") or ()),
            aliases_es=tuple(ov.get("aliases_es") or ()),
            workroom_only=bool(ov.get("workroom_only", False)),
            group="overlay",
            source_ids=tuple(ov.get("source_ids") or (key,)),
            where_family=ov.get("where_family") or "",
        ))
        seen.add(key)

    for quick in quick_items:
        sid = quick["screen"]
        qid = sid if sid not in {"presentation", "workroom-page", "quote"} else ""
        if not qid or qid in seen:
            continue
        features.append(UiFeature(
            id=qid,
            name=quick["label"],
            where=(
                f"Quick Switch (⌘K) → {quick['label']} (shortcut {quick['shortcut']}). "
                f"Opens {_quick_href(sid)}."
            ),
            href=_quick_href(sid),
            aliases_en=(quick["label"].lower(), sid.replace("-", " ")),
            workroom_only=sid not in {"chat", "tasks", "docs", "research", "video", "telegram"},
            group="quick-switch",
            source_ids=(sid,),
        ))
        seen.add(qid)
    return features


def features_for_edition(family: bool | None = None) -> list[UiFeature]:
    family = is_family_edition() if family is None else family
    items = build_ui_map()
    if family:
        return [f for f in items if not f.workroom_only]
    return items


def _norm(text: str) -> str:
    t = (text or "").lower().strip()
    t = t.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    t = t.replace("ñ", "n").replace("ü", "u")
    t = re.sub(r"[?!¿¡.,;:]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _aliases(feat: UiFeature) -> list[str]:
    names = [feat.name, feat.id.replace("-", " "), *feat.aliases_en, *feat.aliases_es]
    return [_norm(n) for n in names if n]


def _strip_find_prefix(query: str) -> str:
    q = _norm(query)
    lead = re.compile(
        r"^(where(?:'s| is| are| do i find| do i open| can i find| can i open)?|"
        r"wheres|how do i (?:open|find|get to|reach|see|start|use)|"
        r"donde(?: esta| queda| encuentro| abro)?|"
        r"como (?:abro|encuentro|llego a|abrir)|"
        r"show me|link to|the|el|la|los|las|my|mi|"
        r"en (?:la )?(?:app|aplicacion))\s+"
    )
    for _ in range(4):
        nxt = lead.sub("", q)
        if nxt == q:
            break
        q = nxt
    return re.sub(r"\s+(in the app|en la app|en la aplicacion|button|boton)$", "", q).strip()


def _query_fits_alias(q: str, alias: str) -> bool:
    """Partial query against an alias. 'search' must not match 'research'."""
    if not q or not alias:
        return False
    if alias.startswith(q) or q.startswith(alias):
        return True
    return any(part.startswith(q) for part in alias.split())


def _best_match(query: str, features: list[UiFeature]) -> Optional[UiFeature]:
    q = _strip_find_prefix(query)
    if not q:
        return None
    best: Optional[UiFeature] = None
    best_len = -1
    for feat in features:
        for alias in _aliases(feat):
            if alias and alias in q and len(alias) > best_len:
                best = feat
                best_len = len(alias)
            if alias and _query_fits_alias(q, alias) and len(q) >= 4 and len(q) > best_len:
                best = feat
                best_len = len(q)
    return best


def lookup_feature(query: str, family: bool | None = None) -> Optional[UiFeature]:
    family = is_family_edition() if family is None else family
    if not _norm(query):
        return None
    all_feats = build_ui_map()
    best_all = _best_match(query, all_feats)
    if family and best_all and best_all.workroom_only:
        return None
    return _best_match(query, features_for_edition(family))


def _spoken_channel(channel: str | None) -> bool:
    return (channel or "").strip().lower() in {"voice", "telegram", "phone", "sms"}


def _link_base(family: bool) -> str:
    """Public origin for web links. Family never gets studio.empirebox.store."""
    import os
    base = (os.getenv("EMPIRE_PUBLIC_BASE_URL") or os.getenv("PUBLIC_BASE_URL") or "").rstrip("/")
    if family and "studio.empirebox.store" in base.lower():
        return ""
    return base


def feature_href(feat: UiFeature, *, family: bool | None = None) -> str:
    family = is_family_edition() if family is None else family
    return feat.href or "/"


def feature_open_label(feat: UiFeature) -> str:
    name = feat.name.split("(")[0].strip()
    if feat.id == "search":
        return "Open Command Center"
    if feat.id == "presentation-mode":
        return "Open Presentation"
    if feat.id == "organizer":
        return "Open Organizer"
    if feat.id == "quotes":
        return "Open Quotes"
    if feat.id == "quote-review":
        return "Open Quote Review"
    return f"Open {name}"


_IN_APP_CHANNELS = frozenset({
    "", "web", "web_cc", "dashboard", "command_center",
    "studio_browser", "mobile_browser",
})


def feature_markdown_link(
    feat: UiFeature,
    *,
    channel: str | None = None,
    family: bool | None = None,
) -> str:
    """Clickable deep link for web; empty on voice/Telegram."""
    if _spoken_channel(channel):
        return ""
    family = is_family_edition() if family is None else family
    href = feature_href(feat, family=family)
    ch = (channel or "web").strip().lower()
    base = "" if ch in _IN_APP_CHANNELS else _link_base(family)
    url = f"{base}{href}" if base else href
    return f"[{feature_open_label(feat)}]({url})"


def feature_where(feat: UiFeature, *, family: bool | None = None) -> str:
    family = is_family_edition() if family is None else family
    if family and feat.where_family:
        return feat.where_family
    return feat.where


def _spoken_where(where: str) -> str:
    """Drop /? deep links and markdown links from spoken copy."""
    out = re.sub(r"\[[^\]]+\]\([^)]+\)", "", where)
    out = re.sub(r"/\?[\w.&=%-]+", "", out)
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"\s+\.", ".", out)
    return out.strip()


def format_feature_reply(
    feat: UiFeature,
    *,
    channel: str | None = None,
    family: bool | None = None,
) -> str:
    family = is_family_edition() if family is None else family
    where = feature_where(feat, family=family)
    if _spoken_channel(channel):
        return f"{feat.name}: {_spoken_where(where)}"
    link = feature_markdown_link(feat, channel=channel, family=family)
    # Always append the tappable link even if the where-text already mentions it.
    if link and link not in where:
        return f"{feat.name}: {where} {link}"
    if link:
        return f"{feat.name}: {where}"
    return f"{feat.name}: {where}"


def is_find_in_app_request(text: str) -> bool:
    """True for 'where is X / how do I open X' about an app surface — not quote records."""
    t = (text or "").strip()
    if not t or len(t) > 160:
        return False
    if not _FIND_CUE.search(t):
        return False
    if _DOC_WORDS.search(t):
        return False
    if _RECORD_LOOKUP.search(t):
        return False
    return True


def find_in_app_reply(
    text: str,
    family: bool | None = None,
    channel: str | None = None,
) -> Optional[str]:
    if not is_find_in_app_request(text):
        return None
    feat = lookup_feature(text, family=family)
    if feat:
        return format_feature_reply(feat, channel=channel, family=family)
    return (
        "I answer that from the live screen-path map, not from repo search. "
        "Tell me the screen name (for example Presentation mode, Organizer, "
        "or Quotes) and I'll give you a tappable link."
    )


def render_ui_map_section(family: bool | None = None) -> str:
    family = is_family_edition() if family is None else family
    lines = [
        "",
        "=== LIVE SCREEN-PATH MAP (where things are in the app — single source of truth) ===",
        "Answer 'where is X / how do I open X / dónde está X' from this map only.",
        "Call find_in_app if you need a lookup. NEVER use shell_execute, grep, rg,",
        "find, file_read, or repo search for these questions. NEVER search",
        ".next, .next.prev, node_modules, talkinghead build files, or minified JS —",
        "those are stale and have already produced wrong answers (a fake gold",
        "lower-left Presentation button; 'no verified Presentation Mode button').",
        "Every where-is answer MUST include a markdown deep link like",
        "[Open Presentation](/?screen=presentation&mode=presentation) so the chat",
        "renderer makes it tappable. Web: relative /? links. Voice and Telegram: no URLs.",
    ]
    if family:
        lines.append(
            "This is a family edition. Only describe screens listed below. "
            "Do not name or offer Workroom-only operator screens."
        )
    lines.append("")
    for feat in features_for_edition(family):
        aliases = ", ".join(a for a in (*feat.aliases_en[:4], *feat.aliases_es[:3]) if a)
        alias_bit = f" [also: {aliases}]" if aliases else ""
        where = feature_where(feat, family=family)
        href = feature_href(feat, family=family)
        link = feature_markdown_link(feat, family=family)
        lines.append(f"- {feat.name}{alias_bit} — {where} → {link or href}")
    lines.append("")
    return "\n".join(lines)


def is_build_dir_search(command: str) -> bool:
    cmd = command or ""
    if BUILD_DIR_RE.search(cmd):
        return True
    lowered = cmd.lower()
    stale = (".next.prev", ".next/", "/.next", "node_modules/", "node_modules\\")
    searching = bool(SEARCH_CMD_RE.search(cmd) or re.search(r"\b(?:grep|rg)\b", lowered))
    return searching and any(p in lowered for p in stale)


def is_repo_search_command(command: str) -> bool:
    cmd = command or ""
    if SEARCH_CMD_RE.search(cmd):
        return True
    return bool(re.search(r"\b(?:grep|rg|ag)\b", cmd))


def refuse_shell_search(command: str, user_message: str | None = None) -> Optional[str]:
    """Return an error string when shell_execute must not run this search."""
    msg = user_message if user_message is not None else current_user_message()
    find_it = is_find_in_app_request(msg) if msg else False
    if is_build_dir_search(command):
        return (
            "Blocked: do not search .next, .next.prev, node_modules or other "
            "build folders. Those files are stale. For 'where is X / how do I "
            "open X' use the live screen-path map / find_in_app."
        )
    if find_it and is_repo_search_command(command):
        return (
            "Blocked: 'where is X / how do I open X' is answered from the live "
            "screen-path map (find_in_app). Do not grep the repo."
        )
    return None


def live_source_ids() -> dict[str, set[str]]:
    """IDs currently declared in the frontend sources (for drift tests)."""
    nav = {i.id for i in parse_left_nav()}
    quick = {q["screen"] for q in parse_quick_switch()}
    return {
        "nav": nav,
        "quick": quick,
        "screens": parse_screen_modes(),
        "products": parse_product_ids(),
        "deep_links": parse_deep_link_keys(),
    }
