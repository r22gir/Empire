"""Load a family-edition seed file as public facts and starting records.

Maxine's seed creates two ConstructionForge projects under the GAC sales
brand. Numbers are taken from the file. Missing per-lot areas and prices
stay unset. No legal entity is created for GAC.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional

from app.edition import edition_name, is_maxine, require_data_root


def seed_path(explicit: Optional[str] = None) -> Path:
    raw = (explicit or os.getenv("EMPIRE_SEED_FILE", "")).strip()
    if raw:
        return Path(raw).expanduser()
    return Path(__file__).resolve().parents[3] / "deploy" / "seeds" / f"{edition_name()}-seed.md"


def _section(text: str, heading: str) -> str:
    """Body of one ### project. Stops at the next ## or ### heading.

    Portal Campestre 2 is the last ### in the Maxine seed. The Argos
    section and the day-one questions are ## headings after it, and they
    must not become part of the project description.
    """
    pattern = re.compile(rf"^###\s+{re.escape(heading)}.*$", re.M)
    match = pattern.search(text)
    if not match:
        raise ValueError(f"La semilla no trae la sección {heading}")
    rest = text[match.end():]
    nxt = re.search(r"^#{2,3}\s+", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def _euro_number(raw: str) -> float:
    return float(raw.replace(".", "").replace(",", ".")) if raw.count(",") == 1 and raw.count(".") >= 1 else float(
        raw.replace(",", ".")
    )


def _facts_from_markdown(text: str) -> list[dict]:
    """Public lines, except the day-one question list which stays confidential.

    Argos Campestre is not loaded here. Maxine asks first, and those lines
    stay confidential until Camilo approves them.
    """
    facts = []
    confidential = False
    skipping_argos = False
    index = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Earlier project: Argos Campestre"):
            skipping_argos = True
            continue
        if skipping_argos:
            if stripped.startswith("## "):
                skipping_argos = False
            else:
                continue
        if stripped.startswith("## Things to ask"):
            confidential = True
            continue
        if stripped.startswith("#"):
            continue
        if not stripped:
            continue
        body = stripped[2:].strip() if stripped.startswith("- ") else stripped
        if len(body) < 8:
            continue
        index += 1
        facts.append({
            "key": f"seed:{index}",
            "text": body,
            "value": body[:240],
            "label": body[:80],
            "visibility": "confidential" if confidential else "public",
            "source": "seed-question" if confidential else "seed",
        })
    return facts


def _store_facts(facts: list[dict]) -> int:
    from app.services.edition_facts import upsert_fact

    for fact in facts:
        upsert_fact(
            key=fact["key"],
            text=fact["text"],
            value=fact["value"],
            label=fact["label"],
            visibility=fact["visibility"],
            source=fact["source"],
        )
    return len(facts)


def _parse_rincon(section: str) -> dict:
    pairs = re.findall(r"(\d{3})\s+and\s+(\d{3})\s+at\s+([\d,\.]+)\s*m", section, re.I)
    if len(pairs) < 2:
        raise ValueError("La semilla de Rincón no trae las áreas de los apartaestudios")
    lots = []
    for left, right, area in pairs:
        meters = _euro_number(area)
        for number in (left, right):
            lots.append({
                "lot_number": number,
                "status": "under_construction",
                "area_m2": meters,
                "price": None,
            })
    if len(lots) != 4:
        raise ValueError("Rincón debe traer 4 unidades, no un número inventado")
    return {
        "name": "Rincón de San Jerónimo",
        "slug": "rincon-de-san-jeronimo",
        "location": "B/ San Jerónimo, Calle 7, Cartago",
        "status": "under_construction",
        "phase": "En ejecución",
        "description": section.strip()[:1200],
        "lots": lots,
        "builder": "OCMA" if "OCMA" in section else None,
    }


def _parse_portal(section: str) -> dict:
    def count(word: str) -> int:
        match = re.search(rf"(\d+)\s+{word}", section, re.I)
        if not match:
            raise ValueError(f"La semilla de Portal Campestre 2 no trae el conteo «{word}»")
        return int(match.group(1))

    available = count("disponibles")
    reserved = count("separados")
    sold = count("vendidos")
    consultar = count("consultar")
    houses = re.search(r"(\d+)\s+single-level houses", section, re.I)
    if not houses:
        raise ValueError("La semilla no dice cuántas casas tiene Portal Campestre 2")
    total = int(houses.group(1))
    counted = available + reserved + sold + consultar
    if counted != total:
        raise ValueError(
            f"Los estados del Portal suman {counted} y el texto dice {total}. No completo la diferencia."
        )
    lots = []
    number = 1
    for status, amount in (
        ("available", available),
        ("reserved", reserved),
        ("sold", sold),
        ("consultar", consultar),
    ):
        for _ in range(amount):
            lots.append({
                "lot_number": str(number),
                "status": status,
                "area_m2": None,
                "price": None,
            })
            number += 1
    return {
        "name": "Portal Campestre 2",
        "slug": "portal-campestre-2",
        "location": "Zaragoza, sala de ventas Calle 12 # 3-18",
        "status": "active",
        "phase": "Vivienda campestre",
        "description": section.strip()[:1200],
        "lots": lots,
        "builder": None,
    }


def _register_business(project: dict, project_id: str) -> None:
    """A project is the business. Brand GAC, no legal name and no NIT."""
    from app.edition import assistant_name
    from app.services import amp_businesses

    registry = amp_businesses._load_registry()
    profile = {
        "slug": project["slug"],
        "name": project["name"],
        "brand": "GAC",
        "industry": "desarrollo inmobiliario",
        "description": project["description"],
        "template": None,
        "locale": "es",
        "modules": ["crm", "quotes", "leadforge", "socialforge"],
        "industry_modules": [],
        "assistant": assistant_name(),
        "model": "constructionforge",
        "cf_project_id": project_id,
        "currency": "COP",
        "country": "Colombia",
        "city": "Cartago" if "Cartago" in project["location"] else "Zaragoza",
    }
    replaced = False
    for index, row in enumerate(registry["businesses"]):
        if row.get("slug") == project["slug"]:
            registry["businesses"][index] = {**row, **profile}
            replaced = True
            break
    if not replaced:
        registry["businesses"].append(profile)
    amp_businesses._save_registry(registry)
    amp_businesses._write_profile(project["slug"], profile)


def _projects_from_seed(text: str) -> list[dict]:
    return [
        _parse_rincon(_section(text, "Rincón de San Jerónimo")),
        _parse_portal(_section(text, "Portal Campestre 2")),
    ]


def _apply_projects(projects: list[dict]) -> list[dict]:
    """Create or refresh each project. Lots that already exist are left in place."""
    from app.services.construction_bridge import ensure_phase, ensure_project, insert_lot

    created = []
    for project in projects:
        row = ensure_project(
            name=project["name"],
            slug=project["slug"],
            location=project["location"],
            description=project["description"],
            status=project["status"],
            currency="COP",
            total_lots=len(project["lots"]),
        )
        phase = ensure_phase(
            row["id"],
            project["phase"],
            total_lots=len(project["lots"]),
            status=project["status"],
        )
        for lot in project["lots"]:
            insert_lot(
                project_id=row["id"],
                phase_id=phase["id"],
                lot_number=lot["lot_number"],
                status=lot["status"],
                area_m2=lot["area_m2"],
                price=lot["price"],
            )
        if project["builder"]:
            _ensure_builder(project["builder"])
        _register_business(project, row["id"])
        created.append({"slug": project["slug"], "id": row["id"], "lots": len(project["lots"])})
    return created


def load_maxine_seed(text: str) -> dict:
    projects = _projects_from_seed(text)
    fact_count = _store_facts(_facts_from_markdown(text))
    created = _apply_projects(projects)
    return {"edition": "maxine", "facts": fact_count, "projects": created, "brand": "GAC"}


def _ensure_builder(name: str) -> None:
    from app.services.construction_bridge import _db

    conn = _db()
    try:
        row = conn.execute("SELECT id FROM cf_contractors WHERE name = ?", (name,)).fetchone()
        if row:
            return
        import uuid
        conn.execute(
            "INSERT INTO cf_contractors (id, name, specialty, notes) VALUES (?,?,?,?)",
            (str(uuid.uuid4()), name, "construcción", "Nombrado en la semilla pública. Sin NIT."),
        )
        conn.commit()
    finally:
        conn.close()


def load_edition_seed(path: Optional[str] = None) -> dict:
    if not is_maxine() and edition_name() != "maxine":
        raise RuntimeError("Esta semilla es de la edición maxine")
    file_path = seed_path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"No está el archivo de semilla: {file_path}")
    text = file_path.read_text(encoding="utf-8")
    if "Rincón de San Jerónimo" not in text or "Portal Campestre 2" not in text:
        raise ValueError("La semilla no trae los dos proyectos")
    result = load_maxine_seed(text)
    marker = require_data_root() / "seed_loaded.json"
    marker.write_text(json.dumps({"path": str(file_path), "projects": result["projects"]}, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def refresh_seed_projects() -> Optional[dict]:
    """Rewrite project copy from the seed file without adding lots or facts.

    A data dir that already has seed_loaded.json still picks this up on the
    next start, so a description that absorbed later sections gets replaced.
    """
    if not is_maxine():
        return None
    file_path = seed_path()
    if not file_path.is_file():
        return None
    text = file_path.read_text(encoding="utf-8")
    created = _apply_projects(_projects_from_seed(text))
    return {"edition": "maxine", "refreshed": True, "projects": created, "brand": "GAC"}


def maybe_load_seed() -> Optional[dict]:
    """Load the Maxine seed, then keep project descriptions aligned with the file.

    The marker records the first load. It does not skip the description
    refresh: the next process start rewrites the existing rows.
    """
    if not is_maxine():
        return None
    root = require_data_root()
    if (root / "seed_loaded.json").is_file():
        return refresh_seed_projects()
    return load_edition_seed()
