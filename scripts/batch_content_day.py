"""
Batch Content Day Scheduler — Schedule 7 content pieces for the week ahead.

Part of CC's Content Day workflow:
  1. CC films 7 pieces on Content Day (drops raw into media/raw/)
  2. video_editor.py edits each (silence removal, filler cuts, captions, music)
  3. video_editor.py sends to Telegram for CC's review
  4. THIS SCRIPT schedules all 7 across the next week via Zernio API

It writes each post to Supabase content_calendar AND schedules it through Zernio
in a single pass. Supports text-only posts and media (video/image) posts.

Usage:
    # Schedule from a content manifest (recommended)
    python scripts/batch_content_day.py schedule --manifest data/content_day/2026-04-28.json

    # Schedule from a directory of processed videos
    python scripts/batch_content_day.py schedule --dir media/exports/batch_2026-04-28

    # Quick-schedule 7 text posts from a JSON array
    python scripts/batch_content_day.py schedule --posts posts.json

    # Preview the schedule without publishing
    python scripts/batch_content_day.py preview --manifest data/content_day/2026-04-28.json

    # Check status of the current week's scheduled posts
    python scripts/batch_content_day.py status

    # Generate a blank manifest template for Content Day
    python scripts/batch_content_day.py template [--date 2026-04-28]

Keys required: LATE_API_KEY, BRAVO_SUPABASE_URL, BRAVO_SUPABASE_SERVICE_ROLE_KEY
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent

# ── Constants ─────────────────────────────────────────────────────────────────

TIMEZONE = "America/New_York"

# Default weekly posting schedule: day_offset -> (hour, minute, pillar, platforms)
# Day 0 = the day AFTER Content Day (e.g., if Content Day is Sunday, Day 0 = Monday)
DEFAULT_SCHEDULE = [
    {"day_offset": 0, "time": "08:00", "pillar": "ceo_log",       "platforms": ["linkedin", "twitter"]},
    {"day_offset": 1, "time": "12:00", "pillar": "the_becoming",   "platforms": ["instagram", "tiktok", "threads"]},
    {"day_offset": 2, "time": "09:00", "pillar": "the_journey",    "platforms": ["instagram", "youtube", "tiktok"]},
    {"day_offset": 3, "time": "11:00", "pillar": "ai_oracle",      "platforms": ["linkedin", "twitter", "threads"]},
    {"day_offset": 4, "time": "08:30", "pillar": "the_becoming",   "platforms": ["instagram", "tiktok"]},
    {"day_offset": 5, "time": "10:00", "pillar": "ceo_log",        "platforms": ["instagram", "linkedin", "twitter", "tiktok", "threads", "facebook"]},
    {"day_offset": 6, "time": "18:00", "pillar": "the_journey",    "platforms": ["instagram", "tiktok", "youtube"]},
]

# Zernio platform name -> connected account ID (populated at runtime)
_account_map: dict[str, str] = {}

# Platform character limits
PLATFORM_LIMITS = {
    "twitter": 280,
    "x": 280,
    "threads": 500,
    "instagram": 2200,
    "linkedin": 3000,
    "tiktok": 4000,
    "facebook": 63206,
    "youtube": 5000,
    "googlebusiness": 1500,
}


# ── Credential loading ────────────────────────────────────────────────────────

def load_env() -> dict[str, str]:
    """Load .env.agents from project root."""
    env_path = PROJECT_ROOT / ".env.agents"
    if not env_path.exists():
        print(f"ERROR: {env_path} not found", file=sys.stderr)
        sys.exit(1)
    env_vars: dict[str, str] = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env_vars[key.strip()] = value.strip()
    return env_vars


def get_supabase_client(env_vars: dict[str, str]):
    """Create a Supabase client for tracking."""
    try:
        from supabase import create_client
    except ImportError:
        print("WARNING: supabase package not installed, skipping calendar tracking", file=sys.stderr)
        return None
    url = env_vars.get("BRAVO_SUPABASE_URL")
    key = env_vars.get("BRAVO_SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("WARNING: Missing Supabase credentials, skipping calendar tracking", file=sys.stderr)
        return None
    return create_client(url, key)


# ── Zernio API helpers ────────────────────────────────────────────────────────

def zernio_request(method: str, path: str, api_key: str,
                   data: dict | None = None, timeout: int = 30) -> dict:
    """Make a raw HTTP request to the Zernio API."""
    base = "https://zernio.com/api/v1"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{base}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        raise RuntimeError(f"Zernio API [{e.code}]: {error_body[:300]}")


def fetch_account_map(api_key: str) -> dict[str, str]:
    """Fetch connected Zernio accounts and build platform -> account_id map."""
    global _account_map
    if _account_map:
        return _account_map

    result = zernio_request("GET", "/accounts", api_key)
    accounts = result.get("accounts", result) if isinstance(result, dict) else result

    mapping: dict[str, str] = {}
    if isinstance(accounts, list):
        for acc in accounts:
            platform = (acc.get("platform") or "").lower().strip()
            acc_id = acc.get("_id") or acc.get("id") or ""
            if platform and acc_id:
                mapping[platform] = acc_id
    # Alias: twitter ↔ x
    if "twitter" in mapping and "x" not in mapping:
        mapping["x"] = mapping["twitter"]
    if "x" in mapping and "twitter" not in mapping:
        mapping["twitter"] = mapping["x"]

    _account_map = mapping
    return _account_map


def schedule_post(api_key: str, content: str, platforms: list[dict],
                  scheduled_for: str, media_urls: list[str] | None = None) -> dict:
    """Schedule a single post via Zernio API."""
    payload: dict = {
        "content": content,
        "platforms": platforms,
        "scheduledFor": scheduled_for,
        "timezone": TIMEZONE,
    }
    if media_urls:
        payload["mediaUrls"] = media_urls

    return zernio_request("POST", "/posts", api_key, data=payload)


# ── Content manifest ──────────────────────────────────────────────────────────

def generate_template(start_date: str | None = None) -> dict:
    """Generate a blank content day manifest template."""
    if start_date:
        base_date = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        # Next Monday
        today = datetime.now()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        base_date = today + timedelta(days=days_until_monday)

    pieces = []
    for i, slot in enumerate(DEFAULT_SCHEDULE):
        post_date = base_date + timedelta(days=slot["day_offset"])
        hour, minute = map(int, slot["time"].split(":"))
        post_dt = post_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

        pieces.append({
            "piece_number": i + 1,
            "pillar": slot["pillar"],
            "scheduled_for": post_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "platforms": slot["platforms"],
            "hook": "",
            "body": "",
            "caption_overrides": {},
            "media_path": "",
            "media_urls": [],
            "notes": "",
        })

    manifest = {
        "content_day": datetime.now().strftime("%Y-%m-%d"),
        "week_starting": base_date.strftime("%Y-%m-%d"),
        "timezone": TIMEZONE,
        "brand": "cc_personal",
        "total_pieces": len(pieces),
        "pieces": pieces,
    }
    return manifest


def load_manifest(manifest_path: str) -> dict:
    """Load a content day manifest from JSON file."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Platform caption builder ─────────────────────────────────────────────────

