"""Companies inside one AMP instance.

Juan's instance starts with AMP itself. He can create additional blank
companies. Each company gets its own directory under the instance data
root and uses only the shared base modules (CRM, LeadForge, SocialForge,
quotes/invoices, scheduling, finance). No industry-specific modules.

Templates seed service categories and CRM fields only. Prices are never
invented: every price field is null.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.edition import (
    AMP_COACH_NAME,
    AMP_SHARED_MODULES,
    assert_under_root,
    assistant_name,
    business_dir,
    is_amp,
    is_family_edition,
    is_maxine,
    require_data_root,
)

SHARED_MODULES = [m for m in AMP_SHARED_MODULES if m != "amp"]

# Tools the EasyStep-style interview can turn on. All stay off unless chosen.
INTERVIEW_MODULES = (
    "crm",
    "quotes",
    "invoices",
    "socialforge",
    "leadforge",
    "courses",
)
INTERVIEW_LAST_STEP = 10
BLANK_TEMPLATES = {"", "blank", "en_blanco", "none"}
PAYMENT_METHODS = ("efectivo", "transferencia", "tarjeta", "nequi", "daviplata", "pse")
# Static API paths under /businesses. Never use these as company slugs.
RESERVED_SLUGS = {"templates", "interview"}
_MODULE_ORDER = list(SHARED_MODULES) + [m for m in INTERVIEW_MODULES if m not in SHARED_MODULES]
_ALLOWED_MODULES = set(_MODULE_ORDER)
_EXTRA_KEYS = {
    "legal_name",
    "trade_name",
    "country",
    "city",
    "contact_email",
    "contact_phone",
    "website",
    "currency",
    "fiscal_year_start",
    "tax_id",
    "charges_iva",
    "payment_methods",
    "customer_type",
    "customer_who",
    "team_mode",
    "roles",
    "sells",
    "starter_items",
    "interview",
    "setup",
    "cf_project_id",
    "brand",
    "model",
}

# Optional starters matched to Juan's background. Categories and CRM
# fields only — price is always null.
TEMPLATES: dict[str, dict] = {
    "ciberseguridad": {
        "label": "Ciberseguridad",
        "description": "Auditorías de seguridad y servicios administrados.",
        "service_categories": [
            ("Auditoría de seguridad", "Revisión del estado de seguridad."),
            ("Servicios administrados", "Operación continua de controles."),
            ("Evaluación de vulnerabilidades", "Hallazgos y seguimiento."),
            ("Políticas y cumplimiento", "Documentos y controles."),
        ],
        "crm_fields": [
            ("empresa", "Empresa"),
            ("contacto", "Contacto"),
            ("sector", "Sector"),
            ("activos_criticos", "Activos críticos"),
            ("alcance", "Alcance"),
            ("notas", "Notas"),
        ],
    },
    "datos_bi": {
        "label": "Consultoría de datos y BI",
        "description": "Diagnóstico de datos, tableros y modelos.",
        "service_categories": [
            ("Diagnóstico de datos", "Estado de las fuentes y la calidad."),
            ("Tablero KPI", "Indicadores y visualización."),
            ("Modelo de datos", "Modelo para análisis."),
            ("Transferencia de datos", "Importación, exportación y paso entre sistemas."),
        ],
        "crm_fields": [
            ("empresa", "Empresa"),
            ("fuentes_de_datos", "Fuentes de datos"),
            ("kpis", "KPIs"),
            ("herramientas", "Herramientas"),
            ("madurez", "Madurez"),
            ("notas", "Notas"),
        ],
    },
    "gis": {
        "label": "GIS y mapas",
        "description": "Análisis espacial, mapas y geodatabases.",
        "service_categories": [
            ("Análisis espacial", "Preguntas geográficas."),
            ("Mapas", "Mapas para decisión o divulgación."),
            ("Geodatabase", "Estructura de datos espaciales."),
            ("Capas", "Capas y simbología."),
        ],
        "crm_fields": [
            ("organizacion", "Organización"),
            ("area_geografica", "Área geográfica"),
            ("capas", "Capas"),
            ("sistema_coordenadas", "Sistema de coordenadas"),
            ("caso_de_uso", "Caso de uso"),
            ("notas", "Notas"),
        ],
    },
    "redes_voip": {
        "label": "Redes y VoIP",
        "description": "Diseño de red, voz sobre IP y soporte.",
        "service_categories": [
            ("Diseño de red", "Topología y direccionamiento."),
            ("VoIP", "Voz sobre IP."),
            ("Monitoreo", "Visibilidad de la red."),
            ("Soporte", "Atención de incidentes."),
        ],
        "crm_fields": [
            ("organizacion", "Organización"),
            ("sitios", "Sitios"),
            ("equipos", "Equipos"),
            ("proveedor", "Proveedor"),
            ("tickets", "Tickets"),
            ("notas", "Notas"),
        ],
    },
    "erp_crm": {
        "label": "Implementación ERP/CRM",
        "description": "Levantamiento, configuración, migración y capacitación.",
        "service_categories": [
            ("Levantamiento", "Procesos y alcance."),
            ("Configuración", "Parametrización del sistema."),
            ("Migración de datos", "Paso de datos entre sistemas."),
            ("Capacitación", "Uso del sistema con el equipo."),
        ],
        "crm_fields": [
            ("empresa", "Empresa"),
            ("sistema_origen", "Sistema origen"),
            ("modulos", "Módulos"),
            ("usuarios", "Usuarios"),
            ("fase", "Fase"),
            ("notas", "Notas"),
        ],
    },
}

BASE_CRM_FIELDS = [
    ("nombre", "Nombre"),
    ("email", "Email"),
    ("telefono", "Teléfono"),
    ("notas", "Notas"),
]

COACHEE_FIELDS = [
    ("nombre", "Nombre"),
    ("email", "Email"),
    ("telefono", "Teléfono"),
    ("ciudad", "Ciudad"),
    ("idioma", "Idioma"),
    ("metas", "Metas"),
    ("historial_sesiones", "Historial de sesiones"),
    ("notas_progreso", "Notas de progreso"),
    ("estado", "Estado"),
    ("inicio", "Fecha de inicio"),
    ("coach", "Coach"),
]

# Placeholders only. price is null on purpose.
COACHING_PACKAGES = [
    {
        "id": "descubrimiento",
        "name": "Llamada de descubrimiento",
        "kind": "intake",
        "billing": "one_time",
        "price": None,
    },
    {
        "id": "sesion",
        "name": "Sesión de coaching",
        "kind": "package",
        "billing": "one_time",
        "price": None,
    },
    {
        "id": "programa",
        "name": "Programa por semanas",
        "kind": "package",
        "billing": "one_time",
        "price": None,
    },
    {
        "id": "membresia",
        "name": "Membresía",
        "kind": "membership",
        "billing": "recurring",
        "price": None,
    },
]


def safe_slug(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "empresa"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _registry_path() -> Path:
    path = require_data_root() / "businesses" / "index.json"
    return assert_under_root(path)


def _connect(slug: str) -> sqlite3.Connection:
    root = business_dir(slug)
    root.mkdir(parents=True, exist_ok=True)
    for sub in ("crm", "leadforge", "socialforge", "quotes", "finance", "scheduling", "generated", "uploads"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    db_path = assert_under_root(root / "workspace.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS crm_fields (
            key TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS crm_contacts (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            phone TEXT,
            fields_json TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS service_categories (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            price REAL
        );
        CREATE TABLE IF NOT EXISTS leads (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            source TEXT,
            note TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS social_posts (
            id TEXT PRIMARY KEY,
            content TEXT,
            status TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS quotes (
            id TEXT PRIMARY KEY,
            title TEXT,
            kind TEXT,
            price REAL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS appointments (
            id TEXT PRIMARY KEY,
            title TEXT,
            when_at TEXT,
            note TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS finance_entries (
            id TEXT PRIMARY KEY,
            kind TEXT,
            memo TEXT,
            amount REAL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """
    )
    conn.commit()
    return conn


