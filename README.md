# CMO Agent — Maven

> **Maven (CMO)** — brand, content, ads, funnels, distribution, growth, research. One third of CC's 3-agent AI C-Suite. Paired with **Bravo (CEO)** for strategy + clients + revenue, and **Atlas (CFO)** for money + tax + wealth. Multi-client marketing intelligence managing OASIS AI, PropFlow, Nostalgic Requests, CC's personal brand, and SunBiz Funding.

Built by one person with AI. Evolves every session.

**The C-Suite:**
- 🏛️ **Bravo (CEO)** — [CC90210/CEO-Agent](https://github.com/CC90210/CEO-Agent)
- 💰 **Atlas (CFO)** — [CC90210/CFO-Agent](https://github.com/CC90210/CFO-Agent)
- 🎨 **Maven (CMO)** — this repo: [CC90210/CMO-Agent](https://github.com/CC90210/CMO-Agent)

## What This Does

Maven is the marketing brain. Not a template bot — a cutting-edge, multi-client CMO that:

- **Runs paid ads** — Meta + Google Ads SDK integrations, campaign creation, budget optimization, A/B testing
- **Produces content** — 29 skills including content-engine (voice + calendar), elite-video-production (15-step cinematic pipeline), persona-content-creator, SEO/AEO, image-generation, competitive-intelligence
- **Renders video ads** — `ad-engine/` sidecar (Remotion 4.0 + Meta Ads SDK, 5 production templates)
- **Orchestrates funnels** — integrates with PULSE (ig-setter-pro) for DM automation, cc-funnel for lead capture, Skool for community
- **Respects the spend gate** — never launches a paid campaign without Atlas's approval via `cfo_pulse.json`

## Architecture

```
CMO-Agent/
├── CLAUDE.md           # Maven identity + entry point
├── brain/              # Agent memory, strategy, client profiles, doctrine
│   ├── SOUL.md         # Immutable identity
│   ├── SHARED_DB.md    # Supabase shared DB protocol
│   ├── clients/        # 5 client brand profiles (OASIS, PropFlow, Nostalgic, CC personal, SunBiz)
│   └── ...
├── skills/             # 29 marketing skills
├── agents/             # 16 specialized sub-agents (ad-strategist, content-creator, video-editor, etc.)
├── campaigns/          # Active campaigns — currently pulse-lead-gen
│   └── pulse-lead-gen/ # Free-PULSE-repo ad campaign + teaser + email templates
├── ad-engine/          # Cloned Shopify-Ad-Engine — Remotion video ad rendering
├── data/pulse/         # cmo_pulse.json (sovereign — Maven writes only here)
├── scripts/            # Python + Node CLIs
└── memory/             # Session logs, patterns, active tasks
```

## Quick Install (One Line) ⭐ Recommended

**macOS / Linux / WSL:**
```bash
curl -sSL https://raw.githubusercontent.com/CC90210/CMO-Agent/main/install/quickstart.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/CC90210/CMO-Agent/main/install/quickstart.ps1 | iex
```

What it does: auto-installs missing prereqs (python ≥3.10, git, node, npm), clones this repo into `~/maven-repo`, runs `npm install` for Remotion + ad-engine, walks you through an interactive wizard (Anthropic required; Meta Ads / Google Ads / ElevenLabs / Late optional). Total time: ~5–10 minutes including npm. Full details: [`install/README.md`](install/README.md).

---

## C-Suite Integration

Maven operates under three non-negotiable rules:

1. **Spend Gate** — every paid-ad dollar requires Atlas approval via pulse round-trip
2. **Strategic Alignment** — reads `ceo_pulse.json` on every session for Bravo's current directive
3. **Sovereignty** — writes only to this repo; other agents READ from here

See `brain/C_SUITE_ARCHITECTURE.md` in the Bravo repo for the full governance contract.

## Shared Database

All three C-Suite agents share Supabase project `phctllmtsogkovoilwos` as long-term memory. See `brain/SHARED_DB.md` for schema + conventions.

## Runtimes Supported

Maven can operate under multiple AI runtimes:
- **Claude Code** — this file (`CLAUDE.md`)
- **Gemini CLI** — `GEMINI.md`
- **Antigravity IDE** — `ANTIGRAVITY.md`

Each runtime reads the same brain + skills; all writes funnel to `data/pulse/cmo_pulse.json`.

---

*"Strategic Cohesion. Results Over Activity. Data-Driven. Aesthetic Excellence. Continuous Experimentation. Financial Discipline."* — Maven SOUL v1.0
