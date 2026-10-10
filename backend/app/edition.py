"""Empire edition selection.

Workroom is the default. Nothing here changes paths, names, or module
visibility unless EMPIRE_EDITION=amp (or ASSISTANT_NAME is set for the
assistant identity only).

The AMP edition is a separate running instance. Its database, uploads,
generated documents, assistant memory, conversation history, and logs
live under EMPIRE_DATA_DIR and must not fall back to Workroom paths.
"""
from __future__ import annotations

import json
import os
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

WORKROOM_EDITION = "workroom"
AMP_EDITION = "amp"
MAXINE_EDITION = "maxine"
# Personal instances that share one codebase: Spanish, own data dir,
# allowlist, usage cap, MiniMax M3. The edition id stays the instance name.
FAMILY_EDITIONS = frozenset({AMP_EDITION, MAXINE_EDITION})

# Workroom display stays "Max" when ASSISTANT_NAME is unset.
# business.json still says "MAX" for older prompt callers; the identity
# helper below is what new code and the AMP instance use.
WORKROOM_ASSISTANT_NAME = "Max"
AMP_ASSISTANT_NAME = "Max-e"
MAXINE_ASSISTANT_NAME = "Maxine"

AMP_COACH_NAME = "Juan Diego Giraldo"
MAXINE_OWNER_NAME = "Camilo Giraldo"

# Display defaults. Ports and hosts are deploy notes, not runtime binds.
EDITION_PROFILES = {
    "workroom": {
        "assistant_default": WORKROOM_ASSISTANT_NAME,
        "locale": "en",
        "primary": "workroom",
        "host": "studio.empirebox.store",
        "backend_port": 8000,
        "frontend_port": 3005,
    },
    "amp": {
        "assistant_default": AMP_ASSISTANT_NAME,
        "locale": "es",
        "primary": "amp",
        "host": "amp.empirebox.store",
        "backend_port": 8011,
        "frontend_port": 3011,
        "data_dir": "/data/amp",
    },
    "maxine": {
        "assistant_default": MAXINE_ASSISTANT_NAME,
        "locale": "es",
        "primary": "construction",
        "host": "maxine.empirebox.store",
        "backend_port": 8012,
        "frontend_port": 3012,
        "data_dir": "/data/maxine",
        "seed": "deploy/seeds/maxine-seed.md",
        "model": "constructionforge",
    },
}

# Hidden in the AMP edition. Shared base modules stay available.
AMP_DISABLED_MODULES = frozenset({
    "workroom",
    "craft",
    "woodcraft",
    "craftforge",
    "luxe",
    "luxeforge",
    "drawings",
    "drawing",
    "custom-shapes",
    "custom_shapes",
    "patterns",
    "pattern_templates",
    "fabrics",
})

# Route prefixes that belong to those hidden modules.
AMP_DISABLED_PREFIXES = (
    "/api/v1/craftforge",
    "/api/v1/drawings",
    "/api/v1/custom-shapes",
    "/api/v1/patterns",
    "/api/v1/fabrics",
    "/api/v1/workroom-capture",
    "/api/luxeforge",
    "/workroom",
)

# Shared base, mapped to coaching on the AMP business and reused as-is
# for any additional blank company Juan creates.
AMP_SHARED_MODULES = (
    "amp",
    "crm",
    "leadforge",
    "socialforge",
    "quotes",
    "invoices",
    "scheduling",
    "finance",
    "max",
)

AMP_MODULE_LABELS_ES = {
    "amp": "AMP — El Portal de la Alegría",
    "crm": "Coachees (CRM)",
    "leadforge": "Ingreso y llamadas de descubrimiento",
    "socialforge": "SocialForge (aprobación antes de publicar)",
    "quotes": "Paquetes y cotizaciones",
    "invoices": "Membresías y facturas",
    "scheduling": "Agenda de sesiones",
    "finance": "Finanzas",
    "max": "Max-e",
}

