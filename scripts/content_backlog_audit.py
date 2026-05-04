"""
content_backlog_audit.py — Maven's cron-safe content inventory check.

This script is intentionally read-only. It scans Maven's local content
working directories and reports enough structure for the nightly cron job
to surface drift without mutating campaigns, queues, or public posts.

Usage:
  python scripts/content_backlog_audit.py
  python scripts/content_backlog_audit.py --json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent


def _files(glob_root: Path, pattern: str) -> list[Path]:
    if not glob_root.exists():
        return []
    return [p for p in glob_root.rglob(pattern) if p.is_file()]


def _iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def build_report() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    ideation = _files(REPO_ROOT / "data" / "ideation", "*.md")
    content_days = _files(REPO_ROOT / "data" / "content_day", "*.json")
    studio_scripts = [
        p for p in _files(REPO_ROOT / "content-studio", "*.md")
        if p.name.upper() not in {"INDEX.md", "README.md"}
    ]
    upload_ready = [
        p for p in _files(REPO_ROOT / "media" / "videos", "*.mp4")
        if "UPLOAD" in p.name.upper() or "LATE" in p.name.upper()
    ]
    published_recent = [
        p for p in upload_ready
        if datetime.fromtimestamp(p.stat().st_mtime, timezone.utc) >= seven_days_ago
    ]

    newest_candidates = ideation + content_days + studio_scripts + upload_ready
    newest = sorted(newest_candidates, key=lambda p: p.stat().st_mtime, reverse=True)[:10]

    warnings: list[str] = []
    if not content_days:
        warnings.append("No content_day JSON files found.")
    if not upload_ready:
        warnings.append("No upload-ready MP4 files found under media/videos.")
    if len(published_recent) == 0:
        warnings.append("No upload-ready videos modified in the last 7 days.")

    return {
        "generated_at": now.isoformat(),
        "repo": str(REPO_ROOT),
        "content_pipeline": {
            "drafts": len(ideation) + len(studio_scripts),
            "scheduled": len(content_days),
            "published_7d": len(published_recent),
            "upload_ready": len(upload_ready),
        },
        "latest_files": [
            {
                "path": str(p.relative_to(REPO_ROOT)),
                "modified_at": _iso_mtime(p),
                "bytes": p.stat().st_size,
            }
            for p in newest
        ],
        "warnings": warnings,
    }


def render_text(report: dict[str, Any]) -> str:
    p = report["content_pipeline"]
    lines = [
        f"Maven content backlog audit — {report['generated_at']}",
        f"  drafts:       {p['drafts']}",
        f"  scheduled:    {p['scheduled']}",
        f"  published_7d: {p['published_7d']}",
        f"  upload_ready: {p['upload_ready']}",
    ]
    if report["warnings"]:
        lines.append("  warnings:")
        for w in report["warnings"]:
            lines.append(f"    - {w}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only Maven content backlog audit.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(render_text(report))


if __name__ == "__main__":
    main()
