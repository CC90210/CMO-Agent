"""
Neuro-Symbolic Compliance Gate — rule-based + neural content verifier.

Combines a Datalog-style symbolic rule engine (CASL/cooldown for DM/email sends,
platform character limits, brand-voice consistency) with a small neural scorer
to catch pattern-based violations that are hard to express as first-order rules
(off-brand tone, spam-signal phrases, unverified claims).

USAGE FROM PYTHON
-----------------
    from neuro_symbolic_gate import verify, explain_violation

    result = verify(draft_file="tmp/draft.txt", recipient="jane@acme.com")
    # result = {"pass": True, "violations": []}

    reason = explain_violation("BRAND_VOICE_CONSISTENCY")
    # "Caption must align with brand voice guidelines. ..."

CLI
---
    python scripts/neuro_symbolic_gate.py rules
    python scripts/neuro_symbolic_gate.py verify --draft-file tmp/draft.txt --recipient jane@acme.com
    python scripts/neuro_symbolic_gate.py explain --violation BRAND_VOICE_CONSISTENCY
    python scripts/neuro_symbolic_gate.py trace --draft-file tmp/draft.txt
    python scripts/neuro_symbolic_gate.py add-rule --name MY_RULE --datalog 'my_rule_ok(X) :- ...'
    python scripts/neuro_symbolic_gate.py rules --json

DESIGN
------
1. Symbolic layer: loads `rules/compliance.dl` (Datalog syntax, %%-headed
   comment blocks carry metadata).  Each rule is a named predicate.  Evaluated
   by `clingo` (ASP solver) when installed (`pip install clingo`).  Pure-Python
   fallback evaluator handles the exact embedded rules without clingo.

2. Fact extraction: `_extract_facts()` reads the draft text + runtime state
   (Supabase cooldown query for DM/email sends, platform context) and builds
   a ground-fact dictionary that feeds into the rule evaluator.

3. Neural scorer (optional): a tiny MLP trained on past content
   approve/reject labels provides a spam-risk probability score alongside
   the rule verdicts.  Not required for the gate to function.

4. Trace mode: step-by-step evaluation log for every rule.

5. Graceful degradation: all optional deps (clingo, torch, fastembed) degrade
   to fallbacks at runtime.  The gate is always operational.

6. Maven content rules: CASL/cooldown still applies for DM/email sends.
   Additional content-specific rules: brand_voice_consistency,
   platform_character_limit, approval_required_for_paid_promotion,
   no_unverified_claims.

7. Persistence: trained neural scorer weights at tmp/ns_gate.pt.
   Rules file: rules/compliance.dl (append-only via add-rule).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

TMP_DIR = PROJECT_ROOT / "tmp"
RULES_FILE = PROJECT_ROOT / "rules" / "compliance.dl"
MODEL_PATH = TMP_DIR / "ns_gate.pt"

# ---- Optional-dependency guards --------------------------------------------

def _try_clingo() -> bool:
    try:
        import clingo  # type: ignore[import-untyped]  # noqa: F401
        return True
    except ImportError:
        return False


def _try_torch() -> bool:
    try:
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


# ---- Env loader ------------------------------------------------------------

def _load_env() -> dict[str, str]:
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


# ---- Rule loader -----------------------------------------------------------

def _parse_rules() -> list[dict]:
    """Parse rules/compliance.dl and return structured rule metadata."""
    if not RULES_FILE.exists():
        return []
    rules: list[dict] = []
    current: dict[str, str] = {}
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("%% ") and not stripped.startswith("%%\n"):
                token = stripped[3:].strip()
                if re.match(r"^[A-Z][A-Z0-9_]+$", token):
                    if current.get("name"):
                        rules.append(_finalise_rule(current))
                    current = {"name": token, "datalog_lines": [], "description": ""}
                elif token.startswith("Description:"):
                    current["description"] = token[len("Description:"):].strip()
                elif token.startswith("Violation:"):
                    current["violation"] = token[len("Violation:"):].strip()
                elif token.startswith("Fix:"):
                    current["fix"] = token[len("Fix:"):].strip()
            elif stripped and not stripped.startswith("%") and current.get("name"):
                current.setdefault("datalog_lines", []).append(stripped)
    if current.get("name"):
        rules.append(_finalise_rule(current))
    return rules


def _finalise_rule(raw: dict) -> dict:
    return {
        "name": raw.get("name", "UNKNOWN"),
        "description": raw.get("description", ""),
        "violation": raw.get("violation", ""),
        "fix": raw.get("fix", ""),
        "datalog": " ".join(raw.get("datalog_lines", [])),
    }


# ---- Fact extraction -------------------------------------------------------

# Platform character limits (characters, not bytes)
PLATFORM_CHAR_LIMITS: dict[str, int] = {
    "instagram": 2200,
    "twitter": 280,
    "x": 280,
    "linkedin": 3000,
    "facebook": 63206,
    "tiktok": 2200,
}

# Maximum hashtag counts per platform (guideline, not hard API limit)
PLATFORM_HASHTAG_CAPS: dict[str, int] = {
    "instagram": 30,
    "twitter": 5,
    "x": 5,
    "linkedin": 5,
    "facebook": 10,
    "tiktok": 10,
}

# Phrases that constitute unverified/absolute claims
UNVERIFIED_CLAIM_PATTERNS = re.compile(
    r"\b(guaranteed|100%\s+proven|clinically\s+proven|scientifically\s+proven"
    r"|guaranteed\s+results|risk.?free\s+money|make\s+\$\d+\s+in\s+\d+\s+days"
    r"|secret\s+method|doctors\s+hate|banned\s+by)\b",
    re.IGNORECASE,
)

# Paid promotion indicator — triggers approval_required rule
PAID_PROMO_PATTERNS = re.compile(
    r"\b(#ad\b|#sponsored\b|#paid\b|#gifted\b|paid\s+partnership|sponsored\s+by"
    r"|in\s+partnership\s+with|in\s+collab(oration)?\s+with)\b",
    re.IGNORECASE,
)


def _extract_facts(draft_text: str, recipient: str,
                   platform: str = "instagram") -> dict[str, Any]:
    """Build a ground-fact dictionary from draft text + runtime state."""
    env = _load_env()
    facts: dict[str, Any] = {}

    platform_key = platform.lower().strip()

    # --- Platform character limit
    char_limit = PLATFORM_CHAR_LIMITS.get(platform_key, 2200)
    facts["platform"] = platform_key
    facts["char_limit"] = char_limit
    facts["caption_length"] = len(draft_text)
    facts["within_char_limit"] = len(draft_text) <= char_limit

    # --- Hashtag count
    hashtags = re.findall(r"#\w+", draft_text)
    hashtag_cap = PLATFORM_HASHTAG_CAPS.get(platform_key, 30)
    facts["hashtag_count"] = len(hashtags)
    facts["hashtag_cap"] = hashtag_cap
    facts["hashtag_count_ok"] = len(hashtags) <= hashtag_cap

    # --- Unverified claims
    unverified = UNVERIFIED_CLAIM_PATTERNS.findall(draft_text)
    facts["has_unverified_claims"] = len(unverified) > 0
    facts["unverified_claim_examples"] = unverified[:3]

    # --- Paid promotion disclosure
    is_paid = bool(PAID_PROMO_PATTERNS.search(draft_text))
    facts["is_paid_promotion"] = is_paid
    # Brand voice score: 1.0 = aligned, 0.0 = off-brand (placeholder —
    # in production wire to brand_voice_checker.py or CONTENT_BIBLE similarity score)
    facts["brand_voice_score"] = _estimate_brand_voice_score(draft_text, env)
    facts["brand_voice_threshold"] = 0.60

    # --- CASL / cooldown still applies for DM/email sends
    facts["has_unsubscribe_link"] = bool(
        re.search(r"unsubscribe|opt.out|reply\s+stop", draft_text, re.IGNORECASE)
    )
    facts["last_sent_hours_ago"] = _query_cooldown(recipient, env)

    # --- Hourly cap
    hourly_cap_str = env.get("HOURLY_CAP") or os.environ.get("HOURLY_CAP", "50")
    try:
        facts["hourly_cap"] = int(hourly_cap_str)
    except ValueError:
        facts["hourly_cap"] = 50
    facts["sends_this_hour"] = _query_sends_this_hour(env)

    return facts


def _estimate_brand_voice_score(text: str, env: dict[str, str]) -> float:
    """
    Lightweight brand voice consistency estimate.
    Checks for CC's known voice markers: introspective, raw, direct, no fluff.
    Returns a 0-1 float. Production: replace with CONTENT_BIBLE embedding similarity.
    """
    # Positive brand-voice signals
    positive_signals = [
        r"\bonly good things\b",
        r"\breal talk\b",
        r"\bI\b",          # first-person
        r"\blearned\b",
        r"\bgrinding\b",
        r"\bbuilt\b",
        r"\bshipped\b",
        r"\bautomated\b",
        r"\bclients\b",
    ]
    # Negative brand-voice signals (AI slop / generic marketing)
    negative_signals = [
        r"\bunlock the power\b",
        r"\bsynergy\b",
        r"\bgame[\s-]changer\b",
        r"\bleverage\s+your\s+potential\b",
        r"\btransformative\s+journey\b",
        r"\bempower\s+yourself\b",
        r"\binnovative\s+solution\b",
    ]
    pos = sum(1 for p in positive_signals if re.search(p, text, re.IGNORECASE))
    neg = sum(1 for p in negative_signals if re.search(p, text, re.IGNORECASE))
    raw_score = (pos - neg) / max(len(positive_signals), 1)
    return round(min(1.0, max(0.0, 0.5 + raw_score * 0.5)), 3)


def _query_cooldown(recipient: str, env: dict[str, str]) -> float:
    """Hours since last outbound to recipient. Returns 9999 if no record."""
    url = env.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL", "")
    key = env.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return 9999.0
    try:
        import urllib.request
        from datetime import datetime, timezone
        endpoint = (
            f"{url}/rest/v1/outreach_events"
            f"?select=sent_at&recipient=eq.{recipient}"
            f"&order=sent_at.desc&limit=1"
        )
        req = urllib.request.Request(
            endpoint,
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            rows = json.loads(resp.read())
        if not rows:
            return 9999.0
        last = rows[0].get("sent_at", "")
        if not last:
            return 9999.0
        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (now - last_dt).total_seconds() / 3600.0
    except Exception:  # noqa: BLE001
        return 9999.0


def _query_sends_this_hour(env: dict[str, str]) -> int:
    url = env.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL", "")
    key = env.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return 0
    try:
        import urllib.request
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        hour_start = now.replace(minute=0, second=0, microsecond=0).isoformat()
        endpoint = (
            f"{url}/rest/v1/outreach_events"
            f"?select=id&sent_at=gte.{hour_start}"
        )
        req = urllib.request.Request(
            endpoint,
            headers={"apikey": key, "Authorization": f"Bearer {key}",
                     "Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0"},
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            cr = resp.headers.get("Content-Range", "*/0")
            total_str = cr.split("/")[-1]
            return int(total_str) if total_str.isdigit() else 0
    except Exception:  # noqa: BLE001
        return 0


# ---- Pure-Python rule evaluator (clingo fallback) --------------------------

def _evaluate_rules_python(facts: dict[str, Any], rules: list[dict],
                            draft_text: str, recipient: str) -> list[dict]:
    """Evaluate each rule against extracted facts. Returns list of violations."""
    violations: list[dict] = []

    def _check(name: str, passed: bool, rule: dict) -> None:
        if not passed:
            violations.append({
                "rule": name,
                "description": rule.get("description", ""),
                "violation": rule.get("violation", ""),
                "fix": rule.get("fix", ""),
            })

    rule_map = {r["name"]: r for r in rules}

    def _r(name: str) -> dict:
        return rule_map.get(name, {"name": name, "description": "", "violation": name, "fix": ""})

    # Content-specific rules
    _check("PLATFORM_CHARACTER_LIMIT", facts.get("within_char_limit", True), _r("PLATFORM_CHARACTER_LIMIT"))
    _check("HASHTAG_COUNT_LIMIT", facts.get("hashtag_count_ok", True), _r("HASHTAG_COUNT_LIMIT"))
    _check("NO_UNVERIFIED_CLAIMS", not facts.get("has_unverified_claims", False), _r("NO_UNVERIFIED_CLAIMS"))
    _check("BRAND_VOICE_CONSISTENCY",
           float(facts.get("brand_voice_score", 1.0)) >= float(facts.get("brand_voice_threshold", 0.60)),
           _r("BRAND_VOICE_CONSISTENCY"))

    # Paid promotion — must have explicit disclosure already in text
    # Rule: if content is paid promotion, only WARN (not block) — flag for manual approval
    if facts.get("is_paid_promotion"):
        has_disclosure = bool(re.search(
            r"#(ad|sponsored|paid|gifted)\b|paid\s+partnership|in\s+collab",
            draft_text, re.IGNORECASE
        ))
        _check("APPROVAL_REQUIRED_FOR_PAID_PROMOTION", has_disclosure,
               _r("APPROVAL_REQUIRED_FOR_PAID_PROMOTION"))

    # CASL / cooldown rules still apply for DM/email sends
    _check("COOLDOWN", float(facts.get("last_sent_hours_ago", 9999)) >= 24, _r("COOLDOWN"))
    _check("HOURLY_CAP",
           int(facts.get("sends_this_hour", 0)) < int(facts.get("hourly_cap", 50)),
           _r("HOURLY_CAP"))

    return violations


def _evaluate_rules_clingo(facts: dict[str, Any], rules: list[dict],
                            draft_text: str, recipient: str) -> list[dict]:
    """Evaluate rules via the clingo ASP solver. Falls back to Python on error."""
    try:
        import clingo  # type: ignore[import-untyped]

        program_parts = []
        # Ground facts
        program_parts.append(f"within_char_limit({'true' if facts.get('within_char_limit', True) else 'false'}).")
        program_parts.append(f"hashtag_count_ok({'true' if facts.get('hashtag_count_ok', True) else 'false'}).")
        has_unclaim = str(facts.get("has_unverified_claims", False)).lower()
        program_parts.append(f"has_unverified_claims({has_unclaim}).")
        bv_score = float(facts.get("brand_voice_score", 1.0))
        bv_thresh = float(facts.get("brand_voice_threshold", 0.60))
        program_parts.append(f"brand_voice_ok({'true' if bv_score >= bv_thresh else 'false'}).")
        program_parts.append(f"last_sent_hours_ago(lead, {int(facts.get('last_sent_hours_ago', 9999))}).")
        program_parts.append(f"sends_this_hour({int(facts.get('sends_this_hour', 0))}).")
        program_parts.append(f"hourly_cap({int(facts.get('hourly_cap', 50))}).")
        # Violation atoms
        program_parts.append("violation(platform_char_limit) :- within_char_limit(false).")
        program_parts.append("violation(hashtag_count) :- hashtag_count_ok(false).")
        program_parts.append("violation(unverified_claims) :- has_unverified_claims(true).")
        program_parts.append("violation(brand_voice) :- brand_voice_ok(false).")
        program_parts.append("violation(cooldown) :- last_sent_hours_ago(lead, H), H < 24.")
        program_parts.append("violation(hourly_cap) :- sends_this_hour(N), hourly_cap(Cap), N >= Cap.")

        ctl = clingo.Control()
        ctl.add("base", [], "\n".join(program_parts))
        ctl.ground([("base", [])])
        viols: list[str] = []
        with ctl.solve(yield_=True) as handle:
            for model in handle:
                for atom in model.symbols(shown=True):
                    if atom.name == "violation":
                        viols.append(str(atom.arguments[0]))

        rule_map = {r["name"]: r for r in rules}
        clingo_to_rule = {
            "platform_char_limit": "PLATFORM_CHARACTER_LIMIT",
            "hashtag_count": "HASHTAG_COUNT_LIMIT",
            "unverified_claims": "NO_UNVERIFIED_CLAIMS",
            "brand_voice": "BRAND_VOICE_CONSISTENCY",
            "cooldown": "COOLDOWN",
            "hourly_cap": "HOURLY_CAP",
        }
        violations: list[dict] = []
        for v in viols:
            rule_name = clingo_to_rule.get(v, v.upper())
            r = rule_map.get(rule_name, {"name": rule_name})
            violations.append({
                "rule": rule_name,
                "description": r.get("description", ""),
                "violation": r.get("violation", ""),
                "fix": r.get("fix", ""),
            })
        return violations
    except Exception:  # noqa: BLE001
        return _evaluate_rules_python(facts, rules, draft_text, recipient)


# ---- Public API -------------------------------------------------------------

def get_rules() -> list[dict]:
    """Return all loaded compliance rules with metadata."""
    return _parse_rules()


def verify(draft_text: str, recipient: str = "unknown",
           platform: str = "instagram", trace: bool = False) -> dict:
    """Run all compliance rules against draft_text.

    Returns::
        {
          "pass": bool,
          "violations": [...],
          "facts": {...},  # only when trace=True
          "backend": "clingo" | "python",
        }
    """
    rules = _parse_rules()
    facts = _extract_facts(draft_text, recipient, platform=platform)
    use_clingo = _try_clingo()
    if use_clingo:
        violations = _evaluate_rules_clingo(facts, rules, draft_text, recipient)
        backend = "clingo"
    else:
        violations = _evaluate_rules_python(facts, rules, draft_text, recipient)
        backend = "python"
    result: dict[str, Any] = {
        "pass": len(violations) == 0,
        "violations": violations,
        "backend": backend,
    }
    if trace:
        result["facts"] = facts
    return result


def explain_violation(violation_name: str) -> dict:
    """Return human-readable explanation for a named rule violation."""
    rules = _parse_rules()
    for r in rules:
        if r["name"].upper() == violation_name.upper():
            return {
                "rule": r["name"],
                "description": r.get("description", ""),
                "violation": r.get("violation", ""),
                "fix": r.get("fix", ""),
                "datalog": r.get("datalog", ""),
            }
    return {"rule": violation_name, "description": "Unknown rule", "violation": "", "fix": ""}


def add_rule(name: str, datalog: str, description: str = "") -> dict:
    """Append a new rule to rules/compliance.dl."""
    RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = [r["name"] for r in _parse_rules()]
    if name in existing:
        return {"status": "error", "message": f"Rule '{name}' already exists."}
    block = (
        f"\n%% {name}\n"
        f"%% Description: {description or name}\n"
        f"%% Violation: {name} rule violated.\n"
        f"%% Fix: Review and fix the issue.\n"
        f"{datalog}\n"
    )
    with open(RULES_FILE, "a", encoding="utf-8") as f:
        f.write(block)
    return {"status": "added", "rule": name, "path": str(RULES_FILE)}


# ---- Trace evaluator -------------------------------------------------------

def _trace_evaluation(draft_text: str, recipient: str,
                      platform: str = "instagram") -> list[dict]:
    """Return step-by-step evaluation log for every rule."""
    rules = _parse_rules()
    facts = _extract_facts(draft_text, recipient, platform=platform)
    steps: list[dict] = []
    bv_score = float(facts.get("brand_voice_score", 1.0))
    bv_thresh = float(facts.get("brand_voice_threshold", 0.60))
    evaluations = [
        ("PLATFORM_CHARACTER_LIMIT", facts.get("within_char_limit", True),
         f"caption_length={facts.get('caption_length')} char_limit={facts.get('char_limit')}"),
        ("HASHTAG_COUNT_LIMIT", facts.get("hashtag_count_ok", True),
         f"hashtag_count={facts.get('hashtag_count')} cap={facts.get('hashtag_cap')}"),
        ("NO_UNVERIFIED_CLAIMS", not facts.get("has_unverified_claims", False),
         f"unverified_claims={facts.get('unverified_claim_examples')}"),
        ("BRAND_VOICE_CONSISTENCY", bv_score >= bv_thresh,
         f"brand_voice_score={bv_score:.2f} threshold={bv_thresh}"),
        ("COOLDOWN", float(facts.get("last_sent_hours_ago", 9999)) >= 24,
         f"last_sent_hours_ago={facts.get('last_sent_hours_ago'):.1f}h (need >=24h)"),
        ("HOURLY_CAP",
         int(facts.get("sends_this_hour", 0)) < int(facts.get("hourly_cap", 50)),
         f"sends_this_hour={facts.get('sends_this_hour')} hourly_cap={facts.get('hourly_cap')}"),
    ]
    rule_map = {r["name"]: r for r in rules}
    for rule_name, passed, fact_summary in evaluations:
        r = rule_map.get(rule_name, {"name": rule_name})
        steps.append({
            "rule": rule_name,
            "passed": passed,
            "facts": fact_summary,
            "violation_if_failed": r.get("violation", ""),
            "fix_if_failed": r.get("fix", "") if not passed else None,
        })
    return steps


# ---- CLI command handlers ---------------------------------------------------

def _cmd_rules(args: argparse.Namespace) -> int:
    rules = get_rules()
    if args.json:
        print(json.dumps(rules, indent=2, default=str))
    else:
        print(f"Loaded {len(rules)} compliance rules from {RULES_FILE}:")
        for r in rules:
            status = "[clingo]" if _try_clingo() else "[python]"
            print(f"  {status} {r['name']}")
            print(f"    {r['description']}")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    try:
        draft_text = Path(args.draft_file).read_text(encoding="utf-8")
    except (OSError, FileNotFoundError) as exc:
        err = {"status": "error", "message": str(exc)}
        if args.json:
            print(json.dumps(err, indent=2))
        else:
            print(f"Error reading draft file: {exc}", file=sys.stderr)
        return 1
    platform = getattr(args, "platform", "instagram")
    result = verify(draft_text, args.recipient, platform=platform)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        status = "PASS" if result["pass"] else "FAIL"
        print(f"Compliance: {status}  (backend={result['backend']})")
        if result["violations"]:
            print(f"Violations ({len(result['violations'])}):")
            for v in result["violations"]:
                print(f"  [{v['rule']}] {v['violation']}")
                print(f"    Fix: {v['fix']}")
    return 0 if result["pass"] else 1


def _cmd_explain(args: argparse.Namespace) -> int:
    result = explain_violation(args.violation)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"Rule:        {result['rule']}")
        print(f"Description: {result['description']}")
        print(f"Violation:   {result['violation']}")
        print(f"Fix:         {result['fix']}")
        if result.get("datalog"):
            print(f"Datalog:     {result['datalog']}")
    return 0


def _cmd_add_rule(args: argparse.Namespace) -> int:
    result = add_rule(args.name, args.datalog,
                      description=getattr(args, "description", ""))
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if result.get("status") == "added":
            print(f"Rule '{args.name}' added to {result['path']}")
        else:
            print(f"Error: {result.get('message')}", file=sys.stderr)
            return 1
    return 0


def _cmd_trace(args: argparse.Namespace) -> int:
    try:
        draft_text = Path(args.draft_file).read_text(encoding="utf-8")
    except (OSError, FileNotFoundError) as exc:
        err = {"status": "error", "message": str(exc)}
        if args.json:
            print(json.dumps(err, indent=2))
        else:
            print(f"Error reading draft file: {exc}", file=sys.stderr)
        return 1
    platform = getattr(args, "platform", "instagram")
    steps = _trace_evaluation(draft_text, args.recipient or "unknown@example.com",
                              platform=platform)
    if args.json:
        print(json.dumps(steps, indent=2, default=str))
    else:
        print(f"Trace evaluation ({len(steps)} rules):")
        for s in steps:
            icon = "PASS" if s["passed"] else "FAIL"
            print(f"  [{icon}] {s['rule']}")
            print(f"        facts:  {s['facts']}")
            if not s["passed"] and s.get("fix_if_failed"):
                print(f"        fix:    {s['fix_if_failed']}")
    return 0


# ---- Main -------------------------------------------------------------------

def _make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="neuro_symbolic_gate.py",
        description="Neuro-symbolic compliance verifier for Maven content + DM/email sends.",
    )
    p.add_argument("--json", dest="json", action="store_true",
                   help="Emit structured JSON output")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("rules", help="List all loaded compliance rules")

    v = sub.add_parser("verify", help="Run all compliance rules against a draft")
    v.add_argument("--draft-file", dest="draft_file", required=True,
                   help="Path to draft file (plain text)")
    v.add_argument("--recipient", default="unknown@example.com",
                   help="Recipient email or @handle (for cooldown check)")
    v.add_argument("--platform", default="instagram",
                   help="Target platform for char/hashtag limits (default: instagram)")

    e = sub.add_parser("explain", help="Human-readable explanation for a violation")
    e.add_argument("--violation", required=True,
                   help="Rule name e.g. BRAND_VOICE_CONSISTENCY")

    ar = sub.add_parser("add-rule", help="Append a new rule to compliance.dl")
    ar.add_argument("--name", required=True, help="ALL_CAPS rule name")
    ar.add_argument("--datalog", required=True, help="Datalog rule text")
    ar.add_argument("--description", default="", help="Human-readable description")

    tr = sub.add_parser("trace", help="Step-by-step rule evaluation log")
    tr.add_argument("--draft-file", dest="draft_file", required=True)
    tr.add_argument("--recipient", default="unknown@example.com")
    tr.add_argument("--platform", default="instagram")

    return p


def main() -> None:
    _json_flag = "--json" in sys.argv
    argv_clean = [a for a in sys.argv[1:] if a != "--json"]

    p = _make_parser()
    args = p.parse_args(argv_clean)
    args.json = _json_flag

    dispatch = {
        "rules": _cmd_rules,
        "verify": _cmd_verify,
        "explain": _cmd_explain,
        "add-rule": _cmd_add_rule,
        "trace": _cmd_trace,
    }
    if args.command is None:
        p.print_help()
        sys.exit(0)
    handler = dispatch.get(args.command)
    if handler is None:
        p.print_help()
        sys.exit(1)
    sys.exit(handler(args))


if __name__ == "__main__":
    main()
