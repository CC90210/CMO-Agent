"""Daily 06:00 Maven briefing — aggregates overnight signal into one prep table.

Output:
  state/snapshots/cmo_briefing_<YYYY-MM-DD>.json
  state/snapshots/latest_cmo_briefing.json

Sections:
  generated_at, day_of_week
  target_mrr_2026_05_30 (CC's growth ceiling)
  pulse         — three-agent state (CEO directive / CFO spend gate / CMO own)
  content       — Late inventory + cmo_pulse content_pipeline
  ads           — Meta + Google snapshot from cmo_pulse
  brand_health  — followers, engagement, draft_critic block rate
  blockers      — open + blocked tasks from state_manager
  substrate     — V6.7 substrate health (DBs exist? index fresh? mirrors in sync?)

CLI:
  python scripts/snapshots/cmo_briefing_snapshot.py [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SNAPSHOT_DIR = PROJECT_ROOT / "state" / "snapshots"
STATE_DB = PROJECT_ROOT / "state" / "empire_state.db"
INDEX_DB = PROJECT_ROOT / "state" / "memory_index.db"
CMO_PULSE = PROJECT_ROOT / "data" / "pulse" / "cmo_pulse.json"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _read_json(path: str | Path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {e}"}


def gather_pulse(allow_missing: bool = False) -> dict:
    home = Path(os.environ.get("USERPROFILE") or os.path.expanduser("~"))
    bravo = Path(os.environ.get("BRAVO_REPO") or (home / "Business-Empire-Agent"))
    atlas = Path(os.environ.get("ATLAS_REPO") or (home / "APPS" / "CFO-Agent"))
    ceo_path = bravo / "data" / "pulse" / "ceo_pulse.json"
    cfo_path = atlas / "data" / "pulse" / "cfo_pulse.json"
    missing = [str(p) for p in (ceo_path, cfo_path, CMO_PULSE) if not p.exists()]
    if missing and not allow_missing:
        raise FileNotFoundError(
            "Required pulse files missing: " + ", ".join(missing)
            + ". Set BRAVO_REPO / ATLAS_REPO env vars to override the discovery,"
              " or pass --allow-missing-pulse to degrade silently."
        )
    return {
        "ceo": _read_json(ceo_path),
        "cfo": _read_json(cfo_path),
        "cmo": _read_json(CMO_PULSE),
    }


def gather_content() -> dict:
    cmo = _read_json(CMO_PULSE)
    pipeline = cmo.get("content_pipeline", {}) if isinstance(cmo, dict) else {}
    late_inventory: dict = {}
    try:
        r = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "late_tool.py"), "posts", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0 and r.stdout.strip():
            late_inventory = json.loads(r.stdout)
        else:
            late_inventory = {"_error": (r.stderr or "no output").strip()[:200]}
    except subprocess.TimeoutExpired:
        late_inventory = {"_error": "late_tool timeout (>30s)"}
    except Exception as e:
        late_inventory = {"_error": f"{type(e).__name__}: {e}"}
    return {"pipeline": pipeline, "late_inventory": late_inventory}


def gather_ads() -> dict:
    cmo = _read_json(CMO_PULSE)
    return cmo.get("ad_performance", {}) if isinstance(cmo, dict) else {}


def gather_brand_health() -> dict:
    cmo = _read_json(CMO_PULSE)
    return cmo.get("brand_health", {}) if isinstance(cmo, dict) else {}


def gather_blockers() -> dict:
    if not STATE_DB.exists():
        return {"_error": "state DB missing"}
    conn = sqlite3.connect(f"file:{STATE_DB.as_posix()}?mode=ro", uri=True, timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, bucket, title, owner, status, updated_at "
            "FROM active_task WHERE status IN ('open','blocked') "
            "ORDER BY priority ASC, updated_at DESC LIMIT 25"
        ).fetchall()
        return {
            "open_count":    sum(1 for r in rows if r["status"] == "open"),
            "blocked_count": sum(1 for r in rows if r["status"] == "blocked"),
            "items": [dict(r) for r in rows],
        }
    finally:
        conn.close()


def gather_substrate() -> dict:
    """V6.7 substrate health gauge — every missing piece is a red flag."""
    return {
        "state_db_exists":  STATE_DB.exists(),
        "state_db_kb":      round(STATE_DB.stat().st_size / 1024, 1) if STATE_DB.exists() else 0,
        "index_db_exists":  INDEX_DB.exists(),
        "index_db_kb":      round(INDEX_DB.stat().st_size / 1024, 1) if INDEX_DB.exists() else 0,
        "exec_guard_mode":  os.environ.get("EMPIRE_HOOK_EXEC_GUARD", "report"),
        "killswitch_dry_run": bool(os.environ.get("MAVEN_FORCE_DRY_RUN")),
    }


def build(allow_missing_pulse: bool = False) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "generated_at":  now.isoformat(timespec="seconds"),
        "day_of_week":   now.strftime("%A"),
        "target_mrr_2026_05_30_usd": 5000,
        "pulse":         gather_pulse(allow_missing=allow_missing_pulse),
        "content":       gather_content(),
        "ads":           gather_ads(),
        "brand_health":  gather_brand_health(),
        "blockers":      gather_blockers(),
        "substrate":     gather_substrate(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily CMO briefing snapshot")
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout")
    parser.add_argument("--allow-missing-pulse", action="store_true",
                        help="Degrade gracefully when sibling repo pulses are missing")
    args = parser.parse_args()

    try:
        snap = build(allow_missing_pulse=args.allow_missing_pulse)
    except FileNotFoundError as e:
        print(f"FATAL  {e}", file=sys.stderr)
        return 2
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    day = snap["generated_at"][:10]
    dated = SNAPSHOT_DIR / f"cmo_briefing_{day}.json"
    latest = SNAPSHOT_DIR / "latest_cmo_briefing.json"
    payload = json.dumps(snap, indent=2)
    dated.write_text(payload, encoding="utf-8")
    latest.write_text(payload, encoding="utf-8")

    if args.json:
        print(payload)
    else:
        print(f"OK  {dated.relative_to(PROJECT_ROOT)}")
        print(f"OK  {latest.relative_to(PROJECT_ROOT)}")
        print(f"    pulse={len(snap['pulse'])} blockers={snap['blockers'].get('blocked_count', '?')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
