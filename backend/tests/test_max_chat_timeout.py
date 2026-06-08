"""Tests for the MAX chat timeout configurability and truthful reporting.

The previous behavior had three related bugs:
    1. The /chat endpoint hardcoded `asyncio.wait_for(..., timeout=45.0)`
       so long planning prompts (which legitimately need >45s of LLM
       time) were being cut off.
    2. The /chat endpoint's `asyncio.TimeoutError` handler returned
       `fallback_used=True` even though no fallback model had been
       attempted — a lie. The UI/MAX downstream consumers would then
       conclude "a fallback model answered" when in fact the primary
       provider had just timed out.
    3. The underlying MiniMax httpx client hardcoded timeout=45.0 in
       two places (`_minimax_chat` and `_minimax_chat_stream`), which
       meant the httpx layer would have raised httpx.TimeoutException
       before the asyncio.wait_for wrapper even fired.

This test pins the new behavior:
    - `_resolve_max_chat_timeout()` reads MAX_CHAT_TIMEOUT_SECONDS
      first, then MINIMAX_CHAT_TIMEOUT_SECONDS, then defaults to 120s.
    - The default is 120s, not 45s.
    - Bad/non-positive values fall back to the default.
    - The chat endpoint's `asyncio.TimeoutError` handler reports
      `fallback_used=False` and `model_used='timeout'` (truthful).
    - The metadata carries `timeout_seconds` for downstream inspection.

We do NOT make live API calls. We exercise the resolver directly and
import-check the router module.
"""
import os
import sys
import subprocess
import textwrap

LIVE_VENV = "/home/rg/empire-repo/backend/venv/lib/python3.12/site-packages"
if LIVE_VENV not in sys.path:
    sys.path.insert(0, LIVE_VENV)