_ALLOWLIST_EXEMPT = (
    ("GET", "/health"),
    ("GET", "/"),
    ("GET", "/api/v1/edition"),
    # Edition login. These do not trust client identity headers.
    ("POST", "/api/v1/amp/auth/request"),
    ("POST", "/api/v1/amp/auth/verify"),
    ("GET", "/api/v1/amp/auth/magic"),
    ("POST", "/api/v1/amp/auth/logout"),
    # Meta calls this with no login cookie. The route still checks the
    # verify token (GET) and X-Hub-Signature-256 (POST).
    ("GET", "/api/v1/whatsapp/webhook"),
    ("POST", "/api/v1/whatsapp/webhook"),
)

_business_slug: ContextVar[str] = ContextVar("empire_business_slug", default="amp")


class EditionPathError(RuntimeError):
    """A data path escaped the instance data root."""


def edition_name() -> str:
    raw = os.getenv("EMPIRE_EDITION", "").strip().lower()
    return raw or WORKROOM_EDITION


def is_amp() -> bool:
    return edition_name() == AMP_EDITION


def is_maxine() -> bool:
    return edition_name() == MAXINE_EDITION


def is_family_edition() -> bool:
    """A personal instance (Max-e, Maxine, …), not the Workroom."""
    return edition_name() in FAMILY_EDITIONS


def edition_profile() -> dict:
    return dict(EDITION_PROFILES.get(edition_name()) or EDITION_PROFILES["workroom"])


def primary_shell() -> str:
    """What opens first. Maxine is ConstructionForge. Max-e keeps AMP. Workroom stays the owner's desk."""
    profile = edition_profile()
    return str(profile.get("primary") or "workroom")


def app_display_name() -> str:
    """Browser tab and chrome. The assistant name, not a business inside the instance."""
    raw = os.getenv("EDITION_DISPLAY_NAME", "").strip()
    if raw:
        return raw
    if is_family_edition():
        return f"{assistant_name()} · Centro de mando"
    return "Empire Command Center"


def default_locale() -> str:
    """Family editions are Spanish-first. Workroom stays English unless configured."""
    if is_family_edition():
        return os.getenv("EMPIRE_DEFAULT_LOCALE", "es").strip().lower() or "es"
    return os.getenv("EMPIRE_DEFAULT_LOCALE", "en").strip().lower() or "en"


def speech_language() -> str:
    """Language tag for TTS and live voice. Family Spanish is es-CO."""
    loc = default_locale()
    if loc.startswith("es"):
        return "es-CO"
    if loc.startswith("en"):
        return "en"
    return loc or "en"


def assistant_name() -> str:
    """Per-instance display name.

    Unset on Workroom → Max. The AMP env sets ASSISTANT_NAME=Max-e.
    If a family edition leaves the variable empty, the profile default is
    used so this instance cannot speak as the Workroom assistant.
    """
    raw = os.getenv("ASSISTANT_NAME", "").strip()
    if raw:
        return raw
    if is_family_edition():
        return str(edition_profile().get("assistant_default") or AMP_ASSISTANT_NAME)
    return WORKROOM_ASSISTANT_NAME


def prompt_identity_name() -> str:
    """Name used in the system prompt identity line.

    Workroom keeps the historical business.json value ("MAX") when
    ASSISTANT_NAME is unset, so the Workroom prompt does not change.
    """
    if os.getenv("ASSISTANT_NAME", "").strip() or is_family_edition():
        return assistant_name()
    try:
        from app.config.business_config import biz
        return biz.ai_assistant_name
    except Exception:
        return "MAX"


def module_enabled(module_id: str) -> bool:
    if not is_family_edition():
        return True
    return module_id.strip().lower() not in AMP_DISABLED_MODULES


def disabled_module_for_path(path: str) -> Optional[str]:
    if not is_family_edition():
        return None
    clean = path.split("?", 1)[0]
    for prefix in AMP_DISABLED_PREFIXES:
        if clean == prefix or clean.startswith(prefix + "/"):
            return prefix.strip("/").split("/")[-1]
    return None


def data_root_or_none() -> Optional[Path]:
    raw = os.getenv("EMPIRE_DATA_DIR", "").strip()
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def require_data_root() -> Path:
    root = data_root_or_none()
    if root is None:
        raise EditionPathError(
            "Esta edición requiere EMPIRE_DATA_DIR "
            "(la instancia no usa los datos del Workroom)"
        )
    root.mkdir(parents=True, exist_ok=True)
    return root