def _load_registry() -> dict:
    path = _registry_path()
    if not path.exists():
        return {"businesses": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {"businesses": []}
    data.setdefault("businesses", [])
    return data


def _save_registry(data: dict) -> None:
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def list_templates() -> list[dict]:
    out = []
    for key, tpl in TEMPLATES.items():
        out.append({
            "id": key,
            "label": tpl["label"],
            "description": tpl["description"],
            "service_categories": [
                {"name": name, "description": desc, "price": None}
                for name, desc in tpl["service_categories"]
            ],
            "crm_fields": [{"key": k, "label": label} for k, label in tpl["crm_fields"]],
        })
    return out


def list_businesses() -> list[dict]:
    if not is_family_edition():
        return []
    if is_amp():
        ensure_maxe_businesses()
    return list(_load_registry()["businesses"])


def get_business(slug: str) -> Optional[dict]:
    wanted = safe_slug(slug)
    for row in list_businesses():
        if row["slug"] == wanted:
            return row
    return None


def _seed_fields(conn: sqlite3.Connection, fields: list[tuple[str, str]]) -> None:
    for index, (key, label) in enumerate(fields):
        conn.execute(
            "INSERT OR REPLACE INTO crm_fields (key, label, sort_order) VALUES (?,?,?)",
            (key, label, index),
        )


def _seed_categories(conn: sqlite3.Connection, categories: list[tuple[str, str]]) -> None:
    for name, description in categories:
        conn.execute(
            "INSERT INTO service_categories (id, name, description, price) VALUES (?,?,?,NULL)",
            (str(uuid.uuid4()), name, description),
        )


def _write_profile(slug: str, profile: dict) -> None:
    path = assert_under_root(business_dir(slug) / "business.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_default_business() -> dict:
    """The AMP coaching workspace. Created once inside the data root."""
    registry = _load_registry()
    for row in registry["businesses"]:
        if row["slug"] == "amp":
            return row
    profile = {
        "slug": "amp",
        "name": "Actitud Mental Positiva",
        "also_known_as": "El Portal de la Alegría",
        "industry": "coaching",
        "description": (
            "Plataforma de actitudmentalpositiva.com. Fusión de cursos "
            "estructurados con audio y meditaciones guiadas por tema, con "
            "registro diario de ánimo. El coach es Juan Diego Giraldo."
        ),
        "template": None,
        "locale": "es",
        "modules": list(AMP_SHARED_MODULES),
        "industry_modules": [],
        "assistant": assistant_name(),
        "coach": AMP_COACH_NAME,
        "created_at": _now(),
    }
    conn = _connect("amp")
    _seed_fields(conn, COACHEE_FIELDS)
    for package in COACHING_PACKAGES:
        conn.execute(
            "INSERT INTO quotes (id, title, kind, price) VALUES (?,?,?,NULL)",
            (package["id"], package["name"], package["kind"]),
        )
    conn.commit()
    conn.close()
    _write_profile("amp", {**profile, "packages": COACHING_PACKAGES, "coachee_fields": [
        {"key": k, "label": label} for k, label in COACHEE_FIELDS
    ]})
    registry["businesses"].append(profile)
    _save_registry(registry)
    return profile


CIBERNETTIC_SERVICES = (
    ("Evaluaciones y auditorías", "Revisión de seguridad o de una plataforma. El precio lo pone quien cotiza."),
    ("Servicios administrados", "Operación continua. Puede ser por horas o por mensualidad."),
    ("Administración de bases de datos", "Oracle y otras bases. Incluye operación, no un precio de lista."),
    ("Respaldos y recuperación", "Backups y recuperación ante desastre."),
    ("Redes y VoIP", "Redes y telefonía IP."),
    ("GIS / Esri", "Mapas, geodatabases y análisis espacial."),
    ("ERP / CRM", "Sistemas de gestión e integración."),
    ("Datos y BI", "Análisis, tableros y proyectos de inteligencia de negocios."),
)


def ensure_cibernettic_business() -> dict:
    """IT company beside AMP. No legal entity data is stored."""
    registry = _load_registry()
    for row in registry["businesses"]:
        if row["slug"] == "cibernettic":
            return row
    profile = {
        "slug": "cibernettic",
        "name": "Cibernettic",
        "industry": "servicios de tecnología",
        "description": (
            "Empresa de tecnología de Juan Diego Giraldo. Oficios: Oracle DBA, "
            "GIS/Esri, redes y VoIP, ERP/CRM, análisis de datos y BI, y "
            "ciberseguridad. Más de 20 años de oficio. Esta ficha no guarda "
            "NIT, representante legal, escritura ni dirección de notaría."
        ),
        "template": None,
        "locale": "es",
        "currency_options": ["COP", "USD"],
        "billing_options": ["hours", "retainer", "project"],
        "modules": list(SHARED_MODULES),
        "industry_modules": [],
        "assistant": assistant_name(),
        "created_at": _now(),
    }
    conn = _connect("cibernettic")
    _seed_fields(conn, [
        ("empresa", "Empresa"),
        ("contacto", "Contacto"),
        ("servicio", "Servicio"),
        ("alcance", "Alcance"),
        ("moneda", "Moneda"),
        ("notas", "Notas"),
    ])
    _seed_categories(conn, CIBERNETTIC_SERVICES)
    conn.commit()
    conn.close()
    _write_profile("cibernettic", profile)
    registry["businesses"].append(profile)
    _save_registry(registry)
    return profile


def ensure_maxe_businesses() -> list[dict]:
    """AMP coaching and Cibernettic IT. Neither one is the whole instance."""
    if not is_amp():
        return []
    return [ensure_default_business(), ensure_cibernettic_business()]


def _normalize_modules(modules: Optional[list]) -> list[str]:
    """Keep known module ids, in a stable order. Unknown ids are dropped."""
    if not modules:
        return []
    wanted = set()
    for item in modules:
        key = str(item).strip().lower()
        if key in _ALLOWED_MODULES:
            wanted.add(key)
    return [key for key in _MODULE_ORDER if key in wanted]


def create_business(
    *,
    name: str,
    industry: str = "",
    description: str = "",
    template: Optional[str] = None,
    modules: Optional[list] = None,
    extra: Optional[dict] = None,
) -> dict:
    """Nueva empresa. Blank unless a known template id is passed.

    ``modules is None`` keeps the shared base (configuración rápida).
    An explicit list, including an empty one, stores only those tools.
    """
    if not is_family_edition():
        raise RuntimeError("Nueva empresa solo existe en esta edición")
    cleaned = (name or "").strip()
    if not cleaned:
        raise ValueError("El nombre de la empresa es obligatorio")
    template_id = (template or "").strip().lower() or None
    if template_id in BLANK_TEMPLATES:
        template_id = None
    if template_id and template_id not in TEMPLATES:
        raise ValueError("Plantilla desconocida")
    if is_amp():
        ensure_default_business()
    registry = _load_registry()
    slug = safe_slug(cleaned)
    taken = {row["slug"] for row in registry["businesses"]}
    base = slug
    n = 2
    while slug in taken or slug in RESERVED_SLUGS:
        slug = f"{base}-{n}"
        n += 1
    profile = {
        "slug": slug,
        "name": cleaned,
        "industry": (industry or "").strip(),
        "description": (description or "").strip(),
        "template": template_id,
        "locale": "es",
        "modules": list(SHARED_MODULES) if modules is None else _normalize_modules(modules),
        "industry_modules": [],
        "assistant": assistant_name(),
        "created_at": _now(),
    }
    conn = _connect(slug)
    fields = list(BASE_CRM_FIELDS)
    categories: list[tuple[str, str]] = []
    if template_id:
        tpl = TEMPLATES[template_id]
        fields = list(tpl["crm_fields"])
        categories = list(tpl["service_categories"])
        if not profile["industry"]:
            profile["industry"] = tpl["label"]
        if not profile["description"]:
            profile["description"] = tpl["description"]
    _seed_fields(conn, fields)
    _seed_categories(conn, categories)
    conn.commit()
    conn.close()
    if extra:
        for key, value in extra.items():
            if key in _EXTRA_KEYS:
                profile[key] = value
    stored = {
        **profile,
        "crm_fields": [{"key": k, "label": label} for k, label in fields],
        "service_categories": [
            {"name": n, "description": d, "price": None} for n, d in categories
        ],
    }
    _write_profile(slug, stored)
    registry["businesses"].append(profile)
    _save_registry(registry)
    if is_maxine():
        from app.services.construction_bridge import attach_project
        stored = attach_project(stored, extra if isinstance(extra, dict) else None)
    return stored


def _clip(value, limit: int) -> str:
    return str(value or "").replace("\x00", "").strip()[:limit]


def _as_bool(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "si", "sí", "yes", "on"}
    return bool(value)


def _price_or_none(value):
    """A price the owner typed. Missing or invalid stays unset — never invented."""
    if value is None or value is False:
        return None
    if isinstance(value, str):
        text = value.strip().replace(" ", "").replace("$", "")
        if not text:
            return None
        if text.count(",") == 1 and text.count(".") == 0:
            text = text.replace(",", ".")
        elif text.count(".") > 1:
            text = text.replace(".", "")
        try:
            number = float(text)
        except ValueError:
            return None
    else:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
    if number < 0 or number > 1_000_000_000_000:
        return None
    if number.is_integer():
        return int(number)
    return round(number, 2)


def _json_price(value):
    if value is None:
        return None
    return _price_or_none(value)


def _choice(value, allowed: set[str], default: str) -> str:
    key = _clip(value, 24).lower()
    return key if key in allowed else default


def _fiscal_year_start(value) -> str:
    digits = "".join(ch for ch in _clip(value, 10) if ch.isdigit())
    if not digits:
        return "01-01"
    month = int(digits[:2]) if len(digits) >= 2 else int(digits)
    if 1 <= month <= 12:
        return f"{month:02d}-01"
    return "01-01"


def _template_id(value) -> str:
    key = _clip(value, 40).lower()
    if key in BLANK_TEMPLATES or key not in TEMPLATES:
        return ""
    return key


def _payment_methods(raw) -> list[str]:
    if not isinstance(raw, list):
        return []
    allowed = set(PAYMENT_METHODS)
    out: list[str] = []
    for item in raw[:12]:
        key = _clip(item, 40).lower()
        if key in allowed and key not in out:
            out.append(key)
    return out


def _roles(raw) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw[:12]:
        role = _clip(item, 80)
        if role and role not in out:
            out.append(role)
    return out


def _customer(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    return {
        "name": _clip(raw.get("name"), 160),
        "email": _clip(raw.get("email"), 160),
        "phone": _clip(raw.get("phone"), 40),
    }


def _modules_map(raw) -> dict:
    base = {key: False for key in INTERVIEW_MODULES}
    if isinstance(raw, dict):
        for key in INTERVIEW_MODULES:
            if key in raw:
                base[key] = _as_bool(raw.get(key))
    elif isinstance(raw, list):
        chosen = {str(item).strip().lower() for item in raw}
        for key in INTERVIEW_MODULES:
            base[key] = key in chosen
    return base


def _sanitize_items(raw) -> list[dict]:
    if not isinstance(raw, list):
        return []
    kinds = {
        "service": "servicio",
        "product": "producto",
        "servicio": "servicio",
        "producto": "producto",
    }
    items = []
    for row in raw[:8]:
        if not isinstance(row, dict):
            continue
        name = _clip(row.get("name"), 160)
        if not name:
            continue
        kind = kinds.get(_clip(row.get("kind"), 20).lower(), "servicio")
        items.append({
            "name": name,
            "kind": kind,
            "price": _price_or_none(row.get("price")),
            "description": _clip(row.get("description"), 400),
        })
    return items


def empty_interview_answers() -> dict:
    return {
        "legal_name": "",
        "trade_name": "",
        "country": "Colombia",
        "city": "",
        "email": "",
        "phone": "",
        "website": "",
        "template": "",
        "industry_description": "",
        "sells": "ambos",
        "items": [],
        "customer_who": "",
        "customer_type": "b2b",
        "first_customer": {"name": "", "email": "", "phone": ""},
        "currency": "COP",
        "fiscal_year_start": "01-01",
        "tax_id": "",
        "charges_iva": False,
        "payment_methods": [],
        "team_mode": "solo",
        "roles": [],
        "modules": {key: False for key in INTERVIEW_MODULES},
        "fact_visibility": {},
        "phase_name": "",
        "lots": [],
        "argos_consent": "",
    }


def sanitize_interview_answers(raw: Optional[dict]) -> dict:
    """Keep a known shape. Defaults: Colombia, COP, tools off."""
    base = empty_interview_answers()
    raw = raw if isinstance(raw, dict) else {}
    text_limits = {
        "legal_name": 200,
        "trade_name": 200,
        "city": 80,
        "email": 160,
        "phone": 40,
        "website": 200,
        "industry_description": 2000,
        "customer_who": 1000,
        "tax_id": 40,
    }
    for key, limit in text_limits.items():
        if key in raw:
            base[key] = _clip(raw.get(key), limit)
    if "country" in raw:
        base["country"] = _clip(raw.get("country"), 80) or "Colombia"
    if not base["country"]:
        base["country"] = "Colombia"
    base["template"] = _template_id(raw.get("template"))
    base["sells"] = _choice(raw.get("sells"), {"servicios", "productos", "ambos"}, "ambos")
    base["customer_type"] = _choice(raw.get("customer_type"), {"b2b", "b2c", "ambos"}, "b2b")
    base["team_mode"] = _choice(raw.get("team_mode"), {"solo", "equipo"}, "solo")
    base["currency"] = _clip(raw.get("currency"), 8).upper()
    if base["currency"] not in {"COP", "USD"}:
        base["currency"] = "COP"
    base["fiscal_year_start"] = _fiscal_year_start(raw.get("fiscal_year_start"))
    base["charges_iva"] = _as_bool(raw.get("charges_iva"))
    base["payment_methods"] = _payment_methods(raw.get("payment_methods"))
    base["roles"] = _roles(raw.get("roles"))
    base["items"] = _sanitize_items(raw.get("items"))
    base["first_customer"] = _customer(raw.get("first_customer"))
    base["modules"] = _modules_map(raw.get("modules"))
    base["fact_visibility"] = _visibility_map(raw.get("fact_visibility"))
    base["phase_name"] = _clip(raw.get("phase_name"), 80)
    base["lots"] = _sanitize_lots(raw.get("lots"))
    base["argos_consent"] = _choice(raw.get("argos_consent"), {"all", "public", "later"}, "")
    return base


def _visibility_map(raw) -> dict:
    if not isinstance(raw, dict):
        return {}
    out = {}
    for key, value in list(raw.items())[:80]:
        key_s = _clip(key, 80)
        vis = _clip(value, 20).lower()
        if key_s and vis in {"public", "confidential"}:
            out[key_s] = vis
    return out


def _sanitize_lots(raw) -> list[dict]:
    if not isinstance(raw, list):
        return []
    statuses = {"available", "reserved", "sold", "under_construction", "delivered", "hold", "consultar"}
    lots = []
    for row in raw[:40]:
        if not isinstance(row, dict):
            continue
        number = _clip(row.get("lot_number"), 40)
        if not number:
            continue
        status = _clip(row.get("status"), 40).lower() or "available"
        if status not in statuses:
            status = "available"
        lots.append({
            "lot_number": number,
            "status": status,
            "area_m2": _optional_number(row.get("area_m2")),
            "price": _price_or_none(row.get("price")),
        })
    return lots


def _optional_number(value):
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _interview_email(email: str) -> str:
    cleaned = (email or "").strip().lower()
    if "@" not in cleaned or len(cleaned) > 200 or "/" in cleaned or "\\" in cleaned:
        raise ValueError("Se necesita una sesión para la entrevista")
    return cleaned


def _drafts_dir() -> Path:
    return assert_under_root(require_data_root() / "businesses" / "interview-drafts")


def _draft_path(email: str) -> Path:
    digest = hashlib.sha256(email.encode("utf-8")).hexdigest()[:12]
    return assert_under_root(_drafts_dir() / f"{safe_slug(email)}-{digest}.json")


def _step(value) -> int:
    try:
        step = int(value)
    except (TypeError, ValueError):
        step = 0
    return max(0, min(step, INTERVIEW_LAST_STEP))


def _empty_draft(email: str) -> dict:
    answers = empty_interview_answers()
    from app.services.edition_facts import confirm_items_for_answers
    return {
        "email": email,
        "status": "empty",
        "step": 0,
        "answers": answers,
        "confirm_items": confirm_items_for_answers(answers),
        "updated_at": None,
        "assistant": assistant_name(),
    }


def _read_draft_file(email: str) -> Optional[dict]:
    path = _draft_path(email)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _merge_answers(current: dict, incoming: Optional[dict]) -> dict:
    merged = empty_interview_answers()
    if isinstance(current, dict):
        merged.update(current)
    incoming = incoming if isinstance(incoming, dict) else {}
    modules = _modules_map(merged.get("modules"))
    if isinstance(incoming.get("modules"), dict):
        for key, value in incoming["modules"].items():
            if key in modules:
                modules[key] = _as_bool(value)
    customer = _customer(merged.get("first_customer"))
    if isinstance(incoming.get("first_customer"), dict):
        customer.update(_customer(incoming.get("first_customer")))
        # _customer clips; also keep keys the patch set to empty on purpose.
        for key in ("name", "email", "phone"):
            if key in incoming["first_customer"]:
                customer[key] = _clip(incoming["first_customer"].get(key), 160 if key != "phone" else 40)
    rest = {key: value for key, value in incoming.items() if key not in {"modules", "first_customer"}}
    merged.update(rest)
    merged["modules"] = modules
    merged["first_customer"] = customer
    return sanitize_interview_answers(merged)


def get_interview_draft(email: str) -> dict:
    """The caller's draft. A missing file is an empty interview, not an error."""
    owner = _interview_email(email)
    data = _read_draft_file(owner)
    if not data:
        return _empty_draft(owner)
    answers = sanitize_interview_answers(data.get("answers"))
    from app.services.edition_facts import confirm_items_for_answers
    payload = {
        "email": owner,
        "status": "draft",
        "step": _step(data.get("step")),
        "answers": answers,
        "confirm_items": confirm_items_for_answers(answers),
        "updated_at": data.get("updated_at"),
        "assistant": assistant_name(),
    }
    return payload


def save_interview_draft(email: str, *, step: int = 0, answers: Optional[dict] = None) -> dict:
    """Merge and store a half-done interview for this user."""
    owner = _interview_email(email)
    current = get_interview_draft(owner)
    payload = {
        "email": owner,
        "status": "draft",
        "step": _step(step),
        "answers": _merge_answers(current.get("answers") or {}, answers),
        "updated_at": _now(),
        "assistant": assistant_name(),
    }
    path = _draft_path(owner)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if is_maxine():
        from app.services.argos_review import sync_argos_consent
        payload["argos_review"] = sync_argos_consent(payload["answers"])
    return payload


def clear_interview_draft(email: str) -> None:
    path = _draft_path(_interview_email(email))
    if path.is_file():
        path.unlink()


def _reject_unknown_template(raw: Optional[dict]) -> None:
    if not isinstance(raw, dict) or "template" not in raw:
        return
    key = _clip(raw.get("template"), 40).lower()
    if key and key not in BLANK_TEMPLATES and key not in TEMPLATES:
        raise ValueError("Plantilla desconocida")


def _category_dict(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "price": _json_price(row["price"]),
    }


def _add_starter_items(slug: str, items: list[dict]) -> list[dict]:
    conn = _connect(slug)
    for item in items:
        conn.execute(
            "INSERT INTO service_categories (id, name, description, price) VALUES (?,?,?,?)",
            (
                str(uuid.uuid4()),
                item["name"],
                item.get("description") or item.get("kind") or "",
                item.get("price"),
            ),
        )
    conn.commit()
    rows = conn.execute("SELECT id, name, description, price FROM service_categories").fetchall()
    conn.close()
    categories = [_category_dict(row) for row in rows]
    path = assert_under_root(business_dir(slug) / "business.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["service_categories"] = [
        {"name": row["name"], "description": row["description"], "price": row["price"]}
        for row in categories
    ]
    _write_profile(slug, data)
    return categories


def finish_interview(email: str, *, step: int = INTERVIEW_LAST_STEP, answers: Optional[dict] = None) -> dict:
    """Create the company from the saved draft plus this screen's answers."""
    owner = _interview_email(email)
    current = get_interview_draft(owner)
    _reject_unknown_template(answers if isinstance(answers, dict) else None)
    # Also reject a bad template that was only saved on the draft.
    draft_answers = current.get("answers") if isinstance(current.get("answers"), dict) else {}
    if isinstance(answers, dict) and "template" not in answers:
        _reject_unknown_template(draft_answers)
    clean = _merge_answers(draft_answers, answers)
    if not clean["legal_name"]:
        raise ValueError("El nombre legal de la empresa es obligatorio")
    enabled = [key for key in INTERVIEW_MODULES if clean["modules"].get(key)]
    created = create_business(
        name=clean["legal_name"],
        industry="",
        description=clean["industry_description"],
        template=clean["template"] or None,
        modules=enabled,
        extra={
            "legal_name": clean["legal_name"],
            "trade_name": clean["trade_name"],
            "country": clean["country"],
            "city": clean["city"],
            "contact_email": clean["email"],
            "contact_phone": clean["phone"],
            "website": clean["website"],
            "currency": clean["currency"],
            "fiscal_year_start": clean["fiscal_year_start"],
            "tax_id": clean["tax_id"],
            "charges_iva": clean["charges_iva"],
            "payment_methods": clean["payment_methods"],
            "customer_type": clean["customer_type"],
            "customer_who": clean["customer_who"],
            "team_mode": clean["team_mode"],
            "roles": clean["roles"],
            "sells": clean["sells"],
            "starter_items": clean["items"],
            "interview": clean,
            "setup": "entrevista",
        },
    )
    created["service_categories"] = _add_starter_items(created["slug"], clean["items"])
    customer = clean["first_customer"]
    if customer.get("name"):
        add_contact(
            created["slug"],
            name=customer["name"],
            email=customer.get("email") or "",
            phone=customer.get("phone") or "",
        )
    created["contacts"] = list_contacts(created["slug"])
    from app.services.edition_facts import persist_interview_facts
    persist_interview_facts(clean)
    if is_maxine():
        from app.services.argos_review import sync_argos_consent
        created["argos_review"] = sync_argos_consent(clean)
    if is_maxine():
        from app.services.construction_bridge import materialize_from_interview
        created = materialize_from_interview(created, clean)
    clear_interview_draft(owner)
    save_step = _step(step)
    created["interview_step"] = save_step
    return created


def add_contact(slug: str, *, name: str, email: str = "", phone: str = "", fields: Optional[dict] = None) -> dict:
    if get_business(slug) is None:
        raise ValueError("Empresa no encontrada")
    if is_maxine():
        from app.services.construction_bridge import upsert_buyer
        buyer = upsert_buyer(name=name, email=email, phone=phone, project_id=None, notes="")
        return {
            "id": buyer["id"],
            "name": name.strip(),
            "email": email or "",
            "phone": phone or "",
            "fields_json": "{}",
            "model": "constructionforge",
        }
    row = {
        "id": str(uuid.uuid4()),
        "name": name.strip(),
        "email": (email or "").strip(),
        "phone": (phone or "").strip(),
        "fields_json": json.dumps(fields or {}, ensure_ascii=False),
    }
    conn = _connect(slug)
    conn.execute(
        "INSERT INTO crm_contacts (id, name, email, phone, fields_json) VALUES (?,?,?,?,?)",
        (row["id"], row["name"], row["email"], row["phone"], row["fields_json"]),
    )
    conn.commit()
    conn.close()
    return row


def list_contacts(slug: str) -> list[dict]:
    if get_business(slug) is None:
        raise ValueError("Empresa no encontrada")
    if is_maxine():
        from app.services.construction_bridge import buyers_as_contacts
        return buyers_as_contacts(slug)
    conn = _connect(slug)
    rows = conn.execute("SELECT * FROM crm_contacts ORDER BY created_at").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_categories(slug: str) -> list[dict]:
    if get_business(slug) is None:
        raise ValueError("Empresa no encontrada")
    conn = _connect(slug)
    rows = conn.execute("SELECT * FROM service_categories").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def workspace_summary(slug: str) -> dict:
    business = get_business(slug)
    if business is None:
        raise ValueError("Empresa no encontrada")
    root = business_dir(slug)
    return {
        **business,
        "data_dir": str(root),
        "contacts": list_contacts(slug),
        "service_categories": list_categories(slug),
        "modules": business.get("modules") or list(SHARED_MODULES),
        "industry_modules": [],
    }


def write_generated_note(slug: str, title: str, body: str) -> Path:
    """A generated document signed by this instance's assistant."""
    if get_business(slug) is None:
        raise ValueError("Empresa no encontrada")
    from app.services.edition_facts import guard_public_text, public_facts_block

    name = assistant_name()
    path = business_dir(slug) / "generated" / f"{safe_slug(title) or 'nota'}.md"
    path = assert_under_root(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_body = guard_public_text(body)
    public = public_facts_block()
    extra = f"\n{public}\n" if public else ""
    path.write_text(
        f"# {title}\n\nPreparado por {name}.\n\n{safe_body}\n{extra}",
        encoding="utf-8",
    )
    return path
