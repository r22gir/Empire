"""Fix B: voice answers 'can you do X' from the capability list."""
from app.services.max.voice_can_do import (
    VOICE_CAPABILITY_LIST,
    answer_can_you_do,
    is_capability_question,
)
from app.services.max.tool_executor import execute_tool


def test_detects_english_and_spanish_can_you():
    assert is_capability_question("can you check my calendar?")
    assert is_capability_question("Can you send me this link")
    assert is_capability_question("puedes mandarme el enlace")
    assert not is_capability_question("what's on today")
    assert not is_capability_question("send me the 3D drawing")


def test_calendar_and_send_link_from_list():
    cal = answer_can_you_do("can you check my calendar?")
    assert cal and "calendar" in cal.lower()
    send = answer_can_you_do("can you send me this link?")
    assert send and "empirebox2026@gmail.com" in send
    assert "rafa22giraldo" in send
    no_client = answer_can_you_do("can you email a client?")
    assert no_client and no_client.startswith("No")


def test_unknown_capability_returns_the_list_not_a_guess():
    out = answer_can_you_do("can you fly the drone?")
    assert out
    assert "calendar" in out.lower()
    assert "empirebox2026@gmail.com" in out


def test_can_you_do_tool_uses_the_list():
    res = execute_tool({"tool": "can_you_do", "question": "can you send me this link"})
    assert res.success
    assert "empirebox2026@gmail.com" in res.result["answer"]
    assert res.result["capability"] == "send_me_link"


def test_capability_list_covers_today_and_send():
    ids = {row["id"] for row in VOICE_CAPABILITY_LIST}
    assert "today_agenda" in ids
    assert "send_me_link" in ids
    assert "client_email" in ids