def assert_under_root(path: Path, root: Optional[Path] = None) -> Path:
    root_path = (root or require_data_root()).resolve()
    resolved = path.expanduser().resolve()
    if resolved != root_path and root_path not in resolved.parents:
        raise EditionPathError(
            f"Ruta fuera del directorio de datos de la instancia: {resolved}"
        )
    return resolved


def active_business_slug() -> str:
    return _business_slug.get() or "amp"


def set_active_business(slug: str):
    cleaned = (slug or "amp").strip().lower() or "amp"
    return _business_slug.set(cleaned)


def reset_active_business(token) -> None:
    _business_slug.reset(token)


def business_dir(slug: str) -> Path:
    """Workspace directory for one company inside this instance."""
    from app.services.amp_businesses import safe_slug
    root = require_data_root()
    path = root / "businesses" / safe_slug(slug)
    return assert_under_root(path, root)


def active_business_root() -> Path:
    return business_dir(active_business_slug())


def _legacy_amp_db() -> Path:
    """Workroom path. Unchanged even when EMPIRE_DATA_DIR is set."""
    return Path(os.path.expanduser("~/empire-repo/backend/data/amp.db"))


def amp_app_dir() -> Path:
    """AMP product files (content db, audio, allowlist).

    The AMP instance uses EMPIRE_DATA_DIR/amp. Workroom keeps the
    historical directory next to amp.db and does not follow EMPIRE_DATA_DIR.
    """
    if is_family_edition():
        root = require_data_root()
        path = root / "amp"
        path.mkdir(parents=True, exist_ok=True)
        return path
    path = _legacy_amp_db().parent / "amp"
    path.mkdir(parents=True, exist_ok=True)
    return path


def amp_sqlite_path() -> Path:
    if is_family_edition():
        return amp_app_dir() / "amp.db"
    path = _legacy_amp_db()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def amp_audio_dir() -> Path:
    path = amp_app_dir() / "audio"
    path.mkdir(parents=True, exist_ok=True)
    return path


def allowlist_path() -> Path:
    return amp_app_dir() / "allowlist.json"


def log_dir() -> Path:
    if is_family_edition():
        path = require_data_root() / "logs"
    else:
        from app.services.data_paths import data_root
        explicit = os.getenv("EMPIRE_LOG_DIR", "").strip()
        path = Path(explicit).expanduser() if explicit else data_root() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def assistant_home() -> Path:
    """Memory, history, and settings for this instance's assistant.

    Workroom (edition unset) keeps using its existing Max paths. This
    directory is only the storage root when the edition is AMP or
    ASSISTANT_NAME is set and EMPIRE_DATA_DIR is set.
    """
    if is_family_edition() or (os.getenv("ASSISTANT_NAME", "").strip() and data_root_or_none()):
        root = require_data_root() if is_family_edition() else data_root_or_none()
        assert root is not None
        path = root / "assistant"
        path.mkdir(parents=True, exist_ok=True)
        return path
    raise EditionPathError("assistant_home() solo aplica a una instancia con directorio de datos")


def assistant_memory_path() -> Path:
    if not is_family_edition() and not os.getenv("ASSISTANT_NAME", "").strip():
        env = os.getenv("MAX_MEMORY_PATH", "").strip()
        if env:
            return Path(env).expanduser()
        # Historical Workroom file. Callers must not write it from AMP code.
        return Path(__file__).resolve().parents[2] / "max" / "memory.md"
    return assistant_home() / "memory.md"


def assistant_settings_path() -> Path:
    return assistant_home() / "settings.json"


def assistant_history_db() -> Path:
    path = assistant_home() / "history"
    path.mkdir(parents=True, exist_ok=True)
    return path / "conversations.db"


