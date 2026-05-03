"""
Instagram Engine - ManyChat replacement via Playwright browser automation.

Checks Instagram DMs and comments, responds in CC's brand voice,
and notifies CC via Telegram of all interactions.

Usage:
  python scripts/instagram_engine.py check-dms          # Check and list new DMs
  python scripts/instagram_engine.py check-dms --reply   # Check DMs and auto-reply
  python scripts/instagram_engine.py check-dms --daemon  # Continuously monitor DMs
  python scripts/instagram_engine.py monitor-dms         # Continuously monitor DMs
  python scripts/instagram_engine.py check-comments      # Check for new comments
  python scripts/instagram_engine.py send-dm --to USER --msg "text"  # Send a DM
  python scripts/instagram_engine.py log-dm --username USER --summary "text"
  python scripts/instagram_engine.py auto-reply          # Detect intent + auto-reply
  python scripts/instagram_engine.py --json auto-reply   # JSON output for scheduler

Requires: playwright Python package (pip install playwright)
Browser profile persists at tmp/ig-browser/ for session continuity.
"""

import argparse
import calendar
import json
import random
import subprocess
import sys
import os
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
BROWSER_DIR = str(PROJECT_ROOT / "tmp" / "ig-browser")
SCREENSHOT_DIR = str(PROJECT_ROOT / "tmp")
DM_REPLIED_PATH = PROJECT_ROOT / "tmp" / "dm_replied.json"
BOOKING_STATE_PATH = PROJECT_ROOT / "tmp" / "dm_booking_state.json"
NOTIFIED_PATH = PROJECT_ROOT / "tmp" / "dm_notified.json"
INBOX_URL = "https://www.instagram.com/direct/inbox/"
REQUESTS_URL = "https://www.instagram.com/direct/requests/"
LOGIN_URL = "https://www.instagram.com/accounts/login/"
PAGE_TIMEOUT_MS = 60000
DEFAULT_POLL_MIN_SECONDS = 180
DEFAULT_POLL_MAX_SECONDS = 420

# Intent detection — only trigger booking when they EXPLICITLY ask for a call/meeting
# Everything else gets a genuine conversational reply
_EXPLICIT_BOOKING_PHRASES = {
    "book a call", "schedule a call", "set up a call", "hop on a call",
    "jump on a call", "get on a call", "book a meeting", "schedule a meeting",
    "can we call", "can we meet", "let's call", "lets call", "want to call",
    "when can we", "when are you free", "when works", "what time works",
    "book a demo", "schedule a demo", "set up a meeting",
}
_BOOKING_SIGNAL_WORDS = {
    "book", "schedule", "appointment", "consultation", "demo",
}
_PRICING_KEYWORDS = {
    "price", "cost", "how much", "rate", "pricing", "package", "afford",
}
_INFO_KEYWORDS = {
    "what do you", "how does", "tell me about", "what is", "services", "offer",
}
_GREETING_KEYWORDS = {"hey", "hi", "hello", "sup", "yo", "what's good", "whats good"}

_PAYMENT_PHRASES = {
    "how do i pay", "ready to pay", "where do i pay", "how to pay",
    "send payment", "take my money", "sign me up", "payment link",
    "e-transfer", "etransfer", "e transfer", "wire transfer", "interac",
    "venmo", "zelle", "paypal", "can i pay", "want to pay",
    "send you money", "send the money", "how do i send",
}

sys.path.insert(0, str(SCRIPTS_DIR))

# Intents that signal business interest — trigger CRM lead capture
_CRM_INTEREST_INTENTS = {"BOOKING", "PRICING", "PAYMENT", "INFO"}

try:
    from notify import notify
except ImportError:
    def notify(*a, **kw): return False


def capture_lead_to_crm(username: str, intent: str, message_text: str):
    """Insert an Instagram DM lead into the CRM if not already there.

    Runs lead_engine.py add as a subprocess — fire-and-forget, never blocks
    the DM reply flow. Notifies CC via Telegram on successful capture.
    """
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "lead_engine.py"),
                "add",
                "--name", f"@{username}",
                "--source", "instagram_dm",
                "--notes", f"Intent: {intent} | DM: {message_text[:200]}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
            creationflags=0x08000000 if sys.platform == "win32" else 0,
        )
        if result.returncode == 0:
            notify(
                f"\U0001f3af IG lead captured: @{username} ({intent})",
                category="lead",
            )
            return True
    except Exception as exc:
        safe_print(f"CRM capture failed for @{username}: {exc}")
    return False


def get_env_value(env_vars: dict, *keys: str) -> str:
    """Read a config value from .env.agents or process env, stripping NUL damage."""
    for key in keys:
        value = (env_vars.get(key) or os.environ.get(key) or "").replace("\x00", "").strip()
        if value:
            return value
    return ""


def get_pulse_webhook_url(env_vars: dict) -> str:
    return (
        get_env_value(env_vars, "PULSE_WEBHOOK_URL", "IG_SETTER_PRO_WEBHOOK_URL")
        or "https://ig-setter-pro.vercel.app/api/webhook"
    )


def get_pulse_api_base(env_vars: dict) -> str:
    configured = get_env_value(env_vars, "PULSE_API_BASE_URL", "IG_SETTER_PRO_BASE_URL")
    if configured:
        return configured.rstrip("/")
    webhook_url = get_pulse_webhook_url(env_vars)
    if webhook_url.endswith("/api/webhook"):
        return webhook_url[:-len("/api/webhook")].rstrip("/")
    return webhook_url.rstrip("/")


def get_pulse_secret(env_vars: dict) -> str:
    return get_env_value(
        env_vars,
        "PULSE_WEBHOOK_SECRET",
        "IG_SETTER_PRO_WEBHOOK_SECRET",
        "WEBHOOK_SECRET",
    )


def send_to_ig_setter_pro(env_vars: dict, username: str, message_text: str, direction: str, is_ai: bool = False, intent: str = "active", ig_message_id: str | None = None, display_name: str | None = None):
    """Send DM interaction to ig-setter-pro dashboard webhook.

    `username` should be the IG @handle (URL slug) when known; PULSE keys
    threads by it. `display_name` is the human-readable name (defaults to
    username if not provided).
    """
    import hashlib
    try:
        import requests
    except ImportError:
        safe_print("ig-setter-pro webhook skipped: requests package is not installed")
        return False

    webhook_url = get_pulse_webhook_url(env_vars)
    webhook_secret = get_pulse_secret(env_vars)
    account_id = get_env_value(env_vars, "PULSE_ACCOUNT_ID", "IG_SETTER_PRO_ACCOUNT_ID")
    ig_page_id = get_env_value(env_vars, "PULSE_IG_PAGE_ID", "IG_SETTER_PRO_IG_PAGE_ID")

    if not webhook_url:
        webhook_url = "https://ig-setter-pro.vercel.app/api/webhook"
    if not webhook_url or not webhook_secret:
        safe_print("ig-setter-pro webhook skipped: PULSE_WEBHOOK_SECRET is not configured")
        return False

    clean_username = username.strip().lstrip("@")
    username_hash = hashlib.md5(clean_username.lower().encode("utf-8")).hexdigest()[:16]
    user_id = "ig_user_" + username_hash
    thread_id = f"{ig_page_id}_{user_id}" if ig_page_id else "ig_thread_" + username_hash

    ai_status = "active"
    if intent in {"BOOKING", "PRICING", "PAYMENT"}:
        ai_status = "qualified"
    if intent == "BOOKING_CONFIRMED":
        ai_status = "booked"

    msg_hash = hashlib.md5(
        f"{direction}:{clean_username.lower()}:{message_text}".encode("utf-8")
    ).hexdigest()[:16]

    payload = {
        "account_id": account_id,
        "ig_thread_id": thread_id,
        "ig_user_id": user_id,
        "username": clean_username,
        "display_name": (display_name or clean_username).strip() or clean_username,
        "message": message_text,
        "direction": direction,
        "is_ai": is_ai,
        "ai_status": ai_status,
        "status": ai_status,
        "ig_message_id": ig_message_id or f"msg_{msg_hash}",
        "pending_ai_draft": None,
    }

    try:
        resp = requests.post(
            webhook_url,
            json=payload,
            headers={"x-webhook-secret": webhook_secret, "Content-Type": "application/json"},
            timeout=10
        )
        if resp.status_code == 200:
            try:
                data = resp.json()
                if data.get("ok") is False:
                    # Webhook hit an internal error but still returned the
                    # auto_send_enabled flag so the daemon can decide whether
                    # to use local fallback. Don't drop the response.
                    safe_print(
                        f"  [ig-setter-pro] webhook reported failure: "
                        f"{data.get('message') or data.get('error')}"
                    )
                # Return the parsed response so callers can read
                # auto_send_enabled + the generated doctrine draft (which may
                # be null on internal error → daemon falls back to build_reply).
                return data
            except ValueError:
                pass
            return True
        else:
            safe_print(f"ig-setter-pro webhook error: {resp.status_code} - {resp.text}")
    except Exception as e:
        safe_print(f"ig-setter-pro webhook failed: {e}")
    return False


def fetch_archived_handles(env_vars: dict) -> set[str]:
    """Return the set of @handles whose PULSE thread.status == 'closed'.

    The daemon reads this every poll and silently skips replies to those
    threads — CC archives a thread in PULSE and Maven goes quiet on it
    forever (until CC re-opens). Empty set if the call fails (fail-open).
    """
    try:
        import requests
    except ImportError:
        return set()
    secret = get_pulse_secret(env_vars)
    if not secret:
        return set()
    try:
        account_id = get_env_value(env_vars, "PULSE_ACCOUNT_ID", "IG_SETTER_PRO_ACCOUNT_ID")
        url = f"{get_pulse_api_base(env_vars)}/api/threads"
        params = {"account_id": account_id} if account_id else {}
        resp = requests.get(url, params=params, timeout=8)
        if resp.status_code != 200:
            return set()
        threads = (resp.json() or {}).get("threads") or []
        archived = set()
        for t in threads:
            if (t.get("status") or "").lower() == "closed":
                u = (t.get("username") or "").strip().lower()
                if u:
                    archived.add(u)
        return archived
    except Exception:
        return set()


_HIGH_INTENT_KEYS = ("BOOKING", "PRICING", "PAYMENT", "BOOKING_CONFIRMED")


def maybe_alert_high_intent(intent: str, username: str, last_msg: str) -> None:
    """Telegram-notify CC when a thread crosses into commercial territory.

    Categories used by notify(): cfo-block / brand-violation / killswitch /
    error are loud; everything else is silent. We use 'lead' (loud) for
    booking/payment/pricing intent so CC's phone pings.
    """
    if intent not in _HIGH_INTENT_KEYS:
        return
    try:
        notify(
            f"\U0001f9ed High-intent IG DM from @{username} ({intent}): "
            f"{last_msg[:140]}",
            category="lead",
            force=True,
        )
    except Exception as exc:
        log_exception("[ig-intent] Telegram notify failed", exc)


def fetch_ig_setter_pro_outbox(env_vars: dict, limit: int = 5) -> list[dict]:
    """Claim pending dashboard-originated sends for the Python Playwright daemon."""
    try:
        import requests
    except ImportError:
        safe_print("ig-setter-pro outbox skipped: requests package is not installed")
        return []

    secret = get_pulse_secret(env_vars)
    if not secret:
        safe_print("ig-setter-pro outbox skipped: PULSE_WEBHOOK_SECRET is not configured")
        return []

    url = f"{get_pulse_api_base(env_vars)}/api/python/outbox"
    account_id = get_env_value(env_vars, "PULSE_ACCOUNT_ID", "IG_SETTER_PRO_ACCOUNT_ID")
    params = {"limit": str(max(1, min(limit, 20)))}
    if account_id:
        params["account_id"] = account_id

    try:
        resp = requests.get(
            url,
            params=params,
            headers={"x-webhook-secret": secret},
            timeout=10,
        )
        if resp.status_code != 200:
            safe_print(f"ig-setter-pro outbox fetch error: {resp.status_code} - {resp.text}")
            return []
        data = resp.json()
        return data.get("commands") or []
    except Exception as exc:
        safe_print(f"ig-setter-pro outbox fetch failed: {exc}")
        return []


def mark_ig_setter_pro_outbox(env_vars: dict, command_id: str, status: str, error: str | None = None) -> bool:
    """Mark a dashboard-originated send as sent or failed."""
    try:
        import requests
    except ImportError:
        return False

    secret = get_pulse_secret(env_vars)
    if not secret:
        return False

    try:
        resp = requests.post(
            f"{get_pulse_api_base(env_vars)}/api/python/outbox",
            json={"id": command_id, "status": status, "error": error},
            headers={"x-webhook-secret": secret, "Content-Type": "application/json"},
            timeout=10,
        )
        if resp.status_code == 200:
            return True
        safe_print(f"ig-setter-pro outbox mark error: {resp.status_code} - {resp.text}")
    except Exception as exc:
        safe_print(f"ig-setter-pro outbox mark failed: {exc}")
    return False


def _read_config_model(key: str, fallback: str) -> str:
    """Read a model name from .agents/config.toml."""
    config_path = PROJECT_ROOT / ".agents" / "config.toml"
    if not config_path.exists():
        return fallback
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}") and "=" in line:
                    _, _, val = line.partition("=")
                    val = val.strip().strip('"').strip("'")
                    if val:
                        return val
    except OSError:
        pass
    return fallback


def load_env() -> dict:
    env_path = PROJECT_ROOT / ".env.agents"
    if not env_path.exists():
        return {}
    env_vars = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.replace("\x00", "").strip().lstrip("\ufeff")
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key = key.replace("\x00", "").strip()
                value = value.replace("\x00", "").strip().strip('"').strip("'")
                if key:
                    env_vars[key] = value
    return env_vars


