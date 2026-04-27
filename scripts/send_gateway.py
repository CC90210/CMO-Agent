"""
Send Gateway — the single outbound chokepoint for every marketing action
Maven (CMO Agent) performs on behalf of CC's empire.

WHY THIS EXISTS
---------------
Marketing email is the highest-blast-radius surface in the empire. Bravo
got bitten by "Hi Contact," — a placeholder name leaked into 9 cold sends
and CC saw it. Marketing blasts run an order of magnitude larger; without
a chokepoint, the same failure fans out to hundreds of recipients on the
first send. This module is the architectural fix: every outbound send
(email, IG DM, Late post, Meta-Ads spend, Google-Ads spend) goes through
`send()`. Idempotency, CASL enforcement, name sanitization, daily caps,
the draft-critic gate, and the CFO spend gate are all enforced
ARCHITECTURALLY — a caller physically cannot send without them, because
the smtplib / API call happens inside this file and nowhere else.

This file mirrors Bravo's send_gateway.py architecture (V5.6 chokepoint)
and inherits the fail-closed critic-gate fix shipped in Bravo's commit
db37263 — any non-`ship` verdict from the critic blocks, and any exception
inside the critic itself ALSO blocks. Better to escalate to CC than to
silently bypass the safety review when the gate itself is down.

Maven adaptations vs Bravo:
  - 5 brands (oasis, conaugh, propflow, nostalgic, sunbiz) instead of 3
  - email cap = 200/day, 30/hr (marketing list is bigger than cold outreach)
  - new channels: meta_ads, google_ads — these consult cfo_pulse.json
    (CFO spend gate) and never SMTP. Spend approval is in the dollar
    amount, not the message count.
  - killswitch env var = MAVEN_FORCE_DRY_RUN (BRAVO_FORCE_DRY_RUN also
    honoured for the shared multi-agent envelope)
  - Supabase resolves MAVEN_SUPABASE_* with a fallback to BRAVO_SUPABASE_*
    because the project is shared (phctllmtsogkovoilwos)

CALLER CONTRACT
---------------
- send() NEVER raises. On error it returns status="error" with reason.
- send() NEVER double-sends. If the cooldown check fails, status="blocked".
- send() NEVER sends to a suppressed address on commercial intent.
- send() ALWAYS routes paid-spend channels through the CFO spend gate.
- send() ALWAYS sanitizes recipient names via name_utils before render.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import smtplib
import sys
import uuid
from datetime import datetime, timedelta, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from casl_compliance import (  # noqa: E402
    should_suppress,
    build_casl_footer,
    build_casl_footer_html,
    add_list_unsubscribe_headers,
)
from name_utils import sanitize_template_vars, safe_first_name  # noqa: E402,F401

try:
    from draft_critic import critique_draft  # noqa: F401
except ImportError:
    def critique_draft(*_a: Any, **_kw: Any) -> dict:  # type: ignore[misc]
        return {
            "verdict": "reject",
            "reasons": ["draft_critic unavailable"],
            "notes": "draft_critic unavailable",
        }


# ---- Telegram notify (V1.3 — Maven-owned bot via scripts/notify.py) --------

try:
    from notify import notify as _maven_notify  # noqa: E402
except Exception:  # pragma: no cover — fall back to no-op so gates never crash
    def _maven_notify(*_a: Any, **_kw: Any) -> bool:  # type: ignore[misc]
        return False


def _telegram_notify(message: str, category: str = "send-gateway-error",
                     **_kw: Any) -> bool:
    """Forwarded to scripts/notify.notify so daily-cap warnings, killswitch
    messages, and gate errors actually reach CC's phone instead of vanishing."""
    try:
        return bool(_maven_notify(message, category=category))
    except Exception:
        return False


# ---- Canonical constants ----------------------------------------------------

# Cooldown windows per channel. Marketing nurture cadences are slower than
# cold outreach — a recipient should not get 2 brand emails on consecutive
# days even if a campaign would otherwise allow it.
DEFAULT_COOLDOWNS: dict[str, int] = {
    "email": 96,        # 4 days between marketing emails to the same lead
    "instagram": 48,    # 2 days
    "instagram_dm": 24, # 24h cooldown per IG recipient (1:1 outbound at scale)
    "skool": 24,        # 1 day
    "telegram": 0,      # internal
    # Paid-spend channels — no recipient-level cooldown (audience targeting
    # is the gate, not per-lead cadence). The CFO spend gate is the cap.
    "meta_ads": 0,
    "google_ads": 0,
    "late_post": 0,     # organic social posting via Late MCP (legacy alias)
    "social": 0,        # organic social — Late publisher unified channel
}

# Daily outbound caps. Stricter than Bravo's because marketing list sizes
# are larger and a runaway script would do more damage faster.
DAILY_CAPS: dict[str, int] = {
    "email": 200,       # marketing-blast cap (per master doc)
    "instagram": 30,
    "instagram_dm": 30, # 1:1 IG DMs — anti-spam discipline
    "late_post": 25,
    "social": 50,       # organic posts across all platforms via Late
    # Paid-spend channels do NOT have a count-based daily cap — the
    # dollar-budget cap from cfo_pulse.json is the meaningful limit.
}

HOURLY_CAPS: dict[str, int] = {
    "email": 30,        # protects sender reputation against bursty sends
    "instagram": 6,
    "instagram_dm": 5,
    "late_post": 5,
    "social": 10,
}

KNOWN_AGENT_SOURCES: frozenset[str] = frozenset({
    "email_blast",
    "meta_ads_engine",
    "google_ads_engine",
    "content_pipeline",
    "jotform_tracker",
    "late_poster",
    "late_publisher",
    "instagram_engine",
    "ad_copy_generator",
    "manual_cc",
    "scheduler",
    "test_harness",
})

KNOWN_CHANNELS: frozenset[str] = frozenset(DEFAULT_COOLDOWNS.keys())
PAID_SPEND_CHANNELS: frozenset[str] = frozenset({"meta_ads", "google_ads"})

VALID_INTENTS: frozenset[str] = frozenset({"commercial", "transactional", "internal"})

# Maven's 5 managed brands. CASL footer + sender identity flow from here.
BRAND_IDENTITY: dict[str, dict[str, str]] = {
    "oasis": {
        "business_name": "OASIS AI Solutions",
        "sender_name": "Conaugh McKenna",
        "business_address": "OASIS AI Solutions, Collingwood, ON, Canada",
        "from_display": "Conaugh McKenna — OASIS AI",
    },
    "conaugh": {
        "business_name": "Conaugh McKenna",
        "sender_name": "Conaugh McKenna",
        "business_address": "Collingwood, ON, Canada",
        "from_display": "Conaugh McKenna",
    },
    "propflow": {
        "business_name": "PropFlow",
        "sender_name": "PropFlow Team",
        "business_address": "PropFlow, Collingwood, ON, Canada",
        "from_display": "PropFlow",
    },
    "nostalgic": {
        "business_name": "Nostalgic Requests",
        "sender_name": "Nostalgic Requests",
        "business_address": "Nostalgic Requests, Collingwood, ON, Canada",
        "from_display": "Nostalgic Requests",
    },
    "sunbiz": {
        # Compliance-sensitive — never use "loan", only "advances/funding/capital".
        "business_name": "SunBiz Funding",
        "sender_name": "SunBiz Funding",
        "business_address": "SunBiz Funding, FL, USA",
        "from_display": "SunBiz Funding",
    },
}

DEFAULT_BRAND = "oasis"
RESERVATION_WINDOW_MINUTES = 30
DAILY_ALERT_THRESHOLD = 0.8
_DAILY_CAP_ALERTS_SENT: set[str] = set()


# ---- Env + DB ---------------------------------------------------------------

def load_env() -> dict[str, str]:
    env_path = PROJECT_ROOT / ".env.agents"
    if not env_path.exists():
        return {}
    env_vars: dict[str, str] = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env_vars[k.strip()] = v.strip()
    for k, v in env_vars.items():
        os.environ.setdefault(k, v)
    return env_vars


