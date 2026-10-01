"""Regression tests for the finance-readiness chat hardening."""
import asyncio
import json

from app.api.v1 import chats
from app.services.max import tool_executor
from app.services.max.finance_readiness_lane import (
    FINANCE_SUM_QUERIES,
    finance_request_wants_dollar_totals,
    format_finance_context,
    is_local_finance_readiness_request,
    resolve_display_model_used,
)
from app.services.max.tool_executor import _env_get, strip_tool_blocks


def test_env_get_sensitive_probe_is_set_only(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "STRIPE_SECRET_KEY=do-not-return\n"
        "SQUARE_ACCESS_TOKEN=also-do-not-return\n"
        "PUBLIC_MODE=production\n"
        "EMPTY_VALUE=\n"
    )
    monkeypatch.setattr(
        tool_executor.os.path,
        "expanduser",
        lambda path: str(env_file) if path.endswith("backend/.env") else path,
    )

    stripe = _env_get({"name": "STRIPE_SECRET_KEY"})
    square = _env_get({"name": "SQUARE_ACCESS_TOKEN"})
    listed = _env_get({})

    assert stripe.success and stripe.result == {"set": True}
    assert square.success and square.result == {"set": True}
    encoded = json.dumps([stripe.result, square.result, listed.result])
    assert "STRIPE_SECRET_KEY" not in encoded
    assert "SQUARE_ACCESS_TOKEN" not in encoded
    assert "do-not-return" not in encoded
    assert "also-do-not-return" not in encoded
    assert all(item["name"] not in {"STRIPE_SECRET_KEY", "SQUARE_ACCESS_TOKEN"} for item in listed.result["variables"])


def test_put_chat_upserts_client_generated_id(tmp_path, monkeypatch):
    monkeypatch.setattr(chats, "CHATS_DIR", tmp_path)
    chat_id = "30ea0046-2bc9-461c-8215-5793e12874cd"
    req = chats.UpdateChatRequest(messages=[{"role": "user", "content": "finance readiness"}])

    response = asyncio.run(chats.update_chat(chat_id, req))

    assert response == {"status": "created", "chat_id": chat_id}
    saved = json.loads((tmp_path / "founder" / f"{chat_id}.json").read_text())
    assert saved["id"] == chat_id
    assert saved["messages"] == req.messages


def test_put_existing_chat_still_updates(tmp_path, monkeypatch):
    monkeypatch.setattr(chats, "CHATS_DIR", tmp_path)
    chat_id = "existing-chat"
    user_dir = tmp_path / "founder"
    user_dir.mkdir()
    (user_dir / f"{chat_id}.json").write_text(json.dumps({"id": chat_id, "title": "old", "created_at": "old", "messages": []}))
    req = chats.UpdateChatRequest(messages=[{"role": "assistant", "content": "complete report"}])

    response = asyncio.run(chats.update_chat(chat_id, req))

    assert response == {"status": "updated", "chat_id": chat_id}
    saved = json.loads((user_dir / f"{chat_id}.json").read_text())
    assert saved["title"] == "old"
    assert saved["messages"] == req.messages


def test_tool_protocol_never_survives_visible_text():
    fenced = "Before\n```json\n{\"tool\": \"db_query\", \"query\": \"SELECT 1\"}\n```\nAfter"
    assert "\"tool\"" not in strip_tool_blocks(fenced)
    assert strip_tool_blocks('{"tool":"db_query","query":"SELECT 1"}') == ""


def test_finance_readiness_detects_local_lane_and_totals():
    prompt = (
        "Give me a finance readiness report: count quotes, invoices, payments, "
        "expenses, customers and vendors, show dollar totals, and plan QuickBooks migration."
    )
    assert is_local_finance_readiness_request(prompt)
    assert finance_request_wants_dollar_totals(prompt)


def test_finance_sum_queries_cover_quotes_invoices_payments_ar():
    labels = {label for label, _ in FINANCE_SUM_QUERIES}
    assert "quotes_dollar_total" in labels
    assert "invoices_dollar_total" in labels
    assert "payments_dollar_total" in labels
    assert "ar_outstanding_balance_due" in labels
    for _, sql in FINANCE_SUM_QUERIES:
        assert sql.strip().upper().startswith("SELECT")
        assert "SUM(" in sql.upper()


def test_format_finance_context_labels_prefetched_rows():
    entries = [
        {
            "success": True,
            "tool": "db_query",
            "result": {"requested_name": "quotes_dollar_total", "sum_total": 1200.5},
        }
    ]
    text = format_finance_context(entries, dumps=lambda obj, **kw: json.dumps(obj, **kw))
    assert "[quotes_dollar_total]" in text
    assert "1200.5" in text


def test_resolve_display_model_used_hides_unknown():
    assert resolve_display_model_used("unknown", None) == "MAX auto"
    assert resolve_display_model_used("", "claude-sonnet-4-6") == "claude-sonnet-4-6"
    assert resolve_display_model_used("groq-llama-3.3-70b", "auto") == "groq-llama-3.3-70b"
