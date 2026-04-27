"""
Maven Notification System — Telegram alerts for CC's marketing surface.

Distinct from Bravo (Business-Empire-Agent) and Atlas (CFO-Agent), Maven runs
its OWN Telegram bot so the three C-suite agents never conflict on polling.
Token and allowed-users live under MAVEN_TELEGRAM_BOT_TOKEN +
MAVEN_TELEGRAM_ALLOWED_USERS in .env.agents. If those keys are missing, this
module falls back to BRAVO_TELEGRAM_BOT_TOKEN / TELEGRAM_BOT_TOKEN so single-
bot setups still work.

Usage:
    from notify import notify
    notify("Meta campaign launched: OASIS pulse-lead-gen — $50/day",
           category="campaign")
    notify("CFO gate blocked $500 Meta spend — pulse stale", category="cfo-block")
    notify("Brand voice violation in draft — campaign held",
           category="brand-violation", force=True)

Marketing-specific categories (default routing):
- ALWAYS LOUD (sound on):
    cfo-block, brand-violation, ad-spend-overrun, draft-critic-block,
    daily-cap-threshold, killswitch, send-gateway-error, error
- SILENT (no sound):
    campaign, lead-captured, content-published, ab-test-winner, performance,
    publish-success
- BLOCKED by default (verbose noise):
    debug, heartbeat

Override via NOTIFY_BLOCKED_CATEGORIES (comma-sep) in .env.agents.

EVERY message also lands in memory/notify.log as a forensic trail —
even if Telegram is down, CC has a tail-able record of what fired.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env.agents"
NOTIFY_LOG = PROJECT_ROOT / "memory" / "notify.log"

_env_cache: dict[str, str] = {}

DEFAULT_BLOCKED = {"debug", "heartbeat"}
DEFAULT_SILENT = {
    "campaign", "lead-captured", "content-published", "ab-test-winner",
    "performance", "publish-success",
}

# Marketing-specific category labels — the line CC sees first on his phone.
CATEGORY_PREFIX: dict[str, str] = {
    "campaign":            "Campaign",
    "ad-spend-overrun":    "Ad Spend Overrun",
    "cfo-block":           "CFO Block",
    "brand-violation":     "Brand Violation",
    "draft-critic-block":  "Critic Block",
    "daily-cap-threshold": "Daily Cap Approaching",
    "killswitch":          "KILLSWITCH",
    "send-gateway-error":  "Send Gateway Error",
    "lead-captured":       "Lead Captured",
    "content-published":   "Content Published",
    "publish-success":     "Published",
    "ab-test-winner":      "A/B Test Winner",
    "performance":         "Performance",
    "error":               "Error",
    "system":              "Maven",
}


def _load_env() -> dict[str, str]:
    """Read .env.agents once and cache it. Returns empty dict if missing."""
    global _env_cache
    if _env_cache:
        return _env_cache
    if not ENV_PATH.exists():
        return _env_cache
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                _env_cache[key.strip()] = value.strip()
    return _env_cache


def _resolve_token(env: dict[str, str]) -> Optional[str]:
    """Maven's bot first; fall back to shared/Bravo so single-bot rigs still work."""
    return (
        env.get("MAVEN_TELEGRAM_BOT_TOKEN")
        or env.get("BRAVO_TELEGRAM_BOT_TOKEN")
        or env.get("TELEGRAM_BOT_TOKEN")
    )


def _resolve_chat_ids(env: dict[str, str]) -> list[str]:
    raw = (
        env.get("MAVEN_TELEGRAM_ALLOWED_USERS")
        or env.get("TELEGRAM_ALLOWED_USERS")
        or ""
    )
    return [c.strip() for c in raw.split(",") if c.strip()]


def _get_blocked_categories(env: dict[str, str]) -> set[str]:
    override = env.get("NOTIFY_BLOCKED_CATEGORIES", "")
    if override:
        return {c.strip().lower() for c in override.split(",") if c.strip()}
    return DEFAULT_BLOCKED


def _append_to_log(category: str, message: str) -> None:
    """File-based forensic trail. Always written, regardless of Telegram outcome."""
    try:
        NOTIFY_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().isoformat()
        with open(NOTIFY_LOG, "a", encoding="utf-8") as f:
            # First-line-only flatten so the log stays grep-friendly
            flat = message.replace("\n", " | ")[:500]
            f.write(f"{ts}\t{category}\t{flat}\n")
    except Exception:
        # Logging must never raise — notify is called from gate fast paths.
        pass


def notify(
    message: str,
    category: str = "system",
    silent: bool = False,
    force: bool = False,
) -> bool:
    """Send a Telegram notification to CC about a Maven-domain event.

    Returns True if Telegram accepted the send, False otherwise. Even on
    False, the message is appended to memory/notify.log so nothing is lost.
    """
    category = (category or "system").lower()
    env = _load_env()

    # File log first so it's the source of truth even when Telegram is dead.
    _append_to_log(category, message)

    # Block noisy categories unless forced.
    if not force and category in _get_blocked_categories(env):
        return False

    # Auto-silence high-volume categories unless caller overrides.
    if category in DEFAULT_SILENT and not force:
        silent = True

    token = _resolve_token(env)
    chat_ids = _resolve_chat_ids(env)

    if not token:
        print("[notify] No Telegram bot token in .env.agents "
              "(MAVEN_TELEGRAM_BOT_TOKEN preferred)", file=sys.stderr)
        return False
    if not chat_ids:
        print("[notify] MAVEN_TELEGRAM_ALLOWED_USERS / TELEGRAM_ALLOWED_USERS "
              "missing or empty in .env.agents", file=sys.stderr)
        return False

    try:
        import requests
    except ImportError:
        # No requests in env — file log already captured the message.
        return False

    prefix = CATEGORY_PREFIX.get(category, "Maven")
    ts = datetime.now().strftime("%#I:%M %p" if sys.platform == "win32" else "%-I:%M %p")
    body = f"{prefix}\n{message}\n\n{ts}"
    if len(body) > 4096:
        body = body[:4093] + "..."

    ok_any = False
    for chat_id in chat_ids:
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": body,
                    "parse_mode": "HTML",
                    "disable_notification": silent,
                },
                timeout=5,
            )
            payload = resp.json() if resp.content else {}
            if payload.get("ok"):
                ok_any = True
            else:
                err = payload.get("description", f"HTTP {resp.status_code}")
                print(f"[notify] Telegram send failed for {chat_id}: {err}",
                      file=sys.stderr)
        except Exception as exc:
            print(f"[notify] Telegram send exception for {chat_id}: {exc}",
                  file=sys.stderr)
    return ok_any


def notify_error(component: str, error: str) -> bool:
    """Always-loud error alert — bypasses category filtering."""
    return notify(f"{component}: {error}", category="error", force=True)


def notify_killswitch_engaged() -> bool:
    """Alert that MAVEN_FORCE_DRY_RUN is engaged so CC knows nothing is sending."""
    return notify(
        "MAVEN_FORCE_DRY_RUN=1 is set. All sends are dry-run; nothing is "
        "actually publishing or charging.",
        category="killswitch", force=True,
    )


if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Maven notification online."
    cat = "system"
    # Allow `python scripts/notify.py campaign:Meta launched 50/day`
    if msg and ":" in msg.split()[0]:
        head, _, rest = msg.partition(" ")
        cat, _, message_only = head.partition(":")
        if rest:
            msg = (message_only + " " + rest).strip() if message_only else rest
        else:
            msg = message_only
    ok = notify(msg, category=cat)
    print(f"Sent: {ok}")
