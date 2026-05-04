"""
token_expiry_check.py — Watch Maven's external API tokens for expiry drift.

Runs as a Maven cron job (Mondays 08:00). Checks every credential Maven
depends on for paid campaigns, social scheduling, and content distribution.
If any token is within N days of expiry (or already expired), posts an
agent_inbox notification to CC and Bravo.

Currently checks:
  - Meta (Facebook + Instagram) — long-lived user token, ~60-day lifecycle
  - Google Ads — refresh token (effectively non-expiring) + access token
  - Late / Zernio API key — non-expiring but configured to flag if missing
  - Anthropic / OpenAI keys — flag if missing (no expiry data exposed)

Output: human-readable to stdout, JSON via --json. Non-zero exit if any
credential is expired or within --warn-days days of expiry.

Usage:
  python scripts/token_expiry_check.py
  python scripts/token_expiry_check.py --warn-days 14 --json
  python scripts/token_expiry_check.py --notify     # post to agent_inbox
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

ENV_KEYS_TO_CHECK = [
    ("META_LONG_LIVED_TOKEN", "Meta (Facebook + Instagram)", 60),
    ("META_TOKEN_ISSUED_AT", None, None),  # ISO 8601 issued-at, paired with above
    ("GOOGLE_ADS_REFRESH_TOKEN", "Google Ads", None),  # refresh tokens don't expire
    ("GOOGLE_ADS_DEVELOPER_TOKEN", "Google Ads developer", None),
    ("LATE_API_KEY", "Late/Zernio", None),
    ("ANTHROPIC_API_KEY", "Anthropic", None),
    ("OPENAI_API_KEY", "OpenAI", None),
]


def _load_env_agents() -> dict[str, str]:
    """Read .env.agents from repo root; tolerate missing file."""
    env_path = REPO_ROOT / ".env.agents"
    if not env_path.exists():
        return {}
    out: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _check_meta(env: dict[str, str]) -> dict[str, Any]:
    token = env.get("META_LONG_LIVED_TOKEN") or os.environ.get("META_LONG_LIVED_TOKEN")
    issued_at = env.get("META_TOKEN_ISSUED_AT") or os.environ.get("META_TOKEN_ISSUED_AT")
    result: dict[str, Any] = {"service": "Meta (Facebook + Instagram)", "key": "META_LONG_LIVED_TOKEN"}
    if not token:
        result["status"] = "MISSING"
        result["days_left"] = None
        return result
    if not issued_at:
        result["status"] = "UNKNOWN_AGE"
        result["days_left"] = None
        result["note"] = "Set META_TOKEN_ISSUED_AT to ISO 8601 date when token was minted"
        return result
    try:
        normalized = issued_at[:-1] + "+00:00" if issued_at.endswith("Z") else issued_at
        issued_dt = datetime.fromisoformat(normalized)
        if issued_dt.tzinfo is None:
            issued_dt = issued_dt.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - issued_dt).days
        days_left = 60 - age_days
        result["days_left"] = days_left
        result["status"] = "EXPIRED" if days_left <= 0 else "OK"
    except (ValueError, TypeError):
        result["status"] = "BAD_DATE"
        result["days_left"] = None
    return result


def _check_present_only(env: dict[str, str], key: str, label: str) -> dict[str, Any]:
    value = env.get(key) or os.environ.get(key)
    return {
        "service": label,
        "key": key,
        "status": "OK" if value else "MISSING",
        "days_left": None,
    }


def run_checks(warn_days: int = 14) -> list[dict[str, Any]]:
    env = _load_env_agents()
    results: list[dict[str, Any]] = []
    results.append(_check_meta(env))
    for key, label, _ in ENV_KEYS_TO_CHECK:
        if key in ("META_LONG_LIVED_TOKEN", "META_TOKEN_ISSUED_AT") or label is None:
            continue
        r = _check_present_only(env, key, label)
        results.append(r)
    for r in results:
        if r["status"] == "OK" and r.get("days_left") is not None and r["days_left"] <= warn_days:
            r["status"] = "EXPIRING"
    return results


def _post_inbox(results: list[dict[str, Any]]) -> None:
    """Post a high-priority message to bravo's inbox if anything is expired/expiring."""
    problems = [r for r in results if r["status"] in ("EXPIRED", "EXPIRING", "MISSING", "UNKNOWN_AGE", "BAD_DATE")]
    if not problems:
        return
    bravo_inbox_script = REPO_ROOT.parent / "Business-Empire-Agent" / "scripts" / "agent_inbox.py"
    if not bravo_inbox_script.exists():
        return
    subject = f"Maven token health: {len(problems)} issue(s)"
    body_lines = ["Maven token_expiry_check.py results:"]
    for p in problems:
        line = f"  [{p['status']}] {p['service']} ({p['key']})"
        if p.get("days_left") is not None:
            line += f" — {p['days_left']} days left"
        if p.get("note"):
            line += f" — {p['note']}"
        body_lines.append(line)
    priority = "high" if any(p["status"] == "EXPIRED" for p in problems) else "normal"
    try:
        subprocess.run(
            [
                sys.executable, str(bravo_inbox_script), "post",
                "--from", "maven", "--to", "bravo",
                "--subject", subject,
                "--body", "\n".join(body_lines),
                "--priority", priority,
            ],
            check=False, timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        pass


def main() -> None:
    p = argparse.ArgumentParser(description="Maven external token expiry watcher.")
    p.add_argument("--warn-days", type=int, default=14, help="Days-before-expiry threshold")
    p.add_argument("--json", action="store_true")
    p.add_argument("--notify", action="store_true", help="Post to Bravo's agent_inbox if any problems")
    args = p.parse_args()

    results = run_checks(warn_days=args.warn_days)
    bad = [r for r in results if r["status"] not in ("OK",)]

    if args.notify:
        _post_inbox(results)

    if args.json:
        print(json.dumps({"warn_days": args.warn_days, "results": results, "issues": len(bad)}, indent=2))
    else:
        for r in results:
            line = f"  [{r['status']:>11}] {r['service']:<35} {r['key']}"
            if r.get("days_left") is not None:
                line += f"  ({r['days_left']}d left)"
            print(line)
        if bad:
            print(f"\n{len(bad)} credential issue(s).")
        else:
            print("\nAll credentials OK.")
    sys.exit(0 if not bad else 1)


if __name__ == "__main__":
    main()
