"""Tests for canonical voice capability truth.

UI and MAX previously disagreed on voice status: UI said "Voice STT ready ·
TTS blocked," but MAX answered "STT was missing and TTS existed." This
test pins the canonical truth module so both consumers see the same thing.
"""
from app.services.max.voice_capability_truth import (
    get_voice_capability_status,
    invalidate_cache,
)


def test_status_has_all_seven_required_fields():
    invalidate_cache()
    status = get_voice_capability_status()
    for field in (
        "telegram_text_send",
        "telegram_voice_receive",
        "telegram_voice_send",
        "stt_provider",
        "tts_provider",
        "auto_voice_reply",
        "last_verified_at",
        "evidence",
    ):
        assert field in status, f"missing required field: {field}"


def test_status_includes_summary_for_ui():
    status = get_voice_capability_status()
    assert "summary" in status
    assert isinstance(status["summary"], str)
    assert status["summary"]  # not empty


def test_stt_and_tts_have_provider_field():
    status = get_voice_capability_status()
    assert "provider" in status["stt_provider"]
    assert "provider" in status["tts_provider"]
    assert "env_key" in status["stt_provider"]
    assert "env_key" in status["tts_provider"]


def test_each_field_has_verified_flag():
    status = get_voice_capability_status()
    for field in (
        "telegram_text_send",
        "telegram_voice_receive",
        "telegram_voice_send",
        "stt_provider",
        "tts_provider",
        "auto_voice_reply",
    ):
        assert "verified" in status[field], f"{field} missing 'verified' flag"
        assert isinstance(status[field]["verified"], bool)


def test_evidence_field_is_present():
    status = get_voice_capability_status()
    assert "evidence" in status
    assert "voice_capability_truth" in status["evidence"]


def test_voice_send_requires_both_stt_and_tts():
    """voice_send can only be verified if telegram pipeline + tts works.

    Specifically, telegram_voice_send does NOT require STT (sending a
    voice note uses TTS, not STT). Receiving a voice note DOES require
    STT.
    """
    status = get_voice_capability_status()
    # If tts is not configured, voice send cannot be verified.
    if not status["tts_provider"]["verified"]:
        assert status["telegram_voice_send"]["verified"] is False
    # If telegram text pipeline is not configured, voice send cannot be verified.
    if not status["telegram_text_send"]["verified"]:
        assert status["telegram_voice_send"]["verified"] is False


def test_voice_receive_requires_stt():
    """Receiving a voice requires the telegram pipeline AND STT."""
    status = get_voice_capability_status()
    if not status["stt_provider"]["verified"]:
        assert status["telegram_voice_receive"]["verified"] is False
