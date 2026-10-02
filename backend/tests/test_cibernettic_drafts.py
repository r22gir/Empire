"""Cibernettic outlines are Spanish drafts. They do not invent clauses or prices."""
from __future__ import annotations

import re


def test_every_line_has_four_empty_spanish_drafts():
    from app.services.voice_doc.cibernettic_drafts import DOCUMENTS, SERVICE_LINES, list_drafts

    rows = list_drafts()
    assert len(rows) == len(SERVICE_LINES) * len(DOCUMENTS)
    titles = {row["title"] for row in rows}
    assert any(title.startswith("Propuesta de servicios · Ciberseguridad") for title in titles)
    assert any("Gestión de datos" in title for title in titles)
    assert any("DBA" in title for title in titles)
    assert any("Redes y VoIP" in title for title in titles)
    assert any("Inteligencia de negocios (BI)" in title for title in titles)
    assert any(title.startswith("Acuerdo de nivel de servicio") for title in titles)
    assert any(title.startswith("Acuerdo de confidencialidad") for title in titles)
    assert any(title.startswith("Contrato de servicios") for title in titles)
    for row in rows:
        assert row["locale"] == "es"
        assert row["status"] == "draft"
        assert row["sent"] is False
        assert row["approved_by_lawyer"] is False
        body = row["body"]
        assert body.startswith("BORRADOR – requiere revisión de abogado")
        assert "{{precio}}" in body
        assert "{{cliente}}" in body
        assert "{{contenido_abogado}}" in body
        assert "se obliga" not in body.lower()
        assert "GAC" not in body
        assert "Grupo Argos" not in body
        assert "NIT" not in body
        assert not re.search(r"\$\s*\d", body)
        assert not re.search(r"\b\d[\d.]{2,}\b", body)


def test_a_spoken_price_stays_out_of_the_draft_outline(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VOICE_DRAFTS_DB", str(tmp_path / "voice_drafts.db"))
    from app.services.voice_doc.pipeline import ingest_transcript
    from app.services.voice_doc.store import get_draft

    view = ingest_transcript(
        "Propuesta de ciberseguridad para Empresa Demo por 2500 dólares. listo",
        channel="web",
        edition="amp",
    )
    draft = get_draft(view["draft"]["id"])
    outlines = draft["payload"]["service_drafts"]
    assert len(outlines) == 4
    assert all(item["service_line"] == "ciberseguridad" for item in outlines)
    assert all(item["sent"] is False for item in outlines)
    joined = "\n".join(item["body"] for item in outlines)
    assert "2500" not in joined
    assert "{{precio}}" in joined