def _run_in_subprocess(extra_env: dict) -> float:
    """Spawn a fresh Python that imports the resolver, with the given env.

    We use a subprocess instead of in-process env mutation because
    `os.environ` mutations during test time are unreliable for a
    module-level resolution. The subprocess is the most honest test.
    """
    env = {
        "HOME": "/home/rg",
        "PATH": "/home/rg/empire-repo/backend/venv/bin:/usr/local/bin:/usr/bin:/bin",
        "PYTHONPATH": "/home/rg/empire-repo-main/backend",
    }
    env.update(extra_env)
    code = textwrap.dedent("""
        from app.routers.max.router import _resolve_max_chat_timeout
        print(_resolve_max_chat_timeout())
    """).strip()
    result = subprocess.run(
        ["/home/rg/empire-repo/backend/venv/bin/python3", "-c", code],
        env=env, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, f"subprocess failed: {result.stderr}"
    return float(result.stdout.strip())


# ── Resolver precedence ──────────────────────────────────────────────────

def test_default_timeout_is_120s():
    """When no env vars are set, default to 120s (was 45s historically)."""
    val = _run_in_subprocess({})
    assert val == 120.0, f"expected 120.0 default, got {val}"


def test_max_chat_timeout_seconds_wins():
    """MAX_CHAT_TIMEOUT_SECONDS is the most authoritative cap."""
    val = _run_in_subprocess({
        "MAX_CHAT_TIMEOUT_SECONDS": "60",
        "MINIMAX_CHAT_TIMEOUT_SECONDS": "45",
    })
    assert val == 60.0, f"expected MAX=60 to win, got {val}"


def test_minimax_chat_timeout_used_when_max_unset():
    """If only MINIMAX is set, use it."""
    val = _run_in_subprocess({"MINIMAX_CHAT_TIMEOUT_SECONDS": "75"})
    assert val == 75.0, f"expected 75.0, got {val}"


def test_bad_value_falls_back_to_default():
    """Non-numeric or non-positive values fall back to 120s."""
    val = _run_in_subprocess({"MAX_CHAT_TIMEOUT_SECONDS": "not-a-number"})
    assert val == 120.0, f"expected fallback to 120, got {val}"

    val = _run_in_subprocess({"MAX_CHAT_TIMEOUT_SECONDS": "-5"})
    assert val == 120.0, f"expected fallback for negative, got {val}"

    val = _run_in_subprocess({"MAX_CHAT_TIMEOUT_SECONDS": "0"})
    assert val == 120.0, f"expected fallback for zero, got {val}"


# ── AI router underlying timeout ─────────────────────────────────────────

def test_ai_router_minimax_timeout_default():
    """The underlying httpx client timeout (in _minimax_chat /
    _minimax_chat_stream) defaults to 120s, not 45s. The previous 45s
    cap was the documented source of the long-prompt timeout bug.
    """
    code = textwrap.dedent("""
        import os
        os.environ.pop('MINIMAX_CHAT_TIMEOUT_SECONDS', None)
        os.environ.pop('MAX_CHAT_TIMEOUT_SECONDS', None)
        from app.services.max.ai_router import ai_router
        v = ai_router._minimax_timeout()
        print(v)
    """).strip()
    result = subprocess.run(
        ["/home/rg/empire-repo/backend/venv/bin/python3", "-c", code],
        env={
            "HOME": "/home/rg",
            "PATH": "/home/rg/empire-repo/backend/venv/bin:/usr/local/bin:/usr/bin:/bin",
            "PYTHONPATH": "/home/rg/empire-repo-main/backend",
        },
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, f"subprocess failed: {result.stderr}"
    val = float(result.stdout.strip())
    assert val == 120.0, f"ai_router default expected 120.0, got {val}"


# ── Truthful timeout response ───────────────────────────────────────────

def test_router_module_imports_cleanly():
    """The router module must still import after the timeout patches.

    This catches the most common regression: forgetting to import the
    new helper, or a syntax error in the patch.
    """
    code = textwrap.dedent("""
        import app.routers.max.router
        import app.services.max.ai_router
        # The new helper must exist
        from app.routers.max.router import _resolve_max_chat_timeout
        from app.services.max.ai_router import ai_router
        assert callable(_resolve_max_chat_timeout)
        assert callable(getattr(ai_router, '_minimax_timeout', None))
        print('OK')
    """).strip()
    result = subprocess.run(
        ["/home/rg/empire-repo/backend/venv/bin/python3", "-c", code],
        env={
            "HOME": "/home/rg",
            "PATH": "/home/rg/empire-repo/backend/venv/bin:/usr/local/bin:/usr/bin:/bin",
            "PYTHONPATH": "/home/rg/empire-repo-main/backend",
        },
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, f"import check failed: {result.stderr}"
    assert "OK" in result.stdout


def test_timeout_handler_truthful_fallback_used():
    """Source-level check: the asyncio.TimeoutError handler in router.py
    must set fallback_used=False (truthful: no fallback model was used)
    and include timeout_seconds in metadata. This prevents the lie
    from creeping back in.
    """
    src_path = "/home/rg/empire-repo-main/backend/app/routers/max/router.py"
    with open(src_path) as f:
        src = f.read()
    # Find the TimeoutError handler block
    assert "except asyncio.TimeoutError" in src, "missing TimeoutError handler"
    # The handler must contain fallback_used=False (truthful)
    idx = src.index("except asyncio.TimeoutError")
    block = src[idx:idx + 1500]
    assert "fallback_used=False" in block, (
        "TimeoutError handler must set fallback_used=False (no fallback occurred)"
    )
    assert 'model_used="timeout"' in block, (
        "TimeoutError handler must set model_used='timeout'"
    )
    assert "timeout_seconds" in block, (
        "TimeoutError handler must surface timeout_seconds in metadata"
    )


# ── Resolver sanity check (in-process) ──────────────────────────────────

def test_resolver_in_process_default():
    """Quick in-process sanity: the default value matches the spec."""
    os.environ.pop("MAX_CHAT_TIMEOUT_SECONDS", None)
    os.environ.pop("MINIMAX_CHAT_TIMEOUT_SECONDS", None)
    from app.routers.max.router import _resolve_max_chat_timeout
    # Note: in-process env may have leaked from the test runner; the
    # subprocess tests above are authoritative. This is just a sanity.
    val = _resolve_max_chat_timeout()
    assert val > 0, "timeout must be positive"
    assert val >= 60, f"default should be at least 60s, got {val}"