def assistant_brain_dir() -> Path:
    path = assistant_home() / "brain"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_persona(name: Optional[str] = None) -> str:
    who = name or assistant_name()
    if is_maxine() or who == MAXINE_ASSISTANT_NAME:
        return (
            f"{who} es la asistente de {MAXINE_OWNER_NAME} para desarrollos "
            "inmobiliarios, construcción y ventas en Cartago y Zaragoza "
            "(Valle del Cauca). La marca comercial de las ventas es GAC. "
            f"{who} no es la dueña. Su centro de mando es ConstructionForge: "
            "proyectos, etapas, lotes, compradores, planes de pago en COP y "
            "avance de obra son un solo registro. Responde en español salvo "
            "que pidan inglés. No inventa precios, áreas ni datos legales. "
            "Lo marcado confidencial no entra en contenido público. "
            "Nada se publica en redes sin aprobación. "
            "No lee ni escribe los datos del Workroom."
        )
    if is_amp() or who == AMP_ASSISTANT_NAME:
        return (
            f"{who} es el asistente de operaciones de {AMP_COACH_NAME}. "
            "Esta instancia tiene dos empresas, y ninguna es la única: "
            "AMP — Actitud Mental Positiva, también El Portal de la Alegría "
            "(actitudmentalpositiva.com), coaching, cursos y membresías; "
            "y Cibernettic, servicios de tecnología (Oracle DBA, GIS/Esri, "
            "redes y VoIP, ERP/CRM, datos y BI, ciberseguridad). "
            f"{who} no es el coach ni la razón social. Opera las dos y "
            "cualquier otra empresa que se cree aquí. Responde en español "
            "salvo que pidan inglés. No inventa precios ni datos legales. "
            "Nada se publica en redes sin aprobación. "
            "No lee ni escribe los datos del Workroom."
        )
    return (
        f"{who} is the Empire Workroom assistant. "
        "Same abilities and tools as always."
    )


def assistant_settings() -> dict:
    """Load this instance's assistant settings, creating them if needed.

    Workroom without ASSISTANT_NAME does not create a second settings file.
    """
    name = assistant_name()
    if not is_family_edition() and not os.getenv("ASSISTANT_NAME", "").strip():
        return {
            "name": name,
            "persona": default_persona(name),
            "locale": default_locale(),
            "separate_from_workroom": False,
        }
    path = assistant_settings_path()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}
    data.setdefault("name", name)
    data.setdefault("persona", default_persona(data["name"]))
    data.setdefault("locale", default_locale())
    if is_maxine():
        data.setdefault("owner_name", MAXINE_OWNER_NAME)
        data.setdefault("owner_role", "desarrollos inmobiliarios")
    else:
        data.setdefault("coach_name", AMP_COACH_NAME if is_amp() else None)
        data.setdefault("coach_role", "AMP coach" if is_amp() else None)
    data.setdefault("separate_from_workroom", True)
    data["name"] = name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert_under_root(path)
    return data


def ensure_assistant_files() -> dict:
    """Create Max-e's own memory, history db, and settings under the data root.

    Does not read or write the Workroom max/memory.md.
    """
    settings = assistant_settings()
    memory = assistant_memory_path()
    if not memory.exists():
        memory.parent.mkdir(parents=True, exist_ok=True)
        name = settings["name"]
        if is_maxine():
            who = f"{MAXINE_OWNER_NAME} lleva los desarrollos. {name} no es la dueña. El modelo es ConstructionForge."
        elif is_amp():
            who = (
                f"{AMP_COACH_NAME} tiene dos empresas en esta instancia: "
                f"AMP (coaching) y Cibernettic (tecnología). {name} no es el coach "
                "ni una razón social."
            )
        else:
            who = f"{name} es el asistente de esta instancia."
        memory.write_text(
            f"# Memoria de {name}\n\n"
            f"{name} es un asistente propio de esta instancia, separado del Max del Workroom.\n"
            f"{who}\n"
            "Memoria, historial y ajustes viven solo bajo el directorio de datos de esta instancia.\n",
            encoding="utf-8",
        )
    history = assistant_history_db()
    if not history.exists():
        import sqlite3
        conn = sqlite3.connect(history)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                business_slug TEXT,
                role TEXT,
                content TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()
        conn.close()
    log_path = log_dir() / "amp.log"
    if is_family_edition():
        log_path.write_text(f"{assistant_name()} listo\n", encoding="utf-8")
        assert_under_root(log_path)
    founder = ensure_founder_profile() if is_family_edition() else {}
    for path in (memory, history, assistant_settings_path()):
        assert_under_root(path)
    return {
        "name": settings["name"],
        "persona": settings["persona"],
        "locale": settings.get("locale", default_locale()),
        "memory_path": str(memory),
        "history_path": str(history),
        "settings_path": str(assistant_settings_path()),
        "brain_dir": str(assistant_brain_dir()),
        "founder_profile": founder,
    }


