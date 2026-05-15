#!/usr/bin/env python3
"""capture_idea.py — friction-free content idea capture for Maven.

CC has thoughts throughout the day. This script catches them, parks them in
data/content/idea_backlog.md, and lets him pull a "ready to film" list when
he picks up his phone. Used both from CLI and from the Telegram /idea command.

Usage:
  capture_idea.py add "raw idea text" [--source telegram|cli|voice]
  capture_idea.py list [--status raw|sharpened|filmed|posted|all] [--limit N]
  capture_idea.py sharpen <id> --hook "..." --outline "..."
  capture_idea.py move <id> --to filmed|posted|archived [--note "..."]
  capture_idea.py show <id>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parent.parent
BACKLOG = REPO / "data" / "content" / "idea_backlog.md"

STATUSES = ["raw", "sharpened", "filmed", "posted", "archived"]
SECTION_MARKERS = {s: (f"<!-- {s}-start -->", f"<!-- {s}-end -->") for s in STATUSES}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _short_id(stamp: str, text: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "", text.lower())[:6] or "idea"
    return f"{stamp.replace('-', '').replace(' ', '').replace(':', '')[:12]}-{base}"


def _read() -> str:
    if not BACKLOG.exists():
        sys.exit(f"backlog missing: {BACKLOG}")
    return BACKLOG.read_text(encoding="utf-8")


def _write(content: str) -> None:
    BACKLOG.write_text(content, encoding="utf-8")


def _section(content: str, status: str) -> tuple[int, int, str]:
    start_marker, end_marker = SECTION_MARKERS[status]
    s = content.index(start_marker) + len(start_marker)
    e = content.index(end_marker)
    return s, e, content[s:e]


def _set_section(content: str, status: str, body: str) -> str:
    s, e, _ = _section(content, status)
    return content[:s] + body + content[e:]


def _append_to(content: str, status: str, line: str) -> str:
    s, e, body = _section(content, status)
    body = body.rstrip() + "\n" + line + "\n"
    if not body.startswith("\n"):
        body = "\n" + body
    return _set_section(content, status, body)


def _remove_line(content: str, status: str, idea_id: str) -> tuple[str, Optional[str]]:
    s, e, body = _section(content, status)
    out_lines = []
    removed = None
    for line in body.splitlines():
        if not line.strip():
            out_lines.append(line)
            continue
        if f"[id:{idea_id}]" in line:
            removed = line
            continue
        out_lines.append(line)
    new_body = "\n".join(out_lines)
    if not new_body.startswith("\n"):
        new_body = "\n" + new_body
    if not new_body.endswith("\n"):
        new_body += "\n"
    return _set_section(content, status, new_body), removed


def _find(content: str, idea_id: str) -> tuple[Optional[str], Optional[str]]:
    for status in STATUSES:
        _, _, body = _section(content, status)
        for line in body.splitlines():
            if f"[id:{idea_id}]" in line:
                return status, line
    return None, None


def cmd_add(args: argparse.Namespace) -> int:
    content = _read()
    stamp = _now()
    idea_id = _short_id(stamp, args.text)
    line = f"- [{stamp}] [src:{args.source}] [id:{idea_id}] {args.text}"
    content = _append_to(content, "raw", line)
    _write(content)
    out = {"ok": True, "id": idea_id, "status": "raw", "captured_at": stamp}
    if args.json:
        print(json.dumps(out))
    else:
        print(f"captured  id={idea_id}  status=raw  at {stamp}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    content = _read()
    targets = STATUSES if args.status == "all" else [args.status]
    rows = []
    for status in targets:
        _, _, body = _section(content, status)
        for line in body.splitlines():
            if line.strip().startswith("- ["):
                rows.append((status, line.strip()))
    if args.limit:
        rows = rows[-args.limit :] if args.status != "all" else rows[: args.limit]
    if args.json:
        print(json.dumps([{"status": s, "line": l} for s, l in rows], indent=2))
        return 0
    if not rows:
        print(f"(no ideas in {args.status})")
        return 0
    last_status = None
    for s, l in rows:
        if s != last_status:
            print(f"\n[{s}]")
            last_status = s
        print(f"  {l[2:]}")
    return 0


def cmd_sharpen(args: argparse.Namespace) -> int:
    content = _read()
    status, line = _find(content, args.id)
    if not status:
        sys.exit(f"id not found: {args.id}")
    if status != "raw":
        sys.exit(f"id {args.id} is in {status}, not raw")
    content, removed = _remove_line(content, "raw", args.id)
    if not removed:
        sys.exit("internal: line vanished")
    enriched = removed.rstrip()
    enriched += f"\n    hook: {args.hook}"
    if args.outline:
        enriched += f"\n    outline: {args.outline}"
    content = _append_to(content, "sharpened", enriched)
    _write(content)
    print(f"sharpened  id={args.id}  status=sharpened")
    return 0


def cmd_move(args: argparse.Namespace) -> int:
    if args.to not in STATUSES:
        sys.exit(f"--to must be one of {STATUSES}")
    content = _read()
    status, line = _find(content, args.id)
    if not status:
        sys.exit(f"id not found: {args.id}")
    if status == args.to:
        print(f"id {args.id} already in {args.to}")
        return 0
    content, removed = _remove_line(content, status, args.id)
    if not removed:
        sys.exit("internal: line vanished")
    if args.note:
        removed = removed.rstrip() + f"\n    note: {args.note}"
    content = _append_to(content, args.to, removed)
    _write(content)
    print(f"moved  id={args.id}  {status} -> {args.to}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    content = _read()
    status, line = _find(content, args.id)
    if not status:
        sys.exit(f"id not found: {args.id}")
    print(f"[{status}] {line}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="capture_idea")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="capture a new raw idea")
    a.add_argument("text")
    a.add_argument("--source", default="cli", choices=["cli", "telegram", "voice", "claude", "other"])
    a.add_argument("--json", action="store_true")
    a.set_defaults(fn=cmd_add)

    l = sub.add_parser("list", help="list ideas by status")
    l.add_argument("--status", default="raw", choices=[*STATUSES, "all"])
    l.add_argument("--limit", type=int, default=0)
    l.add_argument("--json", action="store_true")
    l.set_defaults(fn=cmd_list)

    s = sub.add_parser("sharpen", help="add hook+outline to a raw idea")
    s.add_argument("id")
    s.add_argument("--hook", required=True)
    s.add_argument("--outline", default="")
    s.set_defaults(fn=cmd_sharpen)

    m = sub.add_parser("move", help="move idea between statuses")
    m.add_argument("id")
    m.add_argument("--to", required=True)
    m.add_argument("--note", default="")
    m.set_defaults(fn=cmd_move)

    sh = sub.add_parser("show", help="show a single idea by id")
    sh.add_argument("id")
    sh.set_defaults(fn=cmd_show)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
