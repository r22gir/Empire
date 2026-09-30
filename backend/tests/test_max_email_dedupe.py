from app.routers.max.router import _dedupe_send_tool_calls


def test_duplicate_send_email_calls_are_suppressed_within_turn():
    seen = set()
    calls = [
        {"tool": "send_email", "to": "rafa@example.com", "subject": "Same", "body": "Hi"},
        {"tool": "send_email", "to": "rafa@example.com", "subject": "Same", "body": "Hi"},
        {"tool": "send_email", "to": "rafa@example.com", "subject": "Distinct", "body": "Hi"},
    ]

    result = _dedupe_send_tool_calls(calls, seen)

    assert [call["subject"] for call in result] == ["Same", "Distinct"]
    assert len(seen) == 2
