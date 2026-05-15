"""codex_delegate — Maven-side CLI wrapper for delegating backend marketing tasks (ad-copy variants, attribution math, A/B significance) to OpenAI Codex via codex-companion.mjs."""
#!/usr/bin/env python3
# Wraps $CLAUDE_PLUGIN_ROOT/scripts/codex-companion.mjs.
# Never delegates: brand voice, creative direction, MCP-dependent tasks.

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_PLUGIN_ROOT = Path(os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    r"C:\Users\User\.claude\codex-plugin",
))
COMPANION_SCRIPT = DEFAULT_PLUGIN_ROOT / "scripts" / "codex-companion.mjs"

MAVEN_CONTEXT_PRELUDE = """
[Maven CMO context]
Repo: C:\\Users\\User\\CMO-Agent
Brands: OASIS AI, Conaugh personal brand, PropFlow, Nostalgic Requests, SunBiz Funding.
Constraints:
  - Every ad-copy recommendation must cite at least 1 framework from
    brain/MARKETING_CANON.md (uncited = "craft, not marketing").
  - Marketing email goes through scripts/send_gateway.py — never bypass.
  - Spend requests go through cfo_pulse.json (Atlas approves).
  - SunBiz copy: never use "loan"; use "advances", "funding", "capital".
  - Conaugh's external-facing name is "Conaugh McKenna" (never "CC").
"""


def _run(args: list[str]) -> int:
    if not COMPANION_SCRIPT.exists():
        print(f"ERROR: codex-companion.mjs not found at {COMPANION_SCRIPT}", file=sys.stderr)
        print("Set CLAUDE_PLUGIN_ROOT env var or install the codex plugin.", file=sys.stderr)
        return 2
    cmd = ["node", str(COMPANION_SCRIPT)] + args
    return subprocess.call(cmd, env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(DEFAULT_PLUGIN_ROOT)})


def cmd_task(args) -> int:
    prompt = MAVEN_CONTEXT_PRELUDE.strip() + "\n\n" + args.prompt
    bridge_args = ["task"]
    if args.write:
        bridge_args.append("--write")
    bridge_args.append(prompt)
    return _run(bridge_args)


def cmd_review(args) -> int:
    return _run(["review"])


def cmd_adversarial(args) -> int:
    return _run(["adversarial-review", args.focus])


def cmd_status(args) -> int:
    return _run(["status"])


def cmd_result(args) -> int:
    return _run(["result"])


def main() -> int:
    p = argparse.ArgumentParser(
        prog="codex_delegate.py",
        description="Maven-side Codex delegation wrapper.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pt = sub.add_parser("task", help="Delegate a task to Codex")
    pt.add_argument("--write", action="store_true",
                    help="Allow Codex to write files (default: read-only)")
    pt.add_argument("prompt", help="The task prompt for Codex")

    sub.add_parser("review", help="Run a Codex code-review pass")

    pa = sub.add_parser("adversarial-review", help="Adversarial review with focus")
    pa.add_argument("focus", help="What to focus the review on")

    sub.add_parser("status", help="Check Codex job status")
    sub.add_parser("result", help="Fetch the last Codex result")

    args = p.parse_args()
    return {
        "task": cmd_task,
        "review": cmd_review,
        "adversarial-review": cmd_adversarial,
        "status": cmd_status,
        "result": cmd_result,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