def build_platform_caption(body: str, platform: str,
                           caption_overrides: dict | None = None) -> str:
    """Build platform-specific caption, respecting character limits."""
    if caption_overrides and platform in caption_overrides:
        text = caption_overrides[platform]
    else:
        text = body

    limit = PLATFORM_LIMITS.get(platform, 5000)
    if len(text) > limit:
        text = text[:limit - 3].rstrip() + "..."

    return text


# ── Core scheduling logic ────────────────────────────────────────────────────

def schedule_batch(manifest: dict, api_key: str, supabase_client,
                   dry_run: bool = False, as_json: bool = False) -> list[dict]:
    """Schedule all pieces from a content day manifest."""
    account_map = fetch_account_map(api_key)
    results = []

    pieces = manifest.get("pieces", [])
    brand = manifest.get("brand", "cc_personal")

    if not as_json:
        print(f"\n{'=' * 60}")
        print(f"  Batch Content Day Scheduler")
        print(f"  Week: {manifest.get('week_starting', 'unknown')}")
        print(f"  Pieces: {len(pieces)}")
        print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        print(f"{'=' * 60}\n")

    for piece in pieces:
        piece_num = piece.get("piece_number", "?")
        pillar = piece.get("pillar", "unknown")
        scheduled_for = piece.get("scheduled_for", "")
        platforms = piece.get("platforms", [])
        hook = piece.get("hook", "")
        body = piece.get("body", "")
        media_urls = piece.get("media_urls", [])
        caption_overrides = piece.get("caption_overrides", {})

        if not body and not hook:
            result = {
                "piece": piece_num,
                "status": "skipped",
                "reason": "No content (hook and body are empty)",
            }
            results.append(result)
            if not as_json:
                print(f"  [{piece_num}] SKIP -- no content")
            continue

        # Build the post content
        content = f"{hook}\n\n{body}" if hook and body else (hook or body)

        # Build platform targets
        platform_targets = []
        skipped_platforms = []
        for plat in platforms:
            acc_id = account_map.get(plat)
            if acc_id:
                platform_targets.append({"platform": plat, "accountId": acc_id})
            else:
                skipped_platforms.append(plat)

        if not platform_targets:
            result = {
                "piece": piece_num,
                "status": "failed",
                "reason": f"No connected accounts for platforms: {platforms}",
            }
            results.append(result)
            if not as_json:
                print(f"  [{piece_num}] FAIL -- no connected accounts for {platforms}")
            continue

        # Validate caption lengths per platform
        for target in platform_targets:
            caption = build_platform_caption(content, target["platform"], caption_overrides)
            limit = PLATFORM_LIMITS.get(target["platform"], 5000)
            if len(caption) > limit:
                if not as_json:
                    print(f"  [{piece_num}] WARNING: {target['platform']} caption "
                          f"({len(caption)} chars) exceeds limit ({limit})")

        if dry_run:
            result = {
                "piece": piece_num,
                "pillar": pillar,
                "status": "dry_run",
                "scheduled_for": scheduled_for,
                "platforms": [t["platform"] for t in platform_targets],
                "skipped_platforms": skipped_platforms,
                "content_preview": content[:100] + "..." if len(content) > 100 else content,
                "media_count": len(media_urls),
            }
            results.append(result)
            if not as_json:
                plat_names = ", ".join(t["platform"] for t in platform_targets)
                print(f"  [{piece_num}] DRY_RUN -- {pillar} -> {plat_names} @ {scheduled_for}")
                if skipped_platforms:
                    print(f"         Skipped: {skipped_platforms} (not connected)")
            continue

        # Schedule via Zernio
        try:
            zernio_result = schedule_post(
                api_key=api_key,
                content=content,
                platforms=platform_targets,
                scheduled_for=scheduled_for,
                media_urls=media_urls if media_urls else None,
            )

            post_data = zernio_result.get("post", zernio_result)
            post_id = (
                post_data.get("_id")
                or post_data.get("id")
                or post_data.get("postId")
                or ""
            )

            # Write to Supabase content_calendar for tracking
            if supabase_client:
                try:
                    for target in platform_targets:
                        calendar_entry = {
                            "platform": target["platform"],
                            "title": hook[:100] if hook else None,
                            "body": build_platform_caption(content, target["platform"], caption_overrides),
                            "status": "scheduled",
                            "scheduled_for": scheduled_for,
                            "brand": brand,
                            "late_post_id": post_id,
                            "pillar": pillar,
                        }
                        supabase_client.table("content_calendar").insert(calendar_entry).execute()
                except Exception as db_err:
                    if not as_json:
                        print(f"         DB WARNING: {db_err}", file=sys.stderr)

            result = {
                "piece": piece_num,
                "pillar": pillar,
                "status": "scheduled",
                "zernio_post_id": post_id,
                "scheduled_for": scheduled_for,
                "platforms": [t["platform"] for t in platform_targets],
                "skipped_platforms": skipped_platforms,
            }
            results.append(result)
            if not as_json:
                plat_names = ", ".join(t["platform"] for t in platform_targets)
                print(f"  [{piece_num}] OK SCHEDULED -- {pillar} -> {plat_names} @ {scheduled_for}")
                print(f"         Zernio ID: {post_id}")

        except Exception as exc:
            result = {
                "piece": piece_num,
                "status": "failed",
                "reason": str(exc)[:300],
            }
            results.append(result)
            if not as_json:
                print(f"  [{piece_num}] ERR FAILED -- {exc}", file=sys.stderr)

    # Summary
    scheduled_count = sum(1 for r in results if r["status"] == "scheduled")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    skipped_count = sum(1 for r in results if r["status"] in ("skipped", "dry_run"))

    summary = {
        "total": len(pieces),
        "scheduled": scheduled_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "results": results,
    }

    if as_json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"\n{'=' * 60}")
        print(f"  Summary: {scheduled_count} scheduled, {failed_count} failed, {skipped_count} skipped")
        print(f"{'=' * 60}\n")

    return results


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_schedule(args) -> None:
    """Schedule content from a manifest file."""
    env = load_env()
    api_key = env.get("LATE_API_KEY")
    if not api_key:
        print("ERROR: LATE_API_KEY not found in .env.agents", file=sys.stderr)
        sys.exit(1)

    supabase_client = get_supabase_client(env)

    if args.manifest:
        manifest = load_manifest(args.manifest)
    elif args.posts:
        # Quick mode: load a simple JSON array of posts
        with open(args.posts, "r", encoding="utf-8") as f:
            posts_data = json.load(f)
        manifest = {
            "content_day": datetime.now().strftime("%Y-%m-%d"),
            "week_starting": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
            "timezone": TIMEZONE,
            "brand": "cc_personal",
            "total_pieces": len(posts_data),
            "pieces": posts_data,
        }
    else:
        print("ERROR: Provide --manifest or --posts", file=sys.stderr)
        sys.exit(1)

    schedule_batch(
        manifest=manifest,
        api_key=api_key,
        supabase_client=supabase_client,
        dry_run=args.dry_run,
        as_json=args.json,
    )


