"""2026-10-08: after 'go' Max acts in the same turn; no 'Ask me again', no Status/Done/To finish."""
from app.services.max import founder_action_continuation as fac
from app.services.max.runtime_truth_enforcer import runtime_truth_failure_message

PLAN = [{"role": "user", "content": "update the Marley's quote with the vinyl line"},
        {"role": "assistant", "content": "I can add the vinyl line to EST-2026-299 and re-render the PDF. Want me to go ahead?"}]


def test_go_messages():
    for m in ["go", "Go ahead", "yes do it", "dale", "ok go", "do it now", "sí"]:
        assert fac.is_go_message(m), m
    for m in ["go to the Marley's folder", "what's the total on 299", "yes but only the backs"]:
        assert not fac.is_go_message(m), m


def test_go_without_tools_is_pushed_to_act():
    assert fac.go_without_action("go", PLAN, 0, "Perfect, adding the vinyl line to EST-2026-299.")
    assert not fac.go_without_action("go", PLAN, 1, "Added the line; new total $11,163.82.")
    assert not fac.go_without_action("go", PLAN, 0, "Which quote, 299 or 300?")
    assert not fac.go_without_action("go", [], 0, "Sure.")
    assert "call those tools now" in fac.announced_action_nudge("On it.", "go")


def test_announce_phrases_detected():
    for t in ["On it — creating the quote now.", "Sending it now.", "I'm going to send the PDFs.",
              "Got it, updating the quote right away.", "Let me generate the PDF."]:
        assert fac.announces_action_without_tool(t), t
    assert not fac.announces_action_without_tool("EST-2026-299 is $11,163.82, draft.")


def test_no_ask_me_again():
    msg = runtime_truth_failure_message(["x"])
    assert "ask me again" not in msg.lower()


def test_not_done_is_one_plain_sentence(monkeypatch):
    results = [{"tool": "send_quote_email", "success": False, "error": "recipient_not_in_whitelist: a@b.com"}]
    body, _steps, incomplete = fac.finalize_founder_action_reply(
        "Email the estimate PDF to a@b.com", results, "I tried to email it.")
    assert incomplete
    assert "**Status**" not in body and "To finish" not in body and "Say:" not in body
    assert "Not done:" in body
