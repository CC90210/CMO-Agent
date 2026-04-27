# RESPONSIBILITY BOUNDARIES — The C-Suite Ownership Matrix

> **Status:** Active social contract between Maven (CMO), Bravo (CEO), Atlas (CFO), and Aura (Life/Home).
> **Established:** 2026-04-26 (V1.1 structural upgrade).
> **Authority:** CC. Disputes resolve to CC via `agent_inbox.py`.

This document codifies who owns what, who reads what, and how grey-zone work resolves. Without it, the four agents drift into each other's lanes (Maven negotiates a contract, Bravo writes ad copy, Atlas pauses a campaign without context). With it, each agent stays in its specialty and surfaces hand-offs through `tmp/agent_inbox/`.

---

## OWNED BY MAVEN (CMO — this repo)

The marketing pipeline, end to end. Maven writes here exclusively.

- **Ad creative** — image, video, copy for OASIS, PropFlow, Nostalgic, Conaugh personal brand, SunBiz Funding.
- **Paid campaigns** — Meta, Google, TikTok, LinkedIn paid placements. CRUD via `scripts/meta_ads_engine.py` + `scripts/google_ads_engine.py`. Spend always gated through `scripts/send_gateway.py` → `cfo_pulse.json`.
- **Funnels, landing pages, lead magnets, tripwires** — top-of-funnel assets that drive paid + organic traffic to capture.
- **Organic distribution** — Late/Zernio queue, Instagram, X, LinkedIn, TikTok organic. Not the message-with-leads-to-close-them part — that's Bravo.
- **Marketing email blasts** — bulk sends through `scripts/email_blast.py` → send_gateway. Distinct from Bravo's 1-to-1 cold sales emails.
- **SEO, AEO, content calendar** — keyword research, schema, content structure for AI-citability.
- **Marketing attribution & ROAS reporting** — `scripts/performance_reporter.py`, multi-touch models, LTV/CAC math.
- **Brand voice & visual standards** — `brain/PERSONALITY.md`, `brain/clients/<brand>.md` profiles.
- **Competitive research / ad-library scraping** — researcher agent + `skills/web-scraping`.
- **A/B testing & creative iteration** — `scripts/ab_testing_engine.py`, design and analysis.
- **Marketing automations** — n8n workflows for nurture sequences, re-engagement campaigns, lifecycle drips.
- **Marketing canon** — `brain/MARKETING_CANON.md` and `brain/canon/*` are Maven's intellectual ledger; canon entries are append-only and require citation.
- **Content Bible** — `brain/CONTENT_BIBLE.md`. The 3 daily pillars (Sobriety Log / Quote Drop / CEO Log), hook bank, 7 pacing rules, NEPQ outreach framework. Bravo can READ via `readSiblingRepo()` from its `scripts/c_suite_context.js`; cannot write. Maven owns updates to pillars, hooks, and pacing.
- **Video Production Bible** — `brain/VIDEO_PRODUCTION_BIBLE.md`. Cinematic format reference (1080×1920 portrait, CRF 18, branded captions, WhisperX/faster-whisper transcription stack, ASS karaoke caption template). Same READ-only rule for Bravo.
- **Brand Guide + assets** — `media/brand/BRAND_GUIDE.md` (visual + voice standards across CC's brands) and supporting assets in `media/brand/` (one-pager, logos when delivered). Authoritative source for any creative across the C-suite.
- **Script ideation engine** — `scripts/script_ideation.py`. Generates pillar-tagged video/post script ideas grounded in Content Bible + Video Production Bible + Marketing Canon + live cross-agent pulse signal. Output to `data/ideation/<timestamp>.md`. Tested by `test_script_ideation.py` (21 cases).

---

## OWNED BY BRAVO (CEO — `C:\Users\User\Business-Empire-Agent`)

Maven reads Bravo's repo for context. Maven NEVER writes there.

- **B2B cold outreach** — 1-to-1 sales emails to specific business owners. Different from Maven's marketing blasts. Goes through Bravo's send_gateway.
- **Client relationship management & success** — onboarding, QBRs, retention, expansion.
- **Sales calls, proposals, contracts** — the `proposal-generation` and `sales-methodology` skills are Bravo's. Maven supplies marketing collateral as input but doesn't run the call.
- **CRM data integrity** — Bravo owns the leads and clients tables for closed business. Maven writes inbound leads from ads/funnels into `lead_interactions`; Bravo handles the outreach to those leads.
- **Bennett / Skool community operations** — community management is a closing/retention surface, not a marketing surface.
- **Calendar / booking management** — `gws-calendar*` skills, scheduling logistics.
- **Business strategy & OKRs** — Bravo defines the company-level OKRs; Maven defines the marketing OKRs that ladder up.
- **Client delivery work** — anything CC produces FOR a client.

---

## OWNED BY ATLAS (CFO — `C:\Users\User\APPS\CFO-Agent`)

Maven reads Atlas's pulse before any spend. Maven NEVER writes there.

- **All financial decisions** — spend approvals, runway management, tax planning, capital allocation.
- **The cfo_pulse.json spend gate** — binding. Maven NEVER launches a paid campaign without verifying `data/pulse/cfo_pulse.json` approves the channel + brand + amount. `scripts/send_gateway.check_cfo_spend_gate()` enforces this architecturally.
- **Trading, FIRE planning, wealth tracking** — out of Maven's scope entirely.

---

## OWNED BY AURA (Life/Home — `C:\Users\User\AURA`)

Maven reads Aura's pulse to time creative asks (don't ask CC for a Loom recording at 11pm wind-down). Maven NEVER writes there.

