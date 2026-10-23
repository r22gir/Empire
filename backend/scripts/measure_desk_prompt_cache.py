#!/usr/bin/env python3
"""Before/after desk-prompt prefix stability on the real chat-path assembler.

Mock turns only. No provider HTTP. Reports longest-common-prefix and
cache-hit (stable prefix hash + pinned desk).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.max.desk_prompt import DESK_CACHE_PINS, measure_desk_prefix_stability


DESKS = ("forge", "codeforge", "finance")


def main() -> int:
    rows = []
    for desk_id in DESKS:
        report = measure_desk_prefix_stability(desk_id)
        rows.append(report)
        print(f"desk={desk_id} pin={DESK_CACHE_PINS.get(desk_id)}")
        print(
            f"  BEFORE legacy  lcp_chars={report['before']['lcp_chars']}  "
            f"lcp_ratio={report['before']['lcp_ratio']}  "
            f"cache_hit={report['before']['cache_hit']}"
        )
        print(
            f"  AFTER  cache   lcp_chars={report['after']['lcp_chars']}  "
            f"lcp_ratio={report['after']['lcp_ratio']}  "
            f"cache_hit={report['after']['cache_hit']}  "
            f"gain={report['lcp_gain_chars']}"
        )
    out = {
        "path": "assemble_desk_chat_messages (same system+user shape as ai_router.chat)",
        "desks": rows,
        "outbound": False,
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