def edition_prompt_suffix() -> str:
    """Extra identity block. Empty on Workroom so the cached prompt stays put."""
    if not (os.getenv("ASSISTANT_NAME", "").strip() or is_family_edition()):
        return ""
    name = assistant_name()
    locale = default_locale()
    lines = [
        "",
        f"=== INSTANCE ASSISTANT: {name} ===",
        f"Your name is {name}. Use that name in greetings, signatures, and generated documents.",
        default_persona(name),
        f"Default language for replies and generated content: {locale}.",
    ]
    if is_family_edition():
        lines.append(
            "Responde en español salvo que pidan inglés. "
            "Por defecto usa de 2 a 5 oraciones cortas. "
            "Si la pregunta es vaga, haz una sola pregunta para aclarar. "
            "Para noticias o hechos de hoy: busca primero en la web y luego resume "
            "con 1 o 2 fuentes. No digas que no tienes información antes de buscar."
        )
    if is_amp():
        lines.append(
            f"The app is {app_display_name()}. It is not named AMP. "
            "Two businesses live here, and neither is the only focus: "
            "AMP (Actitud Mental Positiva, also El Portal de la Alegría, "
            "actitudmentalpositiva.com) for coaching, courses, and memberships; "
            "and Cibernettic for IT services (cybersecurity, data management, "
            "Oracle DBA, GIS/Esri, networks/VoIP, ERP/CRM, BI). "
            f"{AMP_COACH_NAME} runs both. You ({name}) handle operations for both "
            "and for any other company created in this instance. "
            "Use AMP wording only when the work is inside the AMP business. "
            "Cibernettic proposals, quotes, SLAs, NDAs, data-processing agreements, "
            "statements of work, and invoices stay drafts until approved. "
            "Do not invent company legal details or prices. Currency is COP or USD "
            "only when the user says so. "
            "Workroom, WoodCraft, LuxeForge and drawing tools are off. "
            "Shared modules stay. Facts marked confidential never appear in public content."
        )
    if is_maxine():
        lines.append(
            "This instance is based on ConstructionForge. That is the only project, "
            "lot, buyer, quote, and payment model. Do not keep a parallel list. "
            f"The app is {app_display_name()}. "
            f"{MAXINE_OWNER_NAME} runs real estate, construction, and development. "
            "The public sales brand is GAC. Do not invent legal or company details, "
            "prices, or per-lot areas. Facts marked confidential never appear in "
            "public posts or shared outputs. Shared Empire modules stay available "
            "and must read and write the same ConstructionForge records."
        )
        try:
            from app.services.construction_bridge import public_portfolio_text
            portfolio = public_portfolio_text()
            if portfolio:
                lines.append(portfolio)
        except Exception:
            pass
    return "\n".join(lines) + "\n"


def apply_edition_prompt(base: str) -> str:
    suffix = edition_prompt_suffix()
    if not suffix:
        return base
    if suffix.strip() in base:
        return base
    return base + suffix


def greeting(locale: Optional[str] = None, *, include_owner: bool = True) -> str:
    """Public anonymous callers get the assistant name only — no owner name."""
    name = assistant_name()
    lang = (locale or default_locale()).lower()
    if lang.startswith("es"):
        if is_maxine():
            if include_owner:
                return f"Hola, soy {name}. Llevo el portafolio de desarrollos en ConstructionForge."
            return f"Hola, soy {name}."
        if is_amp():
            if include_owner:
                return (
                    f"Hola, soy {name}. Juan Diego Giraldo tiene dos empresas aquí: "
                    "AMP (coaching) y Cibernettic (tecnología). Yo llevo la operación de las dos."
                )
            return f"Hola, soy {name}."
        return f"Hola, soy {name}."
    if is_maxine():
        if include_owner:
            return f"Hi, I'm {name}. I run the development portfolio in ConstructionForge."
        return f"Hi, I'm {name}."
    if is_amp():
        if include_owner:
            return (
                f"Hi, I'm {name}. Juan Diego Giraldo has two businesses here: "
                "AMP (coaching) and Cibernettic (technology). I run operations for both."
            )
        return f"Hi, I'm {name}."
    return f"Hi, I'm {name}."


