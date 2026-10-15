"""Fix B: voice answers pure 'can you do X' from the list; action phrases run tools."""
from app.services.max.voice_can_do import (
    VOICE_CAPABILITY_LIST,
    answer_can_you_do,
    can_you_do,
    is_capability_question,
    matching_action_tool,
)


ACTION_PHRASES = (
    ("can you send me the 3D drawing on WhatsApp?", "send_me_this_link"),
    ("can you check my calendar?", "get_today_agenda"),
    ("can you check the weather in Vienna?", "get_weather"),
)


def test_detects_english_and_spanish_can_you():
    assert is_capability_question("can you check my calendar?")
    assert is_capability_question("Can you send me this link")
    assert is_capability_question("puedes mandarme el enlace")
    assert not is_capability_question("what's on today")
    assert not is_capability_question("send me the 3D drawing")


def test_action_can_you_phrases_do_not_get_a_canned_yes():
    for phrase, tool in ACTION_PHRASES:
        assert answer_can_you_do(phrase) is None, phrase
        assert matching_action_tool(phrase) == tool, phrase
        res = can_you_do({"question": phrase})
        assert res["result"]["answer"] is None, phrase
        assert res["result"]["action_tool"] == tool, phrase


def test_pure_capability_still_answers_from_the_list():
    send = answer_can_you_do("are you able to send links to Rafael?")
    assert send and "empirebox2026@gmail.com" in send
    no_client = answer_can_you_do("can you email a client?")
    assert no_client and no_client.startswith("No")


def test_unknown_capability_returns_the_list_not_a_guess():
    out = answer_can_you_do("are you able to fly the drone?")
    assert out
    assert "calendar" in out.lower()
    assert "empirebox2026@gmail.com" in out


def test_can_you_do_tool_routes_actions():
    res = can_you_do({"question": "can you send me the 3D drawing on WhatsApp?"})
    assert res["success"]
    assert res["result"]["action_tool"] == "send_me_this_link"
    assert res["result"]["answer"] is None


def test_capability_list_covers_today_and_send():
    ids = {row["id"] for row in VOICE_CAPABILITY_LIST}
    assert "today_agenda" in ids
    assert "send_me_link" in ids
    assert "client_email" in ids


def test_voice_tool_does_not_canned_yes_action_phrases():
    from app.services.max import voice_live as vl
    src = open(vl.__file__).read()
    assert "answer_can_you_do(typed)" not in src
    for phrase, tool in ACTION_PHRASES:
        out = vl.run_voice_tool("can_you_do", {"question": phrase})
        assert out["success"]
        assert (out.get("result") or {}).get("action_tool") == tool
        assert (out.get("result") or {}).get("answer") is None