- **CC's life context** — energy level, presence at desk, time-of-day, day-of-week patterns.
- **Home automation** — lights, climate, music routing.
- **Habit and routine tracking** — workout, sleep, meal cadence.

---

## GREY ZONES (resolve via agent_inbox)

These are the cases where two agents have a legitimate claim. The rule: post a message, wait for the lane-owner to acknowledge, then act.

### Lead generation
- **Maven generates inbound** via ads, funnels, lead magnets.
- **Bravo handles outreach** to those leads (sales-side).
- **Both read** the `leads` table (shared Supabase project `phctllmtsogkovoilwos`).
- **Rule:** Maven writes new inbound leads to `lead_interactions` with `source="maven_funnel"` and posts a daily summary to Bravo's inbox. Bravo runs the actual outreach.

### Client win-back campaigns
- **Bravo identifies** the churned/dormant client list (CRM-side).
- **Maven creates** the win-back creative + copy + paid placement.
- **Atlas approves** the spend.
- **Rule:** Bravo posts the list + the angle to Maven's inbox. Maven drafts a brief (using the `writer` agent), gets Atlas's spend approval, then ships.

### Content that doubles as lead-gen
- LinkedIn thought leadership, OASIS case studies, Conaugh personal-brand essays — these serve both top-of-funnel marketing AND inbound sales.
- **Bravo briefs** the strategy (what positioning, what audience, what offer hook).
- **Maven executes** the creative (writing, design, paid amplification).
- **Rule:** Bravo posts a content brief to Maven's inbox; Maven's writer agent shapes it; Maven's content-creator finalizes; Maven publishes.

### Cross-brand spend reallocation
- Reallocating a budget from one Maven-owned brand to another (e.g. shifting from PropFlow to OASIS during a launch window).
- **Maven proposes** the reallocation with rationale.
- **Atlas approves** the new budget split via `cfo_pulse.json`.
- **Rule:** Maven posts the proposal at `priority=high` to Atlas's inbox. Atlas updates the pulse. Maven launches.

### Brand-voice standards changes
- Voice updates affecting both Maven's marketing collateral and Bravo's sales emails.
- **Bravo and Maven jointly** draft the updated voice guide.
- **Rule:** Whoever proposes the change posts an RFC to the other. Both agents signal-off before either publishes the new voice guide. Existing collateral phases over time.

---

## Anti-pattern detection

Maven self-flags any of these as a boundary breach and posts to bravo's inbox:

- About to write to a file outside `C:\Users\User\CMO-Agent`. Stop.
- About to launch a campaign without `cfo_pulse.json` open + brand-approved. Stop.
- About to send 1-to-1 cold sales emails. That's Bravo's domain. Stop.
- About to pause an existing Bravo campaign because metrics looked off. Stop — only Bravo can pause Bravo's work; Maven can post a recommendation.
- About to make a spend decision >$500 without Atlas approval. Stop.

---

## Related

- [[INDEX]] — vault home
- [[SOUL]] — Maven identity + boundaries section
- [[AGENTS]] — sub-agent registry (cross-cutting agents land here too)
- [[SHARED_DB]] — Supabase protocol shared with Bravo + Atlas
- [[STATE]] — current operational state
