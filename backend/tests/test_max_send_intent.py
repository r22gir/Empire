"""2026-10-08: find / show / look up never auto-emails; email only when Rafael asks to send it."""
from app.services.max import answer_policy as ap

OFFER = [{"role": "assistant", "content": "Found it. Want me to email it to you?"}]


def held(msg, tc, channel="web", history=None):
    return ap.unrequested_send_error(tc, msg, history or [], channel) is not None


def test_find_show_lookup_never_email():
    assert held("Find the Willard addendum PDF", {"tool": "share_file", "via": "email"})
    assert held("Show me a mockup of the Marley's basketweave seat back", {"tool": "send_email"})
    assert held("look up EST-2026-299", {"tool": "send_quote_email"})
    assert held("Can you send me like a voice message, like a status on the last Marley's quote?",
                {"tool": "send_quote_email"})


def test_studio_link_and_reads_are_not_sends():
    assert not held("Find the Willard addendum PDF", {"tool": "share_file", "via": "studio"})
    assert not held("Find the Willard addendum PDF", {"tool": "find_files"})


def test_explicit_send_or_yes_goes_through():
    assert not held("Email me the Dahlia phase 2 quote", {"tool": "send_quote_email"})
    assert not held("Send me last quote", {"tool": "send_quote_email"}, "whatsapp")
    assert not held("Mándame la cotización EST-2026-297 aquí", {"tool": "send_quote_email"}, "whatsapp")
    assert not held("yes", {"tool": "send_quote_email"}, history=OFFER)
    assert held("yes", {"tool": "send_quote_email"})  # nothing was offered


def test_whatsapp_chat_reply_vs_push_from_studio():
    assert not held("Show me the 4 vs 8 mockup", {"tool": "share_file", "via": "whatsapp"}, "whatsapp")
    assert held("Show me the 4 vs 8 mockup", {"tool": "share_file", "via": "whatsapp"}, "web")