def resolve_socialforge_root() -> Path:
    """Where SocialForge JSON lives. Workroom keeps the legacy path."""
    if is_family_edition():
        return active_business_root() / "socialforge"
    return Path(os.path.expanduser("~/empire-repo/backend/data/socialforge"))


def socialforge_storage_dir() -> Path:
    path = resolve_socialforge_root()
    if is_family_edition():
        path = assert_under_root(path)
    path.mkdir(parents=True, exist_ok=True)
    (path / "posts").mkdir(parents=True, exist_ok=True)
    (path / "campaigns").mkdir(parents=True, exist_ok=True)
    return path


def social_publish_allowed(status: Optional[str]) -> bool:
    """AMP: nothing goes out until a post is explicitly approved."""
    if not is_family_edition():
        return True
    return (status or "").strip().lower() == "approved"


def coerce_social_status(requested: Optional[str]) -> str:
    if not is_family_edition():
        return requested or "draft"
    status = (requested or "pending_approval").strip().lower()
    if status in {"posted", "published", "scheduled", "approved"}:
        return "pending_approval"
    if status in {"draft", "pending_approval"}:
        return status
    return "pending_approval"


def edition_service_ports() -> dict[str, int]:
    """Health probes for this process. Family editions never check Workroom ports."""
    profile = edition_profile()
    if is_family_edition():
        return {
            "Backend API": int(profile.get("backend_port") or 8011),
            "Command Center": int(profile.get("frontend_port") or 3011),
        }
    return {
        "Backend API": 8000,
        "Command Center": 3005,
        "OpenClaw": 7878,
        "Ollama": 11434,
    }


def hermes_memory_dir() -> Path:
    raw = os.getenv("EMPIRE_BOX_MEMORY_DIR", "").strip()
    if raw:
        path = Path(raw).expanduser()
        return assert_under_root(path) if is_family_edition() else path
    if is_family_edition():
        return require_data_root() / "assistant" / "hermes"
    return Path.home() / "empire-box-memory"


def supermemory_store_path() -> Path:
    if is_family_edition():
        return assert_under_root(require_data_root() / "assistant" / "brain" / "supermemory_scaffold.jsonl")
    return Path.home() / "empire-repo" / "backend" / "data" / "max" / "supermemory_scaffold.jsonl"


def session_handoff_path() -> Path:
    if is_family_edition():
        return assert_under_root(require_data_root() / "assistant" / "brain" / "session_handoff.json")
    return Path.home() / "empire-repo" / "backend" / "data" / "max" / "session_handoff.json"


def session_log_path() -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    if is_family_edition():
        return log_dir() / today / "session-log.md"
    return Path.home() / "empire-repo" / "backend" / "data" / "logs" / today / "session-log.md"


def last_chat_summary_path() -> Optional[Path]:
    """Workroom Claude session file. Family editions must not read HOME."""
    if is_family_edition():
        return None
    return Path.home() / ".claude-context" / "last_chat_summary.md"


def founder_profile_path() -> Path:
    return assert_under_root(require_data_root() / "assistant" / "founder.json")


def ensure_founder_profile() -> dict:
    """Empty founder memory: owner name only. No Workroom records."""
    if not is_family_edition():
        return {}
    path = founder_profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    owner = AMP_COACH_NAME if is_amp() else MAXINE_OWNER_NAME
    data: dict = {}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except json.JSONDecodeError:
            data = {}
    data["role"] = "founder"
    data["owner_name"] = owner
    data.setdefault("preferences", {})
    data.setdefault("notes", "")
    data["workroom"] = None
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    stub = assert_under_root(require_data_root() / "assistant" / "brain" / "founder_profile.md")
    stub.parent.mkdir(parents=True, exist_ok=True)
    if not stub.exists():
        stub.write_text(
            f"# Founder\n\nNombre: {owner}\n\n(Perfil vacío. Sin datos del Workroom.)\n",
            encoding="utf-8",
        )
    assert_under_root(path)
    return data


