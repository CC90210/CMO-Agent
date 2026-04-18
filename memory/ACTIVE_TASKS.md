# ACTIVE TASKS — Maven (CMO)

> Updated at task boundaries and session end.
> Last refresh: 2026-04-18 (post-split)

---

## P0 — Critical (Next Session)

- [ ] Verify Google Ads API tokens still valid (`.env.agents`)
- [ ] Verify Meta Ads API tokens still valid (`.env.agents`)
- [ ] Read Atlas's `cfo_pulse.json` for current spend gate + runway
- [ ] Read Bravo's `ceo_pulse.json` for current directives + client priorities
- [ ] Install ad-engine dependencies: `cd ad-engine && npm install` (first time only)

## P1 — High Priority (This Week)

### pulse-lead-gen campaign (primary revenue initiative)
- [ ] Record 90-second Loom for pre-call teaser (script ready in `campaigns/pulse-lead-gen/teaser/README.md`)
- [ ] Finalize 4 Reel variants from `ad-playbook.md` (authority / curiosity / proof / contrarian)
- [ ] Submit spend request to Atlas ($40/day total across 4 ad sets = $1,200/mo) via `data/pulse/cmo_pulse.json`
- [ ] Wait for Atlas approval in `APPS/CFO-Agent/data/pulse/cfo_pulse.json`
- [ ] Launch Meta campaign only after approval (per C-Suite spend-gate protocol)

### Content engine (top-of-funnel for OASIS)
- [ ] Build 7-day rolling content calendar for CC's personal brand (`skills/content-engine/SKILL.md`)
- [ ] Produce at least 1 long-form video per day using `skills/elite-video-production/SKILL.md`
- [ ] Cross-post to IG / TikTok / LinkedIn / YouTube Shorts / X

## P2 — Medium Priority

- [ ] Research competitive landscape for OASIS (see `skills/competitive-intelligence/SKILL.md`)
- [ ] Draft PropFlow launch campaign (pending product beta — coordinate with Adon)
- [ ] Light maintenance on SunBiz email blast (shell out to SunBiz-Marketing repo's `scripts/email_outbound.py`)

## P3 — Backlog

- [ ] Add new client profiles if CC takes on additional brands
- [ ] Integrate Nostalgic Requests promotion (low priority — CC handles DJ content organically)
- [ ] Build retargeting audiences for pulse-lead-gen (Meta Pixel data needed first)

---

## Context Pointers (Start Here If New Session)

1. **Read before acting:** `brain/SOUL.md`, `brain/STATE.md`, `brain/SHARED_DB.md`
2. **Client brand voice lives in:** `brain/clients/*.md` (5 files, one per managed brand)
3. **Active campaign materials:** `campaigns/pulse-lead-gen/`
4. **Video rendering:** `ad-engine/` (Remotion + 5 templates)
5. **Sibling agents:** Bravo CEO at `C:\Users\User\Business-Empire-Agent`, Atlas CFO at `C:\Users\User\APPS\CFO-Agent`
6. **C-Suite contract:** `C:\Users\User\Business-Empire-Agent\brain\C_SUITE_ARCHITECTURE.md`
