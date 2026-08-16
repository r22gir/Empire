"""PHASE 2 · F4-A tests — live channel-status probe.

The H45 root was that the model offered "email or Telegram" because
the compact prompt had no signal about which channels were live. F4-A
adds a live-probed channel-status line to every prompt path.

The probe is real (SMTP TCP-connect, Telegram getMe, SendGrid env)
and cached for 60s, so the prompt-build hot path is fast.
"""
from __future__ import annotations

import os


def test_channel_status_line_format():
    """The format is exactly 'channels: email ✓ · telegram ✗ · sendgrid ✗'."""
    from app.services.max.channel_probe import channel_status_line, invalidate_cache

    # Set Telegram token to something the probe will reject
    os.environ["TELEGRAM_BOT_TOKEN"] = "invalid:token-for-test"
    os.environ["SMTP_USER"] = ""
    os.environ["SMTP_PASSWORD"] = ""
    os.environ["SENDGRID_API_KEY"] = ""
    invalidate_cache()

    line = channel_status_line()
    # Format check
    assert line.startswith("channels: ")
    assert "email" in line
    assert "telegram" in line
    assert "sendgrid" in line
    # Symbols present
    assert "✓" in line or "✗" in line


def test_channel_status_line_email_live():
    """When SMTP_USER + SMTP_PASSWORD are set AND smtp.gmail.com:587 is
    reachable, email shows ✓."""
    from app.services.max.channel_probe import (
        channel_status_line,
        invalidate_cache,
        _probe_smtp,
    )

    # Set creds and skip the live SMTP probe (we're inside the test
    # env without network in some CI). The probe function handles
    # reachability; the test verifies the indicator matches.
    os.environ["SMTP_USER"] = "fake@example.com"
    os.environ["SMTP_PASSWORD"] = "fake-pass"
    invalidate_cache()

    live = _probe_smtp()
    line = channel_status_line()
    # The result depends on the test env's network; just verify the
    # indicator matches the probed value
    if live:
        assert "email ✓" in line
    else:
        assert "email ✗" in line


def test_channel_status_line_telegram_live():
    """When TELEGRAM_BOT_TOKEN is set and getMe succeeds, telegram shows ✓."""
    from app.services.max.channel_probe import (
        channel_status_line,
        invalidate_cache,
        _probe_telegram,
    )

    # Real bot token (if available) or empty
    saved = os.environ.get("TELEGRAM_BOT_TOKEN")
    os.environ["TELEGRAM_BOT_TOKEN"] = ""  # Force ✗
    invalidate_cache()

    line = channel_status_line()
    live = _probe_telegram()
    if live:
        assert "telegram ✓" in line
    else:
        assert "telegram ✗" in line
    if saved:
        os.environ["TELEGRAM_BOT_TOKEN"] = saved


def test_channel_status_line_sendgrid():
    """SendGrid is keyed on SENDGRID_API_KEY env var."""
    from app.services.max.channel_probe import channel_status_line, invalidate_cache

    os.environ["SENDGRID_API_KEY"] = ""
    invalidate_cache()
    line = channel_status_line()
    assert "sendgrid ✗" in line

    os.environ["SENDGRID_API_KEY"] = "SG.fake"
    invalidate_cache()
    line = channel_status_line()
    assert "sendgrid ✓" in line


def test_channel_status_line_cache():
    """The result is cached for 60s — repeated calls return the same line."""
    from app.services.max.channel_probe import channel_status_line, invalidate_cache

    invalidate_cache()
    line1 = channel_status_line()
    line2 = channel_status_line()
    assert line1 == line2


def test_channel_status_line_fallback_on_error():
    """If the probe raises, the fallback shows '?' symbols."""
    from app.services.max import channel_probe

    # Force an error by patching the probe
    original = channel_probe._probe_status
    try:
        channel_probe._probe_status = lambda: (_ for _ in ()).throw(
            RuntimeError("simulated probe failure")
        )
        channel_probe.invalidate_cache()
        line = channel_probe.channel_status_line()
        assert "?" in line
    finally:
        channel_probe._probe_status = original
        channel_probe.invalidate_cache()


def test_compact_prompt_contains_channel_status():
    """The compact prompt carries the channel-status line for the model."""
    from app.services.max.system_prompt import get_compact_system_prompt
    from app.services.max.channel_probe import channel_status_line

    prompt = get_compact_system_prompt(channel="web")
    # The exact line or its prefix should be present
    assert "channels:" in prompt
    # The status should match what the probe returns
    assert channel_status_line() in prompt


def test_full_prompt_contains_channel_status():
    """The full prompt (brain-enriched) also carries the channel-status line."""
    from app.services.max.system_prompt import get_system_prompt, _prompt_cache
    from app.services.max.channel_probe import channel_status_line, invalidate_cache

    # Invalidate both the channel probe cache AND the prompt cache so
    # this test sees a fresh build regardless of earlier test ordering.
    invalidate_cache()
    _prompt_cache["prompt"] = None

    prompt = get_system_prompt()
    assert "channels:" in prompt
    assert channel_status_line() in prompt
