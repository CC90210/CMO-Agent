# Integration: open-design

> **Repo:** https://github.com/nexu-io/open-design (Apache-2.0, ~19k stars)
> **Local clone:** `vendor/open-design/` (~144 MB — heavy; we cherry-pick rather than run the daemon)
> **Stack:** Node 24, pnpm 10.33.2 monorepo (Next.js 16 + Express daemon + SQLite + Electron desktop shell), TypeScript

## What it actually is

An **open-source local-first alternative to Anthropic's Claude Design**. It detects whichever coding-agent CLI you have on `$PATH` (Claude Code, Codex, Cursor, Gemini, Copilot, etc. — 13 supported), then drives that agent through:

- **58 skills** (`vendor/open-design/skills/<name>/SKILL.md` + assets)
- **129 design systems** (`vendor/open-design/design-systems/<brand>/DESIGN.md`)
- **93 prompt templates** (`vendor/open-design/prompt-templates/`)

…to emit **single-file HTML / PDF / PPTX / MP4** artifacts in a sandboxed iframe preview.

CC's framing — "for you to make better effects" — is partially right but the value isn't in FX primitives (there are no particle systems, masks, or 3D engines). The value is in the **skill library** and **design-system library**: pre-built, brand-consistent starting points for high-quality static and animated artifacts.

## Where it fits Maven (and where it doesn't)

**Keep using Remotion** for OASIS YouTube intro/outro cards, ad templates, and any video that needs precise React-driven motion. Open-Design's video output is HTML→MP4 via [HyperFrames](https://github.com/heygen-com/hyperframes) — different mental model, less control than Remotion for our use cases.

**Adopt selectively** for these high-leverage skills:

| Skill | OASIS use case | Path in vendor |
|---|---|---|
| `social-carousel` | IG / LinkedIn 1080×1080 carousel posts | `vendor/open-design/skills/social-carousel/` |
| `magazine-poster` | Premium quote-card statics for the personal brand | `vendor/open-design/skills/magazine-poster/` |
| `email-marketing` | Table-safe HTML for SunBiz daily blast / OASIS outreach | `vendor/open-design/skills/email-marketing/` |
| `html-ppt-pitch-deck` | OASIS sales decks delivered as a single HTML file | `vendor/open-design/skills/html-ppt-pitch-deck/` |
| `digital-eguide` | Lead magnets for OASIS funnel | `vendor/open-design/skills/digital-eguide/` |
| `motion-frames` | Looping CSS keyframe stingers (lighter alternative to Remotion for kinetic typography) | `vendor/open-design/skills/motion-frames/` |
| `hyperframes` | Logo outros, social overlays — HTML→MP4 | `vendor/open-design/skills/hyperframes/` |

**Skills to ignore for now:** anything tied to product onboarding (`mobile-onboarding`, `mobile-app`) and the SaaS landing skills — we have direct landing-page work in the OASIS repo.

## Install — DO NOT run the full daemon

The full open-design stack (daemon + Next.js web UI + Electron) is overkill for our needs and runs poorly on our Windows + bash setup. **Lift skills directly from the cloned repo into Maven's existing skill registry.**

### Lift-and-adapt pattern

```bash
# Pick a skill
cp -r /c/Users/User/CMO-Agent/vendor/open-design/skills/social-carousel \
      /c/Users/User/CMO-Agent/skills/oasis-social-carousel/

# Read the skill contract
cat /c/Users/User/CMO-Agent/skills/oasis-social-carousel/SKILL.md

# Adapt to OASIS brand:
# 1. Replace generic colors with #0A1525 / #1FE3F0 from BRAND_SYSTEM.md
# 2. Swap fonts to Fraunces (headlines) + Inter (body)
# 3. Add the OASIS logo from ad-engine/public/oasis-ai-logo.jpg
# 4. Apply voice rules from BRAND_SYSTEM.md (banned words, em-dash style)
```

**Attribution:** retain Apache-2.0 attribution in any skill we adapt — open-design license headers stay.

### If we ever want the full stack

```bash
cd /c/Users/User/CMO-Agent/vendor/open-design
corepack enable
corepack pnpm --version    # expect 10.33.2
pnpm install
pnpm tools-dev run web     # starts daemon + Next.js
```

Requires Node 24 (`nvm install 24 && nvm use 24`). Auto-creates `.od/` (gitignored SQLite + artifacts).

## Skill anatomy (lift template)

Every skill in `vendor/open-design/skills/<name>/` follows this structure:

```
skill-name/
├── SKILL.md          # YAML frontmatter + instructions for the agent
├── template.html     # base HTML scaffold (sometimes)
├── assets/           # images, fonts (sometimes)
└── examples/         # reference outputs (sometimes)
```

`SKILL.md` frontmatter is parsed by `apps/daemon/src/skills.ts` (open-design's daemon). For Maven's purposes we read it directly — it tells us inputs, outputs, and the design-system contract.

## Design systems

`vendor/open-design/design-systems/<brand>/DESIGN.md` — 129 brand-consistent style guides (Linear, Stripe, Apple, Vercel, Notion, etc.). Useful as **reference material** when CC asks for an OASIS asset that should "feel like" one of those brands. Read but don't copy verbatim — OASIS has its own canon at `brain/brand-assets/oasis-ai/BRAND_SYSTEM.md`.

## Prompt templates

`vendor/open-design/prompt-templates/` — 93 prompts spanning image, video, HyperFrames. Particularly relevant:
- HyperFrame prompts → guide kinetic typography for OASIS hooks
- Image prompts → starting points for hero imagery (then refine with brand cyan + dark navy)

## Trigger phrases

| CC says | Action |
|---|---|
| "Make a quote card / social card for [topic]" | Lift `social-carousel` or `magazine-poster`, brand-adapt with BRAND_SYSTEM.md |
| "Build a sales deck" | Lift `html-ppt-pitch-deck` |
| "Lead magnet / e-guide" | Lift `digital-eguide` |
| "Email outreach template" | Lift `email-marketing` |
| "Kinetic typography stinger" | Try `motion-frames` (CSS) or `hyperframes` (HTML→MP4); fall back to Remotion if precision needed |
| "Show me how brand X handles this" | Read corresponding `vendor/open-design/design-systems/<brand>/DESIGN.md` |

## Update protocol

When upstream ships meaningful new skills:
1. `cd vendor/open-design && git pull`
2. Diff `skills/` to see what's new
3. If a new skill earns a Maven slot, copy + adapt + document here
4. Don't auto-pull — review first, then lift. Avoids picking up unstable changes.
