---
tags: [verticals, product, knowledge-packs]
---

# Vertical Packs — Pluggable Industry Knowledge

> Each vertical is a knowledge pack Maven loads to understand a specific business type. The buyer activates one or more packs at install based on their business.

## The 6 Packs

| Pack | Who it's for | Primary lead channels | Key frameworks |
|------|--------------|----------------------|----------------|
| `agency/` | Consultants, marketing agencies, dev shops, fractional execs | Outbound, referrals, content, partnerships | Utilization math, SOW templates, retainer pricing, client concentration |
| `saas/` | B2B SaaS founders, micro-SaaS, vertical SaaS | Content SEO, paid ads, product-led growth, cold outbound | MRR cohorts, trial-to-paid, NRR, churn triage, freemium economics |
| `ecommerce/` | DTC brands, Shopify stores, physical product | Meta/TikTok ads, influencer, SMS, email | LTV/CAC, AOV, repeat rate, abandoned cart, ROAS |
| `coaching/` | Coaches, course creators, info-products | Organic content, webinars, sales calls | High-ticket sales funnel, cohort-based ops, testimonials |
| `creator/` | Personal brands, newsletters, podcasters, creators | Cross-platform content, email list, sponsorships | Platform-native hooks, audience velocity, collab deal structure |
| `local-service/` | HVAC, plumbing, wellness, real estate, home services | Google LSA, local SEO, Meta lead ads, door knocking, partnerships | Job-costing, crew ops, seasonal demand, reputation mgmt |

## How Packs Load

At session start, Maven reads `personal/active_verticals.json`:
```json
{
  "active": ["agency", "creator"]
}
```

Then loads the pack-specific skills into context. Packs NOT in the list are ignored (not loaded into context). This keeps the window lean.

## What's in Each Pack

```
skills/verticals/<vertical>/
├── README.md              # pack overview (this file's sibling)
├── lead-channels.md       # which acquisition channels work at sub-$50K MRR
├── pricing-playbook.md    # pricing conventions + anchors for this vertical
├── funnel-template.md     # TOFU/MOFU/BOFU mapped to this vertical
├── content-angles.md      # 10+ hook angles proven in this vertical
├── objection-handlers.md  # common buyer objections + NEPQ rebuttals
├── competitors.md         # incumbent + indie competitors to benchmark
├── sources.md             # canonical books/podcasts/experts for this vertical
└── metrics.md             # which KPIs matter + ignore
```

## Research Sources Per Pack (cite in each pack's sources.md)

### Agency
- Blair Enns (Pricing Creativity, Win Without Pitching)
- David C. Baker (The Business of Expertise)
- Chris Do (The Futur — pricing, positioning)
- Chris Orlob (sales for agencies)

### SaaS
- Patrick Campbell (ProfitWell, pricing)
- Jason Lemkin (SaaStr)
- April Dunford (positioning)
- Lenny Rachitsky (Lenny's Newsletter, SaaS metrics)
- Tomasz Tunguz (VC perspective on SaaS KPIs)

### E-commerce
- Ezra Firestone (Smart Marketer)
- Drew Sanocki (CAC/LTV)
- Nik Sharma (DTC audits)
- Ridge / MNML / other operator-led DTCs

### Coaching
- Alex Hormozi ($100M Offers)
- Dan Koe (creator-coach model)
- Russell Brunson (DotCom Secrets for info-products)
- Dean Graziosi

### Creator
- Tiago Forte (Building a Second Brain, PARA)
- Justin Welsh (solopreneur)
- Dickie Bush / Nicolas Cole (writing frameworks)
- Joe Pulizzi (Content Marketing Institute)

### Local service
- Joe Crisara (HVAC sales)
- Ryan Redding (home services marketing)
- Google Local Services Ads docs
- NiceJob (reputation management)

## Pack Maintenance

Each pack evolves independently. When CC finds a new playbook that works for one vertical, it gets added to that pack's content-angles.md (or similar). Buyers pull via `git pull upstream main`.

## For CC's Personal Instance

CC's active verticals: **agency** (OASIS) + **creator** (personal brand + DJ). SunBiz is a client under `agency` pack's "MCA/financial vertical" sub-knowledge if we ever build that sub-vertical; otherwise it's just a client profile.

PropFlow: **saas**.
Nostalgic Requests: **saas** (DJ niche — may warrant a sub-pack later).

## Build Order (prioritized)

1. `agency/` + `creator/` — CC uses these himself, so dogfood these first
2. `saas/` — PropFlow launch + most common indie-hacker persona
3. `local-service/` — OASIS's primary target ICP (HVAC, wellness, real estate)
4. `coaching/` — growing market, lots of buyers
5. `ecommerce/` — most competitive, last priority for V1
