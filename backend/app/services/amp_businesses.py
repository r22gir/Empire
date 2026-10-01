"""Companies inside one AMP instance.

Juan's instance starts with AMP itself. He can create additional blank
companies. Each company gets its own directory under the instance data
root and uses only the shared base modules (CRM, LeadForge, SocialForge,
quotes/invoices, scheduling, finance). No industry-specific modules.

Templates seed service categories and CRM fields only. Prices are never
invented: every price field is null.
"""
from __future__ import annotations

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
    require_data_root,
)

SHARED_MODULES = [m for m in AMP_SHARED_MODULES if m != "amp"]

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
    if not is_amp():
        return []
    ensure_default_business()
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


def create_business(
    *,
    name: str,
    industry: str = "",
    description: str = "",
    template: Optional[str] = None,
) -> dict:
    """Nueva empresa. Blank unless a known template id is passed."""
    if not is_amp():
        raise RuntimeError("Nueva empresa solo existe en la edición AMP")
    cleaned = (name or "").strip()
    if not cleaned:
        raise ValueError("El nombre de la empresa es obligatorio")
    template_id = (template or "").strip().lower() or None
    if template_id and template_id not in TEMPLATES:
        raise ValueError("Plantilla desconocida")
    ensure_default_business()
    registry = _load_registry()
    slug = safe_slug(cleaned)
    taken = {row["slug"] for row in registry["businesses"]}
    base = slug
    n = 2
    while slug in taken:
        slug = f"{base}-{n}"
        n += 1
    profile = {
        "slug": slug,
        "name": cleaned,
        "industry": (industry or "").strip(),
        "description": (description or "").strip(),
        "template": template_id,
        "locale": "es",
        "modules": list(SHARED_MODULES),
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
    return stored


def add_contact(slug: str, *, name: str, email: str = "", phone: str = "", fields: Optional[dict] = None) -> dict:
    if get_business(slug) is None:
        raise ValueError("Empresa no encontrada")
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
    name = assistant_name()
    path = business_dir(slug) / "generated" / f"{safe_slug(title) or 'nota'}.md"
    path = assert_under_root(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# {title}\n\nPreparado por {name}.\n\n{body}\n",
        encoding="utf-8",
    )
    return path