def cmd_preview(args) -> None:
    """Preview the schedule without publishing."""
    args.dry_run = True
    args.posts = None
    cmd_schedule(args)


def cmd_template(args) -> None:
    """Generate a blank content day manifest template."""
    template = generate_template(args.date)

    # Save to data/content_day/
    out_dir = PROJECT_ROOT / "data" / "content_day"
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{template['content_day']}_template.json"
    out_path = out_dir / filename

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2)

    if args.json:
        print(json.dumps({"saved_to": str(out_path), "template": template}, indent=2))
    else:
        print(f"Content Day template saved to: {out_path}")
        print(f"\nWeek starting: {template['week_starting']}")
        print(f"Pieces: {template['total_pieces']}")
        print(f"\nSchedule:")
        for piece in template["pieces"]:
            plats = ", ".join(piece["platforms"])
            print(f"  [{piece['piece_number']}] {piece['pillar']:15s} -> {plats} @ {piece['scheduled_for']}")
        print(f"\nEdit the template to fill in hooks, body text, and media paths.")
        print(f"Then run: python scripts/batch_content_day.py schedule --manifest {out_path}")


def cmd_status(args) -> None:
    """Check status of scheduled posts in content_calendar."""
    env = load_env()
    supabase_client = get_supabase_client(env)
    if not supabase_client:
        print("ERROR: Cannot connect to Supabase for status check", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc).isoformat()
    try:
        # Get this week's posts
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        result = (
            supabase_client.table("content_calendar")
            .select("id, platform, pillar, status, scheduled_for, posted_at, late_post_id")
            .gte("scheduled_for", week_ago)
            .order("scheduled_for", desc=False)
            .execute()
        )
        rows = result.data or []
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps({"posts": rows, "total": len(rows)}, indent=2, default=str))
        return

    if not rows:
        print("No scheduled posts found in the last 7 days.")
        return

    print(f"\nContent Calendar -- Last 7 Days ({len(rows)} posts):\n")
    for row in rows:
        status = row.get("status", "?")
        platform = row.get("platform", "?")
        pillar = row.get("pillar", "?")
        scheduled = row.get("scheduled_for", "?")
        status_icon = {"posted": "OK", "scheduled": ">>", "failed": "XX", "draft": "--"}.get(status, "?")

        print(f"  {status_icon} [{status:10s}] {platform:12s} {pillar:18s} {scheduled}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="batch_content_day.py",
        description="Batch Content Day Scheduler -- schedule 7 pieces for the week via Zernio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--json", action="store_true", help="JSON output for agents")

    sub = parser.add_subparsers(dest="command", required=True)

    # Schedule
    sched = sub.add_parser("schedule", help="Schedule content from a manifest")
    sched.add_argument("--manifest", help="Path to content day manifest JSON")
    sched.add_argument("--posts", help="Path to a simple JSON array of posts")
    sched.add_argument("--dry-run", action="store_true", help="Preview without scheduling")

    # Preview
    prev = sub.add_parser("preview", help="Preview schedule (dry run)")
    prev.add_argument("--manifest", required=True, help="Path to content day manifest JSON")

    # Template
    tmpl = sub.add_parser("template", help="Generate a blank content day manifest")
    tmpl.add_argument("--date", help="Start date for the week (YYYY-MM-DD)")

    # Status
    sub.add_parser("status", help="Check status of scheduled posts")

    args = parser.parse_args()

    if args.command == "schedule":
        cmd_schedule(args)
    elif args.command == "preview":
        cmd_preview(args)
    elif args.command == "template":
        cmd_template(args)
    elif args.command == "status":
        cmd_status(args)


if __name__ == "__main__":
    main()
