# Maven — Autonomous AI CMO

> Maven is CC's Chief Marketing Officer agent — brand, content, ads, funnels, distribution, growth, research. One third of a 3-agent AI C-Suite. Paired with Bravo (CEO) for strategy and Atlas (CFO) for spend approval.

```bash
python scripts/setup_wizard.py
```

Clone, run the wizard, and you have a fully configured AI CMO running on your identity, brand voice, and marketing goals. Total setup: ~5 minutes.

---

## What Maven Does

- **Runs paid ads** — Meta + Google Ads SDK integrations, campaign creation, budget optimization, A/B testing. Spend gate: every dollar requires Atlas pulse approval before launch.
- **Produces content** — 29 skills including content-engine (voice + calendar), elite-video-production (15-step cinematic pipeline), persona-content-creator, SEO/AEO, image-generation, competitive-intelligence.
- **Renders video ads** — `ad-engine/` sidecar (Remotion 4.0 + Meta Ads SDK, 5 production-ready templates). Cinematic output from a Python script.
- **Enforces brand voice** — marketing canon (Dunford, Hormozi, Sharp) baked into every draft. Anti-slop rules hard-coded. Your voice, not a generic AI voice.
- **Orchestrates funnels** — integrates with PULSE (ig-setter-pro) for DM automation, cc-funnel for lead capture, Skool for community growth.
- **Multi-platform publishing** — Zernio scheduling, Instagram native, email blasts (CASL-compliant). One batch session, five platforms.

## Architecture

```
CMO-Agent/
├── CLAUDE.md                   # Maven identity + runtime entry point
├── brain/                      # Agent memory, strategy, client profiles, doctrine
│   ├── SOUL.md                 # Immutable identity
│   ├── USER.template.md        # Operator profile template (committed)
│   ├── USER.md                 # Rendered operator profile (gitignored — local only)
│   ├── operator.profile.json   # Your credentials/identity (gitignored — local only)
│   ├── operator.profile.example.json  # Example for forks
│   ├── clients/                # Brand profiles (OASIS, PropFlow, Nostalgic, personal, SunBiz)
│   └── ...
├── skills/                     # 29 marketing skills
├── agents/                     # 16 specialized sub-agents
├── campaigns/                  # Active campaign artifacts
├── ad-engine/                  # Remotion video ad rendering
├── data/pulse/                 # cmo_pulse.json (Maven writes only here)
├── scripts/                    # Python + Node CLIs (personalize.py, scaffold.py, content_engine.py, ...)
└── memory/                     # Session logs, patterns, active tasks
```

## Fork Mechanism (V6 Scaffolding)

Maven ships as CC's personal agent. To run it as your own:

```bash
# 1. Edit brain/operator.profile.json with your identity
# 2. Preview what changes:
python scripts/scaffold.py --json
# 3. Apply the fork:
python scripts/scaffold.py --apply --backup
# 4. Render your personal brain/USER.md:
python scripts/personalize.py apply
```

`scaffold.py` rewrites CC's name, brand, email, and goals across all tracked files. `personalize.py` renders templated brain files from your profile. Both are idempotent and safe to re-run. Full docs: [`docs/INSTALL.md`](docs/INSTALL.md).

---

## C-Suite Integration

Maven operates under three non-negotiable rules:

1. **Spend Gate** — every paid-ad dollar requires Atlas approval via pulse round-trip
2. **Strategic Alignment** — reads `ceo_pulse.json` on every session for Bravo's current directive
3. **Sovereignty** — writes only to this repo; other agents READ from here

## Runtimes Supported

| Runtime | Entry point |
|---------|-------------|
| Claude Code | `CLAUDE.md` |
| Gemini CLI | `GEMINI.md` |
| Antigravity IDE | `ANTIGRAVITY.md` |

Each runtime reads the same `brain/` and `skills/`. All writes funnel to `data/pulse/cmo_pulse.json`.

---

*"Strategic Cohesion. Results Over Activity. Data-Driven. Aesthetic Excellence. Continuous Experimentation. Financial Discipline."* — Maven SOUL v1.0