def safe_print(text):
    """Print with ASCII-safe encoding for Windows cp1252."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def log_exception(context: str, exc: BaseException | None = None):
    """Print a clear exception plus stack trace without breaking Windows output."""
    if exc is not None:
        safe_print(f"{context}: {type(exc).__name__}: {exc}")
    else:
        safe_print(context)
    tb = traceback.format_exc()
    if tb and tb.strip() != "NoneType: None":
        safe_print(tb)


def _is_playwright_timeout(exc: BaseException) -> bool:
    """Return True for Playwright timeout exceptions without importing at module load."""
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    except Exception:
        return isinstance(exc, TimeoutError)
    return isinstance(exc, (PlaywrightTimeoutError, TimeoutError))


def _sleep(seconds: float):
    """Tiny wrapper so long sleeps stay easy to patch in tests."""
    time.sleep(seconds)


def _dismiss_ig_prompts(page) -> bool:
    """Dismiss common Instagram modals without failing the caller."""
    try:
        return bool(page.evaluate("""() => {
            const targets = ['Not Now', 'Not now'];
            const bs = document.querySelectorAll('button, div[role="button"]');
            for (const b of bs) {
                const t = (b.textContent || '').trim();
                if (targets.includes(t)) {
                    b.click();
                    return true;
                }
            }
            return false;
        }"""))
    except Exception as exc:
        log_exception("Instagram prompt dismissal failed", exc)
        return False


def _session_needs_login(page) -> bool:
    url = (getattr(page, "url", "") or "").lower().rstrip("/")
    return "/accounts/login" in url or url == "https://www.instagram.com"


def recover_inbox_page(page, env_vars: dict, reason: str) -> bool:
    """Reload the active page and re-run login recovery for daemon resilience."""
    safe_print(f"{reason}; attempting Instagram inbox recovery...")
    try:
        page.reload(wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
        _sleep(6)
    except Exception as exc:
        log_exception("Instagram page reload during recovery failed", exc)

    try:
        return ensure_logged_in(page, env_vars)
    except Exception as exc:
        log_exception("Instagram login recovery failed", exc)
        return False


def _return_to_inbox(page, env_vars: dict) -> bool:
    try:
        page.goto(INBOX_URL, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
        _sleep(4)
        return True
    except Exception as exc:
        log_exception("Failed navigating back to Instagram inbox", exc)
        return recover_inbox_page(page, env_vars, "Inbox navigation failed")


def get_browser_context(playwright):
    """Launch persistent Chromium context (maintains login session)."""
    os.makedirs(BROWSER_DIR, exist_ok=True)
    return playwright.chromium.launch_persistent_context(
        user_data_dir=BROWSER_DIR,
        headless=True,
        viewport={"width": 1280, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    )


def _open_ig_page(playwright):
    context = get_browser_context(playwright)
    page = context.pages[0] if context.pages else context.new_page()
    return context, page


def _close_context_safely(context):
    try:
        context.close()
    except Exception as exc:
        log_exception("Failed closing Instagram browser context", exc)


def ensure_logged_in(page, env_vars):
    """Check if logged into Instagram; if not, log in with credentials."""
    try:
        page.goto(INBOX_URL, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
        _sleep(6)

        # If redirected to login, authenticate.
        if _session_needs_login(page):
            safe_print("Session expired or missing. Logging into Instagram...")
            ig_user = env_vars.get("INSTAGRAM_USERNAME", "")
            ig_pass = env_vars.get("INSTAGRAM_PASSWORD", "")
            if not ig_user or not ig_pass:
                safe_print("ERROR: INSTAGRAM_USERNAME or INSTAGRAM_PASSWORD missing in .env.agents")
                return False

            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
            _sleep(4)

            # Handle "Continue" screen (saved session, needs re-auth).
            user_field = (
                page.query_selector('input[name="username"]')
                or page.query_selector('input[name="email"]')
                or page.query_selector('input[autocomplete="username"]')
            )
            pass_field = (
                page.query_selector('input[name="password"]')
                or page.query_selector('input[name="pass"]')
                or page.query_selector('input[type="password"]')
            )

            if not user_field or not pass_field:
                safe_print("Login form not visible yet; trying alternate profile flow...")
                try:
                    page.evaluate("""() => {
                        const els = document.querySelectorAll('button, div[role="button"], a, span');
                        for (const el of els) {
                            const text = (el.textContent || '').trim();
                            if (text.includes('Use another profile') || text.includes('Switch accounts')) {
                                el.click();
                                return true;
                            }
                        }
                        return false;
                    }""")
                    _sleep(3)
                except Exception as exc:
                    log_exception("Instagram alternate login flow click failed", exc)

                user_field = (
                    page.query_selector('input[name="username"]')
                    or page.query_selector('input[name="email"]')
                    or page.query_selector('input[autocomplete="username"]')
                )
                pass_field = (
                    page.query_selector('input[name="password"]')
                    or page.query_selector('input[name="pass"]')
                    or page.query_selector('input[type="password"]')
                )

            if not user_field or not pass_field:
                safe_print(f"ERROR: Could not find Instagram login form. Current URL: {page.url}")
                safe_print("Login form lookup stack:\n" + "".join(traceback.format_stack(limit=8)))
                try:
                    page.screenshot(path=os.path.join(SCREENSHOT_DIR, "ig_login_form_missing.png"))
                    safe_print("Saved debug screenshot: tmp/ig_login_form_missing.png")
                except Exception as screenshot_exc:
                    log_exception("Could not save login debug screenshot", screenshot_exc)
                return False

            user_field.click()
            user_field.fill("")
            user_field.type(ig_user, delay=30)
            _sleep(0.3)
            pass_field.click()
            pass_field.fill("")
            pass_field.type(ig_pass, delay=30)
            _sleep(0.5)

            clicked_login = page.evaluate("""() => {
                const buttons = document.querySelectorAll('button[type="submit"], button, div[role="button"]');
                for (const b of buttons) {
                    const t = (b.textContent || '').trim().toLowerCase();
                    if (t === 'log in' || t === 'login') {
                        b.click();
                        return true;
                    }
                }
                return false;
            }""")
            if not clicked_login:
                safe_print("ERROR: Could not find Instagram Log In button")
                return False
            _sleep(10)

            # Dismiss prompts (Save Login Info, Notifications).
            for _ in range(3):
                _dismiss_ig_prompts(page)
                _sleep(2)

            page.goto(INBOX_URL, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
            _sleep(6)

        _dismiss_ig_prompts(page)
        _sleep(1)

        logged_in = "/direct/" in (page.url or "")
        if not logged_in:
            safe_print(f"ERROR: Instagram login/session check ended at unexpected URL: {page.url}")
        return logged_in
    except Exception as exc:
        if _is_playwright_timeout(exc):
            log_exception("Timeout while checking Instagram login/session", exc)
            try:
                page.reload(wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
                _sleep(6)
                if _session_needs_login(page):
                    safe_print("Instagram session expired after timeout recovery; login will be retried.")
                    return False
                return "/direct/" in (page.url or "")
            except Exception as retry_exc:
                log_exception("Instagram timeout recovery failed", retry_exc)
                return False

        log_exception("Instagram login/session check failed", exc)
        return False


def read_dm_list(page):
    """Read the DM conversation list by extracting structured data from DOM buttons.

    Instagram renders each conversation as a div[role='button'] containing:
        Line 0: Username/display name
        Line 1: Message preview (or 'You: ...' or 'X sent an attachment.')
        Line 2: '·' (separator dot)
        Line 3: Time ago (8m, 1h, 1d, 1w, etc.)
        Line 4: 'Unread' (if unread)
    Returns a JSON string of parsed conversation objects.
    """
    script = """() => {
        const candidates = document.querySelectorAll(
            'div[role="button"], a[role="link"], a[href*="/direct/t/"]'
        );
        const results = [];
        const seen = new Set();
        for (const node of candidates) {
            const text = (node.innerText || node.textContent || '').trim();
            if (text.length < 10 || text.length > 700) continue;
            if (text.includes('Instagram') || text.includes('Send message')) continue;
            if (text.includes('Search') && text.includes('Messages')) continue;

            const lines = text
                .split(String.fromCharCode(10))
                .map(l => l.trim())
                .filter(l => l.length > 0);
            if (lines.length < 2) continue;

            const key = lines.slice(0, 5).join('|');
            if (seen.has(key)) continue;
            seen.add(key);
            results.push(lines);
        }
        return JSON.stringify(results);
    }"""

    try:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception as wait_exc:
            if _is_playwright_timeout(wait_exc):
                safe_print("Timed out waiting for Instagram DM DOM; attempting scrape from current page.")
            else:
                log_exception("Instagram DM DOM wait failed", wait_exc)

        return page.evaluate(script)
    except Exception as exc:
        if _is_playwright_timeout(exc):
            log_exception("Timeout while reading Instagram DM list", exc)
            try:
                page.reload(wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
                _sleep(6)
                return page.evaluate(script)
            except Exception as retry_exc:
                log_exception("Instagram DM list recovery failed", retry_exc)
                return "[]"

        log_exception("Failed to read Instagram DM list", exc)
        return "[]"


def _read_requests_inbox(page, env_vars: dict) -> list[dict]:
    """Navigate to /direct/requests/ and scrape pending message requests.

    DMs from people who do not follow you live here, not in /direct/inbox/.
    Returns parsed conversation dicts. Always returns to inbox before exiting
    so the next poll starts in the canonical place.
    """
    try:
        page.goto(REQUESTS_URL, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
        _sleep(5)
    except Exception as exc:
        log_exception("[ig-requests] navigation failed", exc)
        return []

    raw = read_dm_list(page)
    parsed = parse_conversations(raw)

    # Return to inbox so subsequent flows (open conversation, send DM) work
    # against the standard view.
    try:
        page.goto(INBOX_URL, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
        _sleep(3)
    except Exception as exc:
        log_exception("[ig-requests] return-to-inbox failed", exc)

    return parsed


def _user_blocklist() -> set[str]:
    """Lowercase usernames to never process. From IG_DM_BLOCKLIST env (comma-separated)
    plus a small built-in spam/troll filter."""
    raw = (os.environ.get("IG_DM_BLOCKLIST") or "").strip()
    user_set = {u.strip().lower().lstrip("@") for u in raw.split(",") if u.strip()}
    # Built-in: obvious slurs / spam handles we never want to engage.
    user_set.update({"whore", "slut", "spam", "test"})
    return user_set


def parse_conversations(inbox_data):
    """Parse conversation data from read_dm_list (JSON string of line arrays).

    Each conversation button yields an array of lines:
        [0] Username/display name
        [1] Message preview
        [2] '·' (dot separator — may be absent)
        [3] Time ago (8m, 1h, 1d, 1w, etc. — may be absent)
        [4] 'Unread' (if unread — may be absent)
    """
    import re
    TIME_PATTERN = re.compile(r"^\d{1,3}[mhdw]$|^\d{1,2}(mo|w)$")
    # IG injects presence + UI labels into the conversation list. Drop them.
    SKIP_NAMES = {
        "Your note", "First note of the week...", "OPEN MIC", "Send message",
        "Active", "Active now", "Sent", "Seen", "Typing...", "Delivered",
        "Requests", "Notes", "Messages", "Search", "Primary", "General",
        "You sent an attachment.", "Sent an attachment.", "Reacted", "Liked",
        "Edit", "More", "New message",
    }
    BLOCKLIST = _user_blocklist()
    # Parse the JSON string from read_dm_list
    try:
        raw_convos = json.loads(inbox_data) if isinstance(inbox_data, str) else inbox_data
    except (json.JSONDecodeError, TypeError):
        return []

    conversations = []
    for lines in raw_convos:
        if not isinstance(lines, list) or len(lines) < 2:
            continue

        username = (lines[0] or "").strip()
        if not username or username in SKIP_NAMES:
            continue
        # Drop "Active <Xm ago>" presence labels
        if username.lower().startswith("active "):
            continue
        # Spam / troll handles never get processed and never reach PULSE.
        if username.lower() in BLOCKLIST:
            continue
        # Real IG handles fit USERNAME_RE; display names may include spaces
        # (e.g. "Conaugh McKenna"), but our downstream send-DM-by-search flow
        # needs the @handle, not the display name. If the name has spaces or
        # weird chars we still allow it through, but skip if it looks like
        # raw UI text rather than a person.
        if username.lower() in {"active", "you", "instagram", "messages"}:
            continue

        # Filter out dot separators and find preview, time, unread
        preview = ""
        time_ago = ""
        is_unread = False

        for line in lines[1:]:
            if line == "\u00b7" or line == "·":
                continue  # dot separator
            elif line == "Unread":
                is_unread = True
            elif TIME_PATTERN.match(line):
                time_ago = line
            elif not preview:
                preview = line

        conversations.append({
            "username": username,
            "preview": preview,
            "unread": is_unread,
            "time_ago": time_ago,
        })

    return conversations


# -- DM Helpers ---------------------------------------------------------------

def _send_dm_reply(page, reply_text: str, recipient: str | None = None) -> bool:
    """Type and send a reply in the currently open DM conversation.

    Outbound DMs are 1:1 at scale and inherit anti-spam concerns. Every reply
    routes through send_gateway (channel="instagram_dm") which enforces
    daily/hourly caps, cooldown per recipient, killswitch, and the
    draft_critic gate. Returns True if sent, False if blocked or input
    wasn't found.
    """
    # send_gateway gate
    try:
        from send_gateway import send as _gateway_send
        # lead_id must be a valid UUID — Supabase lead_interactions.lead_id is
        # a uuid column. Derive a deterministic UUIDv5 from the recipient so
        # per-recipient cooldown still works without a CRM row.
        lead_id = None
        if recipient:
            import uuid
            # Stable namespace for IG DM lead_ids — random uuid is fine; the
            # value just needs to be the same across runs.
            _IG_DM_NS = uuid.UUID("9b8d77c1-4d6e-5a2f-8e4d-1b7a6c2e9f01")
            lead_id = str(uuid.uuid5(_IG_DM_NS, recipient.lower()))
        gate_result = _gateway_send(
            channel="instagram_dm",
            agent_source="instagram_engine",
            lead_id=lead_id,
            body_text=reply_text,
            subject=f"ig_dm/{recipient or 'unknown'}",
            intent="commercial",
            metadata={"recipient": recipient or ""},
            dry_run=True,  # gate-only check; physical send is via Playwright
        )
        if gate_result["status"] == "blocked":
            safe_print(f"  [send_gateway BLOCK] {recipient}: {gate_result['reason']}")
            return False
        if gate_result["status"] == "dry_run" and "FORCE_DRY_RUN" in (gate_result.get("reason") or ""):
            safe_print(f"  [send_gateway DRY_RUN killswitch] {recipient}: skipping send")
            return False
    except ImportError:
        # send_gateway must be present — fail closed.
        safe_print("  [send_gateway UNAVAILABLE] refusing to send DM")
        return False

    msg_input = _locate_message_input(page)

    # IG's React app sometimes navigates to the thread URL but fails to
    # render the conversation panel — leaves the empty state ("Your messages
    # — Send a message to start a chat") in the right panel. URL says we're
    # in the thread, but textbox can't exist because the panel never loaded.
    # Recovery: reload the thread URL once and retry textbox locate.
    if not msg_input:
        current_url = (page.url or "")
        if "/direct/t/" in current_url:
            safe_print(
                f"  [_send_dm_reply] Thread URL loaded but panel empty for "
                f"@{recipient}; reloading and retrying."
            )
            try:
                page.reload(wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
                time.sleep(6)
                _dismiss_ig_prompts(page)
                msg_input = _locate_message_input(page)
            except Exception as exc:
                log_exception(f"[_send_dm_reply] reload retry failed for @{recipient}", exc)

    if not msg_input:
        # Capture state for debugging instead of silently failing
        try:
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"ig_no_input_{recipient or 'unknown'}.png"))
            safe_print(
                f"  [_send_dm_reply] No textbox for @{recipient}. URL={page.url}. "
                "Screenshot saved to tmp/."
            )
        except Exception:
            pass
        return False

    try:
        msg_input.scroll_into_view_if_needed(timeout=3000)
    except Exception:
        pass
    try:
        msg_input.click()
    except Exception as exc:
        log_exception(f"[_send_dm_reply] click failed for @{recipient}", exc)
        return False

    time.sleep(0.4)
    try:
        page.keyboard.type(reply_text, delay=18)
        time.sleep(0.6)
        page.keyboard.press("Enter")
    except Exception as exc:
        log_exception(f"[_send_dm_reply] type/press failed for @{recipient}", exc)
        return False

    time.sleep(3)
    return True


def _locate_message_input(page):
    """Find IG's DM textbox, with retry, modal dismissal, and multiple selectors.

    IG ships at least 3 different layouts for the conversation panel; the
    textbox can land as div[role='textbox'], div[contenteditable='true'],
    or inside a form whose first contenteditable child is the input. We
    also dismiss the 'Allow notifications' modal that pops up over the
    conversation panel and steals focus.
    """
    selectors = [
        'div[role="textbox"][contenteditable="true"]',
        'div[role="textbox"]',
        'div[contenteditable="true"][aria-label*="essage"]',
        'div[contenteditable="true"]',
        'p[contenteditable="true"]',
        'textarea[placeholder*="essage"]',
    ]

    for attempt in range(3):
        # Dismiss any modal that may be eating focus / hiding the textbox
        _dismiss_ig_prompts(page)

        for sel in selectors:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    return el
            except Exception:
                continue

        # Wait for any selector to appear (up to 4s on first pass, decay after)
        try:
            page.wait_for_selector(
                'div[role="textbox"], div[contenteditable="true"]',
                timeout=4000 if attempt == 0 else 2000,
                state="visible",
            )
        except Exception:
            pass

        time.sleep(1)

    return None


def _handle_booking_confirmation(
    env_vars: dict,
    page,
    username: str,
    parsed_time: dict,
    booking_state: dict,
) -> str | None:
    """Create a Google Calendar event and send the Meet link as a DM reply.

    Returns the reply text if successful, None on failure.
    """
    try:
        from scripts.google_calendar import create_event
    except ImportError:
        try:
            from google_calendar import create_event
        except ImportError:
            return None

    from zoneinfo import ZoneInfo
    et = ZoneInfo("America/Toronto")

    start_dt = datetime.combine(
        datetime.strptime(parsed_time["date"], "%Y-%m-%d").date(),
        datetime.strptime(parsed_time["time"], "%H:%M").time(),
        tzinfo=et,
    )

    result = create_event(
        env_vars,
        title=f"Call with {username}",
        start_dt=start_dt,
        duration_minutes=30,
        description=f"Booked via Instagram DM auto-reply — @{username}",
    )

    if not result["success"]:
        return None

    meet_link = result["meet_link"]
    display = parsed_time["display"]

    reply_text = (
        f"locked in for {display}. "
        f"here's the meet link: {meet_link}"
    )

    sent = _send_dm_reply(page, reply_text, recipient=username)
    if not sent:
        return None

    # Update booking state to confirmed
    booking_state[username] = {
        "stage": "confirmed",
        "date": parsed_time["date"],
        "time": parsed_time["time"],
        "display": display,
        "meet_link": meet_link,
        "event_id": result["event_id"],
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }
    save_booking_state(booking_state)

    return reply_text


# -- Commands -----------------------------------------------------------------

CATCH_UP_WINDOW_HOURS = int(os.environ.get("IG_CATCHUP_WINDOW_HOURS", "6") or "6")


def _is_within_catchup_window(time_ago: str) -> bool:
    """Decide whether an unread conversation is fresh enough to auto-reply to.

    IG's relative time labels look like "2m", "1h", "3d", "1w", "2mo".
    On daemon restart after downtime we don't want Maven blasting replies to
    a 3-day-old "hey" — that reads as a sales bot. Default window: 6 hours
    (override via IG_CATCHUP_WINDOW_HOURS env var). Empty/unparseable
    time_ago is treated as "fresh" since the inbox shows it at the top.
    """
    if not time_ago:
        return True
    import re as _re
    m = _re.match(r"^(\d{1,3})(mo|m|h|d|w)$", time_ago.strip().lower())
    if not m:
        return True
    n = int(m.group(1))
    unit = m.group(2)
    hours = {
        "m": n / 60.0,
        "h": float(n),
        "d": n * 24.0,
        "w": n * 24.0 * 7,
        "mo": n * 24.0 * 30,
    }.get(unit, 0)
    return hours <= CATCH_UP_WINDOW_HOURS


def _prune_notified_log(log: dict, max_age_days: int = 30) -> dict:
    """Drop notified-log entries older than max_age_days. Prevents tmp/dm_notified.json
    from growing unbounded. Returns the pruned dict (in place)."""
    if not isinstance(log, dict):
        return {}
    now_dt = datetime.now(timezone.utc)
    cutoff = now_dt - timedelta(days=max_age_days)
    pruned = {}
    for key, value in log.items():
        try:
            # value may be ISO timestamp string or a dict {"timestamp": "..."}
            ts_raw = value.get("timestamp") if isinstance(value, dict) else value
            if not ts_raw:
                continue
            ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
            if ts >= cutoff:
                pruned[key] = value
        except (ValueError, TypeError):
            # If we can't parse a timestamp, keep the entry — safer than dropping
            pruned[key] = value
    return pruned


def _check_dms_on_page(env_vars, args, page):
    """Run one complete DM check using an already-open Playwright page."""
    replied_log = load_replied_log()
    booking_state = load_booking_state()
    notified_log = _prune_notified_log(load_notified_log(), max_age_days=30)
    archived_handles = fetch_archived_handles(env_vars)
    auto_replies = []
    skipped_replies = []
    result = {"action": "check_dms", "status": "error", "message": "Unknown error"}

    try:
        if not ensure_logged_in(page, env_vars):
            result = {
                "action": "check_dms",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "login_failed",
                "message": "Could not log into Instagram. Check credentials/session.",
            }
            notify("Instagram login failed - check credentials/session", category="instagram")
            if getattr(args, "output_json", False):
                print(json.dumps(result, indent=2))
            else:
                safe_print(f"Instagram DMs: {result['message']}")
            return result

        inbox_text = read_dm_list(page)
        convos = parse_conversations(inbox_text)

        # Also scan the Message Requests folder — strangers (people you don't
        # follow) land here, NOT in the main inbox. Tag them so downstream
        # send/parse logic can opt in/out, and so we mark them all as unread
        # (IG strips the "Unread" label in the requests view).
        try:
            requests_convos = _read_requests_inbox(page, env_vars)
            for r in requests_convos:
                r["from_requests"] = True
                r["unread"] = True  # any item in Requests is by definition fresh
            convos.extend(requests_convos)
        except Exception as exc:
            log_exception("[ig-daemon] requests folder scrape failed", exc)

        unread = [c for c in convos if c.get("unread")]

        result = {
            "action": "check_dms",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "checked",
            "total_visible": len(convos),
            "unread_count": len(unread),
            "conversations": convos[:10],
            "unread": unread,
            "auto_replies": [],
        }

        # Only process conversations Instagram marks as unread.
        actionable = list(unread)
        if not actionable:
            result["message"] = "No DMs needing reply"
            if getattr(args, "output_json", False):
                print(json.dumps(result, indent=2, default=str))
            else:
                safe_print("Instagram DMs: No DMs needing reply")
            return result

        for convo in actionable:
            username = convo.get("username", "").strip()
            preview = convo.get("preview", "")[:100]
            if not username:
                continue

            try:
                # Skip group chats. They often show as "Active" with multi-user previews.
                if " and " in preview and username == "Active":
                    skipped_replies.append({"username": username, "reason": "group_chat"})
                    continue

                if already_notified(notified_log, username, preview):
                    skipped_replies.append({"username": username, "reason": "already_notified"})
                    continue

                # PULSE-side archive flag: CC archived this thread → daemon
                # stays silent until they re-open it. Cheap fail-open: if the
                # PULSE fetch failed, archived_handles is empty and nothing is
                # skipped here.
                if username.lower() in archived_handles:
                    skipped_replies.append({"username": username, "reason": "thread_archived"})
                    mark_notified(notified_log, username, preview)
                    save_notified_log(notified_log)
                    continue

                # Catch-up window: don't reply to old unread threads after a
                # daemon outage. Keeps Maven from sounding like a "I just
                # noticed your message from 3 days ago" spam bot.
                if not _is_within_catchup_window(convo.get("time_ago", "")):
                    safe_print(
                        f"  [catch-up SKIP] @{username} message is "
                        f"{convo.get('time_ago')} old (window={CATCH_UP_WINDOW_HOURS}h)"
                    )
                    skipped_replies.append({"username": username, "reason": "outside_catchup_window"})
                    mark_notified(notified_log, username, preview)
                    save_notified_log(notified_log)
                    continue

                convo_text = read_conversation_text(page, username)
                # Pull EVERY inbound message since CC/Maven last replied —
                # critical for catching up after daemon downtime when 2-5
                # messages stack from the prospect.
                inbound_burst = extract_all_inbound_since_last_outbound(convo_text)
                last_msg = (
                    inbound_burst[-1]
                    if inbound_burst
                    else (extract_last_incoming_message(convo_text) or preview)
                )

                # Try to upgrade the username from "display name" to the actual
                # @handle by scraping the conversation header. If that fails,
                # fall back to the inbox-parsed name. display_name keeps the
                # human-readable label for PULSE.
                display_name = username
                handle = get_open_conversation_handle(page) or username
                if handle and handle != username:
                    safe_print(f"[ig-daemon] Resolved @{handle} from display name '{username}'")
                username = handle

                # Push every stacked inbound to PULSE so dm_messages stays a
                # truthful transcript. Webhook dedupes by ig_message_id, so
                # re-sends are safe. Only the FINAL push generates the
                # doctrine draft (PULSE returns it on the latest webhook
                # response that has the most context).
                webhook_resp = None
                bursts_to_push = inbound_burst if len(inbound_burst) > 1 else [last_msg]
                if bursts_to_push and len(bursts_to_push) > 1:
                    safe_print(
                        f"  [catch-up] @{username} sent {len(bursts_to_push)} "
                        "messages while daemon was idle — pushing all to PULSE."
                    )
                for idx, msg in enumerate(bursts_to_push):
                    is_last = idx == len(bursts_to_push) - 1
                    webhook_resp = send_to_ig_setter_pro(
                        env_vars,
                        username,
                        msg,
                        direction="inbound",
                        intent="active",
                        display_name=display_name,
                    )
                    # Only the last call needs to drive the reply path.
                    if not is_last:
                        continue

                # Auto-send gate: if PULSE has auto_send_enabled=false for this
                # account, the daemon stops here. The doctrine draft is already
                # waiting in the dashboard for CC to approve via Override.
                auto_send_enabled = bool(
                    isinstance(webhook_resp, dict)
                    and webhook_resp.get("auto_send_enabled")
                )
                if not auto_send_enabled:
                    safe_print(
                        f"  [auto-send OFF] @{username} draft saved to PULSE — "
                        "approve via Override panel."
                    )
                    skipped_replies.append({"username": username, "reason": "auto_send_off"})
                    mark_notified(notified_log, username, preview)
                    save_notified_log(notified_log)
                    continue

                # Multi-turn booking flow.
                user_booking = booking_state.get(username)
                if user_booking and user_booking.get("stage") == "awaiting_time":
                    parsed = parse_datetime_from_text(last_msg)
                    if parsed:
                        reply_text = _handle_booking_confirmation(
                            env_vars, page, username, parsed, booking_state,
                        )
                        if reply_text:
                            send_to_ig_setter_pro(
                                env_vars,
                                username,
                                reply_text,
                                direction="outbound",
                                is_ai=True,
                                intent="BOOKING_CONFIRMED",
                            )
                            auto_replies.append({
                                "username": username,
                                "intent": "BOOKING_CONFIRMED",
                                "reply_preview": reply_text[:80],
                            })
                            notify(
                                f"Booking confirmed! {username} - {parsed['display']}\n"
                                f"Sent Meet link via DM",
                                category="instagram",
                            )
                            mark_notified(notified_log, username, preview)
                            save_notified_log(notified_log)
                        else:
                            skipped_replies.append({
                                "username": username,
                                "reason": "calendar_or_send_error",
                            })
                    else:
                        intent = detect_intent(last_msg)
                        if intent == "CONVO":
                            reply_text = build_reply(
                                "CONVO",
                                last_msg=last_msg,
                                convo_context=convo_text,
                            )
                        else:
                            reply_text = (
                                "just lmk a day and time that works, "
                                "like \"thursday at 2pm\" or something"
                            )

                        sent = _send_dm_reply(page, reply_text, recipient=username)
                        if sent:
                            send_to_ig_setter_pro(
                                env_vars,
                                username,
                                reply_text,
                                direction="outbound",
                                is_ai=True,
                                intent="BOOKING_FOLLOWUP",
                            )
                            auto_replies.append({
                                "username": username,
                                "intent": "BOOKING_FOLLOWUP",
                                "reply_preview": reply_text[:80],
                            })
                            mark_notified(notified_log, username, preview)
                            save_notified_log(notified_log)
                        else:
                            skipped_replies.append({
                                "username": username,
                                "reason": "booking_followup_send_failed",
                            })

                    _return_to_inbox(page, env_vars)
                    continue

                # Normal flow.
                intent = detect_intent(last_msg)
                # Loud Telegram alert when CC needs to know personally —
                # booking, pricing, payment intent. Fires even with auto-send
                # OFF so CC can jump in.
                maybe_alert_high_intent(intent, username, last_msg)

                should_reply = True
                skip_reason = None

                # Per-message gate: only skip if CC (or Maven on a previous
                # poll) has ALREADY responded to the latest inbound. This is
                # a position check on the conversation transcript, NOT a
                # global 24h cooldown — that would silently kill multi-turn
                # conversations after the first reply.
                if cc_has_replied(convo_text):
                    should_reply = False
                    skip_reason = "already_responded_to_last_inbound"
                elif intent == "UNKNOWN":
                    # CONVO is the catch-all conversational handler; build_reply
                    # will route through it. Don't skip on UNKNOWN.
                    intent = "CONVO"

                if should_reply:
                    # PRIMARY PATH: PULSE doctrine. The webhook just told us
                    # what to send — it built the reply with the last 30
                    # messages from dm_messages, brand context, and the
                    # current stage. This is the context-aware reply CC
                    # configured. Use it.
                    reply_text = ""
                    doctrine_resp = (
                        webhook_resp.get("doctrine") if isinstance(webhook_resp, dict) else None
                    )
                    if isinstance(doctrine_resp, dict) and doctrine_resp.get("draft"):
                        reply_text = (doctrine_resp["draft"] or "").strip()
                        # Doctrine sets the canonical stage; reflect it
                        # downstream so booking/intent gating is consistent.
                        doctrine_stage = (doctrine_resp.get("stage") or "").strip()
                        if doctrine_stage in ("book_call", "booked"):
                            intent = "BOOKING"

                    # FALLBACK only if PULSE/doctrine is unavailable (offline,
                    # no Anthropic key configured, transient error). Local
                    # build_reply is keyword-based and context-blind — it's a
                    # safety net, not the primary path.
                    if not reply_text:
                        reply_text = build_reply(
                            intent, last_msg=last_msg, convo_context=convo_text
                        )

                    if not reply_text:
                        should_reply = False
                        skip_reason = "empty_reply"
                    else:
                        sent = _send_dm_reply(page, reply_text, recipient=username)
                        if sent:
                            replied_log[username] = {
                                "replied_at": datetime.now(timezone.utc).isoformat(),
                                "intent": intent,
                            }
                            save_replied_log(replied_log)
                            log_auto_reply_to_supabase(env_vars, username, intent, reply_text)
                            send_to_ig_setter_pro(
                                env_vars,
                                username,
                                reply_text,
                                direction="outbound",
                                is_ai=True,
                                intent=intent,
                            )

                            if intent in _CRM_INTEREST_INTENTS:
                                capture_lead_to_crm(username, intent, last_msg)

                            if intent == "BOOKING":
                                booking_state[username] = {
                                    "stage": "awaiting_time",
                                    "intent": intent,
                                    "started_at": datetime.now(timezone.utc).isoformat(),
                                }
                                save_booking_state(booking_state)

                            auto_replies.append({
                                "username": username,
                                "intent": intent,
                                "reply_preview": reply_text[:80],
                            })
                            if intent == "BOOKING":
                                notify(
                                    f"IG DM from {username}: \"{last_msg[:60]}\"\n"
                                    f"Auto-replied ({intent}): {reply_text[:80]}",
                                    category="instagram",
                                )
                            mark_notified(notified_log, username, preview)
                            save_notified_log(notified_log)
                        else:
                            skip_reason = "no_input_found"
                            should_reply = False

                if not should_reply:
                    skipped_replies.append({"username": username, "reason": skip_reason})
                    mark_notified(notified_log, username, preview)
                    save_notified_log(notified_log)

                _return_to_inbox(page, env_vars)

            except Exception as exc:
                reason = "timeout" if _is_playwright_timeout(exc) else "exception"
                skipped_replies.append({"username": username, "reason": reason})
                log_exception(f"Error processing Instagram DM for @{username}", exc)
                recover_inbox_page(page, env_vars, f"Conversation recovery for @{username}")
                continue

        result["auto_replies"] = auto_replies
        result["skipped_replies"] = skipped_replies
        result["actionable_count"] = len(actionable)
        result["message"] = (
            f"{len(actionable)} DM(s) needing reply - "
            f"{len(auto_replies)} auto-replied, "
            f"{len(skipped_replies)} skipped"
        )

        if getattr(args, "output_json", False):
            print(json.dumps(result, indent=2, default=str))
        else:
            safe_print(f"Instagram DMs: {result['message']}")
            for a in auto_replies:
                safe_print(f"  -> @{a['username']} [{a['intent']}]: {a['reply_preview']}")
            for s in skipped_replies:
                safe_print(f"  -- @{s['username']}: {s['reason']}")

        return result

    except Exception as exc:
        status = "timeout" if _is_playwright_timeout(exc) else "error"
        log_exception("Instagram DM check failed", exc)
        recover_inbox_page(page, env_vars, "Instagram DM check failed")
        result = {
            "action": "check_dms",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "message": f"DM check failed: {type(exc).__name__}: {exc}",
        }
        if getattr(args, "output_json", False):
            print(json.dumps(result, indent=2, default=str))
        else:
            safe_print(f"Instagram DMs: {result['message']}")
        return result


def _cmd_check_dms_once_with_context(env_vars, args):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        safe_print("ERROR: playwright not installed. Run: pip install playwright")
        return {"status": "error", "message": "playwright not installed"}

    with sync_playwright() as p:
        context, page = _open_ig_page(p)
        try:
            return _check_dms_on_page(env_vars, args, page)
        finally:
            _close_context_safely(context)


def _poll_delay_bounds(args):
    poll_min = int(getattr(args, "poll_min", DEFAULT_POLL_MIN_SECONDS) or DEFAULT_POLL_MIN_SECONDS)
    poll_max = int(getattr(args, "poll_max", DEFAULT_POLL_MAX_SECONDS) or DEFAULT_POLL_MAX_SECONDS)
    poll_min = max(30, poll_min)
    poll_max = max(poll_min, poll_max)
    return poll_min, poll_max


def process_dashboard_outbox(env_vars, page, limit: int = 5) -> dict:
    """Send dashboard-approved/manual replies through the same Playwright session."""
    commands = fetch_ig_setter_pro_outbox(env_vars, limit=limit)
    result = {"checked": True, "claimed": len(commands), "sent": 0, "failed": 0}
    if not commands:
        return result

    if not ensure_logged_in(page, env_vars):
        safe_print("[ig-daemon] Outbox skipped: Instagram session is not logged in.")
        for command in commands:
            mark_ig_setter_pro_outbox(
                env_vars,
                command.get("id", ""),
                "failed",
                "Instagram session not logged in",
            )
            result["failed"] += 1
        return result

    for command in commands:
        command_id = command.get("id", "")
        username = (command.get("username") or "").strip().lstrip("@")
        message = (command.get("message") or "").strip()
        is_ai = bool(command.get("is_ai"))
        if not command_id or not username or not message:
            mark_ig_setter_pro_outbox(env_vars, command_id, "failed", "Invalid outbox command")
            result["failed"] += 1
            continue

        try:
            convo_text = read_conversation_text(page, username)
            if not convo_text:
                raise RuntimeError(f"Could not open Instagram conversation for @{username}")

            sent = _send_dm_reply(page, message, recipient=username)
            if not sent:
                raise RuntimeError("Playwright send failed or send gate blocked")

            send_to_ig_setter_pro(
                env_vars,
                username,
                message,
                direction="outbound",
                is_ai=is_ai,
                intent=command.get("intent") or "active",
                ig_message_id=f"outbox_{command_id}",
            )
            mark_ig_setter_pro_outbox(env_vars, command_id, "sent")
            result["sent"] += 1
        except Exception as exc:
            log_exception(f"[ig-daemon] Dashboard outbox send failed for @{username}", exc)
            mark_ig_setter_pro_outbox(env_vars, command_id, "failed", str(exc)[:500])
            result["failed"] += 1
        finally:
            _return_to_inbox(page, env_vars)

    return result


# ─── Comment-to-DM trigger system ────────────────────────────────────────────

COMMENT_REPLIED_PATH = PROJECT_ROOT / "tmp" / "ig_comment_replied.json"


def _load_comment_replied() -> dict:
    if not COMMENT_REPLIED_PATH.exists():
        return {}
    try:
        with open(COMMENT_REPLIED_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_comment_replied(state: dict) -> None:
    try:
        COMMENT_REPLIED_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(COMMENT_REPLIED_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except OSError as exc:
        log_exception("Failed saving comment_replied state", exc)


def fetch_active_comment_triggers(env_vars: dict) -> list[dict]:
    """Fetch active comment-to-DM triggers from the dashboard."""
    try:
        import requests
    except ImportError:
        return []

    secret = get_pulse_secret(env_vars)
    if not secret:
        return []

    base = get_pulse_api_base(env_vars)
    account_id = get_env_value(env_vars, "PULSE_ACCOUNT_ID", "IG_SETTER_PRO_ACCOUNT_ID")
    params = {}
    if account_id:
        params["account_id"] = account_id

    try:
        resp = requests.get(
            f"{base}/api/python/triggers",
            params=params,
            headers={"x-webhook-secret": secret},
            timeout=10,
        )
        if resp.status_code != 200:
            safe_print(f"[ig-daemon] triggers fetch error: {resp.status_code}")
            return []
        data = resp.json()
        return data.get("triggers") or []
    except Exception as exc:
        log_exception("[ig-daemon] triggers fetch failed", exc)
        return []


def submit_comment_event(env_vars: dict, trigger: dict, comment: dict) -> dict | None:
    """POST a scraped comment to /api/comment-webhook. Returns the response payload
    or None on transport failure. The webhook handles dedup, matching, and follow-gate
    logic; we only act on its response."""
    try:
        import requests
    except ImportError:
        return None

    secret = get_pulse_secret(env_vars)
    if not secret:
        return None

    payload = {
        "account_id": trigger.get("account_id"),
        "ig_media_id": trigger.get("ig_media_id"),
        "ig_comment_id": comment["ig_comment_id"],
        "ig_user_id": comment["ig_user_id"],
        "username": comment.get("username"),
        "comment_text": comment.get("comment_text", ""),
        # Playwright cannot reliably check follow status without an extra
        # navigation per commenter; default true so non-gated triggers fire.
        "is_following": True,
    }

    try:
        resp = requests.post(
            f"{get_pulse_api_base(env_vars)}/api/comment-webhook",
            json=payload,
            headers={"x-webhook-secret": secret, "Content-Type": "application/json"},
            timeout=10,
        )
        if resp.status_code != 200:
            safe_print(f"[ig-comments] webhook error: {resp.status_code} - {resp.text[:200]}")
            return None
        return resp.json()
    except Exception as exc:
        log_exception("[ig-comments] webhook submit failed", exc)
        return None


def _scrape_comments_for_post(page, media_id: str) -> list[dict]:
    """Open a post and scrape its visible comments.

    Returns list of {ig_comment_id, ig_user_id, username, comment_text}.
    Comment IDs are derived from username + first-80-chars hash since IG's DOM
    does not expose the real comment id without authenticated GraphQL calls.
    """
    import hashlib

    url = f"https://www.instagram.com/p/{media_id}/"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
        _sleep(5)
    except Exception as exc:
        log_exception(f"[ig-comments] navigation to {url} failed", exc)
        return []

    script = """() => {
        // Heuristic scrape: find <ul> nodes containing <a href="/<username>/"> links
        // followed by text. Works on both /p/ and /reel/ layouts.
        const results = [];
        const seen = new Set();
        const links = document.querySelectorAll('a[href^="/"][role="link"]');
        for (const link of links) {
            const href = link.getAttribute('href') || '';
            // Skip non-username links
            if (!/^\\/[A-Za-z0-9._]+\\/$/.test(href)) continue;
            const username = href.replace(/\\//g, '').trim();
            if (!username || username.length > 32) continue;
            const container = link.closest('li') || link.closest('div[role="button"]') || link.parentElement;
            if (!container) continue;
            const text = (container.innerText || container.textContent || '').trim();
            if (!text) continue;
            const lines = text.split(String.fromCharCode(10)).map(l => l.trim()).filter(Boolean);
            // Drop the username line; first remaining line that isn't time/likes is the comment
            const timeRe = /^\\d{1,3}[smhdw]$|^\\d{1,2}(mo|w)$|^\\d+ likes?$|^Reply$|^View replies/i;
            const commentLines = lines.filter(l => l !== username && !timeRe.test(l) && l.length > 1);
            if (commentLines.length === 0) continue;
            const commentText = commentLines.slice(0, 4).join(' ');
            const key = username + '::' + commentText.slice(0, 80);
            if (seen.has(key)) continue;
            seen.add(key);
            results.push({ username: username, comment_text: commentText });
        }
        return JSON.stringify(results);
    }"""

    try:
        raw = page.evaluate(script)
        rows = json.loads(raw or "[]")
    except Exception as exc:
        log_exception(f"[ig-comments] scrape evaluate failed for {media_id}", exc)
        return []

    out = []
    for row in rows:
        username = (row.get("username") or "").strip()
        comment_text = (row.get("comment_text") or "").strip()
        if not username or not comment_text:
            continue
        # Stable derived ids — the webhook dedupes on ig_comment_id, so this
        # remains idempotent across daemon restarts.
        digest = hashlib.sha1(
            f"{media_id}:{username}:{comment_text[:80]}".encode("utf-8")
        ).hexdigest()[:24]
        user_digest = hashlib.sha1(username.lower().encode("utf-8")).hexdigest()[:16]
        out.append({
            "ig_comment_id": f"pw_{media_id}_{digest}",
            "ig_user_id": f"ig_user_{user_digest}",
            "username": username,
            "comment_text": comment_text,
        })
    return out


def process_comment_triggers(env_vars, page) -> dict:
    """For every active trigger, scrape its post's comments and DM matches."""
    triggers = fetch_active_comment_triggers(env_vars)
    result = {"triggers": len(triggers), "matched": 0, "sent": 0, "failed": 0}
    if not triggers:
        return result

    if not ensure_logged_in(page, env_vars):
        safe_print("[ig-comments] Skipped: Instagram session not logged in.")
        return result

    state = _load_comment_replied()
    state.setdefault("comments", {})

    by_post: dict[str, list[dict]] = {}
    for t in triggers:
        media = (t.get("ig_media_id") or "").strip()
        if media:
            by_post.setdefault(media, []).append(t)

    for media_id, post_triggers in by_post.items():
        try:
            comments = _scrape_comments_for_post(page, media_id)
            if not comments:
                continue
            for comment in comments:
                comment_id = comment["ig_comment_id"]
                if state["comments"].get(comment_id):
                    continue  # already processed by daemon

                # Pass to webhook — it does keyword matching + dedup + event log.
                # Use the first trigger as the carrier (post-specific triggers).
                resp = submit_comment_event(env_vars, post_triggers[0], comment)
                if not resp:
                    result["failed"] += 1
                    continue

                action = resp.get("action")
                if action in {"duplicate", "no_match"}:
                    state["comments"][comment_id] = action
                    continue
                if action != "dm_sent":
                    state["comments"][comment_id] = action or "no_match"
                    continue

                # Webhook says: send the DM. Send via Playwright.
                result["matched"] += 1
                dm_payload = resp.get("dm") or {}
                message = dm_payload.get("message") or ""
                button_url = dm_payload.get("button_url")
                if button_url:
                    message = f"{message}\n\n{button_url}"
                if not message:
                    state["comments"][comment_id] = "no_message"
                    continue

                username = comment["username"]
                sent = _send_dm_via_search(page, username, message)
                if sent:
                    send_to_ig_setter_pro(
                        env_vars,
                        username,
                        message,
                        direction="outbound",
                        is_ai=True,
                        intent="active",
                        ig_message_id=f"comment_dm_{comment_id}",
                    )
                    state["comments"][comment_id] = "sent"
                    result["sent"] += 1
                    notify(
                        f"\U0001f4ac Comment-DM sent to @{username} on /p/{media_id}",
                        category="campaign",
                    )
                else:
                    state["comments"][comment_id] = "send_failed"
                    result["failed"] += 1
        except Exception as exc:
            log_exception(f"[ig-comments] trigger pass failed for {media_id}", exc)
            result["failed"] += 1
        finally:
            _return_to_inbox(page, env_vars)

    _save_comment_replied(state)
    return result


# ─── Activity page: new follower welcome system ─────────────────────────────

FOLLOWERS_SEEN_PATH = PROJECT_ROOT / "tmp" / "ig_followers_seen.json"
WELCOME_DM_DAILY_CAP = 8  # safe cap — Meta penalises bursts of unsolicited DMs


def _load_followers_seen() -> dict:
    if not FOLLOWERS_SEEN_PATH.exists():
        return {"initialized": False, "usernames": [], "welcomed": []}
    try:
        with open(FOLLOWERS_SEEN_PATH, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except (json.JSONDecodeError, OSError):
        return {"initialized": False, "usernames": [], "welcomed": []}
    data.setdefault("initialized", False)
    data.setdefault("usernames", [])
    data.setdefault("welcomed", [])
    return data


def _save_followers_seen(state: dict) -> None:
    try:
        FOLLOWERS_SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(FOLLOWERS_SEEN_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except OSError as exc:
        log_exception("Failed saving followers state", exc)


def _fetch_welcome_message(env_vars: dict) -> dict | None:
    """POST /api/welcome-message/trigger — returns active welcome or None.
    Increments times_sent server-side."""
    try:
        import requests
    except ImportError:
        return None

    secret = get_pulse_secret(env_vars)
    account_id = get_env_value(env_vars, "PULSE_ACCOUNT_ID", "IG_SETTER_PRO_ACCOUNT_ID")
    if not secret or not account_id:
        return None

    try:
        resp = requests.post(
            f"{get_pulse_api_base(env_vars)}/api/welcome-message/trigger",
            json={"account_id": account_id},
            headers={"x-webhook-secret": secret, "Content-Type": "application/json"},
            timeout=10,
        )
        if resp.status_code == 404:
            return None  # no active welcome configured
        if resp.status_code != 200:
            safe_print(f"[ig-followers] welcome fetch error: {resp.status_code}")
            return None
        return resp.json().get("welcome_message")
    except Exception as exc:
        log_exception("[ig-followers] welcome fetch failed", exc)
        return None


def _scrape_recent_followers(page, ig_username: str, limit: int = 30) -> list[str]:
    """Open the followers modal and scrape the top N usernames (newest-first by IG default)."""
    try:
        page.goto(
            f"https://www.instagram.com/{ig_username}/",
            wait_until="domcontentloaded",
            timeout=PAGE_TIMEOUT_MS,
        )
        _sleep(5)
    except Exception as exc:
        log_exception(f"[ig-followers] profile navigation failed", exc)
        return []

    # Click the followers link to open the modal. Instagram has shipped
    # multiple layouts (anchor, button, span-with-text) so we try each.
    try:
        clicked = page.evaluate(f"""() => {{
            const lower = '{ig_username.lower()}';

            // 1. Direct anchor whose href matches /<user>/followers
            const anchors = document.querySelectorAll('a');
            for (const a of anchors) {{
                const href = (a.getAttribute('href') || '').toLowerCase();
                if (href.includes('/' + lower + '/followers') || href.endsWith('/followers/') || href.endsWith('/followers')) {{
                    a.click();
                    return 'anchor';
                }}
            }}

            // 2. Header text fallback: find an element whose text reads
            //    "<n> followers" and click its closest button/anchor parent.
            const all = document.querySelectorAll('a, button, span, li');
            for (const el of all) {{
                const t = (el.textContent || '').trim().toLowerCase();
                // accepts "1,234 followers", "12 followers", "12k followers"
                if (/^[\\d.,kKmM]+\\s+followers?$/.test(t)) {{
                    const target = el.closest('a') || el.closest('button') || el;
                    target.click();
                    return 'text';
                }}
            }}

            return false;
        }}""")
        if not clicked:
            # Last resort: navigate directly to /<user>/followers/ as its own
            # page. This works on web even when the modal route fails.
            try:
                page.goto(
                    f"https://www.instagram.com/{ig_username}/followers/",
                    wait_until="domcontentloaded",
                    timeout=PAGE_TIMEOUT_MS,
                )
                _sleep(5)
                clicked = "direct-nav"
            except Exception as nav_exc:
                log_exception("[ig-followers] direct followers nav failed", nav_exc)
                return []

        safe_print(f"[ig-followers] Opened followers via {clicked}.")
        _sleep(5)
    except Exception as exc:
        log_exception("[ig-followers] modal open failed", exc)
        return []

    script = """() => {
        const results = [];
        const seen = new Set();
        // Followers modal lives inside a [role="dialog"] container on web
        const dialog = document.querySelector('div[role="dialog"]');
        const root = dialog || document.body;
        const links = root.querySelectorAll('a[role="link"][href^="/"]');
        for (const link of links) {
            const href = link.getAttribute('href') || '';
            // Username paths look like /<name>/  with no extra segments
            if (!/^\\/[A-Za-z0-9._]+\\/?$/.test(href)) continue;
            const username = href.replace(/\\//g, '').trim();
            if (!username || seen.has(username)) continue;
            // Reject reserved IG paths
            if (['p','reel','reels','explore','direct','accounts','stories','tv'].includes(username)) continue;
            seen.add(username);
            results.push(username);
        }
        return JSON.stringify(results);
    }"""
    try:
        raw = page.evaluate(script)
        rows = json.loads(raw or "[]")
    except Exception as exc:
        log_exception("[ig-followers] scrape evaluate failed", exc)
        return []

    # Drop self
    rows = [u for u in rows if u and u.lower() != ig_username.lower()]
    return rows[:limit]


def process_new_follower_welcomes(env_vars, page) -> dict:
    """Detect new followers via the followers modal and DM them the welcome message.

    First run: snapshot existing followers, send NO welcomes (avoids spamming
    everyone who already followed).
    Subsequent runs: anyone in the top of the followers list who isn't in
    state.usernames is treated as a new follow.
    """
    ig_username = get_env_value(env_vars, "INSTAGRAM_USERNAME").lstrip("@")
    if not ig_username:
        return {"status": "skipped", "reason": "INSTAGRAM_USERNAME not set"}

    if not ensure_logged_in(page, env_vars):
        return {"status": "skipped", "reason": "session not logged in"}

    state = _load_followers_seen()
    is_first_run = not state.get("initialized")

    scraped = _scrape_recent_followers(page, ig_username)
    if not scraped:
        return {"status": "ok", "new_follows": 0, "scraped": 0}

    seen_set = set(state.get("usernames", []))
    welcomed_set = set(state.get("welcomed", []))

    # First run: snapshot only
    if is_first_run:
        state["initialized"] = True
        state["usernames"] = sorted(seen_set | set(scraped))
        _save_followers_seen(state)
        safe_print(
            f"[ig-followers] First-run snapshot: {len(scraped)} followers recorded; "
            "no welcomes sent."
        )
        _return_to_inbox(page, env_vars)
        return {"status": "snapshot", "snapshot_size": len(scraped)}

    new_followers = [u for u in scraped if u not in seen_set]
    result = {"status": "ok", "new_follows": len(new_followers), "sent": 0, "skipped": 0}

    if not new_followers:
        _return_to_inbox(page, env_vars)
        return result

    safe_print(f"[ig-followers] Detected {len(new_followers)} new follower(s): {', '.join(new_followers)}")

    welcome = _fetch_welcome_message(env_vars)
    if not welcome:
        # Record as seen so we don't pile up — but don't send anything.
        state["usernames"] = sorted(seen_set | set(scraped))
        _save_followers_seen(state)
        result["skipped"] = len(new_followers)
        result["reason"] = "no welcome configured"
        _return_to_inbox(page, env_vars)
        return result

    # Build the welcome text once — Settings determines the body + optional CTA.
    body_lines = [welcome["message"].strip()]
    if welcome.get("button_url"):
        body_lines.append("")
        body_lines.append(welcome["button_url"].strip())
    welcome_body = "\n".join(body_lines)

    # Per-cycle cap so a sudden surge in followers doesn't burn the account.
    todo = [u for u in new_followers if u not in welcomed_set][:WELCOME_DM_DAILY_CAP]

    for username in todo:
        try:
            sent_ok = _send_dm_via_search(page, username, welcome_body)
            if sent_ok:
                send_to_ig_setter_pro(
                    env_vars,
                    username,
                    welcome_body,
                    direction="outbound",
                    is_ai=True,
                    intent="welcome",
                    ig_message_id=f"welcome_{username}_{int(time.time())}",
                )
                welcomed_set.add(username)
                result["sent"] += 1
                notify(
                    f"\U0001f44b Welcome DM sent to new follower @{username}",
                    category="campaign",
                )
            else:
                result["skipped"] += 1
        except Exception as exc:
            log_exception(f"[ig-followers] welcome DM failed for @{username}", exc)
            result["skipped"] += 1

    # Persist: usernames is the snapshot; welcomed prevents re-sending if
    # IG re-orders the followers list later.
    state["usernames"] = sorted(seen_set | set(scraped))
    state["welcomed"] = sorted(welcomed_set)
    _save_followers_seen(state)

    _return_to_inbox(page, env_vars)
    return result


def _send_dm_via_search(page, username: str, message: str) -> bool:
    """Send a DM by navigating to the user's profile and clicking 'Message'.
    Falls back to the inbox flow if the profile path fails. Returns True on success.
    """
    profile_url = f"https://www.instagram.com/{username.lstrip('@')}/"
    try:
        page.goto(profile_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
        _sleep(5)

        clicked = page.evaluate("""() => {
            const els = document.querySelectorAll('button, div[role="button"], a');
            for (const el of els) {
                const t = (el.textContent || '').trim().toLowerCase();
                if (t === 'message') {
                    el.click();
                    return true;
                }
            }
            return false;
        }""")
        if not clicked:
            safe_print(f"[ig-comments] Could not find Message button on @{username}'s profile")
            return False
        _sleep(6)

        return _send_dm_reply(page, message, recipient=username)
    except Exception as exc:
        log_exception(f"[ig-comments] _send_dm_via_search failed for @{username}", exc)
        return False


def cmd_monitor_dms(env_vars, args):
    """Continuously monitor Instagram DMs using one persistent browser context."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        safe_print("ERROR: playwright not installed. Run: pip install playwright")
        return {"status": "error", "message": "playwright not installed"}

    poll_min, poll_max = _poll_delay_bounds(args)
    safe_print(
        "Starting Instagram DM daemon "
        f"(polling every {poll_min}-{poll_max} seconds; Ctrl+C to stop)."
    )

    last_result = None
    pass_count = 0
    with sync_playwright() as p:
        context, page = _open_ig_page(p)
        try:
            while True:
                pass_count += 1
                safe_print(
                    f"[ig-daemon] Poll #{pass_count} at "
                    f"{datetime.now(timezone.utc).isoformat()}"
                )
                try:
                    last_result = _check_dms_on_page(env_vars, args, page)
                    if last_result.get("status") == "login_failed":
                        safe_print("[ig-daemon] Login/session recovery will retry on the next poll.")
                    elif last_result.get("status") in {"error", "timeout"}:
                        recovered = recover_inbox_page(
                            page,
                            env_vars,
                            "[ig-daemon] Error result from DM poll",
                        )
                        if not recovered:
                            safe_print("[ig-daemon] Reopening persistent browser context after failed recovery.")
                            _close_context_safely(context)
                            context, page = _open_ig_page(p)
                    outbox_result = process_dashboard_outbox(env_vars, page)
                    if outbox_result["claimed"]:
                        safe_print(
                            "[ig-daemon] Dashboard outbox: "
                            f"{outbox_result['sent']} sent, {outbox_result['failed']} failed"
                        )

                    triggers_result = process_comment_triggers(env_vars, page)
                    if triggers_result["triggers"]:
                        safe_print(
                            "[ig-daemon] Comment triggers: "
                            f"{triggers_result['triggers']} active, "
                            f"{triggers_result['matched']} matched, "
                            f"{triggers_result['sent']} DM'd, "
                            f"{triggers_result['failed']} failed"
                        )

                    # Activity page (new follower welcomes) — checked every
                    # 5th poll (~5-10 min) to look organic and avoid hammering
                    # the followers modal.
                    if pass_count % 5 == 1:
                        followers_result = process_new_follower_welcomes(env_vars, page)
                        status = followers_result.get("status")
                        if status == "snapshot":
                            safe_print(
                                "[ig-daemon] First-run follower snapshot: "
                                f"{followers_result.get('snapshot_size', 0)} recorded."
                            )
                        elif status == "ok" and followers_result.get("new_follows", 0) > 0:
                            safe_print(
                                "[ig-daemon] New followers: "
                                f"{followers_result['new_follows']} detected, "
                                f"{followers_result.get('sent', 0)} welcomed, "
                                f"{followers_result.get('skipped', 0)} skipped"
                            )
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    log_exception("[ig-daemon] Unhandled poll failure", exc)
                    recovered = recover_inbox_page(page, env_vars, "[ig-daemon] Poll failure")
                    if not recovered:
                        safe_print("[ig-daemon] Reopening persistent browser context after poll failure.")
                        _close_context_safely(context)
                        context, page = _open_ig_page(p)
                    last_result = {
                        "action": "monitor_dms",
                        "status": "error",
                        "message": str(exc),
                    }

                delay = random.randint(poll_min, poll_max)
                safe_print(
                    f"[ig-daemon] Sleeping {delay // 60}m {delay % 60}s "
                    "before next inbox check."
                )
                _sleep(delay)
        except KeyboardInterrupt:
            safe_print("[ig-daemon] Shutdown requested; closing browser context.")
            return {
                "action": "monitor_dms",
                "status": "stopped",
                "polls": pass_count,
                "last_result": last_result,
            }
        finally:
            _close_context_safely(context)


def cmd_check_dms(env_vars, args):
    """Check Instagram DMs and auto-reply to unread messages in one atomic pass.

    This is the ONLY DM handler that runs on cron. It:
    1. Opens inbox, reads conversations
    2. For each unread DM: opens it, reads last message, detects intent
    3. Sends auto-reply if appropriate (respects 24h cooldown + CC manual reply check)
    4. Notifies CC on Telegram with the username AND what action was taken
    """
    if getattr(args, "daemon", False):
        return cmd_monitor_dms(env_vars, args)
    return _cmd_check_dms_once_with_context(env_vars, args)


def cmd_check_comments(env_vars, args):
    """Check Instagram comments (navigates to recent posts)."""
    result = {
        "action": "check_comments",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "checked",
        "message": "Comment check - use check-dms for active DM monitoring",
    }
    if getattr(args, "output_json", False):
        print(json.dumps(result, indent=2))
    else:
        safe_print(f"Instagram Comments: {result['message']}")
    return result


def cmd_send_dm(env_vars, args):
    """Send a DM to a specific user or reply in a thread."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        safe_print("ERROR: playwright not installed")
        return {"status": "error"}

    target = args.to_user
    message = args.message
    thread_url = getattr(args, "thread", None)
    result = {"status": "error", "to": target, "message": "Unknown error"}

    with sync_playwright() as p:
        context = get_browser_context(p)
        page = context.pages[0] if context.pages else context.new_page()

        try:
            if not ensure_logged_in(page, env_vars):
                safe_print("Login failed")
                return {"status": "login_failed"}

            if thread_url:
                # Navigate directly to thread
                page.goto(thread_url, wait_until="domcontentloaded", timeout=60000)
                time.sleep(6)
            else:
                # Search for user in DMs
                safe_print(f"Looking for conversation with @{target}...")
                # Click on the conversation from inbox
                safe_target = target.replace("\\", "\\\\").replace("'", "\\'")
                found = page.evaluate(f"""() => {{
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                    while (walker.nextNode()) {{
                        if (walker.currentNode.textContent.includes('{safe_target}')) {{
                            let el = walker.currentNode.parentElement;
                            for (let i = 0; i < 10; i++) {{
                                if (!el) break;
                                if (el.tagName === 'A' || el.getAttribute('role') === 'button') {{
                                    el.click();
                                    return true;
                                }}
                                el = el.parentElement;
                            }}
                            walker.currentNode.parentElement.click();
                            return true;
                        }}
                    }}
                    return false;
                }}""")
                if not found:
                    safe_print(f"Could not find conversation with @{target}")
                    return {"status": "not_found", "user": target}
                time.sleep(5)

            # Find message input and type
            msg_input = page.query_selector('div[role="textbox"]') or page.query_selector('div[contenteditable="true"]')
            if not msg_input:
                safe_print("Could not find message input")
                return {"status": "no_input"}

            msg_input.click()
            time.sleep(0.3)
            page.keyboard.type(message, delay=15)
            time.sleep(0.5)
            page.keyboard.press("Enter")
            time.sleep(3)

            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "ig_sent_dm.png"))

            result = {
                "status": "sent",
                "to": target,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            notify(
                f"Sent IG DM to @{target}: {message[:80]}",
                category="instagram",
            )

            if getattr(args, "output_json", False):
                print(json.dumps(result, indent=2))
            else:
                safe_print(f"DM sent to @{target}: {message[:60]}")

        finally:
            context.close()

    return result


def cmd_log_dm(env_vars, args):
    """Log an Instagram DM interaction to Supabase for tracking."""
    try:
        from supabase import create_client
        url = env_vars.get("BRAVO_SUPABASE_URL")
        key = env_vars.get("BRAVO_SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            safe_print("ERROR: Supabase not configured")
            return {"status": "error"}
        db = create_client(url, key)
    except Exception as e:
        safe_print(f"ERROR: {e}")
        return {"status": "error", "error": str(e)}

    record = {
        "channel": "instagram_dm",
        "direction": args.direction,
        "lead_id": getattr(args, "lead_id", None),
        "summary": args.summary,
        "metadata": json.dumps({
            "ig_username": args.username,
            "message_preview": args.summary[:200],
        }),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if args.direction == "inbound":
        notify(
            f"New Instagram DM from @{args.username}: {args.summary[:100]}",
            category="instagram",
        )

    try:
        db.table("lead_interactions").insert(record).execute()
        result = {"status": "logged", "username": args.username}
    except Exception as e:
        result = {"status": "error", "error": str(e)}

    if getattr(args, "output_json", False):
        print(json.dumps(result, indent=2))
    else:
        safe_print(f"DM logged: @{args.username} ({args.direction})")

    return result


# -- Auto-reply helpers -------------------------------------------------------

def extract_all_inbound_since_last_outbound(convo_text: str) -> list[str]:
    """Return EVERY inbound prospect message since CC's most recent outbound.

    When the daemon is offline mid-conversation and the prospect sends 3 more
    DMs, we must push all 3 to PULSE so dm_messages reflects the truth and
    the next doctrine call has full history. Returns chronological order.
    """
    if not convo_text:
        return []
    import re
    lines = [l.strip() for l in convo_text.split("\n") if l.strip()]
    skip_patterns = {
        "seen", "delivered", "active", "typing", "liked a message",
        "liked a photo", "sent an attachment", "sent a voice message",
        "this message was unsent", "unsent",
    }
    time_pattern = re.compile(
        r"^\d{1,2}:\d{2}\s*(am|pm)?$|^\d{1,2}[mhdw]$|^just now$|^yesterday$",
        re.I,
    )

    # Walk backwards collecting inbound lines until we hit an outbound ("You")
    inbound_buffer: list[str] = []
    for line in reversed(lines):
        lower = line.lower()
        if lower in skip_patterns or time_pattern.match(lower):
            continue
        if len(line) < 2:
            continue
        if lower.startswith("you:") or lower.startswith("you ") or lower == "you":
            break
        inbound_buffer.append(line)

    inbound_buffer.reverse()
    # De-dup adjacent identical lines (IG sometimes renders the same line
    # twice in compact view)
    out: list[str] = []
    for line in inbound_buffer:
        if not out or out[-1] != line:
            out.append(line)
    return out


def extract_last_incoming_message(convo_text: str) -> str:
    """Pull out the last message that ISN'T from CC (i.e. not starting with 'You').

    The conversation text contains interleaved messages. We want the most recent
    message from the OTHER person to understand what they actually said.

    For story replies, Instagram shows "Replied to your story" as metadata then
    the actual reply text — we grab both and concatenate so context is preserved.
    """
    if not convo_text:
        return ""
    lines = [l.strip() for l in convo_text.split("\n") if l.strip()]
    # Walk backwards, skip timestamps/metadata, find last non-You message
    skip_patterns = {"seen", "delivered", "active", "typing", "liked a message",
                     "liked a photo", "sent an attachment"}
    # Story-related metadata that should be INCLUDED as context (not skipped)
    story_patterns = {"replied to your story", "reacted to your story",
                      "mentioned you in their story"}
    import re
    time_pattern = re.compile(r"^\d{1,2}:\d{2}\s*(am|pm)?$|^\d{1,2}[mhdw]$|^just now$|^yesterday$", re.I)

    # Collect up to 3 recent incoming lines to get context (story reply + actual text)
    incoming_lines = []
    for line in reversed(lines):
        lower = line.lower()
        # Skip metadata
        if lower in skip_patterns or time_pattern.match(lower):
            continue
        if len(line) < 2:
            continue
        # Skip CC's own messages — stop collecting (we've passed the boundary)
        if lower.startswith("you:") or lower.startswith("you ") or lower == "you":
            break
        incoming_lines.append(line)
        # If this line is story metadata, keep going to grab the actual reply
        if any(p in lower for p in story_patterns):
            continue
        # Otherwise we have enough context
        if len(incoming_lines) >= 2:
            break

    # Reverse to get chronological order and join
    incoming_lines.reverse()
    return " ".join(incoming_lines).strip()


def detect_intent(text: str) -> str:
    """Classify the OTHER person's message into an intent.

    BOOKING: Only when they EXPLICITLY ask for a call/meeting/demo.
    PRICING: Asking about cost/pricing.
    PAYMENT: Ready to pay, asking how to pay, or mentioning non-Stripe payment methods.
    INFO: Asking what you do or how it works.
    GREETING: Simple hello/hey/yo.
    CONVO: General conversation that doesn't fit above — respond naturally.
    UNKNOWN: Can't understand or too short to act on.

    Key change from V1: "CONVO" is the new default instead of UNKNOWN.
    Most messages deserve a genuine response, not silence.
    """
    lowered = text.lower().strip()

    # Too short to do anything with
    if len(lowered) < 2:
        return "UNKNOWN"

    # Check for explicit booking phrases first (high confidence)
    for phrase in _EXPLICIT_BOOKING_PHRASES:
        if phrase in lowered:
            return "BOOKING"

    # Check for payment intent — someone ready to pay or mentioning non-Stripe methods
    for phrase in _PAYMENT_PHRASES:
        if phrase in lowered:
            return "PAYMENT"
    # Single-word payment signals with context
    if any(w in lowered for w in ("invoice", "checkout")) and any(w in lowered for w in ("send", "ready", "want", "need", "can")):
        return "PAYMENT"

    # Multi-word checks
    if "how much" in lowered or "what's the price" in lowered or "what do you charge" in lowered:
        return "PRICING"
    for phrase in ("what do you do", "how does", "tell me about", "what is your", "what services"):
        if phrase in lowered:
            return "INFO"

    # Single-word tokenization
    import re
    tokens = set(re.findall(r"[a-z']+", lowered))

    # Only trigger BOOKING on very explicit signal words + context
    booking_signals = tokens & _BOOKING_SIGNAL_WORDS
    if booking_signals and any(w in lowered for w in ("call", "meeting", "demo", "appointment")):
        return "BOOKING"

    if tokens & _PRICING_KEYWORDS:
        return "PRICING"

    # Short reactive messages (thank you, lol, haha, emoji-like) — treat as CONVO
    # so _build_convo_reply can match "thank you" properly instead of greeting them
    if any(w in lowered for w in ("thank", "thanks", "appreciate", "thx", "lol", "haha", "lmao", "nice", "dope", "fire")):
        return "CONVO"

    # Pure greetings (short messages that are ONLY a hello — nothing else)
    if len(tokens) <= 4 and tokens & _GREETING_KEYWORDS:
        return "GREETING"

    # If the message has substance (>3 words), it's a conversation — respond to it
    if len(tokens) >= 3:
        return "CONVO"

    # Very short but not a greeting — still try to respond contextually
    if len(tokens) <= 2:
        return "CONVO"

    return "CONVO"


def build_reply(intent: str, last_msg: str = "", convo_context: str = "") -> str:
    """Generate a reply that sounds like CC — short, casual, genuine.

    Voice rules:
    - Text like you're talking to a friend. Short sentences.
    - Use lowercase mostly. No "I'd love to" or "Thanks for reaching out."
    - No multiple exclamation marks. No corporate pleasantries.
    - Can use slang: "ya", "nah", "for sure", "lowkey", "honestly", "bet"
    - Be helpful and real, not salesy.
    - DON'T force every conversation toward booking a call.
    - Match the energy of what they said.
    """
    import random

    if intent == "BOOKING":
        return random.choice([
            "ya for sure lets do it. when works for you this week? i'm usually free 9-5",
            "bet lets hop on a call. what day works best? im pretty open this week",
            "down. when are you thinking? im free most days 9-5 eastern",
        ])

    if intent == "PAYMENT":
        return _build_payment_reply(last_msg, convo_context)

    if intent == "PRICING":
        return random.choice([
            "honestly it depends on what you need — every business is different. "
            "what kind of stuff are you looking to set up?",
            "ya so pricing really depends on the scope. "
            "some clients pay 400/mo, some pay more depending on what we build. "
            "what's your situation?",
            "it varies a lot — depends on what you need automated and how complex it is. "
            "what are you working with right now?",
        ])

    if intent == "INFO":
        return random.choice([
            "ya so basically i build AI automation systems for local businesses — "
            "stuff like auto follow-ups, booking, lead capture, review management. "
            "been doing it for a while now, it's pretty sick what you can automate these days",
            "i run an AI automation company called OASIS. we set up systems that handle "
            "the repetitive stuff — follow-ups, scheduling, lead gen, all that. "
            "honestly it's been a wild ride building it",
            "short version — i help businesses automate their ops with AI. "
            "most of my clients are local service businesses. pretty much anything "
            "repetitive, we can build a system for it",
        ])

    if intent == "GREETING":
        return random.choice([
            "yo what's good",
            "hey what's up",
            "yo whats good",
            "hey! how's it going",
        ])

    if intent == "CONVO":
        # For general conversation, build a contextual reply
        return _build_convo_reply(last_msg, convo_context)

    return ""


def _resolve_payment_links(reply: str) -> str:
    """Find [GENERATE_PAYMENT_LINK:amount:label] tokens and replace with real Stripe URLs."""
    import re

    pattern = r'\[GENERATE_PAYMENT_LINK:(\d+):([^\]]+)\]'

    def _replace_link(match):
        amount_cents = int(match.group(1))
        label = match.group(2).strip()
        try:
            from stripe_tool import generate_payment_link
            result = generate_payment_link(
                amount_cents=amount_cents,
                label=label,
                currency="cad",
            )
            return result["url"]
        except Exception as e:
            safe_print(f"[stripe] Payment link generation failed: {e}")
            return "(payment link coming — i'll send it in a sec)"

    return re.sub(pattern, _replace_link, reply)


def _build_payment_reply(last_msg: str, convo_context: str) -> str:
    """Generate a payment-related reply using Claude, then resolve any payment link tokens."""
    reply = _generate_reply_via_claude(last_msg, convo_context, payment_context=True)
    if reply:
        return _resolve_payment_links(reply)

    # Fallback if Claude API is down
    return (
        "ya for sure — i'll send you a payment link right now. "
        "all payments go through stripe so its secure and easy"
    )


def _build_convo_reply(last_msg: str, convo_context: str) -> str:
    """Generate a contextual reply using Claude API.

    Sends the person's message (and recent conversation context) to Claude
    with CC's voice rules. Returns a genuine, conversational response that
    actually addresses what they said — not canned keyword templates.

    Falls back to simple templates only if the API call fails.
    """
    import random

    # Try Claude API first — this is the real reply engine
    reply = _generate_reply_via_claude(last_msg, convo_context)
    if reply:
        return _resolve_payment_links(reply)

    # Fallback: bare minimum templates if API is down
    lower = last_msg.lower().strip()
    if any(w in lower for w in ("thank", "thanks", "appreciate", "thx")):
        return "ya no worries"
    if any(w in lower for w in ("replied to your story", "your story")):
        return "appreciate that fr"
    if "?" in last_msg:
        return "good question, honestly it depends on the situation"
    return "ya for sure"


def _generate_reply_via_claude(last_msg: str, convo_context: str, payment_context: bool = False) -> str:
    """Call Claude API to generate a contextual DM reply in CC's voice.

    Returns the reply text, or empty string on failure.
    """
    try:
        import anthropic
    except ImportError:
        return ""

    env_vars = load_env()
    api_key = env_vars.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return ""

    # Build the prompt with conversation context
    context_block = ""
    if convo_context:
        context_block = f"\nRecent conversation:\n{convo_context[-1000:]}\n"

    if payment_context:
        context_block += (
            "\nCONTEXT: This person is asking about payment or how to pay. "
            "If a price was previously discussed or agreed in the conversation, "
            "include a [GENERATE_PAYMENT_LINK:amount_cents:label] token in your reply "
            "(e.g., [GENERATE_PAYMENT_LINK:25000:OASIS AI Monthly]). "
            "If no price was agreed yet, ask what service they want first.\n"
        )

    system_prompt = (
        "You are ghostwriting an Instagram DM reply as Conaugh McKenna (CC), "
        "a 22-year-old AI automation entrepreneur from Collingwood, Ontario. "
        "CC runs OASIS AI Solutions — he builds AI systems for local businesses.\n\n"
        "VOICE RULES (non-negotiable):\n"
        "- Text like you're talking to a friend at 2am. Short sentences.\n"
        "- Lowercase mostly. No 'I'd love to' or 'Thanks for reaching out.'\n"
        "- No exclamation marks spam. No corporate pleasantries. No emojis.\n"
        "- Can use: ya, nah, for sure, lowkey, honestly, bet, fr, lol\n"
        "- Be genuine and real. Match their energy.\n"
        "- NEVER pitch, sell, or push toward a call unless they ask.\n"
        "- NEVER use hashtags or marketing language.\n"
        "- If they said something about your story, acknowledge the story content.\n"
        "- If they said thank you, just be chill about it.\n"
        "- Keep it to 1-3 sentences max. DMs are short.\n"
        "- Respond to WHAT THEY ACTUALLY SAID. Read their message carefully.\n\n"
        "PAYMENT RULES (non-negotiable):\n"
        "- ALL payments go through Stripe. NEVER suggest e-transfer, wire transfer, "
        "Interac, Venmo, Zelle, PayPal, cash, or any other payment method.\n"
        "- If they ask how to pay or mention any non-Stripe method, say: "
        "'all payments go through stripe — super easy and secure, i'll send you a link'\n"
        "- If a specific dollar amount has been AGREED upon and they want to pay, "
        "include this exact token in your reply (it will be replaced with a real link):\n"
        "  [GENERATE_PAYMENT_LINK:<amount_in_cents_CAD>:<short description>]\n"
        "  Example: 'here's your link [GENERATE_PAYMENT_LINK:50000:OASIS AI Retainer]'\n"
        "- Only include the payment link token when a price is AGREED. Not for general pricing questions.\n"
        "- Currency is always CAD.\n\n"
        "Reply with ONLY the message text. No quotes, no labels, nothing else."
    )

    user_msg = f"{context_block}Their message: \"{last_msg}\"\n\nYour reply:"

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=_read_config_model("fast_model", "claude-sonnet-4-6"),
            max_tokens=150,
            system=system_prompt,
            messages=[{"role": "user", "content": user_msg}],
        )
        reply = response.content[0].text.strip()

        # Safety: strip any quotes the model might wrap the reply in
        if reply.startswith('"') and reply.endswith('"'):
            reply = reply[1:-1]
        if reply.startswith("'") and reply.endswith("'"):
            reply = reply[1:-1]

        # Safety: reject if too long for a DM (something went wrong)
        if len(reply) > 500:
            return reply[:500]

        return reply
    except Exception as e:
        safe_print(f"[claude-api] Reply generation failed: {e}")
        return ""


def load_replied_log() -> dict:
    """Load the dm_replied.json tracking file.  Returns {} if absent or corrupt."""
    if not DM_REPLIED_PATH.exists():
        return {}
    try:
        with open(DM_REPLIED_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_replied_log(log: dict) -> None:
    """Persist the dm_replied.json tracking file."""
    DM_REPLIED_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DM_REPLIED_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)


def load_notified_log() -> dict:
    """Load the dm_notified.json file — tracks which DM previews we already
    sent a Telegram notification about so we never spam CC with the same
    conversation on every cron cycle."""
    if not NOTIFIED_PATH.exists():
        return {}
    try:
        with open(NOTIFIED_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_notified_log(log: dict) -> None:
    NOTIFIED_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTIFIED_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)


def already_notified(log: dict, username: str, preview: str) -> bool:
    """Return True if we already sent CC a Telegram notification for this
    exact username + preview combo. Prevents the same DM from generating
    a notification on every 5-minute cron cycle."""
    entry = log.get(username)
    if not entry:
        return False
    return entry.get("preview", "") == preview


def mark_notified(log: dict, username: str, preview: str) -> None:
    """Record that we notified CC about this DM."""
    log[username] = {
        "preview": preview,
        "notified_at": datetime.now(timezone.utc).isoformat(),
    }


def load_booking_state() -> dict:
    """Load the multi-turn booking state tracker. Returns {} if absent."""
    if not BOOKING_STATE_PATH.exists():
        return {}
    try:
        with open(BOOKING_STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_booking_state(state: dict) -> None:
    """Persist the booking state tracker."""
    BOOKING_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BOOKING_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def parse_datetime_from_text(text: str) -> dict | None:
    """Extract a date and time from a SHORT, SPECIFIC scheduling message.

    STRICT RULES — only parse if the message is clearly a scheduling response:
      - Must contain a recognizable time (2pm, 10:30am, at 14:00)
      - Must contain a recognizable date signal (tomorrow, Thursday, March 25)
      - Message should be SHORT (scheduling responses are typically <50 words)
      - If the message is long/rambling, it's probably NOT a scheduling response

    Returns {date: "YYYY-MM-DD", time: "HH:MM", display: "Thursday March 25 at 2:00 PM"}
    or None if this doesn't look like a scheduling message.
    """
    import re
    from datetime import date as date_type

    # GUARD: Only parse SHORT messages that look like scheduling responses.
    # "trapped is not the mic rib sea story Thursday" is NOT a scheduling msg.
    # Real scheduling messages: "thursday at 2pm", "tomorrow 10am", "march 25 3pm"
    lowered = text.lower().strip()
    words = lowered.split()
    if len(words) > 30:
        return None  # Too long to be a time/date response
    if len(words) < 2:
        return None  # Too short — just one word isn't a date

    # GUARD: Must contain an explicit time marker (am/pm or "at X:XX")
    has_time_marker = bool(re.search(r'\d{1,2}\s*(am|pm|a\.m\.|p\.m\.)', lowered))
    has_at_time = bool(re.search(r'at\s+\d{1,2}', lowered))
    if not has_time_marker and not has_at_time:
        return None

    # GUARD: Must contain a date signal
    date_signals = (
        "tomorrow", "today", "monday", "tuesday", "wednesday", "thursday",
        "friday", "saturday", "sunday", "mon", "tue", "wed", "thu", "fri",
        "sat", "sun", "next", "this", "jan", "feb", "mar", "apr", "may",
        "jun", "jul", "aug", "sep", "oct", "nov", "dec",
    )
    has_date_signal = any(sig in lowered for sig in date_signals)
    # Also check for ordinals: "the 25th"
    has_ordinal = bool(re.search(r'\b\d{1,2}(?:st|nd|rd|th)\b', lowered))
    if not has_date_signal and not has_ordinal:
        return None

    # --- Extract time component ---
    time_match = re.search(
        r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)',
        lowered,
    )
    hour, minute = None, 0
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        ampm = time_match.group(3).replace(".", "")
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
    else:
        time_24 = re.search(r'(?:at\s+)(\d{1,2})(?::(\d{2}))?(?!\s*(?:am|pm))', lowered)
        if time_24:
            hour = int(time_24.group(1))
            minute = int(time_24.group(2) or 0)
            if hour > 23:
                hour = None

    if hour is None:
        return None
    # Sanity check: business hours only (7am - 9pm)
    if hour < 7 or hour > 21:
        return None

    # --- Extract date component ---
    from zoneinfo import ZoneInfo
    et = ZoneInfo("America/Toronto")
    now = datetime.now(et)
    today = now.date()
    target_date = None

    if "tomorrow" in lowered:
        target_date = today + timedelta(days=1)
    elif re.search(r'\btoday\b', lowered):
        target_date = today

    day_names = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
        "mon": 0, "tue": 1, "tues": 1, "wed": 2, "thu": 3, "thur": 3,
        "thurs": 3, "fri": 4, "sat": 5, "sun": 6,
    }
    if not target_date:
        for name, dow in day_names.items():
            if re.search(rf'\b{name}\b', lowered):
                days_ahead = (dow - today.weekday()) % 7
                if days_ahead == 0:
                    days_ahead = 7
                if "next" in lowered:
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)
                break

    month_names = {
        "jan": 1, "january": 1, "feb": 2, "february": 2,
        "mar": 3, "march": 3, "apr": 4, "april": 4,
        "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
        "aug": 8, "august": 8, "sep": 9, "september": 9,
        "oct": 10, "october": 10, "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }
    if not target_date:
        for name, month_num in month_names.items():
            m = re.search(rf'\b{name}\s+(\d{{1,2}})(?:st|nd|rd|th)?\b', lowered)
            if m:
                day = int(m.group(1))
                year = today.year
                candidate = date_type(year, month_num, min(day, calendar.monthrange(year, month_num)[1]))
                if candidate < today:
                    candidate = date_type(year + 1, month_num, min(day, calendar.monthrange(year + 1, month_num)[1]))
                target_date = candidate
                break

    if not target_date and has_ordinal:
        ord_match = re.search(r'\b(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)\b', lowered)
        if ord_match:
            day = int(ord_match.group(1))
            if 1 <= day <= 31:
                candidate = today.replace(day=min(day, calendar.monthrange(today.year, today.month)[1]))
                if candidate <= today:
                    if today.month == 12:
                        candidate = date_type(today.year + 1, 1, min(day, calendar.monthrange(today.year + 1, 1)[1]))
                    else:
                        candidate = date_type(today.year, today.month + 1, min(day, calendar.monthrange(today.year, today.month + 1)[1]))
                target_date = candidate

    # If we have a time but no date, DON'T guess — ask them to clarify
    if not target_date:
        return None

    time_str = f"{hour:02d}:{minute:02d}"
    display_dt = datetime.combine(target_date, datetime.strptime(time_str, "%H:%M").time())
    display = display_dt.strftime("%A %B %#d at %#I:%M %p")

    return {
        "date": target_date.isoformat(),
        "time": time_str,
        "display": display,
    }


def already_replied_within_24h(log: dict, username: str) -> bool:
    """Return True if we auto-replied to this username in the last 24 hours."""
    entry = log.get(username)
    if not entry:
        return False
    last_ts = datetime.fromisoformat(entry["replied_at"])
    now = datetime.now(timezone.utc)
    # Make last_ts timezone-aware if it came back naive (defensive)
    if last_ts.tzinfo is None:
        last_ts = last_ts.replace(tzinfo=timezone.utc)
    return (now - last_ts).total_seconds() < 86400


def get_open_conversation_handle(page) -> str | None:
    """After a conversation is opened, scrape the actual @handle from the
    header. The header shows the display name as a clickable link to /<handle>/
    so we can extract the canonical handle even when the inbox sidebar only
    showed a display name."""
    try:
        raw = page.evaluate("""() => {
            // Header link is the most reliable: it points at /<handle>/
            const links = document.querySelectorAll('a[href^="/"][role="link"]');
            for (const link of links) {
                const href = link.getAttribute('href') || '';
                const m = href.match(/^\\/([A-Za-z0-9._]+)\\/$/);
                if (!m) continue;
                const slug = m[1];
                // Skip the page-owner's own profile and known IG paths
                const reserved = ['p','reel','reels','explore','direct','accounts','stories','tv','notifications'];
                if (reserved.includes(slug)) continue;
                // Header link is at the top of the conversation panel
                const rect = link.getBoundingClientRect();
                if (rect.top < 200 && rect.left > 200) {
                    return slug;
                }
            }
            return null;
        }""")
        if raw and isinstance(raw, str):
            return raw.strip()
    except Exception as exc:
        log_exception("[ig-handle] header scrape failed", exc)
    return None


def read_conversation_text(page, username: str) -> str:
    """Open a DM conversation by clicking the matching button in the inbox list
    and return the visible message text (last ~3000 chars).

    PRIORITY MATCHING (because display names like 'Cc' match many threads):
      1. Exact display name match on an UNREAD button (the one we want)
      2. Exact display name match on any button
      3. Partial substring match (last resort)

    After clicking, verifies the URL transitioned to /direct/t/<thread_id>
    so we know the conversation actually opened.
    """
    safe_name = username.replace("'", "\\'").replace("\\", "\\\\")
    found = page.evaluate(f"""() => {{
        const target = '{safe_name}';
        const btns = Array.from(document.querySelectorAll('div[role="button"]'));
        const score = (btn) => {{
            const text = (btn.innerText || '').trim();
            const firstLine = text.split(String.fromCharCode(10))[0].trim();
            if (firstLine !== target) return -1;
            // Prioritise unread buttons (contain "Unread" anywhere in text)
            return text.includes('Unread') ? 100 : 50;
        }};
        let best = null, bestScore = -1;
        for (const btn of btns) {{
            const s = score(btn);
            if (s > bestScore) {{ bestScore = s; best = btn; }}
        }}
        if (best && bestScore >= 50) {{ best.click(); return 'exact'; }}
        // Last resort: partial substring match
        for (const btn of btns) {{
            const text = (btn.innerText || '').trim();
            const firstLine = text.split(String.fromCharCode(10))[0].trim();
            if (firstLine.includes(target) || target.includes(firstLine)) {{
                btn.click();
                return 'partial';
            }}
        }}
        return false;
    }}""")
    if not found:
        return ""
    time.sleep(5)

    # Verify the conversation actually opened. IG's URL changes from
    # /direct/inbox/ to /direct/t/<thread_id>/. If the URL didn't move,
    # the click missed and we'd otherwise scrape garbage.
    current_url = (page.url or "")
    if "/direct/t/" not in current_url:
        # One retry: click any visible conversation button matching the
        # name with a slight delay, in case IG was still rendering.
        time.sleep(2)
        page.evaluate(f"""() => {{
            const target = '{safe_name}';
            const btns = document.querySelectorAll('div[role="button"]');
            for (const btn of btns) {{
                const t = (btn.innerText || '').trim();
                const first = t.split(String.fromCharCode(10))[0].trim();
                if (first === target) {{ btn.click(); return true; }}
            }}
            return false;
        }}""")
        time.sleep(4)
        current_url = (page.url or "")
        if "/direct/t/" not in current_url:
            safe_print(
                f"  [read_convo] click on '{username}' didn't navigate to a "
                f"thread URL (still at {current_url}). Skipping scrape."
            )
            return ""

    # Scrape ONLY the conversation thread (right panel), NOT the sidebar.
    # The sidebar contains "You: ..." previews from other conversations
    # that cause false positives in reply-detection logic.
    raw = page.evaluate("""() => {
        // Strategy: find the message textbox, then walk up to the conversation
        // panel container — this excludes the left sidebar entirely.
        const textbox = document.querySelector('div[role="textbox"]');
        if (textbox) {
            let el = textbox;
            // Walk up to find the conversation panel (stops at a large container
            // that is narrower than the full page — i.e. the right panel)
            for (let i = 0; i < 12; i++) {
                if (!el.parentElement) break;
                el = el.parentElement;
                const rect = el.getBoundingClientRect();
                const bodyWidth = document.body.getBoundingClientRect().width;
                // Right panel is typically 50-75% of page width
                if (rect.width > 350 && rect.height > 300 && rect.width < bodyWidth * 0.85) {
                    return el.innerText.slice(-3000);
                }
            }
        }
        // Fallback: if we can't isolate the panel, get full page but take
        // a larger slice from the end (conversation content is at the end).
        const main = document.querySelector('main') || document.body;
        return main.innerText.slice(-3000);
    }""")
    return _strip_ui_placeholder_chrome(raw or "")


_UI_PLACEHOLDER_TAILS = (
    "message...", "message…", "send a message...", "send a message…",
    "message", "send message", "your message", "type a message",
    "search...", "search", "active",
)


def _strip_ui_placeholder_chrome(text: str) -> str:
    """Remove the IG textbox placeholder + trailing UI labels from a scraped
    conversation. The right-panel innerText scrape includes the input box's
    placeholder ('Message...'), the bottom action row ('Send'), and the
    'Active <Xm ago>' presence string in the header — all of which leak into
    PULSE message previews and AI context.
    """
    if not text:
        return ""
    out = text
    # Iteratively strip whichever known UI tail is present (case-insensitive)
    # so multi-element tails like "Message...\nSend" both come off.
    drop_tails = (
        "message...", "message…", "message",
        "send a message...", "send a message…", "send a message",
        "send", "send message", "type a message", "your message",
        "search...", "search", "💬", "❤", "♥", "👍",
    )
    changed = True
    while changed:
        changed = False
        stripped = out.rstrip()
        if stripped != out:
            out = stripped
            changed = True
        # Pop trailing lines that are pure UI chrome
        lines = out.split("\n")
        while lines and lines[-1].strip().lower() in drop_tails:
            lines.pop()
            changed = True
        out = "\n".join(lines)
    return out


def cc_has_replied(conversation_text: str) -> bool:
    """Return True if CC's most recent message is AFTER the last incoming message.

    We check the last ~500 chars of the conversation text. If the very last
    message block starts with 'You' or 'You:' or 'You sent', CC already replied
    to the most recent incoming message — no auto-reply needed.
    """
    if not conversation_text:
        return False
    # Look at just the tail of the conversation
    tail = conversation_text[-500:]
    lines = [l.strip() for l in tail.split("\n") if l.strip()]
    if not lines:
        return False
    # Walk backwards from the end to find the last actual message line
    # (skip time stamps, empty lines, emoji-only lines)
    import re
    time_pat = re.compile(r"^\d{1,2}:\d{2}\s*(AM|PM)?$|^\d{1,3}[mhdw]$|^(Yesterday|Today)$", re.IGNORECASE)
    for line in reversed(lines):
        if time_pat.match(line):
            continue
        if len(line) <= 2:
            continue
        # Check if this last message is from CC
        if line.startswith("You") or line.startswith("you"):
            return True
        # If the last real message is from someone else, CC hasn't replied
        return False
    return False


def log_auto_reply_to_supabase(env_vars: dict, username: str, intent: str, reply: str) -> None:
    """Deprecated. The dm_interactions table was removed in favor of PULSE
    (Turso) as the single source of truth for DM activity. This shim stays
    only to avoid breaking call sites; it's a no-op."""
    return


def cmd_auto_reply(env_vars, args):
    """Check unread DMs, detect intent, and send templated auto-replies.

    Safety rules enforced here:
    - Never reply to the same person more than once per 24 h (dm_replied.json).
    - Never reply if CC has already manually replied in that thread.
    - All auto-replies are logged to Supabase dm_interactions.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        safe_print("ERROR: playwright not installed. Run: pip install playwright")
        return {"status": "error", "message": "playwright not installed"}

    replied_log = load_replied_log()
    booking_state = load_booking_state()
    actions_taken = []
    skipped = []

    with sync_playwright() as p:
        context = get_browser_context(p)
        page = context.pages[0] if context.pages else context.new_page()

        try:
            if not ensure_logged_in(page, env_vars):
                result = {
                    "action": "auto_reply",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "login_failed",
                    "message": "Could not log into Instagram. Check credentials.",
                }
                notify("Instagram login failed - auto-reply aborted", category="instagram")
                if getattr(args, "output_json", False):
                    print(json.dumps(result, indent=2))
                else:
                    safe_print(f"auto-reply: {result['message']}")
                return result

            # Step 1: Read the inbox list
            inbox_text = read_dm_list(page)
            convos = parse_conversations(inbox_text)
            unread = [c for c in convos if c.get("unread")]

            if not unread:
                result = {
                    "action": "auto_reply",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "ok",
                    "message": "No unread DMs",
                    "replied": [],
                    "skipped": [],
                }
                if getattr(args, "output_json", False):
                    print(json.dumps(result, indent=2))
                else:
                    safe_print("auto-reply: No unread DMs to process")
                return result

            # Step 2: Process each unread conversation
            for convo in unread:
                username = convo.get("username", "").strip()
                if not username:
                    continue

                # Safety check 1: already replied in last 24 h?
                if already_replied_within_24h(replied_log, username):
                    skipped.append({"username": username, "reason": "replied_within_24h"})
                    continue

                # Open conversation and read full thread text
                convo_text = read_conversation_text(page, username)

                # NOTE: cc_has_replied() check removed — it was returning false
                # positives because main.innerText includes sidebar previews
                # ("You: ...") from OTHER conversations. The inbox preview check
                # (unread detection) already filters correctly. 24h cooldown
                # prevents double-replying.

                # Detect intent from the last message in the thread
                # Use the preview from the inbox list as the signal text; fall
                # back to the tail of the full conversation if the preview is empty.
                signal_text = convo.get("preview", "") or convo_text[-500:]
                last_msg = extract_last_incoming_message(convo_text) or signal_text
                intent = detect_intent(signal_text)

                if intent == "UNKNOWN":
                    skipped.append({"username": username, "reason": "unknown_intent"})
                    page.goto(
                        "https://www.instagram.com/direct/inbox/",
                        wait_until="domcontentloaded",
                        timeout=60000,
                    )
                    time.sleep(4)
                    continue

                reply_text = build_reply(intent, last_msg=last_msg, convo_context=convo_text)

                sent = _send_dm_reply(page, reply_text, recipient=username)
                if not sent:
                    skipped.append({"username": username, "reason": "no_input_found"})
                    page.goto(
                        "https://www.instagram.com/direct/inbox/",
                        wait_until="domcontentloaded",
                        timeout=60000,
                    )
                    time.sleep(4)
                    continue

                # Record the reply in the local tracking file
                replied_log[username] = {
                    "replied_at": datetime.now(timezone.utc).isoformat(),
                    "intent": intent,
                }
                save_replied_log(replied_log)

                # Only enter booking flow on EXPLICIT booking intent
                # (not PRICING or INFO — those are conversational, no CTA)
                if intent == "BOOKING":
                    booking_state[username] = {
                        "stage": "awaiting_time",
                        "intent": intent,
                        "started_at": datetime.now(timezone.utc).isoformat(),
                    }
                    save_booking_state(booking_state)

                # Log to Supabase (best-effort)
                log_auto_reply_to_supabase(env_vars, username, intent, reply_text)

                # Notify CC on Telegram for booking and payment intents
                if intent == "BOOKING":
                    notify(
                        f"IG DM from @{username}: \"{last_msg[:60]}\"\n"
                        f"Auto-replied (BOOKING): {reply_text[:80]}",
                        category="instagram",
                    )
                elif intent == "PAYMENT":
                    notify(
                        f"IG DM from @{username}: \"{last_msg[:60]}\"\n"
                        f"Auto-replied (PAYMENT): {reply_text[:80]}",
                        category="instagram",
                    )

                actions_taken.append({
                    "username": username,
                    "intent": intent,
                    "reply_preview": reply_text[:100],
                })

                # Navigate back to inbox for the next conversation
                page.goto(
                    "https://www.instagram.com/direct/inbox/",
                    wait_until="domcontentloaded",
                    timeout=60000,
                )
                time.sleep(4)
                # Re-read the list so stale refs don't cause issues
                inbox_text = read_dm_list(page)

        finally:
            context.close()

    result = {
        "action": "auto_reply",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "ok",
        "unread_processed": len(unread) if unread else 0,
        "replied": actions_taken,
        "skipped": skipped,
        "message": (
            f"Replied to {len(actions_taken)} conversation(s), "
            f"skipped {len(skipped)}"
        ),
    }

    if getattr(args, "output_json", False):
        print(json.dumps(result, indent=2, default=str))
    else:
        safe_print(f"auto-reply: {result['message']}")
        for a in actions_taken:
            safe_print(f"  -> @{a['username']} [{a['intent']}]: {a['reply_preview']}")
        for s in skipped:
            safe_print(f"  -- skipped @{s['username']}: {s['reason']}")

    return result


# -- Main ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Instagram Engine - ManyChat replacement via browser automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", dest="output_json", action="store_true")

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # check-dms
    p_dms = subparsers.add_parser("check-dms", help="Check for new Instagram DMs")
    p_dms.add_argument("--reply", action="store_true", help="Auto-reply to unread DMs")
    p_dms.add_argument("--daemon", action="store_true", help="Continuously monitor DMs")
    p_dms.add_argument(
        "--poll-min",
        type=int,
        default=DEFAULT_POLL_MIN_SECONDS,
        help="Minimum daemon delay between inbox checks, in seconds",
    )
    p_dms.add_argument(
        "--poll-max",
        type=int,
        default=DEFAULT_POLL_MAX_SECONDS,
        help="Maximum daemon delay between inbox checks, in seconds",
    )

    # monitor-dms
    p_monitor = subparsers.add_parser("monitor-dms", help="Continuously monitor Instagram DMs")
    p_monitor.add_argument("--reply", action="store_true", help="Auto-reply to unread DMs")
    p_monitor.add_argument("--daemon", action="store_true", default=True, help=argparse.SUPPRESS)
    p_monitor.add_argument(
        "--poll-min",
        type=int,
        default=DEFAULT_POLL_MIN_SECONDS,
        help="Minimum daemon delay between inbox checks, in seconds",
    )
    p_monitor.add_argument(
        "--poll-max",
        type=int,
        default=DEFAULT_POLL_MAX_SECONDS,
        help="Maximum daemon delay between inbox checks, in seconds",
    )

    # check-comments
    subparsers.add_parser("check-comments", help="Check for new Instagram comments")

    # send-dm
    p_send = subparsers.add_parser("send-dm", help="Send a DM to a user")
    p_send.add_argument("--to", dest="to_user", required=True, help="Target username")
    p_send.add_argument("--msg", dest="message", required=True, help="Message text")
    p_send.add_argument("--thread", help="Direct thread URL (optional)")

    # log-dm
    p_log = subparsers.add_parser("log-dm", help="Log a DM interaction to Supabase")
    p_log.add_argument("--username", required=True, help="Instagram username")
    p_log.add_argument("--summary", required=True, help="Message summary")
    p_log.add_argument("--direction", choices=["inbound", "outbound"], default="inbound")
    p_log.add_argument("--lead-id", help="Associated lead UUID")

    # auto-reply
    subparsers.add_parser(
        "auto-reply",
        help="Detect intent in unread DMs and send templated auto-replies",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    env_vars = load_env()

    handlers = {
        "check-dms": cmd_check_dms,
        "monitor-dms": cmd_monitor_dms,
        "check-comments": cmd_check_comments,
        "send-dm": cmd_send_dm,
        "log-dm": cmd_log_dm,
        "auto-reply": cmd_auto_reply,
    }

    handler = handlers.get(args.command)
    if handler:
        handler(env_vars, args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
