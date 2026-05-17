# Maven — Autonomous AI CMO

> Brand, content, ads, funnels, distribution, growth, research — all automated. One third of a 3-agent AI C-Suite. Paired with Bravo (CEO) for strategy and Atlas (CFO) for spend approval.

```bash
python scripts/setup_wizard.py
```

Clone, run the wizard, and you have a fully configured AI CMO running on your identity, brand voice, and marketing goals. Total setup: ~5 minutes.

---

## What you get

**Maven** is the CMO. It works alongside its sibling C-Suite — together they run the empire:

| Agent | Role | What it owns |
|---|---|---|
| **[Bravo](https://github.com/CC90210/CEO-Agent)** | CEO | Strategy, clients, outreach, revenue, daily ops |
| **[Atlas](https://github.com/CC90210/CFO-Agent)** | CFO | Tax, treasury, research, FIRE planning, financial advisory |
| **Maven** | CMO | Content, brand, ads, social, video pipeline |

All three siblings share the same V6.7+ substrate (state DB, hybrid retrieval, exec_guard, vocabulary layer) and coordinate via the cross-agent pulse protocol. Atlas has veto authority on every paid-ad dollar Maven spends; Bravo's directives in `ceo_pulse.json` set the strategic priority Maven optimizes for.

---

## What Maven actually does

### Content production

- **Three-pillar daily framework** — `brain/CONTENT_BIBLE.md` codifies Sobriety Log, Quote Drop, CEO Log. Every piece of content traces back to one of the three. Slop is hard-blocked by canonical voice rules.
- **Video editor** — `scripts/video_editor.py` runs an 8-step pipeline: silence trim, filler removal, scene detection, color grade, captions via Whisper word-level timestamps, brand intro/outro cards via Remotion, thumbnail generation, render. Cinematic output from raw iPhone footage.
- **Cinematic AI video** — `skills/cinema-worldbuilder/` is the Higgsfield Seedance director with five locked cinema modes and a character gate (no drift across shots). Stills from `skills/banana-pro-director/` feed in as visual references — same DNA across still and motion.
- **Brand voice MAML** — meta-learning adapter trains per-brand from <50 samples. Tone calibrates to operator (OASIS AI vs. SunBiz vs. personal) without retraining a base model.
- **Image generation** — Gemini Imagen primary, with claude-video for pre-publish QA. Brand assets verified against the OASIS color palette (`#0A1525` bg, `#1FE3F0` cyan) + Fraunces/Inter typography on every render.

### Social orchestration

- **Late/Zernio** for scheduled multi-platform publishing (Instagram, X, LinkedIn, Threads, TikTok, YouTube).
- **Instagram DM ia-engine** — Playwright-based `scripts/instagram_engine.py` handles auto-reply, booking confirmation, per-recipient cooldown. 13+ hardening commits.
- **Email blast** via `scripts/email_blast.py` → `send_gateway.py` chokepoint with CASL compliance, cooldowns, domain caps, draft critic, bounce circuit breaker.
- **Telegram bot** (see below) for live ops control from CC's phone.

### Ad spend (gated by Atlas)

- **Google Ads + Meta Ads SDKs** with dedicated sub-agents (`google-ads-specialist`, `meta-ads-specialist`, `ad-strategist`).
- **Spend gate** — every paid-ad dollar requires Atlas's approval via `data/pulse/cfo_pulse.json` round-trip. No `launch_campaign` call ships without it.
- **5 production-ready video ad templates** in `ad-engine/` (Remotion + Meta Ads SDK sidecar), customizable per brand.
- **send_gateway notifications** — every campaign launch, daily-cap threshold, killswitch fire, draft-critic reject routes to CC's phone via `scripts/notify.py` with category filtering.

### Advanced reasoning stack

- **GNN skill router** — graph neural net over the capability graph routes intents to the right skill, replacing trigger-overlap heuristics.
- **RLHF outreach optimizer** — learns from accept/reject feedback on cold DMs and email subject lines.
- **TFT engagement forecasting** — Temporal Fusion Transformer projects engagement/follower trajectory per platform; informs the content calendar.
- **Neural Turing Machine memory** — long-horizon brand-arc memory across campaigns and quarters.
- **Neuro-symbolic gate** — symbolic rules (CASL, brand-voice canon, send-gateway invariants) wrapped around the LLM so it can't override hard constraints.

### Brand system

- **OASIS AI brand canon** — `brain/brand-assets/oasis-ai/BRAND_SYSTEM.md` is the source of truth: palette, typography, voice rules, banned-word list, animation language, 7-point asset verification checklist.
- **Multi-tenant brand profiles** — `brain/clients/` carries separate brand profiles for OASIS, PropFlow, Nostalgic, personal, SunBiz. New operators clone-and-edit, never start from scratch.

### Cross-agent IPC

- **4-agent system** — Bravo (CEO), Atlas (CFO), Maven (CMO, this repo), Aura (Life/Home). Each agent writes only its own pulse file; others read cross-repo.
- **agent_inbox** async messaging — `scripts/agent_inbox.py post|list` for cross-agent requests that don't fit the pulse cadence.
- **Shared event bus** — every pulse refresh, send_gateway block, and brand-violation emits to the Postgres `agent_events` substrate the siblings all subscribe to.

### V6.7+ substrate (shared with siblings)

- **State engine** — `state/empire_state.db` (SQLite/WAL) holds heartbeats, session log, active tasks. Single-writer proxy: `scripts/state_manager.py`. Markdown mirrors (`brain/STATE.md`, `memory/SESSION_LOG.md`, `memory/ACTIVE_TASKS.md`) auto-regenerate.
- **Hybrid semantic memory** — FTS5 + LanceDB cosine RRF fusion over 135+ markdown files. `scripts/memory_retriever.py query "<topic>"` is the entry point — used in place of whole-file Read on every cold turn.
- **Exec guard + secret guard + state guard** — same three policy gates Bravo runs. Three modes per guard (off/report/enforce) via env var.
- **Research-fetch ladder** — `scripts/research_fetch.py` auto-escalates Firecrawl → CloakBrowser → Browser Harness → Playwright with per-domain reputation memory at `state/site_reputation.db`. Mandatory tier for Cloudflare / DataDome / Akamai protected scraping.
- **Daily prep table** — `scripts/snapshots/cmo_briefing_snapshot.py` writes `state/snapshots/latest_cmo_briefing.json` every 06:00 (3-agent pulse aggregation, Late inventory, ad performance, brand health, open/blocked tasks, MRR target tracking).

---

<details>
<summary><strong>V6 architecture timeline</strong></summary>

| Version | Date | Primary deliverable |
|---|---|---|
| **V1.0** | Initial | 29 marketing skills + 16 sub-agents + Remotion ad-engine sidecar |
| **V1.1** | Spring 2026 | Added cross-cutting agents (reviewer, researcher, writer) for Bravo parity |
| **V1.2** | Apr 2026 | 4-agent pulse protocol (Bravo/Atlas/Maven/Aura), spend gate via cfo_pulse.json round-trip |
| **V1.3** | Apr 2026 | Standalone Maven Telegram bot, multi-machine lock arbitration via `bridge_lock.py` |
| **V6.7 Apex** | 2026-05-16 | Substrate ported from Bravo: state engine, hybrid retrieval, exec_guard, stealth tier, daily prep snapshot |
| **V6.8** | 2026-05-16 | Vocabulary layer (CONTEXT.md), ADRs (`docs/adr/`), skill frontmatter conventions, lifecycle dirs |
| **V6.8.1** | 2026-05-16 | All 5 entry points (CLAUDE/AGENTS/OPENCODE/ANTIGRAVITY/GEMINI) reference CONTEXT.md on operational turns |

Source of truth: [`CLAUDE.md`](CLAUDE.md) and [`brain/CAPABILITIES.md`](brain/CAPABILITIES.md). The README is the curated surface; the graph is the inventory.

</details>

---

## Capability catalog

<!-- STATS:skills-->**60 skills**<!-- /STATS --> · <!-- STATS:sub_agents-->**19 sub-agents**<!-- /STATS --> · <!-- STATS:scripts-->**73 scripts**<!-- /STATS --> · <!-- STATS:workflows-->**11 workflows**<!-- /STATS --> · <!-- STATS:mcp_servers-->**6 MCP servers**<!-- /STATS --> (counts auto-regenerated by [`scripts/update_readme_stats.py`](scripts/update_readme_stats.py) — `--check` exits 1 on drift)

The README highlights the parts worth highlighting. Full inventory lives in a machine-readable graph: [`brain/CAPABILITY_GRAPH.json`](brain/CAPABILITY_GRAPH.json). It's auto-discovered from frontmatter and MCP configs; never hand-maintained.

```bash
# Resolve an intent to its best-fit skill
python scripts/capability_query.py resolve "render Instagram carousel"

# Verify a node's hard dependencies (env vars, daemons, state files)
python scripts/capability_query.py check-deps cinema-worldbuilder

# Add a new skill end-to-end (frontmatter + graph rebuild + self-audit)
python scripts/register.py skill my-new-skill --description "..." --triggers "..."
```

**Domain breakdown:**

- **Marketing skills** (~32) — content-engine, persona-content-creator, SEO/AEO, competitive-intelligence, image-generation, elite-video-production (15-step cinematic), cinema-worldbuilder, banana-pro-director, brand-voice-MAML, social-carousel, magazine-poster, email-marketing, lead-magnet, etc.
- **Cross-cutting skills** (~22) — systematic-debugging, browser-harness, e2e-testing, mcp-operations, security-protocol, memory-management, cli-anything, hooks-automation, codex-delegation, anti-drift, self-healing, etc.
- **Workflows** (11) — campaign-create, ad-launch, content-plan, performance, optimize, report, health, prime, sync, debug, post-publish-qa.

Full inventory: [`brain/CAPABILITIES.md`](brain/CAPABILITIES.md).

---

## Specialized sub-agents

19 personas live in [`agents/`](agents/) — each one is a focused decision-maker spawned via the Task tool:

| Cluster | Agents |
|---|---|
| **Strategy & analytics** | `ad-strategist`, `analytics-analyst`, `seo-specialist` |
| **Content & creative** | `content-creator`, `video-editor`, `image-generator`, `media-manager` |
| **Platform execution** | `google-ads-specialist`, `meta-ads-specialist`, `email-outbound`, `audience-builder` |
| **System** | `architect`, `debugger`, `explorer`, `documenter`, `workflow-builder` |
| **Cross-cutting (Bravo parity)** | `reviewer`, `researcher`, `writer` |

---

## Telegram surface

Maven runs its own Telegram bot — distinct from Bravo's and Atlas's. The three never conflict because each polls a different token, and [`scripts/bridge_lock.py`](scripts/bridge_lock.py) prevents two machines from polling the same token at once (Windows + Mac dual-paired setup works without conflict).

**Setup (one-time):**

1. Message `@BotFather`, send `/newbot`, copy the token.
2. Add `MAVEN_TELEGRAM_BOT_TOKEN=<token>` + `MAVEN_TELEGRAM_ALLOWED_USERS=<your-user-id>` to `.env.agents`.
3. Set cross-agent file paths in `.env.agents` (defaults to Windows layout):
   ```
   BRAVO_REPO=/Users/<you>/Business-Empire-Agent
   ATLAS_REPO=/Users/<you>/APPS/CFO-Agent
   AURA_REPO=/Users/<you>/AURA
   MAVEN_REPO=/Users/<you>/CMO-Agent
   ```
4. `node telegram_agent.js` — lock file at `tmp/maven_telegram.lock.json` blocks duplicate pollers.

**In-chat commands** (authorized chat IDs only):

| Command | What it does |
|---|---|
| `/status` | Pulse status across Bravo/Atlas/Aura/Maven |
| `/spend` | Atlas spend-gate summary (cfo_pulse approvals) |
| `/campaigns` | send_gateway daily stats |
| `/killswitch` · `/unleash` | Toggle MAVEN_FORCE_DRY_RUN |
| `/pulse` | Refresh cmo_pulse.json |
| `/sync` | Full state_sync (STATE + SESSION_LOG + cmo_pulse + mem0) |
| `/audit` | Health score across credentials, scripts, MCPs |
| `/tests` | Run all test files, report pass/fail |
| `/inbox` | Unread agent_inbox messages addressed to Maven |
| `/post bravo\|atlas\|aura subject \|\| body` | Cross-repo agent_inbox post |
| Plain text | Spawned to Maven's Claude Code session |

---

## Vendor integrations

External repos + AI-platform director skills wired in. Full docs in [`brain/integrations/`](brain/integrations/).

| Tool | Path | Role | Trigger |
|---|---|---|---|
| **claude-video** | `vendor/claude-video/` | Video understanding (frames + transcript). Pre-publish QA, competitive teardowns, bug-repro. | "QA this ad" / "what's the hook on this Reel" |
| **open-design** | `vendor/open-design/` | 58 skills + 129 design systems. Lift skills like `social-carousel`, `magazine-poster`, `email-marketing` and re-brand to OASIS. | "Make a social card" / "build a deck" / "lead magnet" |
| **graphify** | (Bravo-owned, reads from `Business-Empire-Agent/graphify-out/`) | Knowledge graph + Obsidian vault export. | "What playbooks touch X" / "Obsidian graph" |
| **Higgsfield director skills** | `skills/cinema-worldbuilder/` + `skills/banana-pro-director/` | Seedance cinematic video + Banana Pro / Soul Cinema / GPT-2 image prompt grammars. Five cinema modes, locked photoreal stack, character gate. | "make a Seedance prompt" / "build a character sheet" / "scene plate" |

**Lift-and-adapt rule for open-design skills:** copy from `vendor/open-design/skills/<name>/` → into `skills/oasis-<name>/` → swap colors to `#0A1525` + `#1FE3F0`, fonts to Fraunces + Inter, voice rules from `BRAND_SYSTEM.md`. Retain Apache-2.0 attribution.

---

## Fork mechanism (V6 scaffolding)

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

## Under the hood

- **Python 3.12** + **Node 20** runtime
- **Shared Supabase** (Postgres + RLS + pgvector) — project `phctllmtsogkovoilwos`. All three C-Suite agents share the same DB; tenant-scoped by agent.
- **Anthropic Claude** (Opus 4.6 / Sonnet 4.6 / Haiku 4.5) primary; OpenAI / OpenRouter / Groq / DeepSeek / Ollama as fallbacks
- **5 runtime entry points** — `CLAUDE.md` (Claude Code), `AGENTS.md` (Codex/Cursor/Aider), `OPENCODE.md`, `ANTIGRAVITY.md`, `GEMINI.md`. All five wake Maven up with the same identity, state, and mission. Lockstep sync enforced by RULE 0.
- **6 MCP servers** — google-ads-mcp, meta-ads-mcp, playwright, context7, memory, sequential-thinking (n8n + Late routed through CLI tools instead of MCPs for reliability)
- **Ad-engine sidecar** — `ad-engine/` (Remotion 4.0 + Meta Ads SDK + Shopify), 5 production video templates, OASIS-branded intro/outro cards
- **Anti-slop hard rules** — banned-word list, generic-bullet detection, "Unlock the power of..." opener blocked, brand-voice canon enforced via neuro-symbolic gate
- **Self-audit gate** — `python scripts/self_audit.py` enforces graph health, orphan detection, frontmatter compliance. Verdict must be `HEALTHY` to ship.

See [`brain/CAPABILITIES.md`](brain/CAPABILITIES.md) for the full inventory and [`CONTEXT.md`](CONTEXT.md) for the canonical Maven-domain vocabulary (Sobriety Log, Quote Drop, CEO Log, brand assets, pulse, drop, pillar pacing).

---

## Pricing

**Free.** MIT-licensed. Fork it, scaffold it for your operator identity, run it on your infrastructure. No SaaS tier.

If you want help installing or customizing it for your business: [open an issue](https://github.com/CC90210/CMO-Agent/issues) or reach out to the original operator below.

---

## Built by

[Conaugh McKenna](https://oasisai.work) (CC) — founder, [OASIS AI Solutions](https://oasisai.work). One operator's working AI CMO, designed from the start to fork for anyone else.

[MIT licensed](LICENSE) · [Issues](https://github.com/CC90210/CMO-Agent/issues)

## Obsidian
- [[CLAUDE]] · [[CONTEXT]] · [[brain/SOUL]] · [[brain/CAPABILITIES]] · [[docs/INSTALL]]

> *"Strategic cohesion. Results over activity. Data-driven. Aesthetic excellence. Continuous experimentation. Financial discipline."* — Maven SOUL v1.0
