"""Standard job document names: Client_Area_DocType_REV# plus _INTERNAL."""
from __future__ import annotations

import re
from pathlib import Path

from app.services.job_stages.catalog import DOC_TYPE_SLUGS, infer_stage_key

_SAFE = re.compile(r"[^A-Za-z0-9]+")
_REV = re.compile(r"_REV(\d+)", re.I)
_STANDARD = re.compile(
    r"^(?P<client>[A-Za-z0-9]+)_"
    r"(?P<area>[A-Za-z0-9]+)_"
    r"(?P<doc_type>[A-Za-z0-9]+)_"
    r"REV(?P<rev>\d+)"
    r"(?P<internal>_INTERNAL)?"
    r"(?P<ext>\.[A-Za-z0-9]+)?$",
    re.I,
)


def slug_part(value: str | None, fallback: str) -> str:
    text = _SAFE.sub("", (value or "").strip())
    return text or fallback


def doc_type_slug(stage_key: str | None, document_type: str | None = None) -> str:
    if stage_key and stage_key in DOC_TYPE_SLUGS:
        return DOC_TYPE_SLUGS[stage_key]
    inferred = infer_stage_key(document_type or stage_key)
    if inferred and inferred in DOC_TYPE_SLUGS:
        return DOC_TYPE_SLUGS[inferred]
    return slug_part(document_type or stage_key, "Document")


def build_standard_name(
    *,
    client: str | None,
    area: str | None,
    doc_type: str | None,
    revision: int,
    internal: bool = False,
    extension: str | None = None,
    stage_key: str | None = None,
) -> str:
    """Client_Area_DocType_REV# plus _INTERNAL for internal copies."""
    client_part = slug_part(client, "Client")
    area_part = slug_part(area, "Area")
    type_part = doc_type_slug(stage_key, doc_type)
    rev = max(1, int(revision or 1))
    name = f"{client_part}_{area_part}_{type_part}_REV{rev}"
    if internal:
        name += "_INTERNAL"
    ext = (extension or "").strip()
    if ext and not ext.startswith("."):
        ext = f".{ext}"
    return f"{name}{ext}"


def parse_standard_name(filename: str | None) -> dict | None:
    if not filename:
        return None
    match = _STANDARD.match(Path(filename).name)
    if not match:
        return None
    return {
        "client": match.group("client"),
        "area": match.group("area"),
        "doc_type": match.group("doc_type"),
        "revision": int(match.group("rev")),
        "internal": bool(match.group("internal")),
        "extension": match.group("ext") or "",
    }


def revision_from_name(filename: str | None) -> int | None:
    parsed = parse_standard_name(filename)
    if parsed:
        return parsed["revision"]
    if not filename:
        return None
    match = _REV.search(filename)
    return int(match.group(1)) if match else None


def next_revision(existing_filenames: list[str], *, internal: bool | None = None) -> int:
    """Next REV# for this document family. New revision supersedes older docs."""
    highest = 0
    for name in existing_filenames or []:
        parsed = parse_standard_name(name)
        if parsed:
            if internal is not None and parsed["internal"] != internal:
                continue
            highest = max(highest, parsed["revision"])
            continue
        found = revision_from_name(name)
        if found:
            highest = max(highest, found)
    return highest + 1


def family_key(
    *,
    client: str | None,
    area: str | None,
    doc_type: str | None,
    stage_key: str | None = None,
    internal: bool = False,
) -> str:
    return "|".join((
        slug_part(client, "Client").lower(),
        slug_part(area, "Area").lower(),
        doc_type_slug(stage_key, doc_type).lower(),
        "internal" if internal else "client",
    ))
