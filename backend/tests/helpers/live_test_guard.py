"""
Hermes centralized helper for live/runtime/payment test guards.

⚠️  DO NOT REMOVE OR WEAKEN THESE GUARDS ⚠️

Background:
  On 2026-06-14 at 15:22:57 EDT, an unsafe pytest run of
  ``backend/tests/test_apostille_public.py`` accidentally created 17
  ApostApp order files + 17 customer files + at least one Stripe
  Checkout Session on the LIVE backend. The test claimed
  "Stripe is in test mode" but the env was in LIVE mode and the
  orders were saved with ``metadata.test_mode: False``.

  This module provides a single safety guard that any test
  calling the LIVE backend, the LIVE Stripe account, or
  mutating LIVE runtime state (orders, customers, webhooks)
  MUST use to ensure the test can never be run accidentally.

Guarded tests must call ``require_live_test_token()`` at module
import time (BEFORE any other imports that could trigger side
effects). The function will:

  * Return True if the env var ``APOSTILLE_LIVE_TEST_TOKEN`` is set
    to the exact string ``I_APPROVE_LIVE_APOSTAPP_PAYMENT_TESTS``
  * Call ``pytest.skip(...)`` with a clear reason otherwise

Usage in a guarded test file::

    # AT THE VERY TOP, BEFORE ALL OTHER IMPORTS:
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from helpers.live_test_guard import require_live_test_token
    require_live_test_token(__file__)

    # Only after the guard passes should other imports happen:
    import json
    import requests
    import pytest
    ...

To run a guarded test (Founder only, after explicit approval)::

    APOSTILLE_LIVE_TEST_TOKEN=I_APPROVE_LIVE_APOSTAPP_PAYMENT_TESTS \\
        /home/rg/empire-repo/backend/venv/bin/pytest \\
        backend/tests/test_apostille_public.py -v

Without the env var, pytest will report a SKIP for every test
in the file (or a collection error if the guard is at module
top-level).

Reference:
  OPERATOR-AUDIT-GATE3-UNSAFE-TEST-ATTEMPT-20260614.md
  HERMES-REPORT-GATE3-PAYMENT-INCIDENT-CLEANUP-AND-TEST-GUARDS-20260614.md
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


# The exact token that must be present in APOSTILLE_LIVE_TEST_TOKEN
# for any guarded test to run. This is a public constant (NOT a secret)
# because its purpose is to be human-readable so accidental exposure
# in chat/logs is obvious.
LIVE_TEST_TOKEN: str = "I_APPROVE_LIVE_APOSTAPP_PAYMENT_TESTS"
ENV_VAR_NAME: str = "APOSTILLE_LIVE_TEST_TOKEN"


def is_live_test_authorized() -> bool:
    """Return True iff the env var is set to the exact live-test token.

    This is a pure predicate; it does NOT raise or skip. Use
    :func:`require_live_test_token` for the guard that skips tests.
    """
    return os.environ.get(ENV_VAR_NAME) == LIVE_TEST_TOKEN


def require_live_test_token(test_file_path: str | None = None) -> bool:
    """Guard: skip the calling test if the live-test env token is not set.

    Must be called at the very top of a guarded test file, BEFORE
    any imports that could trigger runtime/Stripe side effects.

    Parameters
    ----------
    test_file_path : str | None
        Optional path to the calling test file (for the skip message
        and the audit log). Defaults to ``__file__`` of the caller.

    Returns
    -------
    bool
        True if the live-test token is set correctly (test may proceed).

    Side effects
    ------------
    Calls ``pytest.skip(...)`` and returns ``False`` if the env var
    is not set to the exact token. This is the expected behavior —
    the skip is the safety mechanism.

    Notes
    -----
    This function imports ``pytest`` lazily to avoid forcing a pytest
    import on tests that don't use it (e.g., when imported for
    documentation or static analysis). If pytest is not importable,
    the function raises a clear RuntimeError instead of skipping.
    """
    if is_live_test_authorized():
        return True

    # Import pytest lazily so this helper can be imported without pytest.
    try:
        import pytest
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "pytest is required to use require_live_test_token(), "
            "but it could not be imported. Install pytest or use "
            "is_live_test_authorized() directly."
        ) from e

    caller = test_file_path or "this test file"
    env_val = os.environ.get(ENV_VAR_NAME)
    if env_val is None:
        reason = (
            f"SKIPPED (live test guard): {caller} calls the LIVE "
            f"backend and/or LIVE Stripe account. To run, set the env "
            f"var {ENV_VAR_NAME}={LIVE_TEST_TOKEN!r} (requires explicit "
            f"Founder approval via `APPROVE LIVE STRIPE ACTION`). "
            f"Without this token, these tests SKIP to prevent "
            f"accidental order/customer/Stripe mutations."
        )
    else:
        reason = (
            f"SKIPPED (live test guard): {caller} requires the env var "
            f"{ENV_VAR_NAME} to be set to the EXACT string "
            f"{LIVE_TEST_TOKEN!r} (got {env_val!r} which is wrong). "
            f"This guard exists to prevent the 2026-06-14 accidental "
            f"Stripe/order/customer mutation incident from recurring. "
            f"Requires explicit Founder approval via `APPROVE LIVE "
            f"STRIPE ACTION`."
        )

    # Use pytest.skip with allow_module_level=True so the entire module
    # is skipped (not just the first test). This is the standard pattern
    # for "this entire file requires a precondition" guards.
    pytest.skip(reason, allow_module_level=True)
    # Unreachable, but keeps the type checker happy.
    return False
