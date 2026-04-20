"""One-shot: inject canon_references into every skill's SKILL.md frontmatter.

Idempotent: if frontmatter exists, adds canon_references if missing.
If frontmatter missing, prepends a minimal one preserving the existing H1.
Skips files that already have canon_references populated.

Retirement: this script can be deleted after 2026-04-30.
"""
from __future__ import annotations
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"

# skill_name -> list[str]  (pillar short-names keyed to MARKETING_CANON.md)
CANON_MAP: dict[str, list[str]] = {
    "a-b-testing": ["sharp-how-brands-grow", "ritson-diagnosis", "hormozi-value-equation"],
    "ad-copywriting": ["dunford-positioning", "hormozi-value-equation", "miner-nepq", "sutherland-signalling"],
    "audience-targeting": ["sharp-mental-availability", "godin-smallest-viable-audience", "holmes-buyer-pyramid"],
    "brand-guidelines": ["dunford-positioning", "sharp-distinctive-assets", "sutherland-signalling"],
    "browser-automation": ["ritson-diagnosis"],
    "budget-optimization": ["sharp-reach-over-frequency", "hormozi-lead-flows", "ritson-diagnosis"],
    "campaign-creation": ["dunford-positioning", "ritson-diagnosis", "hormozi-value-equation", "brunson-funnel"],
    "competitive-intelligence": ["ritson-diagnosis", "dunford-positioning", "fishkin-sparktoro"],
    "content-engine": ["godin-permission", "holmes-buyer-pyramid", "sharp-mental-availability"],
    "elite-video-production": ["sutherland-signalling", "dunford-positioning"],
    "email-marketing": ["hormozi-lead-flows", "godin-permission", "miner-nepq"],
    "email-outbound": ["hormozi-lead-flows", "godin-permission", "miner-nepq", "ross-predictable-revenue"],
    "funnel-management": ["brunson-funnel", "hormozi-value-equation", "ritson-diagnosis"],
    "google-ads-management": ["sharp-mental-availability", "ritson-diagnosis"],
    "growth-engine": ["sharp-how-brands-grow", "hormozi-lead-flows", "brunson-funnel"],
    "image-generation": ["sutherland-signalling", "dunford-positioning", "godin-permission"],
    "lead-generation": ["hormozi-lead-flows", "holmes-buyer-pyramid", "miner-nepq"],
    "lead-management": ["ross-predictable-revenue", "holmes-buyer-pyramid", "hormozi-lead-flows", "miner-nepq"],
    "lending-industry": ["ritson-diagnosis"],
    "linkedin-outreach": ["ross-predictable-revenue", "miner-nepq", "holmes-dream-100"],
    "media-upload": ["ritson-diagnosis"],
    "meta-ads-management": ["sharp-mental-availability", "ritson-diagnosis"],
    "performance-optimization": ["sharp-mental-availability", "ritson-diagnosis", "hormozi-value-equation"],
    "persona-content-creator": ["dunford-positioning", "godin-tribes"],
    "reporting-analytics": ["ritson-diagnosis", "sharp-mental-availability"],
    "self-healing": ["ritson-diagnosis"],
    "self-improvement-protocol": ["ritson-diagnosis"],
    "seo-aeo": ["sharp-mental-availability", "godin-permission", "fishkin-sparktoro"],
    "systematic-debugging": ["ritson-diagnosis"],
    "video-editing": ["sutherland-signalling", "dunford-positioning"],
}

CANON_DOC = "brain/MARKETING_CANON.md"
FM_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def format_refs(refs: list[str]) -> str:
    return "[" + ", ".join(refs) + "]"


def inject(path: pathlib.Path, refs: list[str]) -> str:
    """Return the updated file body (no write)."""
    body = path.read_text(encoding="utf-8")
    refs_str = format_refs(refs)
    match = FM_PATTERN.match(body)
    if match:
        fm = match.group(1)
        if "canon_references" in fm:
            return body  # idempotent
        new_fm = fm.rstrip() + f"\ncanon_references: {refs_str}\ncanon_source: {CANON_DOC}"
        return f"---\n{new_fm}\n---\n" + body[match.end():]
    # No frontmatter. Prepend one. Preserve original content entirely.
    name_guess = path.parent.name
    header = (
        f"---\n"
        f"name: {name_guess}\n"
        f"canon_references: {refs_str}\n"
        f"canon_source: {CANON_DOC}\n"
        f"universal: true\n"
        f"note: Examples in this skill may reference SunBiz (legacy client); the skill itself is brand-agnostic. Per-brand context lives in brain/clients/<brand>.md.\n"
        f"---\n\n"
    )
    return header + body


def main() -> None:
    touched = []
    skipped = []
    for skill_dir in sorted(SKILLS.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name == "verticals":
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        refs = CANON_MAP.get(skill_dir.name)
        if not refs:
            skipped.append(skill_dir.name + " (no canon map)")
            continue
        original = skill_md.read_text(encoding="utf-8")
        updated = inject(skill_md, refs)
        if updated == original:
            skipped.append(skill_dir.name + " (already has canon_references)")
            continue
        skill_md.write_text(updated, encoding="utf-8")
        touched.append(skill_dir.name)
    print("TOUCHED:", ", ".join(touched) if touched else "(none)")
    print("SKIPPED:", ", ".join(skipped) if skipped else "(none)")


if __name__ == "__main__":
    main()
