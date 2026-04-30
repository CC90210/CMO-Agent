"""
Script Ideation Engine — generates creative video/post ideas for CC.

Built 2026-04-26 in response to CC's ask: "I want to start brainstorming
some content, and I want it to help me with creative script ideas for
videos, or with general ideas that will inspire the content creation."

This is Maven's IP. Bravo can read the OUTPUT (ideas saved to
data/ideation/) but the generator lives here.

What it does
------------
1. Loads Maven's strategic foundation:
     - brain/SOUL.md (identity + voice)
     - brain/WRITING.md (voice/hook/anti-slop guardrails)
     - brain/MARKETING_CANON.md (10 pillars framework)
     - brain/SHORT_FORM_HOOKS.md (CC's locked personal short-form hook patterns)
     - brain/CONTENT_BIBLE.md (4 content pillars, hook bank, pacing rules)
     - brain/VIDEO_PRODUCTION_BIBLE.md (cinematic format reference)
2. Pulls live signal:
     - Bravo's ceo_pulse.json (current focus / wins / blockers)
     - Atlas's cfo_pulse.json (any spend-gate context worth referencing)
     - Aura's pulse (CC's current energy / mood — affects what's authentic)
3. Sends a structured prompt to Claude Sonnet asking for N script ideas
   that fit CC's voice, pillar mix, and current life context.
4. Writes the result to `data/ideation/<timestamp>.md` and prints
   summary to stdout.

Usage
-----
    python scripts/script_ideation.py generate                 # 10 ideas, default mix
    python scripts/script_ideation.py generate --count 20      # more ideas
    python scripts/script_ideation.py generate --pillar ceo_log
    python scripts/script_ideation.py generate --format short_video
    python scripts/script_ideation.py generate --topic "Bennett rev share"
    python scripts/script_ideation.py generate --json          # JSON output for agents
    python scripts/script_ideation.py list                     # list past ideation runs
    python scripts/script_ideation.py view <timestamp>         # view a past run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


# ---------------------------------------------------------------------------
# Env loading (same shape as every Maven CLI)
# ---------------------------------------------------------------------------

def load_env() -> dict[str, str]:
    env_path = PROJECT_ROOT / ".env.agents"
    if not env_path.exists():
        # Maven can also fall back to Bravo's .env.agents if present
        bravo_env = Path(os.environ.get("BRAVO_REPO", r"C:\Users\User\Business-Empire-Agent")) / ".env.agents"
        if bravo_env.exists():
            env_path = bravo_env
        else:
            print(f"ERROR: no .env.agents at {env_path} or sibling Bravo path", file=sys.stderr)
            sys.exit(1)
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


# ---------------------------------------------------------------------------
# Foundation loaders — read Maven's voice + canon + pillars
# ---------------------------------------------------------------------------

def _read(rel_path: str, max_lines: int = 0) -> str:
    p = PROJECT_ROOT / rel_path
    if not p.exists():
        return ""
    text = p.read_text(encoding="utf-8", errors="replace")
    if max_lines > 0:
        text = "\n".join(text.split("\n")[:max_lines])
    return text.strip()


def load_foundation() -> dict[str, str]:
    """Load every strategic foundation file Maven uses for ideation."""
    return {
        "soul": _read("brain/SOUL.md"),
        "writing": _read("brain/WRITING.md"),
        "marketing_canon": _read("brain/MARKETING_CANON.md"),
        "short_form_hooks": _read("brain/SHORT_FORM_HOOKS.md"),
        "content_bible": _read("brain/CONTENT_BIBLE.md"),
        "cc_creative_identity": _read("brain/CC_CREATIVE_IDENTITY.md"),
        "video_production_bible": _read("brain/VIDEO_PRODUCTION_BIBLE.md", max_lines=80),
    }


# ---------------------------------------------------------------------------
# Cross-agent pulse loaders — current life/business context
# ---------------------------------------------------------------------------

SIBLING_REPOS = {
    "bravo": Path(os.environ.get("BRAVO_REPO", r"C:\Users\User\Business-Empire-Agent")),
    "atlas": Path(os.environ.get("ATLAS_REPO", r"C:\Users\User\APPS\CFO-Agent")),
    "aura":  Path(os.environ.get("AURA_REPO",  r"C:\Users\User\AURA")),
}


def _read_pulse(agent: str, filename: str) -> dict | None:
    """Read a sibling agent's pulse JSON. Returns None if missing/malformed."""
    root = SIBLING_REPOS.get(agent)
    if not root:
        return None
    pulse_path = root / "data" / "pulse" / filename
    if not pulse_path.exists():
        return None
    try:
        return json.loads(pulse_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_current_signal() -> dict[str, dict | None]:
    """Pull live pulse data from each sibling for context-aware ideation."""
    return {
        "bravo": _read_pulse("bravo", "ceo_pulse.json"),
        "atlas": _read_pulse("atlas", "cfo_pulse.json"),
        "aura":  _read_pulse("aura",  "aura_pulse.json"),
    }


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

PILLAR_OPTIONS = {
    "ai_oracle":    "The AI Oracle — CC sees what others can't. AI impact, misinformation, showing systems. Time Traveler energy.",
    "the_becoming": "The Becoming — self-improvement, masculinity, emotional regulation, psychology, relationships. Wise friend at 2am.",
    "the_journey":  "The Journey — sobriety, dropping out, entrepreneurship at 22, Montreal move, growth arc. Raw and sentimental.",
    "ceo_log":      "The CEO Log — building-in-public, behind-the-scenes OASIS AI. Effortless operator, 'another day at the office'.",
    "any":          "Mix all 4 pillars — let context decide which fits each idea",
}

FORMAT_OPTIONS = {
    "short_video":   "30–90 second talking head or B-roll-heavy short (TikTok / Reels / Shorts)",
    "long_video":    "3–10 min YouTube video — proper hook, segments, CTA",
    "carousel":      "Instagram/LinkedIn carousel — 6–10 slides, hook on slide 1",
    "thread":        "X thread — 5–12 tweets, opening hook, payoff in last tweet",
    "podcast_clip":  "Audio-first short — soundbite + caption overlay",
    "any":           "Best format per idea — let topic decide",
}


def build_prompt(
    foundation: dict[str, str],
    signal: dict[str, dict | None],
    count: int,
    pillar: str,
    fmt: str,
    topic: str | None,
) -> str:
    """Assemble the full ideation prompt from foundation + signal + user options."""
    parts: list[str] = []

    parts.append(
        "You are Maven, CC's CMO. CC needs creative video/post script ideas "
        "for the next 1–2 weeks of content. Generate ideas that fit CC's "
        "voice, current life context, and the pillar/format spec below. "
        "No generic LinkedIn-bro slop. No 'Unlock the power of...' openers. "
        "For short-form ideas, rotate CC's hook patterns and make the first "
        "line observational, not needy. Every idea must feel like CC actually said it."
    )
    parts.append("")
    parts.append("=== CC's IDENTITY (brain/SOUL.md) ===")
    parts.append(foundation.get("soul", "")[:3000])
    parts.append("")
    parts.append("=== VOICE & ANTI-SLOP RULES (brain/WRITING.md) ===")
    parts.append(foundation.get("writing", "")[:3000])
    parts.append("")
    if foundation.get("short_form_hooks"):
        parts.append("=== SHORT-FORM HOOK SYSTEM (brain/SHORT_FORM_HOOKS.md) ===")
        parts.append(foundation["short_form_hooks"][:3000])
        parts.append("")
    parts.append("=== MARKETING CANON (10 pillars framework) ===")
    parts.append(foundation.get("marketing_canon", "")[:3000])
    parts.append("")
    parts.append("=== CONTENT BIBLE (pillars, hook bank, pacing) ===")
    parts.append(foundation.get("content_bible", "")[:4000])
    parts.append("")

    if foundation.get("cc_creative_identity"):
        parts.append("=== CC'S CREATIVE IDENTITY (persona, voice, topics, archetype) ===")
        parts.append(foundation["cc_creative_identity"][:5000])
        parts.append("")

    if foundation.get("video_production_bible"):
        parts.append("=== VIDEO PRODUCTION BIBLE (top of) ===")
        parts.append(foundation["video_production_bible"][:1500])
        parts.append("")

    parts.append("=== CURRENT BUSINESS / LIFE SIGNAL ===")
    bravo = signal.get("bravo")
    if bravo:
        note = (bravo.get("session_note") or "").strip()[:300]
        recent = bravo.get("recent_shipped", [])
        blockers = bravo.get("blockers", [])
        parts.append(f"Bravo (CEO) note: {note or '(none)'}")
        if recent:
            parts.append(f"Recent ships: {recent[:5]}")
        if blockers:
            parts.append(f"Open blockers: {blockers[:5]}")
    atlas = signal.get("atlas")
    if atlas:
        note = (atlas.get("session_note") or "").strip()[:300]
        parts.append(f"Atlas (CFO) note: {note or '(none)'}")
    aura = signal.get("aura")
    if aura:
        note = (aura.get("session_note") or "").strip()[:300]
        parts.append(f"Aura (Life) note: {note or '(none)'}")
    parts.append("")

    parts.append("=== IDEATION SPEC ===")
    parts.append(f"- Count: {count} ideas")
    parts.append(f"- Pillar: {pillar} — {PILLAR_OPTIONS.get(pillar, pillar)}")
    parts.append(f"- Format: {fmt} — {FORMAT_OPTIONS.get(fmt, fmt)}")
    if topic:
        parts.append(f"- Anchor topic: {topic}")
    parts.append("")

    parts.append("=== OUTPUT FORMAT ===")
    parts.append(
        "For each idea, write a markdown block with these fields:\n"
        "  ### {N}. {Tight 6-10 word title}\n"
        "  - **Pillar**: which content pillar this is\n"
        "  - **Format**: short_video | long_video | carousel | thread | podcast_clip\n"
        "  - **Hook pattern used**: one of SHORT_FORM_HOOKS, or a brief reason another pattern fits better\n"
        "  - **Hook (first 3 seconds)**: the literal opening line CC says or text on screen\n"
        "  - **Why this works**: 1 sentence — what tension or insight makes it pull\n"
        "  - **Beat sheet**: 3–6 bullet points covering the body\n"
        "  - **CTA / payoff**: the close. Soft when CEO Log, sharp when Quote Drop\n"
        "  - **B-roll / visuals** (if video): what to shoot\n"
        "Number ideas 1..N. No preamble. No closing summary. Ideas only."
    )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Claude API call
# ---------------------------------------------------------------------------

def call_claude(prompt: str, env: dict[str, str]) -> str:
    """Call Anthropic Sonnet via the SDK; return the text response."""
    api_key = env.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY missing in .env.agents", file=sys.stderr)
        sys.exit(1)

    try:
        from anthropic import Anthropic  # type: ignore[import-not-found]
    except ImportError:
        print("ERROR: anthropic package not installed. pip install anthropic",
              file=sys.stderr)
        sys.exit(1)

    client = Anthropic(api_key=api_key)
    # Prefer env override (CLAUDE_MODEL=…) so CC can swap without code edits.
    # Default to current Sonnet (4.6 as of 2026-04). Bumping the default
    # lives in this one place; every Maven script that talks to Claude
    # should read CLAUDE_MODEL the same way.
    model = env.get("CLAUDE_MODEL") or os.environ.get("CLAUDE_MODEL") or "claude-sonnet-4-6"
    resp = client.messages.create(
        model=model,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    # New SDK shape: resp.content is a list of blocks
    parts: list[str] = []
    for block in resp.content:
        text = getattr(block, "text", "") or ""
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


# ---------------------------------------------------------------------------
# Output writer
# ---------------------------------------------------------------------------

def save_run(prompt: str, response: str, meta: dict) -> Path:
    out_dir = PROJECT_ROOT / "data" / "ideation"
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"{timestamp}.md"
    parts = [
        "---",
        f"generated_at: {datetime.now(timezone.utc).isoformat()}",
        f"count: {meta['count']}",
        f"pillar: {meta['pillar']}",
        f"format: {meta['format']}",
        f"topic: {meta.get('topic') or ''}",
        "---",
        "",
        f"# Script Ideation — {timestamp}",
        "",
        response,
        "",
        "---",
        "## Prompt that produced this run",
        "```",
        prompt,
        "```",
    ]
    out_path.write_text("\n".join(parts), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_generate(args, output_json: bool) -> None:
    env = load_env()
    foundation = load_foundation()

    missing = [k for k, v in foundation.items() if not v]
    if missing:
        msg = f"WARNING: missing foundation files: {missing} — ideation may be weaker."
        if output_json:
            print(json.dumps({"warning": msg}), file=sys.stderr)
        else:
            print(msg, file=sys.stderr)

    signal = load_current_signal()
    prompt = build_prompt(
        foundation=foundation,
        signal=signal,
        count=args.count,
        pillar=args.pillar,
        fmt=args.format,
        topic=args.topic,
    )

    response = call_claude(prompt, env)
    out_path = save_run(prompt, response, {
        "count": args.count,
        "pillar": args.pillar,
        "format": args.format,
        "topic": args.topic,
    })

    if output_json:
        print(json.dumps({
            "ok": True,
            "saved_to": str(out_path),
            "count": args.count,
            "pillar": args.pillar,
            "format": args.format,
            "ideas_text": response,
        }, indent=2))
    else:
        print(f"\n=== {args.count} ideas saved to: {out_path} ===\n")
        print(response)


def cmd_list(args, output_json: bool) -> None:
    out_dir = PROJECT_ROOT / "data" / "ideation"
    if not out_dir.exists():
        if output_json:
            print(json.dumps({"runs": []}))
        else:
            print("(no ideation runs yet — try: python scripts/script_ideation.py generate)")
        return
    runs = sorted([p.stem for p in out_dir.glob("*.md")], reverse=True)
    if output_json:
        print(json.dumps({"runs": runs}))
    else:
        for r in runs[: args.limit]:
            print(r)


def cmd_view(args, output_json: bool) -> None:
    out_dir = PROJECT_ROOT / "data" / "ideation"
    target = out_dir / f"{args.timestamp}.md"
    if not target.exists():
        print(f"ERROR: no run at {target}", file=sys.stderr)
        sys.exit(1)
    text = target.read_text(encoding="utf-8")
    if output_json:
        print(json.dumps({"timestamp": args.timestamp, "content": text}))
    else:
        print(text)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Maven script-ideation engine — creative video/post ideas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--json", action="store_true", help="JSON output for agents")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate N script ideas")
    gen.add_argument("--count", type=int, default=10, help="how many ideas (default 10)")
    gen.add_argument("--pillar", choices=list(PILLAR_OPTIONS.keys()), default="any",
                     help="lock to one of the 3 daily pillars, or 'any' (default)")
    gen.add_argument("--format", choices=list(FORMAT_OPTIONS.keys()), default="any",
                     help="lock format (default 'any' — model picks per idea)")
    gen.add_argument("--topic", type=str, default=None,
                     help="anchor topic (e.g. 'Bennett rev share', 'tax season')")

    lst = sub.add_parser("list", help="List past ideation runs")
    lst.add_argument("--limit", type=int, default=20)

    vw = sub.add_parser("view", help="View a past ideation run")
    vw.add_argument("timestamp", help="timestamp slug (use 'list' to find)")

    args = parser.parse_args()
    output_json = args.json

    if args.command == "generate":
        cmd_generate(args, output_json)
    elif args.command == "list":
        cmd_list(args, output_json)
    elif args.command == "view":
        cmd_view(args, output_json)


if __name__ == "__main__":
    main()
