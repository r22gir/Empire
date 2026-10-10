"""Spanish factual-guard and search-query behavior for Max-e."""
from app.services.max.factual_guard import (
    is_factual_question,
    search_unavailable_reply,
)
from app.services.max.runtime_truth_check import _is_performative_web_search_request
from app.services.max.search_context import build_search_query


def test_spanish_news_question_triggers_search():
    assert is_factual_question("Que paso en Panama")
    assert is_factual_question("Qué pasó en Panamá")
    assert is_factual_question("qué está pasando en Colombia")
    assert is_factual_question("noticias de hoy")
    assert is_factual_question("última hora en Bogotá")
    assert is_factual_question("quién ganó las elecciones")
    assert is_factual_question("cuánto cuesta el dólar")
    assert is_factual_question("cómo está el clima en Medellín")
    assert is_factual_question("cuál es la TRM")
    assert is_factual_question("resultados del partido de ayer")


def test_spanish_evergreen_questions_trigger_search():
    assert is_factual_question("qué es el coaching ontológico")
    assert is_factual_question("cómo funciona una VPN")
    assert is_factual_question("por qué sube el dólar")
    assert is_factual_question("diferencia entre coaching y mentoring")


def test_spanish_chitchat_does_not_trigger_search():
    assert not is_factual_question("hola")
    assert not is_factual_question("gracias")
    assert not is_factual_question("buenos días")
    assert not is_factual_question("cómo estás")


def test_max_e_and_spanish_words_do_not_suppress_search():
    assert is_factual_question("Max-e, qué pasó en Panamá")
    assert is_factual_question("dime el máximo de la TRM hoy")
    assert is_factual_question("alexandra, qué es una VPN")
    assert is_factual_question("el empirebox de Juan: noticias de hoy")


def test_internal_markers_still_block_search():
    assert not is_factual_question("What is the status of quote # EST-2026-293?")
    assert not is_factual_question("What is our founder pricing rule for goblet pleats?")
    assert not is_factual_question("job status of the work order")


def test_spanish_search_verbs_are_performative():
    assert _is_performative_web_search_request("busca las noticias de Panamá")
    assert _is_performative_web_search_request("investiga el dólar hoy")
    assert _is_performative_web_search_request("búscame el clima en Bogotá")
    assert _is_performative_web_search_request("averigua en internet quién ganó")


def test_spanish_news_query_keeps_spanish_place_and_hoy():
    out = build_search_query("Que paso en Panama")
    assert "Panama" in out["query"] or "Panamá" in out["query"]
    assert "hoy" in out["query"].lower()
    assert "Que paso" in out["query"] or "paso" in out["query"].lower()


def test_search_failure_reply_is_short_spanish():
    reply = search_unavailable_reply()
    assert "no tengo información" not in reply.lower()
    assert "No pude consultar" in reply