def family_prompt_context_paths() -> dict[str, Path]:
    """Every live-context file a family prompt may read. All under the data root."""
    if not is_family_edition():
        raise EditionPathError("family_prompt_context_paths() solo aplica a amp/maxine")
    root = require_data_root()
    today = datetime.now().strftime("%Y-%m-%d")
    hermes = hermes_memory_dir()
    brain = Path(os.getenv("EMPIRE_BRAIN_DIR", "").strip() or (root / "assistant" / "brain"))
    logs = Path(os.getenv("EMPIRE_LOG_DIR", "").strip() or (root / "logs"))
    return {
        "hermes_root": hermes,
        "hermes_context": hermes / "CONTEXT.md",
        "hermes_memory": hermes / "MEMORY.md",
        "hermes_user": hermes / "USER.md",
        "supermemory": supermemory_store_path(),
        "handoff": session_handoff_path(),
        "brain_db": brain / "memories.db",
        "founder_profile": founder_profile_path(),
        "founder_memory": brain / "founder_profile.md",
        "session_log": logs / today / "session-log.md",
        "quotes": root / "quotes",
        "inbox": root / "inbox",
        "assistant_memory": root / "assistant" / "memory.md",
        "logs": logs,
    }


def family_forbidden_prompt_roots() -> tuple[Path, ...]:
    """HOME / repo trees family live context must never resolve into."""
    home = Path.home()
    return (
        home / ".claude-context",
        home / "empire-repo",
        home / "empire-box-memory",
        home / "empire-data",
    )


def brain_sync_storage_paths() -> dict[str, Path]:
    """Quote / inbox / brain files counted by nightly sync.

    Family editions stay under EMPIRE_DATA_DIR. Workroom keeps the
    historical HOME/repo paths so its counts do not change.
    """
    if is_family_edition():
        root = require_data_root()
        brain = Path(os.getenv("EMPIRE_BRAIN_DIR", "").strip() or (root / "assistant" / "brain"))
        return {
            "quotes": root / "quotes",
            "inbox": root / "inbox",
            "brain_db": brain / "memories.db",
        }
    home_data = Path.home() / "empire-repo" / "backend" / "data"
    return {
        "quotes": home_data / "quotes",
        "inbox": home_data / "inbox",
        "brain_db": home_data / "brain" / "memories.db",
    }


def apply_amp_process_paths() -> None:
    """Force process data paths under EMPIRE_DATA_DIR for a family instance.

    Called after dotenv so a shared Workroom .env cannot redirect this
    process at the Workroom database, brain, Hermes memory, or memory file.
    No-op unless EMPIRE_EDITION is amp or maxine.
    """
    if not is_family_edition():
        return
    root = data_root_or_none()
    if root is None:
        return
    root.mkdir(parents=True, exist_ok=True)
    hermes = root / "assistant" / "hermes"
    brain = root / "assistant" / "brain"
    os.environ["EMPIRE_DATA_DIR"] = str(root)
    os.environ["EMPIRE_BRAIN_DIR"] = str(brain)
    os.environ["EMPIRE_BOX_MEMORY_DIR"] = str(hermes)
    os.environ["MAX_MEMORY_PATH"] = str(root / "assistant" / "memory.md")
    os.environ["DATABASE_URL"] = f"sqlite:///{root / 'empirebox.db'}"
    os.environ["EMPIRE_TASK_DB"] = str(root / "empire.db")
    os.environ["EMPIRE_LOG_DIR"] = str(root / "logs")
    os.environ.setdefault("ASSISTANT_NAME", str(edition_profile().get("assistant_default") or AMP_ASSISTANT_NAME))
    os.environ.setdefault("EMPIRE_DEFAULT_LOCALE", "es")
    os.environ["MAX_SELECTED_PROVIDER"] = "minimax"
    os.environ["MAX_SELECTED_MODEL"] = os.getenv("MINIMAX_MODEL", "").strip() or "MiniMax-M3"
    os.environ.setdefault("INSTANCE_USAGE_CAP_PCT", "20")
    brain.mkdir(parents=True, exist_ok=True)
    hermes.mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(parents=True, exist_ok=True)
    (root / "quotes").mkdir(parents=True, exist_ok=True)
    (root / "inbox").mkdir(parents=True, exist_ok=True)
    ensure_founder_profile()


