"""Maxine asks before loading Argos Campestre. Those lines stay confidential until approved."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _env(monkeypatch, tmp_path, edition="maxine"):
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Maxine" if edition == "maxine" else "Max-e")
    monkeypatch.setenv("AMP_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("AMP_JWT_SECRET", "test-secret")
    monkeypatch.delenv("FOUNDER_EMAIL", raising=False)


def test_welcome_lists_sections_and_argos_is_its_own_maxine_screen():
    script = """
import { ARGOS_OPTIONS, interviewSteps, welcomeCopy } from './empire-command-center/app/lib/interviewWelcome.mjs';
const maxine = welcomeCopy('maxine');
const names = maxine.sections.map((row) => row.es);
if (names.join('|') !== 'Tu empresa|Industria|Qué vendes, etapas y lotes|Clientes|Dinero|Equipo|Herramientas|Confirmar datos|Revisión') {
  throw new Error(names.join('|'));
}
if (!maxine.argosNoteEs.includes('Argos Campestre')) throw new Error('note');
if (!maxine.argosNoteEs.includes('Rafael')) throw new Error('rafael');
if (!maxine.argosNoteEs.includes('Confidencial')) throw new Error('confidential');
const maxe = welcomeCopy('amp');
if (maxe.argosNoteEs || maxe.argosNoteEn) throw new Error('max-e argos note');
if (maxe.sections.some((row) => /argos/i.test(row.es + row.en))) throw new Error('max-e section');
if (maxe.sections.some((row) => row.es.includes('etapas'))) throw new Error('max-e lots');
const maxineSteps = interviewSteps('maxine').map((row) => row.id);
if (maxineSteps[0] !== 'bienvenida' || maxineSteps[1] !== 'argos') throw new Error(maxineSteps.join(','));
const ampSteps = interviewSteps('amp').map((row) => row.id);
if (ampSteps.includes('argos')) throw new Error('amp argos step');
if (ampSteps[0] !== 'bienvenida' || ampSteps[1] !== 'empresa') throw new Error(ampSteps.join(','));
const labels = ARGOS_OPTIONS.map((row) => row.es);
if (labels.join('|') !== 'Sí, cargar todo|Solo lo público|Ahora no') throw new Error(labels.join('|'));
process.stdout.write('ok');
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout == "ok"
    page = (ROOT / "empire-command-center" / "app" / "amp" / "empresas" / "entrevista" / "page.tsx").read_text(encoding="utf-8")
    assert "currentId === 'bienvenida'" in page
    assert "currentId === 'argos'" in page
    assert "welcome.argosNoteEs" in page
    revision = page.split("currentId === 'revision'", 1)[1]
    assert 'href="/ayuda/dispositivos"' in revision.split("currentId ===", 1)[0]


def test_seed_does_not_publish_argos_before_consent(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.edition_facts import list_facts
    from app.services.edition_seed import load_edition_seed

    load_edition_seed()
    blob = "\n".join(fact["text"] for fact in list_facts())
    assert "Limonar" not in blob
    assert "#ECA400" not in blob
    assert "170" not in blob
    assert "321 495 0275" in blob


def test_consent_loads_only_the_chosen_argos_lines_as_confidential(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.amp_businesses import finish_interview
    from app.services.edition_facts import list_facts

    finish_interview(
        "owner@example.com",
        step=10,
        answers={"legal_name": "GAC", "argos_consent": "all", "fact_visibility": {"argos:marca": "public"}},
    )
    facts = {fact["key"]: fact for fact in list_facts() if str(fact["key"]).startswith("argos:")}
    assert set(facts) == {"argos:lugar", "argos:planos", "argos:marca"}
    assert facts["argos:lugar"]["visibility"] == "confidential"
    assert facts["argos:planos"]["visibility"] == "confidential"
    assert facts["argos:marca"]["visibility"] == "public"
    joined = "\n".join(fact["text"] for fact in facts.values())
    assert "170 m²" in joined
    assert "#208D63" in joined
    assert "550" not in joined
    assert "NIT" not in joined

    finish_interview(
        "owner@example.com",
        step=10,
        answers={"legal_name": "GAC dos", "argos_consent": "public"},
    )
    facts = {fact["key"]: fact for fact in list_facts() if str(fact["key"]).startswith("argos:")}
    assert set(facts) == {"argos:lugar"}
    assert facts["argos:lugar"]["visibility"] == "confidential"

    finish_interview(
        "owner@example.com",
        step=10,
        answers={"legal_name": "GAC tres", "argos_consent": "later"},
    )
    assert [fact for fact in list_facts() if str(fact["key"]).startswith("argos:")] == []


def test_max_e_does_not_load_argos(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    from app.services.amp_businesses import finish_interview, get_interview_draft
    from app.services.edition_facts import list_facts

    draft = get_interview_draft("owner@example.com")
    assert "argos_catalog" not in draft
    finish_interview(
        "owner@example.com",
        step=9,
        answers={"legal_name": "AMP", "argos_consent": "all"},
    )
    assert [fact for fact in list_facts() if str(fact["key"]).startswith("argos:")] == []
