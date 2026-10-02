"""Maxine asks before any Argos import. Sí opens Rafael's task and Camilo's queue."""
from __future__ import annotations

import json
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


def test_welcome_asks_argos_early_and_max_e_does_not():
    script = """
import { ARGOS_OPTIONS, ARGOS_QUESTION, interviewSteps, welcomeCopy } from './empire-command-center/app/lib/interviewWelcome.mjs';
if (!ARGOS_QUESTION.es.includes('correos y archivos 2021–2024, planos')) throw new Error(ARGOS_QUESTION.es);
if (!ARGOS_QUESTION.es.includes('para que yo la revise contigo')) throw new Error('review');
const labels = ARGOS_OPTIONS.map((row) => row.es);
if (labels.join('|') !== 'Sí, cargar todo|Solo lo público|Ahora no') throw new Error(labels.join('|'));
if (!ARGOS_OPTIONS[0].detailEs.includes('Importación Argos pendiente')) throw new Error('task');
if (!ARGOS_OPTIONS[1].detailEs.toLowerCase().includes('semilla pública')) throw new Error('public seed');
const maxine = welcomeCopy('maxine');
const names = maxine.sections.map((row) => row.es);
if (names[0] !== 'Tu empresa' || !names.some((name) => name.includes('etapas y lotes'))) throw new Error(names.join('|'));
if (!maxine.argosNoteEs.includes('Confidencial')) throw new Error('note');
const steps = interviewSteps('maxine').map((row) => row.id);
if (steps[0] !== 'bienvenida' || steps[1] !== 'argos') throw new Error(steps.join(','));
const maxe = welcomeCopy('amp');
if (maxe.argosNoteEs || maxe.argosNoteEn) throw new Error('max-e note');
if (interviewSteps('amp').some((row) => row.id === 'argos')) throw new Error('amp step');
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
    assert "ARGOS_QUESTION" in page
    assert "ArgosReviewQueue" in page
    assert "Cola de revisión" in page


def test_seed_stays_public_and_has_no_gac_legal_record(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.argos_review import review_state
    from app.services.edition_facts import list_facts
    from app.services.edition_seed import load_edition_seed

    load_edition_seed()
    blob = "\n".join(fact["text"] for fact in list_facts())
    assert "321 495 0275" in blob
    assert "Limonar" not in blob
    assert review_state()["active"] is False
    for path in Path(tmp_path, "businesses").rglob("*.json"):
        raw = path.read_text(encoding="utf-8")
        assert "tax_id" not in raw
        assert "NIT" not in raw
        assert "legal_name" not in raw


def test_yes_creates_one_owner_task_and_a_confidential_queue(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.amp_businesses import save_interview_draft
    from app.services.argos_review import TASK_TITLE, decide_item, enqueue_item, review_state
    from app.services.edition_facts import list_facts, public_facts_block

    first = save_interview_draft("owner@example.com", step=1, answers={"argos_consent": "all"})
    second = save_interview_draft("owner@example.com", step=1, answers={"argos_consent": "all"})
    assert first["argos_review"]["task"]["title"] == TASK_TITLE
    assert first["argos_review"]["task"]["id"] == second["argos_review"]["task"]["id"]
    assert first["argos_review"]["task"]["assigned_to"] == "owner@example.com"
    assert first["argos_review"]["task"]["owner_name"] == "Rafael"
    assert first["argos_review"]["task"]["status"] == "todo"
    assert "NIT" in first["argos_review"]["task"]["description"]
    assert "datos legales" in first["argos_review"]["task"]["description"]
    assert first["argos_review"]["items"] == []
    assert [fact for fact in list_facts() if str(fact.get("source")) == "argos"] == []

    item = enqueue_item(title="Plano 2022", text="Plano de un lote, sin precio y sin NIT.")
    assert item["visibility"] == "confidential"
    assert item["status"] == "pending"
    assert review_state()["items"][0]["id"] == item["id"]
    assert all(fact.get("text") != item["text"] for fact in list_facts())
    assert item["text"] not in public_facts_block()

    hidden = decide_item(item["id"], "confidential")
    assert hidden["fact"]["visibility"] == "confidential"
    stored = next(fact for fact in list_facts() if fact["key"] == hidden["fact"]["key"])
    assert stored["visibility"] == "confidential"
    assert item["text"] not in public_facts_block()

    shown = decide_item(item["id"], "public")
    assert shown["fact"]["visibility"] == "public"
    assert item["text"] in public_facts_block()


def test_public_only_keeps_the_seed_and_drops_the_import(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.amp_businesses import finish_interview, save_interview_draft
    from app.services.argos_review import enqueue_item, review_state
    from app.services.edition_facts import list_facts, upsert_fact
    from app.services.edition_seed import load_edition_seed

    load_edition_seed()
    save_interview_draft("owner@example.com", step=1, answers={"argos_consent": "all"})
    enqueue_item(title="Correo 2021", text="Un correo que no debe quedar si él dice solo lo público.")
    upsert_fact(key="argos:old", text="Pieza vieja", value="Pieza vieja", visibility="confidential", source="argos")

    finish_interview(
        "owner@example.com",
        step=10,
        answers={"legal_name": "Proyecto de Camilo", "argos_consent": "public"},
    )
    state = review_state()
    assert state["active"] is False
    assert state["task"] is None
    assert state["items"] == []
    facts = list_facts()
    assert all(fact.get("source") != "argos" for fact in facts)
    assert any("321 495 0275" in fact["text"] for fact in facts)
    blob = json.dumps(facts, ensure_ascii=False)
    assert "Un correo que no debe quedar" not in blob
    assert "Pieza vieja" not in blob


def test_not_now_and_max_e_do_not_open_the_import(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.amp_businesses import finish_interview, save_interview_draft
    from app.services.argos_review import review_state

    save_interview_draft("owner@example.com", step=1, answers={"argos_consent": "later"})
    assert review_state()["active"] is False
    finish_interview("owner@example.com", step=10, answers={"legal_name": "Sin importar", "argos_consent": "later"})
    assert not (tmp_path / "argos_review.json").read_text(encoding="utf-8").count("Importación Argos pendiente")

    amp_root = tmp_path / "amp"
    _env(monkeypatch, amp_root, "amp")
    finish_interview("owner@example.com", step=9, answers={"legal_name": "AMP", "argos_consent": "all"})
    assert review_state()["active"] is False
    assert not (amp_root / "argos_review.json").exists()
