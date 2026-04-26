---
tags: [verticals, product-architecture, business-in-a-box]
---

# PRODUCT VERTICALS — Maven's Pluggable Knowledge Packs

> Maven is a clonable CMO-in-a-box (per Bravo's PRODUCT_ARCHITECTURE). Every buyer gets core brain + core skills + 1-2 vertical packs activated based on their business type. This file is the master index of which packs exist, what each contains, and which canon they draw from.
>
> Canon-aware summary. Full content lives in `skills/verticals/<pack>/`.

---

## How Verticals Work

Each vertical is a folder under `skills/verticals/` containing 4 canonical files:

- **lead-channels.md** — channels ranked + what works at sub-$50K MRR
- **pricing-playbook.md** — pricing models + offer structure
- **objection-handlers.md** — 8-12 common objections with NEPQ-structured responses
- **sources.md** — per-vertical canonical voices (reading/listening pack)

When Maven is activated for a specific buyer's business:
1. Identify buyer's vertical (agency / creator / SaaS / etc.)
2. Load the matching pack as "primary vertical context"
3. Optionally load a second pack as "secondary" (many businesses span verticals)

---

## Current Status (2026-04-21)

| Pack | Status | Primary canon | Applied to (internal) |
|------|--------|--------------|----------------------|
| **[[agency/lead-channels\|Agency]]** | ✅ Populated | [[enns-agency-pricing]], [[agency/sources]] (Blair Enns, Baker, Chris Do, Ross) | [[oasis-ai]] |
| **[[creator/lead-channels\|Creator]]** | ✅ Populated | [[godin-permission]], [[creator/sources]] (Welsh, Koe, Cole, Bush, Pulizzi) | [[conaugh-personal]] |
| **SaaS** | 🟡 Stub | [[balfour-4-fits]], [[moore-crossing-chasm]], [[ellis-pmf-engine]] | [[propflow]] (pre-beta — waiting on signal) |
| **E-commerce** | 🟡 Stub | Ezra Firestone, Drew Sanocki, Nik Sharma | None yet |
| **Coaching** | 🟡 Stub | [[hormozi-value-equation]], Dan Koe, [[brunson-funnels]], Dean Graziosi | None yet |
| **Local service** | 🟡 Stub | Joe Crisara, Ryan Redding | [[oasis-ai]] ICP sub-vertical (HVAC, wellness) |

---

## Pack Structure Rationale

### Why 4 files per pack?

- **lead-channels** — operators need to know WHERE buyers come from first. Channel decision precedes copy.
- **pricing-playbook** — pricing signals positioning ([[sutherland-signalling]]). Wrong price = wrong buyer.
- **objection-handlers** — 80% of sales friction is 5-8 predictable objections. NEPQ-structured responses close faster.
- **sources** — the authoritative reading list so Maven can cite-by-name when recommending vertical-specific action.

### Why not more files?

Keep packs tight. More files = more maintenance, less adoption. Start with 4 canonical. Add vertical-specific extras only when pattern earns it across 3+ installs.

---

## Agency Pack — Summary

**Applies to:** consultancies, marketing agencies, dev shops, fractional execs, boutique studios.
**Maven's internal application:** OASIS AI (CC's agency — primary revenue engine).

