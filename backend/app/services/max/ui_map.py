"""Live Command Center UI map — single source of truth for 'where is X'.

Generated from the real nav / screen / home IDs in:
  empire-command-center/app/components/layout/LeftNav.tsx
  empire-command-center/app/CommandCenterApp.tsx
  empire-command-center/app/components/home3/MaxHome.tsx

Max answers "where is X / how do I open X" from this map. Never grep the
repo, and never read stale build folders (.next, .next.prev, node_modules).

Family editions (AMP / Max-e, Maxine) only see family-safe entries.
Workroom-only screens are omitted from family prompts and lookups.
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
MAX_HOME_PATH = CC_APP / "components" / "home3" / "MaxHome.tsx"
CC_APP_PATH = CC_APP / "CommandCenterApp.tsx"

# Workroom / studio operator surfaces. Family editions must never hear these.
WORKROOM_ONLY_IDS = frozenset({
    "workroom", "craft", "construction", "luxe", "storefront",
    "schedule", "final-docs", "daily-summary",
    "business-profile", "vendorops", "contractor", "lead", "crm", "pay",
    "pricing-studio",
    "drawings", "vision", "recovery",
    "social", "market", "support", "ship",
    "archive", "transcript",
    "platform", "openclaw", "max-continuity", "hardware",
    "relist", "llc", "apost", "assist", "vetforge", "petforge", "dev",
    "jobs", "invoices", "invoice", "quote", "docs", "product-docs",
    "pricing",
})

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
_NOT_APP_FEATURE = re.compile(
    r"\b(?:quote|quotes|estimate|invoice|job|email|inbox mail|pdf|file|attachment|"
    r"nelma|dahlia|marley|est-\d+)\b",
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
            return False


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


def parse_id_set(source: str, const_name: str) -> set[str]:
    block = re.search(
        rf"{re.escape(const_name)}\s*=\s*new Set<string>\(\[([\s\S]*?)\]\)",
        source,
    )
    if not block:
        return set()
    return set(re.findall(r"'([^']+)'", block.group(1)))


def parse_command_center_ids(source: str | None = None) -> dict[str, set[str]]:
    text = source if source is not None else _read(CC_APP_PATH)
    return {
        "products": parse_id_set(text, "NAV_PRODUCT_IDS"),
        "screens": parse_id_set(text, "NAV_SCREEN_IDS"),
    }


def parse_max_home(source: str | None = None) -> list[dict[str, str]]:
    text = source if source is not None else _read(MAX_HOME_PATH)
    out: list[dict[str, str]] = []
    for m in re.finditer(
        r"id:\s*'([^']+)'\s*,\s*label:\s*'([^']+)'\s*,\s*href:\s*'([^']+)'",
        text,
    ):
        out.append({"id": m.group(1), "label": m.group(2), "href": m.group(3)})
    if re.search(r'label="Talk"', text):
        out.append({"id": "talk", "label": "Talk", "href": "/"})
    if re.search(r'data-testid="mh-presentation"', text):
        out.append({
            "id": "presentation-mode",
            "label": "Presentation mode",
            "href": "/?screen=presentation&mode=presentation",
        })
    if re.search(r"<HomeFace", text):
        out.append({"id": "ai-face", "label": "AI face", "href": "/"})
    return out


def _href_for_nav(item: NavItem) -> str:
    if item.kind == "daily-summary":
        return "/?product=owner&screen=dashboard"
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
    if item.kind == "screen" and item.screen:
        return (
            f"Left nav → {group} → {item.name}. Also open {_href_for_nav(item)}."
        )
    return f"Left nav → {group} → {item.name}. Also open {_href_for_nav(item)}."


# Rich directions + EN/ES aliases layered on top of the live nav/home IDs.
# Keys match nav id, home quick id, or overlay id.
_OVERLAYS: dict[str, dict] = {
    "presentation-mode": {
        "name": "Presentation mode",
        "where": (
            "MAX Home (/) shows the Simli face with Talk and a Presentation mode "
            "button in the hero, next to Talk. Presentation is also in the left "
            "nav: Command → MAX Avatar, and at /?screen=presentation&mode=presentation. "
            "On the Presentation screen, the Presentation / Compact / Text toggle "
            "is at the top of that page."
        ),
        "href": "/?screen=presentation&mode=presentation",
        "aliases_en": (
            "presentation mode", "presentation", "present mode",
            "presentation button", "max avatar", "avatar mode",
        ),
        "aliases_es": (
            "modo presentacion", "modo presentación", "presentacion",
            "presentación", "boton de presentacion", "botón de presentación",
        ),
        "workroom_only": False,
        "source_ids": ("presentation-mode", "max-avatar", "presentation", "avatar"),
    },
    "ai-face": {
        "name": "AI face (Simli)",
        "where": (
            "MAX Home (/) shows the Simli AI face in the hero orb. Tap the face "
            "to start it. Talk on that same hero starts the face with voice. "
            "The face is also on the Presentation screen "
            "(/?screen=presentation)."
        ),
        "href": "/",
        "aliases_en": (
            "ai face", "the ai face", "face", "avatar", "simli", "simli face",
            "talking head", "talkinghead", "max face", "the face",
        ),
        "aliases_es": (
            "cara de ia", "cara ia", "cara", "avatar", "simli", "cara de simli",
            "cara de max", "la cara",
        ),
        "workroom_only": False,
        "source_ids": ("ai-face", "max-avatar", "presentation"),
    },
    "talk": {
        "name": "Talk",
        "where": (
            "MAX Home (/) hero: the Talk button sits next to Presentation mode, "
            "under the Simli face. It starts a live voice call and the face."
        ),
        "href": "/",
        "aliases_en": ("talk", "talk button", "voice call", "live voice", "speak"),
        "aliases_es": ("hablar", "boton hablar", "botón hablar", "llamada de voz", "voz"),
        "workroom_only": False,
        "source_ids": ("talk",),
    },
    "max-avatar": {
        "name": "MAX Avatar",
        "where": (
            "Left nav → Command → MAX Avatar, or the MAX Avatar chip on MAX Home. "
            "Opens /?screen=presentation. Presentation mode itself is the "
            "Presentation button on MAX Home (/) next to Talk."
        ),
        "href": "/?screen=presentation",
        "aliases_en": ("max avatar", "avatar screen"),
        "aliases_es": ("avatar de max", "pantalla de avatar"),
        "workroom_only": False,
    },
    "improvements": {
        "name": "Improvements",
        "where": (
            "Left nav → System → Improvements, or MAX Home → Growth → Improvements "
            "(Open). Also /?product=improvements. Ask Max for a change and it "
            "lands here for your Approve tap."
        ),
        "href": "/?product=improvements",
        "aliases_en": ("improvements", "improvement", "change requests", "requests"),
        "aliases_es": ("mejoras", "solicitudes", "pedidos de cambio"),
        "workroom_only": False,
    },
    "family-help": {
        "name": "Family help",
        "where": (
            "Family editions (Max-e / Maxine): left nav → Ayuda, or /ayuda. "
            "Studio/founder: Command → Family help inbox at /?screen=family-help "
            "when that screen is on this checkout."
        ),
        "href": "/?screen=family-help",
        "aliases_en": ("family help", "help inbox", "ayuda", "help"),
        "aliases_es": ("ayuda familiar", "ayuda", "ayuda de la familia", "buzon de ayuda"),
        "workroom_only": False,
        "source_ids": ("family-help", "ayuda"),
    },
    "minimax-usage": {
        "name": "MiniMax usage",
        "where": (
            "Studio/founder: left nav → System → Tokens & Costs "
            "(/?product=tokens or /?screen=costs) — MiniMax and other model "
            "usage live on that page. Family editions: MiniMax usage "
            "(/?screen=minimax-usage) when that screen is on the checkout; "
            "otherwise Tokens & Costs."
        ),
        "href": "/?product=tokens",
        "aliases_en": (
            "minimax usage", "minimax", "token usage", "tokens", "usage",
            "costs", "token meter",
        ),
        "aliases_es": (
            "uso minimax", "uso de minimax", "uso de tokens", "tokens",
            "consumo", "costos",
        ),
        "workroom_only": False,
        "source_ids": ("tokens", "minimax-usage"),
    },
    "tokens": {
        "name": "Tokens & Costs",
        "where": (
            "Left nav → System → Tokens & Costs. Opens /?product=tokens "
            "(costs screen). MiniMax usage is on this page."
        ),
        "href": "/?product=tokens",
        "aliases_en": ("tokens & costs", "tokens and costs", "cost tracker"),
        "aliases_es": ("tokens y costos", "costos"),
        "workroom_only": False,
    },
    "organizer": {
        "name": "Organizer",
        "where": (
            "MAX Home (/) → Today has reminders and the Tasks link. Full list: "
            "home chip or /?screen=tasks."
        ),
        "href": "/?screen=tasks",
        "aliases_en": ("organizer", "organiser", "photo organizer", "tasks list"),
        "aliases_es": ("organizador", "organizador de fotos", "tareas"),
        "workroom_only": False,
        "source_ids": ("tasks", "organizer"),
    },
    "scheduler": {
        "name": "Scheduler",
        "where": (
            "MAX Home (/) → Today → Schedule (job dates for the next 7 days). "
            "Tasks and reminders: /?screen=tasks."
        ),
        "href": "/",
        "aliases_en": ("scheduler", "schedule", "calendar", "today schedule"),
        "aliases_es": ("agenda", "calendario", "horario", "programador"),
        "workroom_only": False,
        "source_ids": ("scheduler",),
    },
    "schedule": {
        "name": "Schedule Control",
        "where": (
            "Left nav → Command → Schedule Control. Opens /?screen=calendar "
            "(pickup / drop-off log and scheduled events). Workroom operator "
            "screen — family editions do not see this; they use Today on MAX Home."
        ),
        "href": "/?screen=calendar",
        "aliases_en": ("schedule control", "pickup log", "drop-off log"),
        "aliases_es": ("control de agenda", "registro de recogida"),
        "workroom_only": True,
    },
    "owner": {
        "name": "Owner's Desk / Max chat",
        "where": "MAX Home ask bar, or left nav → Command → Owner's Desk (/?product=owner) opens Max chat.",
        "href": "/?product=owner",
        "aliases_en": ("max chat", "owner's desk", "chat", "ask max"),
        "aliases_es": ("chat de max", "escritorio del dueño", "preguntar a max"),
        "workroom_only": False,
    },
    "video": {
        "name": "Video Call",
        "where": "MAX Home quick actions, or left nav → More → Video Call. Opens /?screen=video.",
        "href": "/?screen=video",
        "aliases_en": ("video call", "video"),
        "aliases_es": ("videollamada", "video"),
        "workroom_only": False,
    },
    "telegram": {
        "name": "Telegram",
        "where": "MAX Home quick actions, or left nav → More → Telegram. Opens /?screen=telegram.",
        "href": "/?screen=telegram",
        "aliases_en": ("telegram",),
        "aliases_es": ("telegram",),
        "workroom_only": False,
    },
    "memory-bank": {
        "name": "Memory Bank",
        "where": "MAX Home quick actions, or left nav → More → Memory Bank. Opens /?screen=memory-bank.",
        "href": "/?screen=memory-bank",
        "aliases_en": ("memory bank", "memory"),
        "aliases_es": ("banco de memoria", "memoria"),
        "workroom_only": False,
    },
    "tasks": {
        "name": "Tasks",
        "where": "MAX Home quick actions or Today → Tasks. Opens /?screen=tasks.",
        "href": "/?screen=tasks",
        "aliases_en": ("tasks", "to-dos", "todo"),
        "aliases_es": ("tareas", "pendientes"),
        "workroom_only": False,
    },
    "research": {
        "name": "Research desk",
        "where": "MAX Home top tabs → Research, or the Research desk chip (/?screen=research).",
        "href": "/?screen=research",
        "aliases_en": ("research", "research desk"),
        "aliases_es": ("investigacion", "investigación"),
        "workroom_only": False,
    },
    "search": {
        "name": "Search",
        "where": (
            "Search is on MAX Home and every Command Center screen, desktop and phone. "
            "Tap the search control in the top band or press Ctrl/⌘+K. "
            "It searches screens (including Improvements, Tokens, Family help, "
            "Organizer, MiniMax usage, Presentation), jobs, quotes, invoices, "
            "people, files, organizer items, pending email, and chat memory. "
            "Results group by type. Enter opens the top hit. Draft reply goes "
            "to the approval queue — nothing is sent without your tap."
        ),
        "where_family": (
            "Search is on MAX Home and every screen, desktop and phone. "
            "Tap the search control or press Ctrl/⌘+K. It finds screens and "
            "your own records only — never Workroom jobs or another edition's data."
        ),
        "href": "/",
        "aliases_en": (
            "search", "search bar", "search anything", "quick switch",
            "command k", "cmd k", "ctrl k", "header search", "universal search",
        ),
        "aliases_es": (
            "buscador", "barra de busqueda", "barra de búsqueda", "buscar",
            "busqueda", "búsqueda", "quick switch",
        ),
        "workroom_only": False,
        "source_ids": ("search",),
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


def build_ui_map(
    nav_items: list[NavItem] | None = None,
    home_items: list[dict[str, str]] | None = None,
) -> list[UiFeature]:
    """Build the live map from current LeftNav + MaxHome, plus overlays."""
    nav_items = nav_items if nav_items is not None else parse_left_nav()
    home_items = home_items if home_items is not None else parse_max_home()
    features: list[UiFeature] = []
    seen: set[str] = set()

    for item in nav_items:
        wid = item.id in WORKROOM_ONLY_IDS
        feat = UiFeature(
            id=item.id,
            name=item.name,
            where=_default_where(item),
            href=_href_for_nav(item),
            aliases_en=(item.name.lower(), item.id.replace("-", " ")),
            aliases_es=(),
            workroom_only=wid,
            group=item.group,
            source_ids=(item.id, item.screen) if item.screen else (item.id,),
        )
        if item.id in _OVERLAYS:
            feat = _merge_overlay(feat, _OVERLAYS[item.id])
        features.append(feat)
        seen.add(item.id)

    extras = [
        "presentation-mode", "ai-face", "talk", "family-help",
        "minimax-usage", "organizer", "scheduler", "search",
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
            group="home",
            source_ids=tuple(ov.get("source_ids") or (key,)),
            where_family=ov.get("where_family") or "",
        ))
        seen.add(key)

    # Home quick chips that are not already nav ids.
    for home in home_items:
        hid = home["id"]
        if hid in seen or hid in {"avatar", "presentation", "memory"}:
            continue
        features.append(UiFeature(
            id=hid,
            name=home["label"],
            where=f"MAX Home (/) quick actions → {home['label']}. Opens {home['href']}.",
            href=home["href"],
            aliases_en=(home["label"].lower(), hid.replace("-", " ")),
            workroom_only=hid in WORKROOM_ONLY_IDS,
            group="home",
            source_ids=(hid,),
        ))
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
    if alias.startswith(q):
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
    try:
        from app.services.max.doc_links import is_spoken_channel
        return is_spoken_channel(channel)
    except Exception:
        return (channel or "").strip().lower() in {"voice", "telegram", "phone", "sms"}


def _link_base(family: bool) -> str:
    """Public origin for web links. Family never gets studio.empirebox.store."""
    try:
        from app.services.max.doc_links import public_base
        base = public_base() or ""
    except Exception:
        base = ""
    if family and "studio.empirebox.store" in base.lower():
        return ""
    return base.rstrip("/")


def feature_href(feat: UiFeature, *, family: bool | None = None) -> str:
    family = is_family_edition() if family is None else family
    if family and feat.id == "family-help":
        return "/ayuda"
    return feat.href or "/"


def feature_open_label(feat: UiFeature) -> str:
    name = feat.name.split("(")[0].strip()
    if feat.id == "search":
        return "Open Command Center"
    if feat.id == "presentation-mode":
        return "Open Presentation"
    if feat.id == "ai-face":
        return "Open MAX Home"
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
    """Clickable deep link for web; empty on voice/Telegram (PR #105).

    In-app chat uses a relative /? link so ChatMarkdown can open it same-origin.
    Other text channels may use this edition's public host — never studio on family.
    """
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
    """Drop /? deep links from spoken copy (PR #105). Keep 'MAX Home (/)'."""
    out = re.sub(r"/\?[\w.&=%-]+", "", where)
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
    if link:
        return f"{feat.name}: {where} {link}"
    return f"{feat.name}: {where}"


def is_find_in_app_request(text: str) -> bool:
    """True for 'where is X / how do I open X' about an app surface — not quotes/files."""
    t = (text or "").strip()
    if not t or len(t) > 160:
        return False
    if not _FIND_CUE.search(t):
        return False
    if _DOC_WORDS.search(t):
        return False
    if _NOT_APP_FEATURE.search(t) and not lookup_feature(t):
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
        "I answer that from the live UI map, not from repo search. "
        "Tell me the screen name (for example Presentation mode, Talk, "
        "the AI face, Improvements, Family help, MiniMax usage, Organizer, "
        "or the scheduler) and I'll say exactly where it is."
    )


def render_ui_map_section(family: bool | None = None) -> str:
    family = is_family_edition() if family is None else family
    lines = [
        "",
        "=== LIVE UI MAP (where things are in the app — single source of truth) ===",
        "Answer 'where is X / how do I open X / dónde está X' from this map only.",
        "Call find_in_app if you need a lookup. NEVER use shell_execute, grep, rg,",
        "find, file_read, or repo search for these questions. NEVER search",
        ".next, .next.prev, node_modules, talkinghead build files, or minified JS —",
        "those are stale and have already produced wrong answers (a fake gold",
        "lower-left Presentation button; 'no verified Presentation Mode button').",
        "Truth since PR #108: MAX Home (/) shows the Simli face with Talk and",
        "Presentation buttons; Presentation is also in the left nav (MAX Avatar).",
        "Every where-is answer MUST include a markdown deep link like",
        "[Open Presentation](/?screen=presentation) so ChatMarkdown makes it clickable.",
        "Web: relative /? links (or this edition's public host). Family editions",
        "never use studio.empirebox.store. Voice and Telegram: no URLs at all.",
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
            "open X' use the live UI map / find_in_app."
        )
    if find_it and is_repo_search_command(command):
        return (
            "Blocked: 'where is X / how do I open X' is answered from the live "
            "UI map (find_in_app). Do not grep the repo."
        )
    return None


def live_source_ids() -> dict[str, set[str]]:
    """IDs currently declared in the frontend sources (for drift tests)."""
    nav = {i.id for i in parse_left_nav()}
    home = {h["id"] for h in parse_max_home()}
    cc = parse_command_center_ids()
    return {
        "nav": nav,
        "home": home,
        "products": cc["products"],
        "screens": cc["screens"],
    }
