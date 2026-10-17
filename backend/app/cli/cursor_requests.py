"""Chief e pickup CLI for the edition Cursor-request queue.

    cd ~/empire-amp/backend && EMPIRE_EDITION=amp EMPIRE_DATA_DIR=/data/amp \\
        venv/bin/python -m app.cli.cursor_requests list --status queued --json

Never imports app.main. Never sources the env file.
"""
from __future__ import annotations

import argparse
import json
import sys


def _payload(item: dict) -> dict:
    from app.services.cursor_requests import screenshot_abs_paths

    out = dict(item)
    out["screenshot_abs_paths"] = screenshot_abs_paths(item)
    return out


def _print(data) -> int:
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    from app.services.cursor_requests import (
        CursorRequestError,
        can_launch,
        get,
        list_requests,
        set_status_cli,
        validate_edition_data_dir,
    )

    parser = argparse.ArgumentParser(prog="cursor_requests")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list")
    p_list.add_argument("--status", default="")
    p_list.add_argument("--json", action="store_true")

    p_show = sub.add_parser("show")
    p_show.add_argument("id")
    p_show.add_argument("--json", action="store_true")

    p_can = sub.add_parser("can-launch")
    p_can.add_argument("id")
    p_can.add_argument("--json", action="store_true")

    p_set = sub.add_parser("set-status")
    p_set.add_argument("id")
    p_set.add_argument("--status", required=True)
    p_set.add_argument("--pr-url", default="")
    p_set.add_argument("--note-es", default="")
    p_set.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    try:
        validate_edition_data_dir()
        if args.cmd == "list":
            rows = list_requests(status=args.status or None)
            return _print([_payload(r) for r in rows])
        if args.cmd == "show":
            return _print(_payload(get(args.id)))
        if args.cmd == "can-launch":
            return _print(can_launch(args.id))
        if args.cmd == "set-status":
            return _print(
                _payload(
                    set_status_cli(
                        args.id,
                        args.status,
                        pr_url=args.pr_url or None,
                        note_es=args.note_es or None,
                    )
                )
            )
    except CursorRequestError as exc:
        print(json.dumps({"error": exc.message}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