def edition_manifest() -> dict:
    name = assistant_name()
    manifest = {
        "edition": edition_name(),
        "default_locale": default_locale(),
        "locales": ["es", "en"] if is_family_edition() else ["en", "es"],
        "app": {
            "title": app_display_name(),
            "kind": "personal_agent_command_center" if is_family_edition() else "workroom",
            "primary": primary_shell(),
        },
        "profile": edition_profile(),
        "assistant": {
            "name": name,
            "persona": default_persona(name),
            "greeting_es": greeting("es", include_owner=not is_family_edition()),
            "greeting_en": greeting("en", include_owner=not is_family_edition()),
            "separate_from_workroom": bool(is_family_edition() or os.getenv("ASSISTANT_NAME", "").strip()),
        },
        "modules": {
            "enabled": (
                sorted(list(AMP_SHARED_MODULES) + (["construction"] if is_maxine() else []))
                if is_family_edition() else ["*"]
            ),
            "disabled": sorted(AMP_DISABLED_MODULES) if is_family_edition() else [],
            "labels_es": AMP_MODULE_LABELS_ES if is_family_edition() else {},
        },
        "businesses": [
            {
                "slug": "amp",
                "name": "Actitud Mental Positiva",
                "also_known_as": "El Portal de la Alegría",
                "focus": "coaching, cursos y membresías",
            },
            {
                "slug": "cibernettic",
                "name": "Cibernettic",
                "focus": "servicios de tecnología",
                "lines": [
                    "ciberseguridad",
                    "datos y BI",
                    "Oracle DBA",
                    "GIS/Esri",
                    "redes y VoIP",
                    "ERP/CRM",
                ],
            },
        ] if is_amp() else [],
        "product": {
            "name": "Actitud Mental Positiva",
            "also_known_as": "El Portal de la Alegría",
            "site": "https://actitudmentalpositiva.com",
            "coach": AMP_COACH_NAME,
            "coach_is_assistant": False,
            "role": "business_inside_instance",
            "model": "Cursos estructurados con audio y meditaciones guiadas por tema, más registro diario de ánimo",
        } if is_amp() else (
            {
                "name": "GAC",
                "kind": "marca comercial",
                "model": "constructionforge",
                "note": "Marca de ventas. Esta ficha no guarda datos legales de la sociedad.",
            } if is_maxine() else None
        ),
        "data_root_configured": data_root_or_none() is not None,
        "simli": {
            "face_env": (
                "SIMLI_FACE_ID_MAX_E" if is_amp()
                else "SIMLI_FACE_ID_MAXINE" if is_maxine()
                else "SIMLI_FACE_ID"
            ),
            "fallback": "current_avatar",
        },
    }
    return manifest


def access_exempt(method: str, path: str) -> bool:
    clean = path.split("?", 1)[0]
    for allowed_method, allowed_path in _ALLOWLIST_EXEMPT:
        if method.upper() == allowed_method and clean == allowed_path:
            return True
    return False


def sin_acceso_body() -> dict:
    return {
        "detail": "Sin acceso. Esta edición solo está disponible para cuentas autorizadas.",
        "code": "sin_acceso",
    }


def paths_touched_by_provision(root: Path) -> Iterable[Path]:
    """Files a provisioned AMP instance is allowed to create. Used by tests."""
    yield root / "amp" / "allowlist.json"
    yield root / "amp" / "amp.db"
    yield root / "assistant" / "memory.md"
    yield root / "assistant" / "settings.json"
    yield root / "assistant" / "history" / "conversations.db"
    yield root / "logs" / "amp.log"
    yield root / "businesses" / "amp" / "business.json"
    yield root / "whatsapp_credentials.json"
