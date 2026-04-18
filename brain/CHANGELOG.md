# CHANGELOG

---

## V2.0 — 2026-03-10
**Major Release — SunBiz Funding Identity & MCA Pivot**

### Changed (BREAKING)
- **Client identity:** Generic "Lending Company" → **SunBiz Funding** (MCA consolidation & business funding)
- **Product type:** Business Term Loans → **Merchant Cash Advance (MCA) consolidation + growth capital**
- **Language rules:** "Loan" → NEVER. Now "advance," "funding," "capital" everywhere
- **SOUL.md rewritten:** AdVantage V2.0 with SunBiz philosophy, multi-phase consolidation approach, MCA brand voice
- **CLIENT.md fully rewritten:** SunBiz ICP (consolidation merchants $25K-$500K/mo revenue, 2-5 MCA positions), negative targeting, language rules, objection handling, MCA-specific lead scoring, JotForm integration
- **All CTAs now link to JotForm** — single lead capture destination for every ad
- **North Star Metric:** CPL → CPQL (Cost Per Qualified Lead)

### Rewritten
- `agents/content-creator.md` — MCA copywriting frameworks (PAS, Multi-Phase Education, Before/After, Objection Pre-empt), headline templates, language rules
- `agents/image-generator.md` — 5 MCA prompt templates (before/after, roadmap, payment table, growth capital, stories), analytical/infographic visual direction
- `skills/ad-copywriting/SKILL.md` — MCA terminology, compliance red lines, safe copy patterns, funnel-stage CTAs
- `skills/lead-generation/SKILL.md` — JotForm integration, MCA lead scoring, Higher Intent forms, speed-to-lead automation
- `skills/image-generation/SKILL.md` — Updated API examples for `generate_consolidation_ad()` and `generate_growth_ad()`
- `scripts/imagen_generate.py` — Replaced `generate_lending_ad()` with `generate_consolidation_ad()` (3 styles) + `generate_growth_ad()`
- `CLAUDE.md` — SunBiz identity, MCA compliance rule
- `ANTIGRAVITY.md` — SunBiz identity, MCA language rules, CPQL metric

### Added
- MCA-specific market research (`brain/LENDING_AD_RESEARCH.md`) — 40+ sources
- SunBiz SOP integration — ICP, multi-phase approach, SEO keywords, compliance
- JotForm as universal CTA destination
- Objection handling frameworks in ad copy
- Before/After consolidation visual template system
- Negative targeting rules (exclude <$15K revenue, >7 NSFs, death spiral merchants)

### Counts
- Agents: 15 | Skills: 18 | Workflows: 11 | MCP Servers: 8 | Scripts: 6

---

## V1.2 — 2026-03-10
**Enhancement — AI Image Generation, Lead Generation, Autonomous Posting**

### Added
- Image generator agent (`agents/image-generator.md`) — Gemini Imagen ad creative generation with 3 prompt formulas
- Gemini Imagen script (`scripts/imagen_generate.py`) — Python integration: `generate_lending_ad()`, `generate_ad_variants()`, `generate_all_sizes()`
- Image generation skill (`skills/image-generation/SKILL.md`) — prompt engineering, conversion drivers, quality checklist, iteration process
- Lead generation skill (`skills/lead-generation/SKILL.md`) — Meta Lead Form API, lead scoring, follow-up sequences, tracking/attribution
- `GEMINI_API_KEY` added to `.env.agents.template`
- Autonomous posting schedule in CLIENT.md (Mon/Wed/Fri/Sat)
- Ad creative style guide from competitor research (color psychology, layout patterns, proven CTR drivers)

### Updated
- CLIENT.md extensively rewritten with business lending context, loan tiers ($50K-$500K), ad style guide
- AGENTS.md updated to 15 agents (was 14) — added image-generator
- CAPABILITIES.md updated to 18 skills (was 16), added Gemini Imagen tool section
- CLAUDE.md updated with new agent and skill counts
- ANTIGRAVITY.md updated with image-generator in dispatch table, skill count to 18
- All orchestration matrices updated to include image-generator

### Counts
- Agents: 15 | Skills: 18 | Workflows: 11 | MCP Servers: 8 | Scripts: 6

---

## V1.1 — 2026-03-10
**Enhancement — SEO, Video, Billing, Antigravity Format**

### Added
- SEO specialist agent (`agents/seo-specialist.md`) — keyword research, Quality Score, AEO, landing page audits
- Video editor agent (`agents/video-editor.md`) — FFmpeg pipeline, Whisper captioning, platform formatting
- SEO/AEO skill (`skills/seo-aeo/SKILL.md`) — comprehensive keyword research, schema markup, featured snippet targeting
- Video editing skill (`skills/video-editing/SKILL.md`) — full production pipeline with FFmpeg commands
- Billing & payment documentation in CAPABILITIES.md (how ad spend works via API)
- Proper Antigravity workflow format (YAML front matter + `// turbo-all` on all 11 workflows)

### Updated
- ANTIGRAVITY.md rewritten to match Business Empire Agent format (WHAT/WHY/HOW structure, full rules)
- AGENTS.md updated to 14 agents (was 12)
- CAPABILITIES.md updated to 16 skills (was 14), added video tools + billing docs
- CLAUDE.md updated with new agent and skill counts
- All orchestration matrices updated to include seo-specialist and video-editor
- All workflow files now have proper Antigravity format

### Counts
- Agents: 14 | Skills: 16 | Workflows: 11 | MCP Servers: 8 | Scripts: 5

---

## V1.0 — 2026-03-10
**Initial Release — Full Infrastructure Build**

### Added
- Complete agent file structure (brain, memory, agents, skills, scripts, workflows)
- 3 entry points: CLAUDE.md (Opus), ANTIGRAVITY.md (IDE), GEMINI.md (Speed)
- 12 specialized sub-agents for marketing operations
- 14 skills covering Google Ads, Meta Ads, campaign creation, ad copywriting, audience targeting, optimization, reporting, and more
- 11 Antigravity workflow commands
- 10-step BRAIN_LOOP reasoning protocol (LATS + Reflexion inspired)
- 5-dimension self-healing system
- Lending industry compliance framework (ECOA, TILA, Meta Special Ad Category)
- MCP server configurations for 8 MCP servers
- Python SDK fallback scripts for both platforms
- Memory system with campaign tracking, performance logging, pattern recognition

### Pending
- Google Ads API credential setup
- Meta Marketing API credential setup
- MCP server installation and testing
- First campaign launch
