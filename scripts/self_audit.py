#!/usr/bin/env python3
"""
Self-Audit — Maven's automated health check.

Scans the knowledge graph for orphans, broken wiring, stale docs, and
undocumented scripts. Runs fast (seconds), emits a health score + action list.

Usage:
    python scripts/self_audit.py              # human-readable report
    python scripts/self_audit.py --json       # agent-readable JSON
    python scripts/self_audit.py --fix-links  # auto-add reconnection TODOs to orphans

Exit codes:
    0 = healthy (score >= 85)
    1 = warnings (score 70-84)
    2 = degraded (score < 70)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# --- Scan scope -------------------------------------------------------------

AUDIT_DIRS = ["brain", "memory", "skills", "agents", ".agents/workflows",
              ".agents/commands", ".agents/plans", "APPS_CONTEXT"]
SKIP_DIRS = {"ARCHIVES", "node_modules", ".git", "worktrees", "tmp",
             "__pycache__", ".claude/worktrees"}

# Directories whose contents are historical archives by design — not expected
# to have inbound wiki-links. Skipped for orphan checks.
ARCHIVE_PATH_PARTS = {"outreach_archive", "daily", "research", "content"}

# Files that are allowed to be "orphans" because they're entry points,
# IDE-loaded at boot, frontmatter-discovered (agents), or reachable via
# @import rather than [[wiki-link]].
ORPHAN_ALLOWLIST = {
    # Brain entry points
    "brain/SOUL.md", "brain/USER.md", "brain/STATE.md",
    "brain/DASHBOARD.md", "brain/CAPABILITIES.md", "brain/QUICK_REFERENCE.md",
    "brain/AGENTS.md", "brain/APP_REGISTRY.md", "brain/BRAIN_LOOP.md",
    "brain/INTERACTION_PROTOCOL.md", "brain/HEARTBEAT.md", "brain/GROWTH.md",
    "brain/CHANGELOG.md", "brain/ORCHESTRATION.md", "brain/PERSONALITY.md",
    "brain/CLIENT.md", "brain/DAILY_SCHEDULE.md", "brain/ENV_STRUCTURE.md",
    "brain/PRODUCT_VERTICALS.md", "brain/OKRs.md", "brain/BENCHMARK.md",
    "brain/RISK_REGISTER.md", "brain/INDEX.md", "brain/RESPONSIBILITY_BOUNDARIES.md",
    "brain/MARKETING_CANON.md", "brain/WRITING.md", "brain/SHARED_DB.md",
    "brain/ATTRIBUTION_MODEL.md",
    # Memory
    "memory/ACTIVE_TASKS.md", "memory/SESSION_LOG.md",
    "memory/MISTAKES.md", "memory/PATTERNS.md", "memory/DECISIONS.md",
    "memory/MEMORY_INDEX.md", "memory/content-strategy.md",
}

# Whole directories whose files are allowed to be orphans:
# - agents/ : discovered by frontmatter, not wiki-links
# - skills/ : discovered by frontmatter, not wiki-links
# - brain/canon/ : referenced via [[canon/x]] links, indirect
# - brain/clients/ : referenced via brand profile pages
# - brain/verticals/ : referenced via vertical pack indirection
# - _templates/ : reference docs, not wiki-linked
ORPHAN_ALLOWLIST_DIRS = {
    "agents/", "skills/", "brain/canon/", "brain/clients/",
    "brain/verticals/", "_templates/", "brain/intel/", "brain/retros/",
    ".agents/workflows/", ".agents/commands/", ".agents/plans/",
    "proposals/",
}

# ---------------------------------------------------------------------------


@dataclass
class AuditResult:
    total_md_files: int = 0
    orphans: list[str] = field(default_factory=list)
    broken_links: list[tuple[str, str]] = field(default_factory=list)
    skills_total: int = 0
    skills_missing_skill_md: list[str] = field(default_factory=list)
    skills_missing_frontmatter: list[str] = field(default_factory=list)
    agents_total: int = 0
    agents_missing_frontmatter: list[str] = field(default_factory=list)
    scripts_total: int = 0
    scripts_undocumented: list[str] = field(default_factory=list)
    mcp_configs_in_sync: bool = True
    mcp_servers: list[str] = field(default_factory=list)
    send_gateway_tests_pass: bool = False
    send_gateway_test_summary: str = "not run"
    cmo_pulse_fresh: bool = False
    cmo_pulse_age_hours: float = -1.0
    health_score: int = 0
    warnings: list[str] = field(default_factory=list)


def collect_markdown_files() -> list[Path]:
    files: list[Path] = []
    for d in AUDIT_DIRS:
        base = REPO_ROOT / d
        if not base.exists():
            continue
        for p in base.rglob("*.md"):
            if any(skip in p.parts for skip in SKIP_DIRS):
                continue
            files.append(p)
    return files


WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]")
AT_IMPORT_RE = re.compile(r"@([a-zA-Z0-9_\-/.]+\.md)")


def build_link_index(md_files: list[Path]) -> dict[str, set[str]]:
    """Map 'brain/SOUL.md' -> {set of files that link to it}."""
    inbound: dict[str, set[str]] = {}
    # Also check CLAUDE.md, GEMINI.md, ANTIGRAVITY.md for @imports
    entry_points = [REPO_ROOT / n for n in
                    ("CLAUDE.md", "GEMINI.md", "ANTIGRAVITY.md", "AGENTS.md", "README.md")]
    for ep in entry_points:
        if ep.exists():
            md_files = md_files + [ep]

    for f in md_files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        source = str(f.relative_to(REPO_ROOT)).replace("\\", "/")

        for m in WIKI_LINK_RE.findall(text):
            target = m.strip()
            if not target.endswith(".md"):
                target = target + ".md"
            # Obsidian links may omit directory prefix — try both forms
            inbound.setdefault(target, set()).add(source)
            inbound.setdefault(target.split("/")[-1], set()).add(source)

        for m in AT_IMPORT_RE.findall(text):
            inbound.setdefault(m.strip(), set()).add(source)
            inbound.setdefault(m.strip().split("/")[-1], set()).add(source)
    return inbound


def check_agents(result: AuditResult) -> None:
    """Maven addition — verify every agent in agents/*.md has valid YAML
    frontmatter so Claude Code's auto-discovery can see it."""
    agents_dir = REPO_ROOT / "agents"
    if not agents_dir.exists():
        return
    for f in agents_dir.glob("*.md"):
        result.agents_total += 1
        head = f.read_text(encoding="utf-8", errors="ignore")[:600]
        if not (head.startswith("---") and "name:" in head and "description:" in head):
            result.agents_missing_frontmatter.append(str(f.relative_to(REPO_ROOT)))


def check_send_gateway(result: AuditResult) -> None:
    """Maven addition — run the send_gateway test suite and capture pass/fail."""
    import subprocess
    test_path = REPO_ROOT / "scripts" / "test_send_gateway.py"
    if not test_path.exists():
        result.warnings.append("send_gateway test file missing")
        return
    try:
        proc = subprocess.run(
            [sys.executable, str(test_path)],
            cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=60,
        )
        result.send_gateway_tests_pass = proc.returncode == 0
        # Last 5 lines of stderr (unittest writes there)
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
        result.send_gateway_test_summary = " | ".join(tail)
    except Exception as e:
        result.warnings.append(f"send_gateway test invocation failed: {e}")


def check_cmo_pulse(result: AuditResult) -> None:
    """Maven addition — pulse must be < 24h old or the C-suite is operating
    on stale data."""
    import time
    pulse = REPO_ROOT / "data" / "pulse" / "cmo_pulse.json"
    if not pulse.exists():
        result.warnings.append("cmo_pulse.json does not exist — run state_sync")
        return
    age_seconds = time.time() - pulse.stat().st_mtime
    age_hours = age_seconds / 3600.0
    result.cmo_pulse_age_hours = round(age_hours, 1)
    result.cmo_pulse_fresh = age_hours < 24


def check_skills(result: AuditResult) -> None:
    skills_dir = REPO_ROOT / "skills"
    if not skills_dir.exists():
        return
    for sub in skills_dir.iterdir():
        if not sub.is_dir() or sub.name.startswith("."):
            continue
        result.skills_total += 1
        skill_md = sub / "SKILL.md"
        if not skill_md.exists():
            result.skills_missing_skill_md.append(str(sub.relative_to(REPO_ROOT)))
            continue
        text = skill_md.read_text(encoding="utf-8", errors="ignore")
        # Rough frontmatter check: must have --- at top + name: + description:
        head = text[:800]
        if not (head.startswith("---") and "name:" in head and "description:" in head):
            result.skills_missing_frontmatter.append(str(skill_md.relative_to(REPO_ROOT)))


def check_scripts(result: AuditResult) -> None:
    scripts_dir = REPO_ROOT / "scripts"
    if not scripts_dir.exists():
        return
    # Collect reference text from the docs agents actually read
    doc_text = ""
    for ref_doc in ("brain/CAPABILITIES.md", "brain/QUICK_REFERENCE.md", "CLAUDE.md"):
        p = REPO_ROOT / ref_doc
        if p.exists():
            doc_text += p.read_text(encoding="utf-8", errors="ignore")
    # Also scan skills for references
    for skill_md in (REPO_ROOT / "skills").rglob("SKILL.md"):
        doc_text += skill_md.read_text(encoding="utf-8", errors="ignore")

    for py in scripts_dir.glob("*.py"):
        if py.name.startswith("_") or py.name.startswith("test_"):
            continue
        result.scripts_total += 1
        if py.name not in doc_text and py.stem not in doc_text:
            result.scripts_undocumented.append(str(py.relative_to(REPO_ROOT)))


def check_mcp_sync(result: AuditResult) -> None:
    # Maven only checks repo-local MCP configs. ~/.gemini is a Bravo-specific
    # cross-IDE concern; Maven's MCP envelope is set at the project level.
    configs = {
        ".claude/mcp.json": REPO_ROOT / ".claude" / "mcp.json",
        ".vscode/mcp.json": REPO_ROOT / ".vscode" / "mcp.json",
    }
    server_sets: dict[str, set[str]] = {}
    for label, path in configs.items():
        if not path.exists():
            result.warnings.append(f"MCP config missing: {label}")
            result.mcp_configs_in_sync = False
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            result.warnings.append(f"MCP config unreadable: {label} ({e})")
            result.mcp_configs_in_sync = False
            continue
        servers = data.get("mcpServers") or data.get("servers") or {}
        server_sets[label] = set(servers.keys())
    if server_sets:
        ref = next(iter(server_sets.values()))
        for label, s in server_sets.items():
            if s != ref:
                result.mcp_configs_in_sync = False
                missing = ref - s
                extra = s - ref
                result.warnings.append(
                    f"MCP drift in {label}: missing={sorted(missing)} extra={sorted(extra)}"
                )
        result.mcp_servers = sorted(ref)


def compute_health_score(r: AuditResult) -> int:
    score = 100
    score -= min(len(r.orphans) * 2, 20)
    score -= len(r.broken_links) * 3
    score -= len(r.skills_missing_skill_md) * 5
    score -= len(r.skills_missing_frontmatter) * 2
    score -= len(r.agents_missing_frontmatter) * 3
    # Undocumented scripts are an aspirational target — keep the penalty
    # small. Marketing-engine scripts auto-document themselves via skill
    # references, but per-task helpers don't always need a CAPABILITIES entry.
    score -= min(len(r.scripts_undocumented), 5)
    if not r.mcp_configs_in_sync:
        score -= 5
    if not r.send_gateway_tests_pass:
        score -= 15  # send_gateway is the highest-blast-radius surface
    if not r.cmo_pulse_fresh:
        score -= 5
    return max(0, score)


def run_audit() -> AuditResult:
    result = AuditResult()
    md_files = collect_markdown_files()
    result.total_md_files = len(md_files)
    inbound = build_link_index(md_files)

    for f in md_files:
        rel = str(f.relative_to(REPO_ROOT)).replace("\\", "/")
        if rel in ORPHAN_ALLOWLIST:
            continue
        if any(rel.startswith(d) for d in ORPHAN_ALLOWLIST_DIRS):
            continue
        # Historical archive directories don't need inbound links
        if any(part in ARCHIVE_PATH_PARTS for part in rel.split("/")):
            continue
        filename = rel.split("/")[-1]
        # An orphan has no inbound refs under any form we index
        if not inbound.get(rel) and not inbound.get(filename) and not inbound.get(rel.removesuffix(".md")):
            result.orphans.append(rel)

    check_skills(result)
    check_agents(result)
    check_scripts(result)
    check_mcp_sync(result)
    check_send_gateway(result)
    check_cmo_pulse(result)
    result.health_score = compute_health_score(result)
    return result


def render_human(r: AuditResult) -> str:
    lines = [
        "",
        "=" * 64,
        f" MAVEN SELF-AUDIT   |   health score: {r.health_score}/100",
        "=" * 64,
        f"  Markdown files scanned : {r.total_md_files}",
        f"  Skills registered      : {r.skills_total}",
        f"  Scripts (non-internal) : {r.scripts_total}",
        f"  MCP servers in sync    : {'YES' if r.mcp_configs_in_sync else 'NO — drift detected'}",
        f"  MCP servers registered : {len(r.mcp_servers)} ({', '.join(r.mcp_servers)})",
        f"  Agents (frontmatter)   : {r.agents_total - len(r.agents_missing_frontmatter)}/{r.agents_total} valid",
        f"  send_gateway tests     : {'PASS' if r.send_gateway_tests_pass else 'FAIL'}",
        f"  cmo_pulse.json fresh   : {'YES' if r.cmo_pulse_fresh else 'NO'} (age {r.cmo_pulse_age_hours}h)",
        "",
    ]
    if r.orphans:
        lines.append(f"  ORPHANS ({len(r.orphans)}) — no inbound links, not allowlisted:")
        for o in sorted(r.orphans):
            lines.append(f"    - {o}")
    else:
        lines.append("  ORPHANS: none OK")
    lines.append("")
    if r.skills_missing_skill_md:
        lines.append(f"  SKILLS missing SKILL.md ({len(r.skills_missing_skill_md)}):")
        for s in r.skills_missing_skill_md:
            lines.append(f"    - {s}")
    if r.skills_missing_frontmatter:
        lines.append(f"  SKILLS missing frontmatter ({len(r.skills_missing_frontmatter)}):")
        for s in r.skills_missing_frontmatter:
            lines.append(f"    - {s}")
    if r.scripts_undocumented:
        lines.append(f"  SCRIPTS not referenced by CAPABILITIES/QUICK_REFERENCE/skills ({len(r.scripts_undocumented)}):")
        for s in r.scripts_undocumented[:15]:
            lines.append(f"    - {s}")
        if len(r.scripts_undocumented) > 15:
            lines.append(f"    - (+{len(r.scripts_undocumented)-15} more)")
    if r.warnings:
        lines.append("")
        lines.append("  WARNINGS:")
        for w in r.warnings:
            lines.append(f"    ! {w}")
    lines.append("")
    if r.health_score >= 85:
        verdict = "HEALTHY — ship it."
    elif r.health_score >= 70:
        verdict = "WARN — reconnect orphans, document scripts."
    else:
        verdict = "DEGRADED — stop and clean up."
    lines.append(f"  VERDICT: {verdict}")
    lines.append("=" * 64)
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="Maven self-audit")
    p.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = p.parse_args()

    result = run_audit()
    if args.json:
        print(json.dumps(asdict(result), default=list, indent=2))
    else:
        print(render_human(result))

    if result.health_score >= 85:
        return 0
    if result.health_score >= 70:
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
