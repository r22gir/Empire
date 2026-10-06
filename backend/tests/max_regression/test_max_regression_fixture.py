"""Offline checks for the Max regression fixture and scorer (no model, no data)."""
import json
from pathlib import Path

from tests.max_regression.scoring import gate, score_answer, summarize

FIXTURE = json.loads((Path(__file__).with_name("questions.json")).read_text())
QS = {q["id"]: q for q in FIXTURE["questions"]}


def test_fixture_shape():
    assert 40 <= len(QS) <= 60
    assert len(QS) == len(FIXTURE["questions"])
    kinds = {q["kind"] for q in QS.values()}
    for k in ("quote_number", "quote_client", "send_me", "file_find", "status", "solar", "research",
              "email_me", "alias", "small_talk", "spanish", "multi_part"):
        assert k in kinds, k
    for q in QS.values():
        assert q["channel"] in ("studio", "whatsapp")
        assert q["message"].strip() and isinstance(q["expect"], dict)


def test_scorer_flags_real_bad_answers():
    changelog = ("Here's what's new:\n\n- Recent live changes:\n  • 9974207c — Fix Max PDF/document attachments\n"
                 "- Status: Live backend (8000) is up")
    s = score_answer(QS["q28"], {"text": changelog, "tools": ["shortcut:whats_new"]})
    assert not s["route"] and not s["grounded"] and not s["clean"]
    raw = "I have not run that yet. Claim 'I read' has no structured proof object. MAX must say 'I have not run that yet.'"
    assert not score_answer(QS["q52"], {"text": raw, "tools": ["model"]})["clean"]
    status = ("I still need to know which document.\n\n**Status**\n\n**Done**\n- (none yet)\n\n**Not done**\n- Generate PDF(s)"
              "\n\n**To finish**\nSay: \"Run send_quote_email for each quote_id to the recipient.\"")
    assert not score_answer(QS["q21"], {"text": status, "tools": ["model"]})["clean"]
    assert not score_answer(QS["q40"], {"text": "IMAGE_NOT_AVAILABLE", "tools": []})["clean"]
    web = "### Verified\n- An article [1](https://example.com/blog)\n\nSources:\n1. https://example.com"
    s = score_answer(QS["q22"], {"text": web, "tools": ["web_search"]})
    assert not s["route"] and not s["concise"]


def test_scorer_passes_good_answers():
    good = "EST-2026-297 for Dahlia Design (Nehal, Phase 1): $3,411.84, still a draft."
    assert score_answer(QS["q01"], {"text": good, "tools": ["get_quote"]}, known_quotes={"EST-2026-297"})["pass"]
    s = score_answer(QS["q01"], {"text": good.replace("297", "999"), "tools": ["get_quote"]}, known_quotes={"EST-2026-297"})
    assert not s["grounded"]
    hi = "Good evening, Rafael. What can I do for you?"
    assert score_answer(QS["q41"], {"text": hi, "tools": []})["pass"]
    es = "La última cotización de Dahlia es EST-2026-298, la fase 2, por $9,350.76. Está en borrador."
    assert score_answer(QS["q46"], {"text": es, "tools": ["search_quotes"]})["pass"]


def test_gate():
    base = {"route": 30, "grounded": 30, "concise": 30, "clean": 30, "pass": 20, "total": 55}
    better = dict(base, route=35, **{"pass": 25})
    assert gate(base, better)[0]
    worse = dict(better, clean=29)
    ok, reasons = gate(base, worse)
    assert not ok and any("clean" in r for r in reasons)
    assert not gate(base, dict(base))[0]
    assert summarize({"a": {"route": True, "grounded": True, "concise": False, "clean": True, "pass": False}})["pass"] == 0