Key rankings (see [[agency/lead-channels]]):
1. Warm outreach + referrals (highest ROI sub-$50K MRR)
2. Authority content (Enns + Baker)
3. Partnerships / sub-contracting
4. Cold outbound (Predictable Revenue era)
5. Paid ads (DE-PRIORITIZED sub-$50K MRR — agency buyers don't click ads)

Pricing (see [[agency/pricing-playbook]]):
- Value-based > day-rate > hourly (Enns hierarchy)
- 4-tier offer: discovery ($1.5-$5K) → pilot ($5-$15K) → retainer ($2-$8K/mo) → transformation ($25-$100K)

Sources (see [[agency/sources]]): Blair Enns, David C. Baker, Aaron Ross, Chris Do, Hormozi.

---

## Creator Pack — Summary

**Applies to:** personal-brand creators, newsletter operators, podcasters, course creators, solopreneurs.
**Maven's internal application:** Conaugh McKenna personal brand (top-of-funnel for OASIS).

Key rankings (see [[creator/lead-channels]]):
1. Organic social (platform-native, daily cadence)
2. Newsletter (highest-intent owned channel)
3. Podcast guesting (authority-building)
4. Community (Skool / Discord / Circle)
5. Paid (DE-PRIORITIZED — creators win on audience-native content)

Pricing ladder (see [[creator/pricing-playbook]]):
- Free → $25-99 → $200-1K → $2.5-25K (Welsh 4-tier model)
- Cohort-first rule: $500-$1K cohort before self-paced
- Founder's pricing 50-70% for pilot cohort

Sources (see [[creator/sources]]): Justin Welsh, Dan Koe, Nicolas Cole, Dickie Bush, Tiago Forte, Joe Pulizzi, Kevin Kelly (1,000 True Fans).

---

## SaaS Pack — Planned Scope

**Will apply to:** SaaS products sub-$1M ARR, vertical SaaS, indie hackers, product-led growth plays.
**Maven's internal application:** PropFlow (when product ships).

Primary canon to lean on:
- [[balfour-4-fits]] — the 4 Fits framework determining growth mechanics
- [[moore-crossing-chasm]] — adoption curve + beachhead strategy
- [[ellis-pmf-engine]] — 40% PMF test before any paid acquisition
- [[ries-trout-positioning]] — category warfare for vertical SaaS
- [[miller-storybrand]] — clarity in landing page + onboarding copy

Planned file skeleton:
- `skills/verticals/saas/lead-channels.md` — content + SEO + partnerships + PLG + paid (stage-dependent)
- `skills/verticals/saas/pricing-playbook.md` — pricing tiers, usage vs seat, annual discount, freemium math
- `skills/verticals/saas/objection-handlers.md` — "we'll build this internally," "too expensive," "what about security"
- `skills/verticals/saas/sources.md` — Patrick Campbell (ProfitWell), Lenny Rachitsky, Jason Lemkin, Balfour, Elena Verna, Andrew Chen, Sean Ellis, April Dunford

---

## E-commerce Pack — Planned Scope

**Will apply to:** DTC brands, Shopify stores, Amazon sellers, vertically-integrated e-comm.
**Maven's internal application:** Nostalgic Requests (partial — transactional, low-volume).

Planned canon:
- [[hopkins-scientific-advertising]] — testing rigor for paid
- [[ogilvy-advertising]] — brand-as-asset for DTC
- [[sharp-how-brands-grow]] — light-buyer acquisition math
- [[binet-field-long-short]] — 60:40 DTC application

Planned file skeleton:
- `skills/verticals/ecommerce/lead-channels.md` — Meta + Google + TikTok + email + affiliate (volume-heavy)
- `skills/verticals/ecommerce/pricing-playbook.md` — psychology of anchoring + bundles + subscriptions
- `skills/verticals/ecommerce/objection-handlers.md` — "shipping too expensive," "don't trust the brand," "how's the return policy"
- `skills/verticals/ecommerce/sources.md` — Ezra Firestone, Drew Sanocki, Nik Sharma, Ben Chestnut (ConvertKit founder), Cole Gordon

---

## Coaching Pack — Planned Scope

**Will apply to:** 1:1 coaches, group coaching, mastermind operators, certification programs.
**Maven's internal application:** potential future CC productization of OASIS consulting.

Planned canon:
- [[hormozi-value-equation]] — offer stacking for high-ticket
- [[brunson-funnels]] — webinar / high-ticket funnels
- [[cialdini-influence]] — authority + scarcity + commitment ladders
- [[miller-storybrand]] — customer-as-hero narrative

---

## Local Service Pack — Planned Scope

**Will apply to:** HVAC, plumbing, wellness, real estate, home services, personal services.
**Maven's internal application:** OASIS AI ICP sub-vertical (HVAC, wellness — primary OASIS buyer type).

Planned canon:
- [[cialdini-influence]] — social proof heavily weighted
- [[godin-permission]] — local tribe-building
- [[ritson-diagnosis]] — local market diagnosis
- [[ogilvy-advertising]] — direct-response mail tactics

Sources to populate: Joe Crisara, Ryan Redding, Tommy Mello, Jobber content team.

---

## Maintenance Rules

- **Never copy-paste between packs.** If something is universal, it belongs in the core brain/ or skills/. If it's vertical-specific, it earns its own file.
- **Every pack file cites its canonical sources** in frontmatter (`canon_references: [...]`).
- **Update pack quarterly** if being actively used. Stale pack = outdated advice.
- **Deprecate rather than delete** if a pack becomes obsolete. Move to `skills/verticals/_archive/`.

---

## Related

- [[INDEX]] — vault home
- [[MARKETING_CANON]] + [[canon/INDEX]] — framework library packs draw from
- [[WRITING]] — writing doctrine packs apply
- [[ATTRIBUTION_MODEL]] — attribution that measures pack-specific performance
- Clients the packs apply to: [[oasis-ai]] · [[conaugh-personal]] · [[propflow]] · [[nostalgic-requests]] · [[sunbiz-funding]]

## Obsidian Links
- [[INDEX]] | [[MARKETING_CANON]] | [[canon/INDEX]] | [[WRITING]] | [[agency/lead-channels]] | [[creator/lead-channels]]
