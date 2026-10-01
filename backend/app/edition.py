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
from pathlib import Path
from typing import Iterable, Optional

WORKROOM_EDITION = "workroom"
AMP_EDITION = "amp"

# Workroom display stays "Max" when ASSISTANT_NAME is unset.
# business.json still says "MAX" for older prompt callers; the identity
# helper below is what new code and the AMP instance use.
WORKROOM_ASSISTANT_NAME = "Max"
AMP_ASSISTANT_NAME = "Max-e"

AMP_COACH_NAME = "Juan Diego Giraldo"

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
)

_business_slug: ContextVar[str] = ContextVar("empire_business_slug", default="amp")


class EditionPathError(RuntimeError):
    """A data path escaped the instance data root."""


def edition_name() -> str:
    raw = os.getenv("EMPIRE_EDITION", "").strip().lower()
    return raw or WORKROOM_EDITION


def is_amp() -> bool:
    return edition_name() == AMP_EDITION


def default_locale() -> str:
    """AMP is Spanish-first. Workroom stays English unless configured."""
    if is_amp():
        return os.getenv("EMPIRE_DEFAULT_LOCALE", "es").strip().lower() or "es"
    return os.getenv("EMPIRE_DEFAULT_LOCALE", "en").strip().lower() or "en"


def assistant_name() -> str:
    """Per-instance display name.

    Unset on Workroom → Max. The AMP env sets ASSISTANT_NAME=Max-e.
    If the edition is AMP and the variable was left empty, Max-e is still
    the name so this instance cannot speak as the Workroom assistant.
    """
    raw = os.getenv("ASSISTANT_NAME", "").strip()
    if raw:
        return raw
    if is_amp():
        return AMP_ASSISTANT_NAME
    return WORKROOM_ASSISTANT_NAME


def prompt_identity_name() -> str:
    """Name used in the system prompt identity line.

    Workroom keeps the historical business.json value ("MAX") when
    ASSISTANT_NAME is unset, so the Workroom prompt does not change.
    """
    if os.getenv("ASSISTANT_NAME", "").strip() or is_amp():
        return assistant_name()
    try:
        from app.config.business_config import biz
        return biz.ai_assistant_name
    except Exception:
        return "MAX"


def module_enabled(module_id: str) -> bool:
    if not is_amp():
        return True
    return module_id.strip().lower() not in AMP_DISABLED_MODULES


def disabled_module_for_path(path: str) -> Optional[str]:
    if not is_amp():
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
            "EMPIRE_EDITION=amp requiere EMPIRE_DATA_DIR "
            "(la instancia AMP no usa los datos del Workroom)"
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
    if is_amp():
        root = require_data_root()
        path = root / "amp"
        path.mkdir(parents=True, exist_ok=True)
        return path
    path = _legacy_amp_db().parent / "amp"
    path.mkdir(parents=True, exist_ok=True)
    return path


def amp_sqlite_path() -> Path:
    if is_amp():
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
    if is_amp():
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
    if is_amp() or (os.getenv("ASSISTANT_NAME", "").strip() and data_root_or_none()):
        root = require_data_root() if is_amp() else data_root_or_none()
        assert root is not None
        path = root / "assistant"
        path.mkdir(parents=True, exist_ok=True)
        return path
    raise EditionPathError("assistant_home() solo aplica a una instancia con directorio de datos")


