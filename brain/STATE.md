---
tags: [state, ephemeral]
---

# STATE — Maven V1.0 Operational State

> Last updated: 2026-04-18
> Session: Clean split from SunBiz-Marketing. Maven is fully operational as standalone CMO-Agent.

---

## Identity
- **Agent:** Maven (CMO)
- **Project:** `C:\Users\User\CMO-Agent`
- **GitHub:** CC90210/CMO-Agent
- **Version:** 1.0 (fresh split from AdVantage V2.0 / SunBiz-Marketing)

## C-Suite Position
- **CFO (Atlas):** `C:\Users\User\APPS\CFO-Agent` — read `data/pulse/cfo_pulse.json` for spend gate
- **CEO (Bravo):** `C:\Users\User\Business-Empire-Agent` — read `data/pulse/ceo_pulse.json` for directives
- **CMO (Maven, self):** write `data/pulse/cmo_pulse.json` only — never touch others

## System Health

| Component | Status | Notes |
|-----------|--------|-------|
| Identity docs | OK | SOUL.md, CLAUDE.md, GEMINI.md, ANTIGRAVITY.md all Maven V1.0 |
| Clients | OK (5 profiles) | OASIS AI, PropFlow, Nostalgic, CC personal, SunBiz (see `brain/clients/`) |
| Skills | OK (29 loaded) | 20 AdVantage heritage + 10 migrated from Bravo |
| Sub-agents | OK (16 agents) | ad-strategist, content-creator, video-editor, etc. |
| ad-engine | OK (cloned) | Remotion 4.0 + Meta Ads SDK in `ad-engine/`. Run `cd ad-engine && npm install && npx remotion studio` |
| Pulse protocol | OK (tested) | 14/15 stress tests pass. cmo_pulse.json sovereign in `data/pulse/` |
| Shared Supabase | OK (documented) | `brain/SHARED_DB.md`. Project: phctllmtsogkovoilwos. Tag rows with agent='maven'. |
| ENV / API health | Verify on next session | Re-check Google Ads + Meta Ads tokens |
| Git | OK (clean) | Pushed to origin/main (CC90210/CMO-Agent) |

## Active Campaigns
- **pulse-lead-gen** — Free PULSE repo lead magnet for OASIS AI
  - Playbook: `campaigns/pulse-lead-gen/creative/ad-playbook.md` (4 hooks, reels, statics, retargeting)
  - Teaser email: `campaigns/pulse-lead-gen/emails/teaser.md`
  - Repo delivery email: `campaigns/pulse-lead-gen/emails/full-delivery.md`
  - Setup guide for the free repo: `campaigns/pulse-lead-gen/SETUP.md`
  - Status: Code-complete. Ad launch blocked pending Atlas spend approval.

## Known Blockers
- No active paid campaigns. Atlas approval required before Meta/Google ad launch (see pulse protocol).
- Meta App Review for ig-setter-pro (PULSE) is pending — when approved, PULSE auto-reply will fire for cold DMs.

## Next Session Priorities
1. Read `data/pulse/cfo_pulse.json` to confirm runway + spend gate status
2. Read `data/pulse/ceo_pulse.json` to confirm Bravo's current directives
3. Execute `pulse-lead-gen` ad campaign when spend gate opens
4. Deep content research for OASIS (see `brain/clients/oasis-ai.md` + `campaigns/pulse-lead-gen/`)

## Focus Areas (Medium-Term)
- OASIS AI lead-gen via pulse-lead-gen campaign (primary)
- CC's personal brand content engine (top-of-funnel for OASIS)
- PropFlow launch campaign (when product ships)
- SunBiz legacy maintenance (`scripts/email_outbound.py` daily blast — note: email_outbound lives in the separate SunBiz-Marketing repo now, invoke via subprocess if needed)

## Memory Health
- SESSION_LOG: will receive entries per session
- PATTERNS: carried over from AdVantage era, still valid for general marketing
- MISTAKES: audit on first full session — avoid repeating AdVantage-era single-client thinking
