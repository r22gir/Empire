"""Chief e pickup CLI. Never imports app.main. Never sources .env."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from app.services.cursor_requests import (
    CursorRequestError,
    assert_edition_data_dir,
    can_launch,
    get_request,
    list_requests,
    screenshot_abs_paths,
    set_status,
)


def _dump(payload: Any) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _err(message: str) -> int:
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False), file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cursor_requests")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list")
    p_list.add_argument("--status")
    p_list.add_argument("--json", action="store_true")

    p_show = sub.add_parser("show")
    p_show.add_argument("id")
    p_show.add_argument("--json", action="store_true")

    p_launch = sub.add_parser("can-launch")
    p_launch.add_argument("id")
    p_launch.add_argument("--json", action="store_true")

    p_set = sub.add_parser("set-status")
    p_set.add_argument("id")
    p_set.add_argument("--status", required=True)
    p_set.add_argument("--pr-url")
    p_set.add_argument("--note-es")
    p_set.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    try:
        assert_edition_data_dir()
        if args.cmd == "list":
            rows = list_requests(status=args.status)
            return _dump(rows)
        if args.cmd == "show":
            row = get_request(args.id)
            row["screenshot_paths"] = screenshot_abs_paths(row)
            return _dump(row)
        if args.cmd == "can-launch":
            return _dump(can_launch(args.id))
        if args.cmd == "set-status":
            row = set_status(args.id, status=args.status, pr_url=args.pr_url, note_es=args.note_es)
            return _dump(row)
        return _err("unknown command")
    except CursorRequestError as exc:
        return _err(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