def get_supabase(env_vars: Optional[dict[str, str]] = None):
    env = env_vars if env_vars is not None else load_env()
    url = (env.get("MAVEN_SUPABASE_URL")
           or env.get("BRAVO_SUPABASE_URL")
           or os.environ.get("MAVEN_SUPABASE_URL")
           or os.environ.get("BRAVO_SUPABASE_URL"))
    key = (env.get("MAVEN_SUPABASE_SERVICE_ROLE_KEY")
           or env.get("BRAVO_SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("MAVEN_SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("BRAVO_SUPABASE_SERVICE_ROLE_KEY"))
    if not url or not key:
        raise RuntimeError(
            "Missing Supabase URL / service-role key in .env.agents — "
            "send_gateway cannot query the interaction ledger."
        )
    from supabase import create_client
    return create_client(url, key)


def _env_bool(env: dict[str, str], key: str, default: bool) -> bool:
    raw = (env.get(key) or os.environ.get(key) or "").strip().lower()
    if not raw:
        return default
    return raw not in {"0", "false", "no", "off"}


def _env_int(env: dict[str, str], key: str, default: int) -> int:
    raw = (env.get(key) or os.environ.get(key) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_ratio(env: dict[str, str], key: str, default: float) -> float:
    raw = (env.get(key) or os.environ.get(key) or "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    if value > 1:
        value /= 100.0
    return max(0.0, min(1.0, value))


def _killswitch_engaged(env: dict[str, str]) -> bool:
    """Either Maven's own killswitch or the Bravo-shared one fires the
    fail-closed dry-run short-circuit. Maven respects both because the
    multi-agent envelope is shared."""
    return _env_bool(env, "MAVEN_FORCE_DRY_RUN", False) or _env_bool(env, "BRAVO_FORCE_DRY_RUN", False)


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    text = str(value).replace("'", "''")
    return f"'{text}'"


def _json_sql_literal(value: Any) -> str:
    return _sql_literal(json.dumps(value or {}, separators=(",", ":"))) + "::jsonb"


def _extract_domain(to_email: Optional[str]) -> Optional[str]:
    normalized = (to_email or "").strip().lower()
    if "@" not in normalized:
        return None
    _, _, domain = normalized.rpartition("@")
    return domain or None


def _count_window(db: Any, channel: str, window_start: datetime) -> int:
    rows = (
        db.table("lead_interactions")
        .select("id", count="exact")
        .eq("channel", channel)
        .gte("created_at", window_start.isoformat())
        .execute()
    )
    return rows.count or 0


def _daily_alert_key(channel: str, day_start: datetime) -> str:
    return f"{day_start.date().isoformat()}:{channel}"


def _maybe_notify_daily_cap_threshold(channel: str, count: int, cap: Optional[int]) -> None:
    if cap is None or cap <= 0:
        return
    threshold = max(1, math.ceil(cap * DAILY_ALERT_THRESHOLD))
    if count < threshold:
        return
    day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    key = _daily_alert_key(channel, day_start)
    if key in _DAILY_CAP_ALERTS_SENT:
        return
    _DAILY_CAP_ALERTS_SENT.add(key)
    try:
        _telegram_notify(
            f"{channel} outbound is at {count}/{cap} today. "
            "Maven gateway is still open, but you're inside the red zone.",
            category="marketing",
        )
    except Exception:  # noqa: BLE001
        pass


# ---- CFO spend gate (Atlas pulse) -------------------------------------------

CFO_PULSE_PATH = Path(r"C:\Users\User\APPS\CFO-Agent\data\pulse\cfo_pulse.json")


def _read_cfo_pulse() -> Optional[dict]:
    """Read Atlas's spend pulse. Returns None if unavailable. Override the
    path with MAVEN_CFO_PULSE_PATH for tests."""
    override = os.environ.get("MAVEN_CFO_PULSE_PATH")
    path = Path(override) if override else CFO_PULSE_PATH
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


CFO_PULSE_STALE_HOURS = 24


def check_cfo_spend_gate(channel: str, brand: str, amount_usd: Optional[float] = None) -> dict:
    """Consult cfo_pulse.json. Fail-closed on missing, stale (>24h), closed,
    no-channel-approval, no-brand-approval, zero-budget, or amount-over-budget.

    Returns:
        {"allowed": bool, "reason": str, "approved_budget": float|None}
    """
    if channel not in PAID_SPEND_CHANNELS:
        return {"allowed": True, "reason": "non-paid channel", "approved_budget": None}

    pulse = _read_cfo_pulse()
    if pulse is None:
        return {
            "allowed": False,
            "reason": "cfo_pulse.json unavailable — Atlas spend gate fails closed",
            "approved_budget": None,
        }

    # Staleness check — pulse older than 24h means Atlas isn't actively
    # speaking. Fail closed; Atlas should refresh before any spend.
    pulse_ts_raw = pulse.get("updated_at") or (pulse.get("spend_gate") or {}).get("updated_at")
    if pulse_ts_raw:
        try:
            pulse_ts = datetime.fromisoformat(str(pulse_ts_raw).replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - pulse_ts).total_seconds() / 3600.0
            if age_hours > CFO_PULSE_STALE_HOURS:
                return {
                    "allowed": False,
                    "reason": f"cfo_pulse.json stale ({age_hours:.1f}h > {CFO_PULSE_STALE_HOURS}h) — refusing spend",
                    "approved_budget": None,
                }
        except (ValueError, TypeError):
            return {
                "allowed": False,
                "reason": f"cfo_pulse.json updated_at unparseable ({pulse_ts_raw!r})",
                "approved_budget": None,
            }

    spend_gate = pulse.get("spend_gate") or {}
    if spend_gate.get("status") != "open":
        return {
            "allowed": False,
            "reason": f"Atlas spend gate status={spend_gate.get('status', 'unknown')} (need 'open')",
            "approved_budget": None,
        }

    approvals = spend_gate.get("approvals") or {}
    channel_block = approvals.get(channel) or {}
    brand_block = channel_block.get(brand) or channel_block.get("*")
    if not brand_block:
        return {
            "allowed": False,
            "reason": f"no Atlas approval for channel={channel} brand={brand}",
            "approved_budget": None,
        }

    approved_budget = brand_block.get("daily_budget_usd")
    # Zero-budget is a hard block even if the channel/brand combo exists.
    if approved_budget is not None and approved_budget <= 0:
        return {
            "allowed": False,
            "reason": f"Atlas approved budget for {channel}/{brand} is $0.00 — spend disabled",
            "approved_budget": approved_budget,
        }
    if amount_usd is not None and approved_budget is not None and amount_usd > approved_budget:
        return {
            "allowed": False,
            "reason": (
                f"requested ${amount_usd:.2f} exceeds Atlas daily approval "
                f"${approved_budget:.2f} for {channel}/{brand}"
            ),
            "approved_budget": approved_budget,
        }

    return {"allowed": True, "reason": "ok", "approved_budget": approved_budget}


# ---- Marketing-specific content gates ---------------------------------------

import re as _re  # noqa: E402

_UTM_REQUIRED = ("utm_source", "utm_medium", "utm_campaign")
_URL_RE = _re.compile(r"https?://[^\s<>\"']+", _re.IGNORECASE)
_SUBJECT_SLOP_PATTERNS = [
    _re.compile(r"\bunlock the power of\b", _re.IGNORECASE),
    _re.compile(r"\bgame[- ]chang(er|ing)\b", _re.IGNORECASE),
    _re.compile(r"\brevolution(ize|ary|izing)\b", _re.IGNORECASE),
    _re.compile(r"\btake your .* to the next level\b", _re.IGNORECASE),
]


def check_utm_compliance(text: Optional[str]) -> dict:
    """Every outbound link in commercial copy must carry utm_source +
    utm_medium + utm_campaign. Returns {allowed, reason, missing_links}."""
    if not text:
        return {"allowed": True, "reason": "no body", "missing_links": []}
    missing = []
    for url in _URL_RE.findall(text):
        # Skip unsubscribe + transactional links — they intentionally don't
        # carry campaign UTMs.
        if "unsubscribe" in url.lower() or "/u/" in url.lower():
            continue
        # mailto: handled by the regex's http(s) anchor, so any URL captured here is web.
        url_lower = url.lower()
        if not all(tag in url_lower for tag in _UTM_REQUIRED):
            missing.append(url)
    if missing:
        return {
            "allowed": False,
            "reason": f"UTM tags missing on {len(missing)} link(s): "
                      + ", ".join(m[:80] for m in missing[:3]),
            "missing_links": missing,
        }
    return {"allowed": True, "reason": "ok", "missing_links": []}


def check_subject_slop(subject: Optional[str]) -> dict:
    """Subject-line slop detection — block 'Unlock the power of...',
    all-caps subjects, generic emoji-only opens."""
    if not subject:
        return {"allowed": True, "reason": "no subject"}
    s = subject.strip()
    # All-caps test (allow short codes like SALE but block whole-line ALL CAPS over 12 chars)
    letters = [c for c in s if c.isalpha()]
    if len(letters) >= 12 and all(c.isupper() for c in letters):
        return {"allowed": False, "reason": f"all-caps subject blocked: {s[:60]!r}"}
    # Emoji-only opener: if first 4 non-space chars are all non-alphanumeric
    head = s.lstrip()[:4]
    if head and not any(c.isalnum() for c in head):
        return {"allowed": False, "reason": f"emoji-only subject opener blocked: {s[:60]!r}"}
    for pat in _SUBJECT_SLOP_PATTERNS:
        if pat.search(s):
            return {"allowed": False, "reason": f"subject slop pattern matched: {pat.pattern!r}"}
    return {"allowed": True, "reason": "ok"}


def check_image_alt_text(attachments: Optional[list[dict]]) -> dict:
    """Every image attachment MUST have alt_text. ADA + anti-slop discipline.
    Non-image attachments are exempt (PDFs, .ics, etc.)."""
    if not attachments:
        return {"allowed": True, "reason": "no attachments"}
    missing = []
    for att in attachments:
        ctype = (att.get("content_type") or "").lower()
        if not ctype.startswith("image/"):
            continue
        if not (att.get("alt_text") or "").strip():
            missing.append(att.get("filename") or "<unnamed>")
    if missing:
        return {"allowed": False,
                "reason": f"{len(missing)} image(s) missing alt_text: {missing[:3]}"}
    return {"allowed": True, "reason": "ok"}


def check_creative_fatigue(db: Any, lead_id: Optional[str], channel: str,
                           creative_id: Optional[str], window_days: int = 14) -> dict:
    """Block sending the same creative_id to the same lead within window_days.
    Returns {allowed, reason}."""
    if not lead_id or not creative_id:
        return {"allowed": True, "reason": "no creative_id or lead_id; cannot check fatigue"}
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
        rows = (
            db.table("lead_interactions")
            .select("metadata, created_at")
            .eq("lead_id", lead_id)
            .eq("channel", channel)
            .gte("created_at", cutoff)
            .execute()
            .data
        ) or []
        for r in rows:
            md = r.get("metadata") or {}
            if isinstance(md, dict) and md.get("creative_id") == creative_id:
                return {
                    "allowed": False,
                    "reason": f"creative {creative_id} already sent to lead {lead_id} "
                              f"in last {window_days}d ({r.get('created_at')})",
                }
    except Exception as exc:  # noqa: BLE001
        return {"allowed": False, "reason": f"creative-fatigue check failed: {exc}"}
    return {"allowed": True, "reason": "ok"}


# ---- VIP segment override (env-driven) --------------------------------------

def is_vip_recipient(to_email: Optional[str], env: Optional[dict[str, str]] = None) -> bool:
    """VIP segment override — for flagged accounts, draft_critic non-ship
    verdicts return ship-with-warning instead of blocking. Defined by
    env var MAVEN_VIP_EMAILS (comma-sep) or by suffix MAVEN_VIP_DOMAINS.

    Source-of-truth precedence: .env.agents (the project's audited credential
    file) ALWAYS wins. os.environ is only consulted when .env.agents is silent
    on a key. This prevents an attacker who can set os.environ from elevating
    arbitrary recipients to VIP status against the operator's vetted list."""
    if not to_email:
        return False
    env = env if env is not None else load_env()
    # If the operator has set MAVEN_VIP_EMAILS in .env.agents at all (even
    # to empty string), treat that as authoritative. Only fall back to
    # os.environ when the key is absent from the audited file.
    raw_emails = env["MAVEN_VIP_EMAILS"] if "MAVEN_VIP_EMAILS" in env else os.environ.get("MAVEN_VIP_EMAILS", "")
    raw_domains = env["MAVEN_VIP_DOMAINS"] if "MAVEN_VIP_DOMAINS" in env else os.environ.get("MAVEN_VIP_DOMAINS", "")
    vip_emails = {e.strip().lower() for e in (raw_emails or "").split(",") if e.strip()}
    vip_domains = {d.strip().lower().lstrip("@") for d in (raw_domains or "").split(",") if d.strip()}
    norm = to_email.strip().lower()
    if norm in vip_emails:
        return True
    domain = norm.rpartition("@")[2]
    return domain in vip_domains


# ---- List-mode caps (≥50 recipients in <1h => list-mode) --------------------

LIST_MODE_THRESHOLD = 50
LIST_MODE_WINDOW_MINUTES = 60
LIST_MODE_HOURLY_CAP = 200  # 4× single-recipient hourly cap of 30 + slack
LIST_MODE_DAILY_CAP = 500


def check_list_mode_caps(db: Any, channel: str) -> dict:
    """When >= LIST_MODE_THRESHOLD sends in the trailing hour, treat the
    burst as a list/blast and apply the higher list-mode cap as the gate.
    Returns {allowed, reason, in_list_mode}."""
    try:
        window_start = datetime.now(timezone.utc) - timedelta(minutes=LIST_MODE_WINDOW_MINUTES)
        recent = _count_window(db, channel, window_start)
    except Exception as exc:  # noqa: BLE001
        return {"allowed": False, "reason": f"list-mode check failed: {exc}", "in_list_mode": False}
    if recent < LIST_MODE_THRESHOLD:
        return {"allowed": True, "reason": "single-recipient mode", "in_list_mode": False}
    if recent >= LIST_MODE_HOURLY_CAP:
        return {
            "allowed": False,
            "reason": f"list-mode hourly cap hit: {recent}/{LIST_MODE_HOURLY_CAP}",
            "in_list_mode": True,
        }
    return {"allowed": True, "reason": "in list-mode under cap", "in_list_mode": True}


# ---- Lead resolution --------------------------------------------------------

def resolve_lead_id(db, to_email: Optional[str], lead_id: Optional[str]) -> Optional[str]:
    if lead_id:
        return lead_id
    if not to_email:
        return None
    norm = to_email.strip().lower()
    try:
        existing = db.table("leads").select("id").eq("email", norm).limit(1).execute()
        if existing.data:
            return existing.data[0]["id"]
        now = datetime.now(timezone.utc).isoformat()
        created = db.table("leads").insert({
            "name": norm.split("@")[0],
            "email": norm,
            "status": "new",
            "source": "maven_gateway_autocreate",
            "created_at": now,
            "updated_at": now,
        }).execute()
        return created.data[0]["id"] if created.data else None
    except Exception as exc:  # noqa: BLE001
        print(f"[maven send_gateway] resolve_lead_id warning: {exc}", file=sys.stderr)
        return None


def get_bounce_rate(db, last_n_hours: int = 24) -> float:
    return _get_bounce_window_stats(db, last_n_hours=last_n_hours)["rate"]


def _get_bounce_window_stats(db, last_n_hours: int = 24) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=last_n_hours)
    env = load_env()
    minimum_sample = _env_int(env, "BOUNCE_MIN_SAMPLE_SIZE", 20)
    try:
        rows = (
            db.table("email_log")
            .select("status, sent_at")
            .gte("sent_at", window_start.isoformat())
            .execute()
            .data
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[maven send_gateway] bounce-rate query warning: {exc}", file=sys.stderr)
        return {"rate": 0.0, "failed": 0, "total": 0, "minimum_sample": minimum_sample}

    total = 0
    failed = 0
    for row in rows or []:
        status = (row.get("status") or "").strip().lower()
        if status not in {"sent", "failed"}:
            continue
        total += 1
        if status == "failed":
            failed += 1
    rate = (failed / total) if total >= minimum_sample and total > 0 else 0.0
    return {"rate": rate, "failed": failed, "total": total, "minimum_sample": minimum_sample}


def can_act_domain(
    db: Any,
    to_email: Optional[str],
    channel: str = "email",
    last_n_hours: int = 24,
) -> dict[str, Any]:
    env = load_env()
    cap = _env_int(env, "DOMAIN_DAILY_CAP", 5)  # marketing list — slightly looser than Bravo's 3
    domain = _extract_domain(to_email)
    if not domain or cap <= 0:
        return {"allowed": True, "reason": "ok", "domain": domain, "count": 0, "cap": cap}

    window_start = datetime.now(timezone.utc) - timedelta(hours=last_n_hours)
    try:
        leads = db.table("leads").select("id, email").execute().data or []
        lead_ids = {
            row.get("id")
            for row in leads
            if row.get("id") and (row.get("email") or "").strip().lower().endswith("@" + domain)
        }
        if not lead_ids:
            return {"allowed": True, "reason": "ok", "domain": domain, "count": 0, "cap": cap}

        recent = (
            db.table("lead_interactions")
            .select("lead_id, channel, created_at")
            .eq("channel", channel)
            .gte("created_at", window_start.isoformat())
            .execute()
            .data
        ) or []
        count = sum(1 for row in recent if row.get("lead_id") in lead_ids)
        if count >= cap:
            return {
                "allowed": False,
                "reason": f"domain cap hit: {count}/{cap} {channel} actions to @{domain} in the last 24h",
                "domain": domain,
                "count": count,
                "cap": cap,
            }
        return {"allowed": True, "reason": "ok", "domain": domain, "count": count, "cap": cap}
    except Exception as exc:  # noqa: BLE001
        print(
            f"[maven send_gateway] domain-cap query failed: {exc}; "
            "blocking send because the domain ledger is unavailable.",
            file=sys.stderr,
        )
        return {
            "allowed": False,
            "reason": f"domain cap ledger unavailable: {exc}",
            "domain": domain,
            "count": 0,
            "cap": cap,
        }


# ---- Idempotency core -------------------------------------------------------

def can_act(
    lead_id: Optional[str],
    channel: str,
    to_email: Optional[str] = None,
    cooldown_hours: Optional[int] = None,
    db: Any = None,
) -> dict:
    db = db if db is not None else get_supabase()
    now = datetime.now(timezone.utc)
    channel = channel.lower()

    env = load_env()
    result: dict[str, Any] = {
        "allowed": True,
        "reason": "ok",
        "last_action_at": None,
        "cooldown_until": None,
        "daily_count": 0,
        "daily_cap": DAILY_CAPS.get(channel),
        "hourly_count": 0,
        "hourly_cap": HOURLY_CAPS.get(channel),
        "domain_count": 0,
        "domain_cap": _env_int(env, "DOMAIN_DAILY_CAP", 5),
        "bounce_rate": 0.0,
    }

    # Gate 1: bounce-rate circuit breaker.
    try:
        bounce_stats = _get_bounce_window_stats(db, last_n_hours=24)
        result["bounce_rate"] = bounce_stats["rate"]
        bounce_threshold = _env_ratio(env, "BOUNCE_RATE_THRESHOLD", 0.03)
        if bounce_stats["total"] >= bounce_stats["minimum_sample"] and bounce_stats["rate"] > bounce_threshold:
            result.update(
                allowed=False,
                reason=(
                    "bounce-rate circuit breaker active: "
                    f"{bounce_stats['failed']}/{bounce_stats['total']} "
                    f"({bounce_stats['rate']:.1%}) over the last 24h"
                ),
            )
            return result
    except Exception as exc:  # noqa: BLE001
        result.update(allowed=False, reason=f"bounce-rate check failed: {exc}")
        return result

    # Gate 2: empty email
    if to_email is not None and not (to_email or "").strip():
        result.update(allowed=False, reason="empty recipient")
        return result

    # Gate 3: active cooldown on this lead+channel.
    if lead_id:
        last = None
        try:
            rows = (
                db.table("lead_interactions")
                .select("created_at, cooldown_until, type")
                .eq("lead_id", lead_id)
                .eq("channel", channel)
                .order("created_at", desc=True)
                .limit(10)
                .execute()
                .data
            )
        except Exception:
            try:
                rows = (
                    db.table("lead_interactions")
                    .select("created_at, type")
                    .eq("lead_id", lead_id)
                    .eq("channel", channel)
                    .order("created_at", desc=True)
                    .limit(10)
                    .execute()
                    .data
                )
                for r in rows or []:
                    r["cooldown_until"] = None
            except Exception as exc2:  # noqa: BLE001
                print(
                    f"[maven send_gateway] can_act cooldown query failed: {exc2}; "
                    "blocking send because the interaction ledger is unavailable.",
                    file=sys.stderr,
                )
                result.update(
                    allowed=False,
                    reason=f"cooldown ledger unavailable: {exc2}",
                )
                return result

        if rows:
            for candidate in rows:
                ctype = (candidate.get("type") or "").strip().lower()
                if ctype == f"{channel}_failed" or ctype == "email_failed":
                    continue
                if ctype == "reserving":
                    result.update(allowed=False, reason="concurrent send detected")
                    return result
                last = candidate
                break
        if rows and last:
            result["last_action_at"] = last.get("created_at")
            cu_raw = last.get("cooldown_until")
            if cu_raw:
                try:
                    cu = datetime.fromisoformat(cu_raw.replace("Z", "+00:00"))
                    result["cooldown_until"] = cu.isoformat()
                    if now < cu:
                        result.update(
                            allowed=False,
                            reason=f"cooldown active until {cu.isoformat()}",
                        )
                        return result
                except (ValueError, TypeError):
                    pass
            else:
                try:
                    created_at = datetime.fromisoformat(
                        (last.get("created_at") or "").replace("Z", "+00:00")
                    )
                    window_hours = (
                        cooldown_hours
                        if cooldown_hours is not None
                        else DEFAULT_COOLDOWNS.get(channel, 0)
                    )
                    if window_hours > 0:
                        implied_cu = created_at + timedelta(hours=window_hours)
                        result["cooldown_until"] = implied_cu.isoformat()
                        if now < implied_cu:
                            result.update(
                                allowed=False,
                                reason=(
                                    f"implied cooldown (legacy row, "
                                    f"{window_hours}h window) "
                                    f"until {implied_cu.isoformat()}"
                                ),
                            )
                            return result
                except (ValueError, TypeError):
                    pass

    # Gate 3b: hourly cap.
    hourly_cap = HOURLY_CAPS.get(channel)
    if hourly_cap is not None:
        try:
            count = _count_window(db, channel, now - timedelta(hours=1))
            result["hourly_count"] = count
            if count >= hourly_cap:
                result.update(
                    allowed=False,
                    reason=f"hourly cap hit: {count}/{hourly_cap} {channel} actions in the last hour",
                )
                return result
        except Exception as exc:  # noqa: BLE001
            result.update(allowed=False, reason=f"hourly cap ledger unavailable: {exc}")
            return result

    # Gate 4: daily cap.
    cap = DAILY_CAPS.get(channel)
    if cap is not None:
        try:
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            count = _count_window(db, channel, day_start)
            result["daily_count"] = count
            _maybe_notify_daily_cap_threshold(channel, count, cap)
            if count >= cap:
                result.update(
                    allowed=False,
                    reason=f"daily cap hit: {count}/{cap} {channel} actions today",
                )
                return result
        except Exception as exc:  # noqa: BLE001
            print(
                f"[maven send_gateway] can_act daily-cap query failed: {exc}; "
                "blocking send because the interaction ledger is unavailable.",
                file=sys.stderr,
            )
            result.update(
                allowed=False,
                reason=f"daily cap ledger unavailable: {exc}",
            )
            return result

    # Gate 5: domain cap.
    domain_check = can_act_domain(db=db, to_email=to_email, channel=channel)
    result["domain_count"] = domain_check.get("count", 0)
    result["domain_cap"] = domain_check.get("cap")
    if not domain_check["allowed"]:
        result.update(allowed=False, reason=domain_check["reason"])
        return result

    return result


# ---- Logging ----------------------------------------------------------------

def _mirror_email_log(
    db: Any,
    *,
    to_email: Optional[str],
    subject: Optional[str],
    content_preview: Optional[str],
    status: str,
    lead_id: Optional[str],
    error_message: Optional[str] = None,
) -> None:
    try:
        payload = {
            "to_email": to_email,
            "subject": subject or "",
            "body_preview": (content_preview or "")[:200],
            "status": status,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "lead_id": lead_id,
        }
        if error_message:
            payload["error_message"] = error_message
        db.table("email_log").insert(payload).execute()
    except Exception as exc:  # noqa: BLE001
        print(f"[maven send_gateway] email_log mirror warning: {exc}", file=sys.stderr)


def _touch_lead_last_contact(db: Any, lead_id: Optional[str], action_type: str) -> None:
    if lead_id and action_type in {"email_sent", "dm_sent", "late_post_sent"}:
        try:
            now = datetime.now(timezone.utc).isoformat()
            db.table("leads").update({
                "last_contacted_at": now,
                "updated_at": now,
            }).eq("id", lead_id).execute()
        except Exception as exc:  # noqa: BLE001
            print(f"[maven send_gateway] leads.last_contacted_at update warning: {exc}", file=sys.stderr)


def log_action(
    db,
    lead_id: Optional[str],
    channel: str,
    action_type: str,
    subject: Optional[str],
    content_preview: Optional[str],
    agent_source: str,
    cooldown_hours: Optional[int],
    metadata: Optional[dict] = None,
    to_email: Optional[str] = None,
) -> Optional[str]:
    now = datetime.now(timezone.utc)
    cooldown_until: Optional[str] = None
    if cooldown_hours and cooldown_hours > 0:
        cooldown_until = (now + timedelta(hours=cooldown_hours)).isoformat()

    row: dict[str, Any] = {
        "type": action_type,
        "channel": channel,
        "created_at": now.isoformat(),
    }
    if lead_id:
        row["lead_id"] = lead_id
    if subject:
        row["subject"] = subject[:500]
    if content_preview:
        row["content"] = content_preview[:1000]
    if metadata:
        row["metadata"] = metadata
    if agent_source:
        row["agent_source"] = agent_source
    if cooldown_until:
        row["cooldown_until"] = cooldown_until

    interaction_id: Optional[str] = None
    try:
        res = db.table("lead_interactions").insert(row).execute()
        interaction_id = res.data[0].get("id") if res.data else None
    except Exception:
        legacy_row = {k: v for k, v in row.items() if k not in {"cooldown_until", "agent_source"}}
        try:
            res = db.table("lead_interactions").insert(legacy_row).execute()
            interaction_id = res.data[0].get("id") if res.data else None
            print(
                "[maven send_gateway] degraded mode: migration columns not applied; "
                "cooldown_until + agent_source NOT persisted.",
                file=sys.stderr,
            )
        except Exception as exc2:  # noqa: BLE001
            print(
                f"[maven send_gateway] lead_interactions insert failed: {exc2}",
                file=sys.stderr,
            )

    if channel == "email" and action_type in {"email_sent", "email_reply"}:
        _mirror_email_log(
            db,
            to_email=to_email,
            subject=subject,
            content_preview=content_preview,
            status="sent" if action_type == "email_sent" else "received",
            lead_id=lead_id,
        )

    _touch_lead_last_contact(db, lead_id, action_type)
    return interaction_id


def _update_interaction_row(db: Any, interaction_id: str, payload: dict[str, Any]) -> bool:
    try:
        db.table("lead_interactions").update(payload).eq("id", interaction_id).execute()
        return True
    except Exception:
        reduced = {
            k: v for k, v in payload.items()
            if k not in {"cooldown_until", "agent_source", "metadata"}
        }
        try:
            db.table("lead_interactions").update(reduced).eq("id", interaction_id).execute()
            return True
        except Exception as exc2:  # noqa: BLE001
            print(f"[maven send_gateway] lead_interactions update failed: {exc2}", file=sys.stderr)
            return False


def _try_reserve_slot_via_rpc(
    db: Any,
    *,
    lead_id: str,
    channel: str,
    subject: Optional[str],
    content_preview: Optional[str],
    agent_source: str,
    cooldown_hours: Optional[int],
    metadata: Optional[dict[str, Any]],
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    cooldown_until = (
        (now + timedelta(hours=cooldown_hours)).isoformat()
        if cooldown_hours and cooldown_hours > 0 else None
    )
    reservation_metadata = dict(metadata or {})
    reservation_metadata.update({
        "reservation_status": "pending",
        "reserved_at": now.isoformat(),
    })
    marker = {
        "lead_id": lead_id,
        "channel": channel,
        "subject": (subject or "")[:500],
        "content_preview": (content_preview or "")[:1000],
        "agent_source": agent_source,
        "cooldown_until": cooldown_until,
        "metadata": reservation_metadata,
    }
    sql = (
        f"/* send_gateway_reserve:{json.dumps(marker, separators=(',', ':'))} */ "
        "WITH guard AS ("
        f"  SELECT pg_try_advisory_xact_lock(hashtext({_sql_literal(lead_id + '|' + channel)})) AS acquired"
        "), existing AS ("
        "  SELECT id FROM lead_interactions"
        f"  WHERE lead_id = {_sql_literal(lead_id)}"
        f"    AND channel = {_sql_literal(channel)}"
        "    AND type = 'reserving'"
        f"    AND created_at >= NOW() - INTERVAL '{RESERVATION_WINDOW_MINUTES} minutes'"
        "  ORDER BY created_at DESC"
        "  LIMIT 1"
        "), inserted AS ("
        "  INSERT INTO lead_interactions (lead_id, type, channel, created_at, subject, content, agent_source, cooldown_until, metadata)"
        "  SELECT "
        f"    {_sql_literal(lead_id)},"
        "    'reserving',"
        f"    {_sql_literal(channel)},"
        "    NOW(),"
        f"    {_sql_literal((subject or '')[:500])},"
        f"    {_sql_literal((content_preview or '')[:1000])},"
        f"    {_sql_literal(agent_source)},"
        f"    {_sql_literal(cooldown_until)},"
        f"    {_json_sql_literal(reservation_metadata)} "
        "  FROM guard"
        "  WHERE acquired AND NOT EXISTS (SELECT 1 FROM existing)"
        "  RETURNING id, created_at"
        ") "
        "SELECT "
        "  COALESCE((SELECT acquired FROM guard), false) AS lock_acquired, "
        "  (SELECT id FROM existing LIMIT 1) AS existing_reservation_id, "
        "  (SELECT id FROM inserted LIMIT 1) AS reservation_id, "
        "  (SELECT created_at FROM inserted LIMIT 1) AS reservation_created_at"
    )
    res = db.rpc("exec_sql", {"sql_query": sql}).execute()
    data = getattr(res, "data", None)
    if isinstance(data, dict):
        rows = data.get("rows") or []
    elif isinstance(data, list):
        rows = data
    else:
        rows = []
    row = rows[0] if rows else {}
    if not row.get("lock_acquired", True):
        return {"status": "blocked", "reason": "concurrent send detected"}
    if row.get("existing_reservation_id"):
        return {"status": "blocked", "reason": "concurrent send detected"}
    if row.get("reservation_id"):
        return {"status": "reserved", "reservation_id": row["reservation_id"], "mode": "rpc"}
    return {"status": "error", "reason": "reservation RPC returned no reservation_id"}


def reserve_send_slot(
    db: Any,
    *,
    lead_id: Optional[str],
    channel: str,
    subject: Optional[str],
    content_preview: Optional[str],
    agent_source: str,
    cooldown_hours: Optional[int],
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    reservation_metadata = dict(metadata or {})
    reservation_metadata.update({
        "reservation_status": "pending",
        "reserved_at": datetime.now(timezone.utc).isoformat(),
    })
    if lead_id and hasattr(db, "rpc"):
        try:
            return _try_reserve_slot_via_rpc(
                db,
                lead_id=lead_id,
                channel=channel,
                subject=subject,
                content_preview=content_preview,
                agent_source=agent_source,
                cooldown_hours=cooldown_hours,
                metadata=metadata,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[maven send_gateway] reservation RPC unavailable: {exc}", file=sys.stderr)

    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "type": "reserving",
        "channel": channel,
        "created_at": now.isoformat(),
        "subject": (subject or "")[:500],
        "content": (content_preview or "")[:1000],
        "agent_source": agent_source,
        "metadata": reservation_metadata,
    }
    if lead_id:
        payload["lead_id"] = lead_id
    if cooldown_hours and cooldown_hours > 0:
        payload["cooldown_until"] = (now + timedelta(hours=cooldown_hours)).isoformat()
    try:
        res = db.table("lead_interactions").insert(payload).execute()
        reservation_id = res.data[0].get("id") if res.data else None
        return {"status": "reserved", "reservation_id": reservation_id, "mode": "fallback"}
    except Exception:
        reduced = {
            k: v for k, v in payload.items()
            if k not in {"cooldown_until", "agent_source", "metadata"}
        }
        try:
            res = db.table("lead_interactions").insert(reduced).execute()
            reservation_id = res.data[0].get("id") if res.data else None
            return {"status": "reserved", "reservation_id": reservation_id, "mode": "fallback_legacy"}
        except Exception as exc2:  # noqa: BLE001
            return {"status": "error", "reason": f"reservation failed: {exc2}"}


def finalize_reserved_action(
    db: Any,
    *,
    interaction_id: Optional[str],
    lead_id: Optional[str],
    channel: str,
    action_type: str,
    subject: Optional[str],
    content_preview: Optional[str],
    agent_source: str,
    cooldown_hours: Optional[int],
    metadata: Optional[dict[str, Any]] = None,
    to_email: Optional[str] = None,
    error_message: Optional[str] = None,
) -> Optional[str]:
    if not interaction_id:
        return log_action(
            db=db,
            lead_id=lead_id,
            channel=channel,
            action_type=action_type,
            subject=subject,
            content_preview=content_preview,
            agent_source=agent_source,
            cooldown_hours=cooldown_hours,
            metadata=metadata,
            to_email=to_email,
        )

    now = datetime.now(timezone.utc)
    final_metadata = dict(metadata or {})
    final_metadata["reservation_status"] = "completed" if action_type.endswith("_sent") else "failed"
    if error_message:
        final_metadata["error_message"] = error_message
    payload: dict[str, Any] = {
        "type": action_type,
        "subject": (subject or "")[:500],
        "content": (content_preview or "")[:1000],
        "agent_source": agent_source,
        "metadata": final_metadata,
    }
    if action_type.endswith("_sent") and cooldown_hours and cooldown_hours > 0:
        payload["cooldown_until"] = (now + timedelta(hours=cooldown_hours)).isoformat()
    else:
        payload["cooldown_until"] = None
    ok = _update_interaction_row(db, interaction_id, payload)
    if not ok:
        return None
    if channel == "email":
        _mirror_email_log(
            db,
            to_email=to_email,
            subject=subject,
            content_preview=content_preview,
            status="sent" if action_type == "email_sent" else "failed",
            lead_id=lead_id,
            error_message=error_message,
        )
    if action_type.endswith("_sent"):
        _touch_lead_last_contact(db, lead_id, action_type)
    return interaction_id


def get_entity_history(db, lead_id: str, limit: int = 20) -> list[dict]:
    try:
        rows = (
            db.table("lead_interactions")
            .select("*")
            .eq("lead_id", lead_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
        )
        return rows or []
    except Exception as exc:  # noqa: BLE001
        print(f"[maven send_gateway] get_entity_history warning: {exc}", file=sys.stderr)
        return []


def get_daily_stats(db, channel: Optional[str] = None) -> dict:
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    result: dict[str, Any] = {
        "date": day_start.date().isoformat(),
        "channels": {},
        "hourly_counts": {},
        "bounce_rate": get_bounce_rate(db),
    }
    channels = [channel] if channel else list(KNOWN_CHANNELS)
    for c in channels:
        try:
            r_count = _count_window(db, c, day_start)
            result["channels"][c] = {"count": r_count, "cap": DAILY_CAPS.get(c)}
        except Exception as exc:  # noqa: BLE001
            result["channels"][c] = {"count": None, "cap": DAILY_CAPS.get(c), "error": str(exc)}
        try:
            result["hourly_counts"][c] = {
                "count": _count_window(db, c, now - timedelta(hours=1)),
                "cap": HOURLY_CAPS.get(c),
            }
        except Exception as exc:  # noqa: BLE001
            result["hourly_counts"][c] = {"count": None, "cap": HOURLY_CAPS.get(c), "error": str(exc)}
    result["total"] = sum((c["count"] or 0) for c in result["channels"].values())
    return result


# ---- Email sender (the real smtplib call) -----------------------------------

def _build_email_mime(
    gmail_address: str,
    brand: dict[str, str],
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str],
    intent: str,
    ics_content: Optional[str] = None,
    ics_filename: str = "meeting.ics",
    attachments: Optional[list[dict]] = None,
) -> MIMEMultipart:
    if intent != "internal":
        body_text = body_text + build_casl_footer(
            to_email,
            business_name=brand["business_name"],
            business_address=brand["business_address"],
            sender_name=brand["sender_name"],
        )
        if body_html:
            body_html = body_html + build_casl_footer_html(
                to_email,
                business_name=brand["business_name"],
                business_address=brand["business_address"],
                sender_name=brand["sender_name"],
            )

    outer = MIMEMultipart("mixed")
    outer["Subject"] = subject
    outer["From"] = f'{brand["from_display"]} <{gmail_address}>'
    outer["To"] = to_email
    if intent != "internal":
        add_list_unsubscribe_headers(outer, to_email)

    body_alt = MIMEMultipart("alternative")
    body_alt.attach(MIMEText(body_text, "plain"))
    if body_html:
        body_alt.attach(MIMEText(body_html, "html"))
    outer.attach(body_alt)

    if ics_content:
        ics_part = MIMEBase("text", "calendar", method="REQUEST")
        ics_part.set_payload(ics_content.encode("utf-8"))
        encoders.encode_base64(ics_part)
        ics_part.add_header("Content-Disposition", "attachment", filename=ics_filename)
        outer.attach(ics_part)

    for att in (attachments or []):
        fname = att.get("filename") or "attachment.bin"
        content_bytes = att.get("content")
        if not content_bytes:
            continue
        ctype = att.get("content_type") or "application/octet-stream"
        maintype, _, subtype = ctype.partition("/")
        if not subtype:
            maintype, subtype = "application", "octet-stream"
        part = MIMEBase(maintype, subtype)
        part.set_payload(content_bytes)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename=fname)
        outer.attach(part)

    return outer


def _send_email_smtp(
    env: dict[str, str],
    mime: MIMEMultipart,
    to_email: str,
) -> tuple[bool, Optional[str]]:
    gmail_user = env.get("GMAIL_USER") or env.get("GMAIL_ADDRESS", "")
    gmail_pass = env.get("GMAIL_APP_PASSWORD", "")
    if not gmail_user or not gmail_pass:
        return False, "GMAIL_USER/GMAIL_APP_PASSWORD missing in .env.agents"
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
            smtp.login(gmail_user, gmail_pass)
            smtp.sendmail(gmail_user, to_email, mime.as_string())
        return True, None
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed — rotate GMAIL_APP_PASSWORD"
    except smtplib.SMTPRecipientsRefused:
        return False, f"recipient refused by server: {to_email}"
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {e}"
    except Exception as e:  # noqa: BLE001
        return False, f"unexpected send error: {e}"


# ---- Public API -------------------------------------------------------------

def send(
    channel: str,
    agent_source: str,
    *,
    to_email: Optional[str] = None,
    lead_id: Optional[str] = None,
    subject: Optional[str] = None,
    body_text: Optional[str] = None,
    body_html: Optional[str] = None,
    template_vars: Optional[dict] = None,
    brand: str = DEFAULT_BRAND,
    intent: str = "commercial",
    cooldown_hours: Optional[int] = None,
    metadata: Optional[dict] = None,
    ics_content: Optional[str] = None,
    ics_filename: str = "meeting.ics",
    attachments: Optional[list[dict]] = None,
    spend_amount_usd: Optional[float] = None,
    dry_run: bool = False,
    db: Any = None,
) -> dict:
    """Single outbound chokepoint for Maven.

    Returns: {"status": "sent"|"blocked"|"suppressed"|"dry_run"|"error",
              "reason": str, "lead_id": str|None, "interaction_id": str|None,
              "cooldown_until": str|None, "daily_count": int|None}

    NEVER raises. Email channel runs the full send path; non-email channels
    are logged here and the engine performs the physical platform-API call.
    Paid-spend channels (meta_ads, google_ads) consult the CFO spend gate
    via cfo_pulse.json before approving.
    """
    channel = (channel or "").lower()
    if channel not in KNOWN_CHANNELS:
        return {"status": "error", "reason": f"unknown channel '{channel}'",
                "lead_id": lead_id, "interaction_id": None,
                "cooldown_until": None, "daily_count": None}
    if intent not in VALID_INTENTS:
        return {"status": "error", "reason": f"invalid intent '{intent}'",
                "lead_id": lead_id, "interaction_id": None,
                "cooldown_until": None, "daily_count": None}
    if not agent_source:
        return {"status": "error", "reason": "agent_source required",
                "lead_id": lead_id, "interaction_id": None,
                "cooldown_until": None, "daily_count": None}
    if brand not in BRAND_IDENTITY:
        return {"status": "error", "reason": f"unknown brand '{brand}' — "
                f"known: {sorted(BRAND_IDENTITY.keys())}",
                "lead_id": lead_id, "interaction_id": None,
                "cooldown_until": None, "daily_count": None}
    brand_cfg = BRAND_IDENTITY[brand]

    # ---- Per-channel required fields ----
    if channel == "email":
        if not to_email or not subject or not body_text:
            return {"status": "error",
                    "reason": "email channel requires to_email, subject, body_text",
                    "lead_id": lead_id, "interaction_id": None,
                    "cooldown_until": None, "daily_count": None}
        # Name sanitization — render-path defense against placeholder leaks.
        if template_vars:
            template_vars = sanitize_template_vars(template_vars, key="first_name")

    # ---- Multi-AI safety killswitch (highest precedence) ----
    # MAVEN_FORCE_DRY_RUN=1 (or BRAVO_FORCE_DRY_RUN=1) forces dry_run
    # regardless of caller. Short-circuits BEFORE the gateway touches
    # Supabase, the suppression list, the cooldown ledger, the daily cap,
    # the bounce-rate breaker, the CFO spend gate, or the draft critic.
    env = load_env()
    if _killswitch_engaged(env):
        return {"status": "dry_run",
                "reason": "MAVEN_FORCE_DRY_RUN/BRAVO_FORCE_DRY_RUN engaged — killswitch, no gates evaluated, no send",
                "lead_id": lead_id, "interaction_id": None,
                "cooldown_until": None, "daily_count": None}

    # ---- Paid-spend channels: route through CFO spend gate FIRST ----
    if channel in PAID_SPEND_CHANNELS and intent != "internal":
        gate = check_cfo_spend_gate(channel=channel, brand=brand, amount_usd=spend_amount_usd)
        if not gate["allowed"]:
            return {"status": "blocked",
                    "reason": f"CFO spend gate: {gate['reason']}",
                    "lead_id": lead_id, "interaction_id": None,
                    "cooldown_until": None, "daily_count": None}

    # ---- Resolve DB + lead ----
    try:
        db = db if db is not None else get_supabase(env)
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "reason": f"supabase unavailable: {exc}",
                "lead_id": lead_id, "interaction_id": None,
                "cooldown_until": None, "daily_count": None}

    lead_id = resolve_lead_id(db, to_email, lead_id)

    # ---- Gate 1: commercial suppression (email only) ----
    if intent == "commercial" and to_email and should_suppress(to_email):
        return {"status": "suppressed",
                "reason": f"{to_email} is on CASL suppression list",
                "lead_id": lead_id, "interaction_id": None,
                "cooldown_until": None, "daily_count": None}

    # ---- Gate 2 + 3: cooldown + daily cap (skipped for internal intent) ----
    if intent != "internal":
        check = can_act(
            lead_id=lead_id,
            channel=channel,
            to_email=to_email,
            cooldown_hours=cooldown_hours,
            db=db,
        )
        if not check["allowed"]:
            return {"status": "blocked",
                    "reason": check["reason"],
                    "lead_id": lead_id, "interaction_id": None,
                    "cooldown_until": check.get("cooldown_until"),
                    "daily_count": check.get("daily_count")}

    # ---- Dry run ----
    if dry_run:
        return {"status": "dry_run",
                "reason": "dry_run=True, nothing sent",
                "lead_id": lead_id, "interaction_id": None,
                "cooldown_until": None, "daily_count": None}

    # ---- Channel dispatch ----
    if channel == "email":
        gmail_user = env.get("GMAIL_USER") or env.get("GMAIL_ADDRESS", "")
        if not gmail_user:
            return {"status": "error",
                    "reason": "GMAIL_USER missing in .env.agents",
                    "lead_id": lead_id, "interaction_id": None,
                    "cooldown_until": None, "daily_count": None}

        effective_cooldown = (
            cooldown_hours
            if cooldown_hours is not None
            else DEFAULT_COOLDOWNS.get(channel, 0)
        )
        full_metadata = dict(metadata or {})
        full_metadata.update({
            "brand": brand,
            "intent": intent,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        })

        # ---- Marketing content gates (commercial intent only) ----
        if intent == "commercial":
            # UTM compliance: every link in the body needs utm_source/medium/campaign
            if _env_bool(env, "UTM_COMPLIANCE_ENABLED", True):
                utm_check = check_utm_compliance(body_text)
                if not utm_check["allowed"]:
                    return {"status": "blocked",
                            "reason": f"UTM compliance: {utm_check['reason']}",
                            "lead_id": lead_id, "interaction_id": None,
                            "cooldown_until": None, "daily_count": None}
            # Subject-line slop
            subj_check = check_subject_slop(subject)
            if not subj_check["allowed"]:
                return {"status": "blocked",
                        "reason": f"subject slop: {subj_check['reason']}",
                        "lead_id": lead_id, "interaction_id": None,
                        "cooldown_until": None, "daily_count": None}
            # Image alt-text presence
            alt_check = check_image_alt_text(attachments)
            if not alt_check["allowed"]:
                return {"status": "blocked",
                        "reason": f"image alt-text: {alt_check['reason']}",
                        "lead_id": lead_id, "interaction_id": None,
                        "cooldown_until": None, "daily_count": None}
            # Creative fatigue: don't ship the same creative_id twice in 14d
            creative_id = (metadata or {}).get("creative_id") if metadata else None
            if creative_id:
                fatigue_check = check_creative_fatigue(db, lead_id, channel, creative_id)
                if not fatigue_check["allowed"]:
                    return {"status": "blocked",
                            "reason": f"creative fatigue: {fatigue_check['reason']}",
                            "lead_id": lead_id, "interaction_id": None,
                            "cooldown_until": None, "daily_count": None}
            # List-mode caps when burst exceeds threshold
            list_check = check_list_mode_caps(db, channel)
            if not list_check["allowed"]:
                return {"status": "blocked",
                        "reason": list_check["reason"],
                        "lead_id": lead_id, "interaction_id": None,
                        "cooldown_until": None, "daily_count": None}

        # Fail-closed draft-critic gate (mirrors Bravo db37263 fix).
        if intent == "commercial" and _env_bool(env, "DRAFT_CRITIC_ENABLED", True):
            try:
                critic_result = critique_draft(
                    draft_subject=subject,  # type: ignore[arg-type]
                    draft_body=body_text,  # type: ignore[arg-type]
                    brand=brand,
                    intent=intent,
                    env=env,
                )
            except Exception as critic_exc:  # noqa: BLE001
                return {"status": "blocked",
                        "reason": f"draft_critic unavailable: {critic_exc}",
                        "lead_id": lead_id, "interaction_id": None,
                        "cooldown_until": None, "daily_count": None}
            verdict = critic_result.get("verdict")
            if verdict != "ship":
                # VIP override: ship-with-warning instead of block. Maven still
                # logs the critic verdict in metadata so post-send review can
                # surface the override.
                if is_vip_recipient(to_email, env):
                    full_metadata["critic_override"] = "vip"
                    full_metadata["critic_verdict"] = verdict
                    full_metadata["critic_reasons"] = (critic_result.get("reasons") or [])[:5]
                else:
                    reasons = critic_result.get("reasons") or []
                    reason_text = (
                        "; ".join(str(r) for r in reasons[:5])
                        or critic_result.get("notes")
                        or verdict
                        or "rejected"
                    )
                    return {"status": "blocked",
                            "reason": f"draft_critic rejected: {reason_text}",
                            "lead_id": lead_id, "interaction_id": None,
                            "cooldown_until": None, "daily_count": None}

        reservation = reserve_send_slot(
            db=db,
            lead_id=lead_id,
            channel=channel,
            subject=subject,
            content_preview=body_text,
            agent_source=agent_source,
            cooldown_hours=effective_cooldown,
            metadata=full_metadata,
        )
        if reservation["status"] == "blocked":
            return {"status": "blocked",
                    "reason": reservation["reason"],
                    "lead_id": lead_id, "interaction_id": None,
                    "cooldown_until": None, "daily_count": None}
        if reservation["status"] != "reserved":
            return {"status": "error",
                    "reason": reservation.get("reason", "reservation failed"),
                    "lead_id": lead_id, "interaction_id": None,
                    "cooldown_until": None, "daily_count": None}

        mime = _build_email_mime(
            gmail_address=gmail_user,
            brand=brand_cfg,
            to_email=to_email,  # type: ignore[arg-type]
            subject=subject,  # type: ignore[arg-type]
            body_text=body_text,  # type: ignore[arg-type]
            body_html=body_html,
            intent=intent,
            ics_content=ics_content,
            ics_filename=ics_filename,
            attachments=attachments,
        )
        ok, err = _send_email_smtp(env, mime, to_email)  # type: ignore[arg-type]
        if not ok:
            finalize_reserved_action(
                db=db,
                interaction_id=reservation.get("reservation_id"),
                lead_id=lead_id,
                channel=channel,
                action_type="email_failed",
                subject=subject,
                content_preview=body_text,
                agent_source=agent_source,
                cooldown_hours=None,
                metadata=full_metadata,
                to_email=to_email,
                error_message=err,
            )
            return {"status": "error", "reason": err,
                    "lead_id": lead_id, "interaction_id": None,
                    "cooldown_until": None, "daily_count": None}

        interaction_id = finalize_reserved_action(
            db=db,
            interaction_id=reservation.get("reservation_id"),
            lead_id=lead_id,
            channel=channel,
            action_type="email_sent",
            subject=subject,
            content_preview=body_text,
            agent_source=agent_source,
            cooldown_hours=effective_cooldown,
            metadata=full_metadata,
            to_email=to_email,
        )
        return {"status": "sent",
                "reason": "ok",
                "lead_id": lead_id,
                "interaction_id": interaction_id,
                "cooldown_until": (datetime.now(timezone.utc)
                                   + timedelta(hours=effective_cooldown)).isoformat()
                if effective_cooldown else None,
                "daily_count": None}

    # Non-email channels: log only. The engine performs the physical send.
    effective_cooldown = (
        cooldown_hours
        if cooldown_hours is not None
        else DEFAULT_COOLDOWNS.get(channel, 0)
    )
    full_metadata = dict(metadata or {})
    full_metadata.update({"brand": brand, "intent": intent})
    if spend_amount_usd is not None:
        full_metadata["spend_amount_usd"] = spend_amount_usd
    interaction_id = log_action(
        db=db,
        lead_id=lead_id,
        channel=channel,
        action_type=f"{channel}_sent",
        subject=subject,
        content_preview=body_text,
        agent_source=agent_source,
        cooldown_hours=effective_cooldown,
        metadata=full_metadata,
        to_email=to_email,
    )
    return {"status": "sent",
            "reason": f"non-email channel ({channel}): logged only, engine performs platform call",
            "lead_id": lead_id,
            "interaction_id": interaction_id,
            "cooldown_until": (datetime.now(timezone.utc)
                               + timedelta(hours=effective_cooldown)).isoformat()
            if effective_cooldown else None,
            "daily_count": None}


# ---- CLI --------------------------------------------------------------------

def _print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, default=str))


def _cmd_send(args) -> int:
    result = send(
        channel=args.channel,
        agent_source=args.agent_source,
        to_email=args.to,
        lead_id=args.lead_id,
        subject=args.subject,
        body_text=args.body,
        body_html=args.body_html,
        brand=args.brand,
        intent=args.intent,
        cooldown_hours=args.cooldown,
        spend_amount_usd=args.spend,
        dry_run=args.dry_run,
    )
    if args.output_json:
        _print_json(result)
    else:
        print(f"[maven send_gateway] status={result['status']} reason={result['reason']}")
        if result.get("interaction_id"):
            print(f"  interaction_id: {result['interaction_id']}")
        if result.get("cooldown_until"):
            print(f"  cooldown_until: {result['cooldown_until']}")
    return 0 if result["status"] in {"sent", "dry_run"} else 1


def _cmd_can_act(args) -> int:
    db = get_supabase()
    r = can_act(
        lead_id=args.lead_id,
        channel=args.channel,
        to_email=args.to,
        cooldown_hours=args.cooldown,
        db=db,
    )
    if args.output_json:
        _print_json(r)
    else:
        print(f"allowed: {r['allowed']}\nreason: {r['reason']}")
        if r.get("last_action_at"):
            print(f"last_action_at: {r['last_action_at']}")
        if r.get("cooldown_until"):
            print(f"cooldown_until: {r['cooldown_until']}")
        print(f"daily_count: {r.get('daily_count')}/{r.get('daily_cap')}")
    return 0 if r["allowed"] else 1


def _cmd_history(args) -> int:
    db = get_supabase()
    rows = get_entity_history(db, args.lead_id, limit=args.limit)
    if args.output_json:
        _print_json(rows)
        return 0
    if not rows:
        print(f"No history for lead {args.lead_id}.")
        return 0
    for r in rows:
        print(f"  {r.get('created_at','')[:19]}  "
              f"{r.get('channel','-'):10}  "
              f"{r.get('type','-'):14}  "
              f"src={r.get('agent_source','-')}  "
              f"subj={(r.get('subject') or '-')[:60]}")
    print(f"\n  {len(rows)} interaction(s).")
    return 0


def _cmd_stats(args) -> int:
    db = get_supabase()
    s = get_daily_stats(db, channel=args.channel)
    if args.output_json:
        _print_json(s)
    else:
        print(f"Daily stats ({s['date']}):")
        for ch, d in s["channels"].items():
            cap = d.get("cap")
            cnt = d.get("count")
            print(f"  {ch:12}  {cnt}/{cap if cap is not None else '-'}")
        print(f"Bounce rate (24h): {s['bounce_rate']:.1%}")
        print(f"  TOTAL        {s['total']}")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(
        prog="send_gateway.py",
        description="Maven outbound chokepoint: CASL + cooldown + daily cap + critic + CFO spend gate.",
    )
    p.add_argument("--json", dest="output_json", action="store_true")
    sub = p.add_subparsers(dest="command")

    ps = sub.add_parser("send", help="Send an outbound message or spend action")
    ps.add_argument("--channel", required=True, choices=sorted(KNOWN_CHANNELS))
    ps.add_argument("--agent-source", dest="agent_source", required=True)
    ps.add_argument("--to", default=None)
    ps.add_argument("--lead-id", dest="lead_id", default=None)
    ps.add_argument("--subject", default=None)
    ps.add_argument("--body", default=None)
    ps.add_argument("--body-html", dest="body_html", default=None)
    ps.add_argument("--brand", default=DEFAULT_BRAND, choices=sorted(BRAND_IDENTITY.keys()))
    ps.add_argument("--intent", default="commercial", choices=sorted(VALID_INTENTS))
    ps.add_argument("--cooldown", type=int, default=None)
    ps.add_argument("--spend", type=float, default=None,
                    help="Spend amount in USD (paid channels only)")
    ps.add_argument("--dry-run", dest="dry_run", action="store_true")

    pc = sub.add_parser("can-act", help="Check if a send is allowed")
    pc.add_argument("--lead-id", dest="lead_id", default=None)
    pc.add_argument("--channel", required=True, choices=sorted(KNOWN_CHANNELS))
    pc.add_argument("--to", default=None)
    pc.add_argument("--cooldown", type=int, default=None)

    ph = sub.add_parser("history", help="Recent interactions for a lead")
    ph.add_argument("--lead-id", dest="lead_id", required=True)
    ph.add_argument("--limit", type=int, default=20)

    pss = sub.add_parser("stats", help="Today's outbound counts by channel")
    pss.add_argument("--channel", default=None, choices=sorted(KNOWN_CHANNELS))

    args = p.parse_args()

    if args.command == "send":
        sys.exit(_cmd_send(args))
    elif args.command == "can-act":
        sys.exit(_cmd_can_act(args))
    elif args.command == "history":
        sys.exit(_cmd_history(args))
    elif args.command == "stats":
        sys.exit(_cmd_stats(args))
    else:
        p.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
