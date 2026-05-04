"""
pulse_publish.py — Atomic, schema-validated writer for Maven's cmo_pulse.json.

Per ../Business-Empire-Agent/brain/AGENT_ORCHESTRATION.md: cmo_pulse.json is
one-way (Maven writes; Bravo + Atlas read). Direct edits forbidden.

Auto mode pulls live data from:
  - Maven's own content pipeline state (drafts/scheduled/published counts)
  - Maven's ad-platform reporters (when token_expiry_check confirms tokens are live)

Auto mode aborts WITHOUT writing if no live data is available — never publishes
a half-formed pulse.

Usage:
  python scripts/pulse_publish.py refresh \\
    --drafts 3 --scheduled 7 --published-7d 2 \\
    --meta-campaigns 0 --google-campaigns 0 \\
    --ad-spend-30d-cad 0

  python scripts/pulse_publish.py auto       # cron-friendly
  python scripts/pulse_publish.py validate
  python scripts/pulse_publish.py status [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
PULSE_PATH = REPO_ROOT / "data" / "pulse" / "cmo_pulse.json"
SCHEMA_VERSION = "1.1"

REQUIRED_TOP_LEVEL = {"agent", "version", "updated_at", "status", "content_pipeline", "ad_performance"}
REQUIRED_CONTENT_PIPELINE = {"drafts", "scheduled", "published_7d"}
REQUIRED_AD_PERFORMANCE = {"meta_active_campaigns", "google_active_campaigns", "total_ad_spend_30d_cad"}


def _now_iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_pulse() -> dict[str, Any] | None:
    if not PULSE_PATH.exists():
        return None
    try:
        return json.loads(PULSE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing_top = REQUIRED_TOP_LEVEL - set(payload.keys())
    if missing_top:
        errors.append(f"missing top-level fields: {sorted(missing_top)}")
    pipeline = payload.get("content_pipeline", {})
    if isinstance(pipeline, dict):
        missing_pipe = REQUIRED_CONTENT_PIPELINE - set(pipeline.keys())
        if missing_pipe:
            errors.append(f"missing content_pipeline fields: {sorted(missing_pipe)}")
    else:
        errors.append("content_pipeline must be an object")
    ads = payload.get("ad_performance", {})
    if isinstance(ads, dict):
        missing_ads = REQUIRED_AD_PERFORMANCE - set(ads.keys())
        if missing_ads:
            errors.append(f"missing ad_performance fields: {sorted(missing_ads)}")
    else:
        errors.append("ad_performance must be an object")
    if "updated_at" in payload:
        try:
            ts = payload["updated_at"]
            if isinstance(ts, str):
                normalized = ts[:-1] + "+00:00" if ts.endswith("Z") else ts
                datetime.fromisoformat(normalized)
        except (ValueError, TypeError):
            errors.append("updated_at must be ISO 8601")
    return errors


def _atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, path)


def _try_live_data() -> dict[str, Any]:
    """Pull current values from Maven's content + ad reporters when wired.

    Currently no live readers expose clean snapshot interfaces — the
    `content_pipeline` and `ad_performance` dicts must come from CLI flags
    in `refresh` mode. When `scripts/content_pipeline.py snapshot --json`
    and `scripts/performance_reporter.py snapshot --json` land, wire them
    here. Until then, auto mode pulls only the cross-agent fields.
    """
    live: dict[str, Any] = {}
    cfo_pulse_path = REPO_ROOT.parent / "APPS" / "CFO-Agent" / "data" / "pulse" / "cfo_pulse.json"
    if not cfo_pulse_path.exists():
        return live
    try:
        cfo = json.loads(cfo_pulse_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return live
    spend_cap = None
    spend_gate = cfo.get("spend_gate")
    if isinstance(spend_gate, dict):
        spend_cap = spend_gate.get("approved_ad_spend_monthly_cap_cad")
    if spend_cap is not None:
        live["spend_cap_from_atlas_cad"] = spend_cap
    return live


def cmd_refresh(args: argparse.Namespace) -> int:
    existing = _read_pulse() or {}
    payload = dict(existing)
    payload["agent"] = "maven"
    payload["version"] = SCHEMA_VERSION
    payload["updated_at"] = _now_iso_utc()
    payload["status"] = args.status or existing.get("status", "OPERATIONAL")
    if args.session_note:
        payload["session_note"] = args.session_note

    pipeline = dict(existing.get("content_pipeline", {}))
    if args.drafts is not None:
        pipeline["drafts"] = args.drafts
    if args.scheduled is not None:
        pipeline["scheduled"] = args.scheduled
    if args.published_7d is not None:
        pipeline["published_7d"] = args.published_7d
    pipeline.setdefault("drafts", existing.get("content_pipeline", {}).get("drafts", 0))
    pipeline.setdefault("scheduled", existing.get("content_pipeline", {}).get("scheduled", 0))
    pipeline.setdefault("published_7d", existing.get("content_pipeline", {}).get("published_7d", 0))
    pipeline.setdefault("formats", existing.get("content_pipeline", {}).get("formats", ["video", "image", "text", "email"]))
    payload["content_pipeline"] = pipeline

    ads = dict(existing.get("ad_performance", {}))
    if args.meta_campaigns is not None:
        ads["meta_active_campaigns"] = args.meta_campaigns
    if args.google_campaigns is not None:
        ads["google_active_campaigns"] = args.google_campaigns
    if args.ad_spend_30d_cad is not None:
        ads["total_ad_spend_30d_cad"] = args.ad_spend_30d_cad
    if args.avg_roas is not None:
        ads["avg_roas"] = args.avg_roas
    ads.setdefault("meta_active_campaigns", 0)
    ads.setdefault("google_active_campaigns", 0)
    ads.setdefault("total_ad_spend_30d_cad", 0)
    ads.setdefault("avg_roas", existing.get("ad_performance", {}).get("avg_roas"))
    ads.setdefault("avg_cac_cad", existing.get("ad_performance", {}).get("avg_cac_cad"))
    ads.setdefault("best_performing_creative", existing.get("ad_performance", {}).get("best_performing_creative"))
    payload["ad_performance"] = ads

    if "funnel_metrics" not in payload:
        payload["funnel_metrics"] = existing.get("funnel_metrics", {
            "visitors_30d": 0, "leads_30d": 0, "conversion_rate": None, "email_list_size": 0
        })

    cross_agent = _try_live_data()
    if cross_agent:
        payload.update(cross_agent)

    errors = validate(payload)
    if errors:
        print("VALIDATION FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(json.dumps(payload, indent=2, default=str))
        print("\n(dry-run — pulse not written)", file=sys.stderr)
        return 0

    _atomic_write(PULSE_PATH, payload)
    print(f"OK — cmo_pulse refreshed at {payload['updated_at']}")
    print(f"  drafts:        {pipeline['drafts']}")
    print(f"  scheduled:     {pipeline['scheduled']}")
    print(f"  published_7d:  {pipeline['published_7d']}")
    print(f"  meta_active:   {ads['meta_active_campaigns']}")
    print(f"  google_active: {ads['google_active_campaigns']}")
    print(f"  ad_spend_30d:  ${ads['total_ad_spend_30d_cad']:,.2f} CAD")
    if "spend_cap_from_atlas_cad" in payload:
        print(f"  atlas_spend_cap: ${payload['spend_cap_from_atlas_cad']:,.2f} CAD")
    return 0


def cmd_auto(args: argparse.Namespace) -> int:
    """Cron-friendly: refresh cross-agent fields only (content + ad data needs CLI flags
    until snapshot interfaces land in content_pipeline.py / performance_reporter.py)."""
    existing = _read_pulse() or {}
    cross_agent = _try_live_data()
    if not cross_agent:
        print("ERROR — no cross-agent live data available; refusing to publish stale pulse", file=sys.stderr)
        return 3
    payload = dict(existing)
    payload.update(cross_agent)
    payload["agent"] = "maven"
    payload["version"] = SCHEMA_VERSION
    payload["updated_at"] = _now_iso_utc()
    errors = validate(payload)
    if errors:
        print("VALIDATION FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 2
    _atomic_write(PULSE_PATH, payload)
    print(f"OK — cmo_pulse auto-refreshed at {payload['updated_at']} (cross-agent fields: {sorted(cross_agent.keys())})")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    payload = _read_pulse()
    if payload is None:
        print(f"ERROR — pulse not readable at {PULSE_PATH}", file=sys.stderr)
        return 2
    errors = validate(payload)
    if args.json:
        print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
    else:
        print("VALID" if not errors else "INVALID:\n" + "\n".join(f"  - {e}" for e in errors))
    return 0 if not errors else 1


def cmd_status(args: argparse.Namespace) -> int:
    payload = _read_pulse()
    if payload is None:
        print(f"ERROR — pulse not readable at {PULSE_PATH}", file=sys.stderr)
        return 2
    updated = payload.get("updated_at", "?")
    age_hours: float | None = None
    try:
        ts = updated[:-1] + "+00:00" if isinstance(updated, str) and updated.endswith("Z") else updated
        dt = datetime.fromisoformat(ts) if isinstance(ts, str) else None
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    except (ValueError, TypeError):
        pass
    pipeline = payload.get("content_pipeline", {})
    ads = payload.get("ad_performance", {})
    summary = {
        "updated_at": updated,
        "age_hours": round(age_hours, 1) if age_hours is not None else None,
        "drafts": pipeline.get("drafts"),
        "scheduled": pipeline.get("scheduled"),
        "published_7d": pipeline.get("published_7d"),
        "meta_active_campaigns": ads.get("meta_active_campaigns"),
        "google_active_campaigns": ads.get("google_active_campaigns"),
        "total_ad_spend_30d_cad": ads.get("total_ad_spend_30d_cad"),
        "spend_cap_from_atlas_cad": payload.get("spend_cap_from_atlas_cad"),
    }
    if args.json:
        print(json.dumps(summary, indent=2, default=str))
    else:
        for k, v in summary.items():
            print(f"  {k}: {v}")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Maven cmo_pulse atomic publisher.")
    sub = p.add_subparsers(dest="command", required=True)

    pr = sub.add_parser("refresh", help="Update cmo_pulse with manual values")
    pr.add_argument("--drafts", type=int, default=None)
    pr.add_argument("--scheduled", type=int, default=None)
    pr.add_argument("--published-7d", type=int, default=None)
    pr.add_argument("--meta-campaigns", type=int, default=None)
    pr.add_argument("--google-campaigns", type=int, default=None)
    pr.add_argument("--ad-spend-30d-cad", type=float, default=None)
    pr.add_argument("--avg-roas", type=float, default=None)
    pr.add_argument("--status", type=str, default=None)
    pr.add_argument("--session-note", type=str, default=None)
    pr.add_argument("--dry-run", action="store_true")

    sub.add_parser("auto", help="Cron-friendly: refresh cross-agent fields (Atlas spend cap)")

    pv = sub.add_parser("validate", help="Validate current pulse against schema")
    pv.add_argument("--json", action="store_true")

    ps = sub.add_parser("status", help="Show current pulse summary + freshness")
    ps.add_argument("--json", action="store_true")

    args = p.parse_args()
    handlers = {"refresh": cmd_refresh, "auto": cmd_auto, "validate": cmd_validate, "status": cmd_status}
    sys.exit(handlers[args.command](args))


if __name__ == "__main__":
    main()