def assistant_memory_path() -> Path:
    if not is_amp() and not os.getenv("ASSISTANT_NAME", "").strip():
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
    if is_amp() or who == AMP_ASSISTANT_NAME:
        return (
            f"{who} es el asistente de operaciones de {AMP_COACH_NAME} "
            "(Cali). Juan es el coach de AMP — Actitud Mental Positiva, "
            "también El Portal de la Alegría (actitudmentalpositiva.com). "
            f"{who} no es el coach. Tiene las mismas capacidades y herramientas "
            "que Max en el Workroom, es de la misma familia de código, y puede "
            "crecer hacia cualquier industria. Prepara sesiones, seguimientos, "
            "agenda, cobros y reportes, y opera cada empresa que se cree en "
            "esta instancia. Responde en español salvo que pidan inglés. "
            "No inventa precios. Nada se publica en redes sin aprobación. "
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
    if not is_amp() and not os.getenv("ASSISTANT_NAME", "").strip():
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
        coach = AMP_COACH_NAME
        memory.write_text(
            f"# Memoria de {name}\n\n"
            f"{name} es un asistente propio de esta instancia, separado del Max del Workroom.\n"
            f"Coach de AMP: {coach}. {name} no es el coach.\n"
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
    if is_amp():
        log_path.write_text(f"{assistant_name()} listo\n", encoding="utf-8")
        assert_under_root(log_path)
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
    }


def edition_prompt_suffix() -> str:
    """Extra identity block. Empty on Workroom so the cached prompt stays put."""
    if not (os.getenv("ASSISTANT_NAME", "").strip() or is_amp()):
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
    if is_amp():
        lines.append(
            "This is the AMP edition (actitudmentalpositiva.com / El Portal de la Alegría): "
            "a fusion of structured multi-week courses with audio, and themed guided "
            "meditations plus a daily mood check-in. "
            f"{AMP_COACH_NAME} is the coach. You ({name}) handle operations around him "
            "and any additional blank company created in this instance. "
            "Workroom, WoodCraft, LuxeForge and drawing tools are off. "
            "Shared modules stay: CRM, LeadForge, SocialForge (approval before anything posts), "
            "packages and memberships, scheduling, finance. Do not invent prices."
        )
    return "\n".join(lines) + "\n"


def apply_edition_prompt(base: str) -> str:
    suffix = edition_prompt_suffix()
    if not suffix:
        return base
    if suffix.strip() in base:
        return base
    return base + suffix


def greeting(locale: Optional[str] = None) -> str:
    name = assistant_name()
    lang = (locale or default_locale()).lower()
    if lang.startswith("es"):
        if is_amp():
            return f"Hola, soy {name}. Juan Diego Giraldo es el coach; yo me encargo de la operación."
        return f"Hola, soy {name}."
    if is_amp():
        return f"Hi, I'm {name}. Juan Diego Giraldo is the coach; I run operations."
    return f"Hi, I'm {name}."


def resolve_socialforge_root() -> Path:
    """Where SocialForge JSON lives. Workroom keeps the legacy path."""
    if is_amp():
        return active_business_root() / "socialforge"
    return Path(os.path.expanduser("~/empire-repo/backend/data/socialforge"))


def socialforge_storage_dir() -> Path:
    path = resolve_socialforge_root()
    if is_amp():
        path = assert_under_root(path)
    path.mkdir(parents=True, exist_ok=True)
    (path / "posts").mkdir(parents=True, exist_ok=True)
    (path / "campaigns").mkdir(parents=True, exist_ok=True)
    return path


def social_publish_allowed(status: Optional[str]) -> bool:
    """AMP: nothing goes out until a post is explicitly approved."""
    if not is_amp():
        return True
    return (status or "").strip().lower() == "approved"


def coerce_social_status(requested: Optional[str]) -> str:
    if not is_amp():
        return requested or "draft"
    status = (requested or "pending_approval").strip().lower()
    if status in {"posted", "published", "scheduled", "approved"}:
        return "pending_approval"
    if status in {"draft", "pending_approval"}:
        return status
    return "pending_approval"


def apply_amp_process_paths() -> None:
    """Force process data paths under EMPIRE_DATA_DIR for the AMP instance.

    Called after dotenv so a shared Workroom .env cannot redirect this
    process at the Workroom database, brain, or memory file.
    No-op unless EMPIRE_EDITION=amp.
    """
    if not is_amp():
        return
    root = data_root_or_none()
    if root is None:
        return
    root.mkdir(parents=True, exist_ok=True)
    os.environ["EMPIRE_DATA_DIR"] = str(root)
    os.environ["EMPIRE_BRAIN_DIR"] = str(root / "assistant" / "brain")
    os.environ["MAX_MEMORY_PATH"] = str(root / "assistant" / "memory.md")
    os.environ["DATABASE_URL"] = f"sqlite:///{root / 'empirebox.db'}"
    os.environ["EMPIRE_TASK_DB"] = str(root / "empire.db")
    os.environ["EMPIRE_LOG_DIR"] = str(root / "logs")
    os.environ.setdefault("ASSISTANT_NAME", AMP_ASSISTANT_NAME)
    os.environ.setdefault("EMPIRE_DEFAULT_LOCALE", "es")
    (root / "assistant" / "brain").mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(parents=True, exist_ok=True)


def edition_manifest() -> dict:
    name = assistant_name()
    manifest = {
        "edition": edition_name(),
        "default_locale": default_locale(),
        "locales": ["es", "en"] if is_amp() else ["en", "es"],
        "assistant": {
            "name": name,
            "persona": default_persona(name),
            "greeting_es": greeting("es"),
            "greeting_en": greeting("en"),
            "separate_from_workroom": bool(is_amp() or os.getenv("ASSISTANT_NAME", "").strip()),
        },
        "modules": {
            "enabled": sorted(AMP_SHARED_MODULES) if is_amp() else ["*"],
            "disabled": sorted(AMP_DISABLED_MODULES) if is_amp() else [],
            "labels_es": AMP_MODULE_LABELS_ES if is_amp() else {},
        },
        "product": {
            "name": "Actitud Mental Positiva",
            "also_known_as": "El Portal de la Alegría",
            "site": "https://actitudmentalpositiva.com",
            "coach": AMP_COACH_NAME,
            "coach_is_assistant": False,
            "model": "Cursos estructurados con audio y meditaciones guiadas por tema, más registro diario de ánimo",
        } if is_amp() else None,
        "data_root_configured": data_root_or_none() is not None,
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
