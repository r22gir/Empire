#!/usr/bin/env python3
"""Demo: Studio frozen gate rejects a bad mock change and keeps a good one.

Mock data only. Nothing is sent. Uses STUDIO_FROZEN_MUTATION so the frozen
suite sees a deliberately bad change, then a clean one.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.max.studio_frozen_gate import decide_keep_change, evaluate_studio_frozen_gate


def _apply_bad() -> None:
    os.environ["STUDIO_FROZEN_MUTATION"] = "bad"


def _revert() -> None:
    os.environ["STUDIO_FROZEN_MUTATION"] = "clean"


def main() -> int:
    os.environ.setdefault("EMPIRE_OUTBOUND_DISABLED", "1")
    os.environ.setdefault("EMPIRE_ALLOW_OUTBOUND", "0")
    os.environ["STUDIO_FROZEN_MUTATION"] = "clean"

    print("=== DEMO 1: deliberately bad mock change ===")
    bad = decide_keep_change(apply_fn=_apply_bad, revert_fn=_revert)
    print(bad["log_line"])
    print(json.dumps({
        "kept": bad["kept"],
        "reverted": bad["reverted"],
        "verdict": bad["verdict"],
        "passes": bad["passes"],
        "outbound": bad["outbound"],
    }, indent=2))

    print("\n=== DEMO 2: good / clean change ===")
    _revert()
    good = evaluate_studio_frozen_gate()
    print(good["log_line"])
    print(json.dumps({
        "kept": good["keep"],
        "verdict": good["verdict"],
        "passes": good["passes"],
        "outbound": good["outbound"],
    }, indent=2))

    ok = (bad["verdict"] == "NO" and bad["kept"] is False and bad["reverted"] is True
          and good["verdict"] == "YES" and good["keep"] is True)
    print("\nDEMO_RESULT", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
