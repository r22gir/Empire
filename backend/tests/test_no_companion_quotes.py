"""2026-10-08: no unrequested companion quotes (EST-2026-300 was a U-only copy nobody asked for)."""
from app.services.max import answer_policy as ap

DONE = [{"tool": "create_engine_quote", "success": True, "result": {"quote_number": "EST-2026-299"}}]
TC = {"tool": "create_engine_quote", "customer_name": "Marley's"}


def test_first_quote_always_ok():
    assert ap.unrequested_companion_quote_error(TC, "quote Marley's U and L benches", [], []) is None


def test_second_quote_held_without_ask():
    err = ap.unrequested_companion_quote_error(TC, "quote Marley's U and L benches", [], DONE)
    assert err and "EST-2026-299" in err


def test_second_quote_ok_when_asked():
    for m in ["make two quotes, one per bench", "separate quote for the U", "also an option without vinyl",
              "quote phase 1 and phase 2", "haz dos cotizaciones"]:
        assert ap.unrequested_companion_quote_error(TC, m, [], DONE) is None, m


def test_go_after_offer_of_two_quotes():
    hist = [{"role": "assistant", "content": "I can split it into two quotes, U and L. Want that?"}]
    assert ap.unrequested_companion_quote_error(TC, "yes", hist, DONE) is None
    assert ap.unrequested_companion_quote_error(TC, "yes", [], DONE) is not None


def test_reads_never_held():
    assert ap.unrequested_companion_quote_error({"tool": "get_quote"}, "x", [], DONE) is None
