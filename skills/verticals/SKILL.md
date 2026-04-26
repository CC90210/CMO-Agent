---
name: verticals
description: Vertical-pack registry for Maven. Routes a brand to its industry-specific marketing playbook (SaaS, agency, coaching, e-commerce, local-service, creator).
---

# SKILL: Verticals — Per-Industry Marketing Packs

> Maven serves multi-vertical brands. Each vertical has its own buying psychology, channel mix, compliance constraints, and proof requirements. Don't apply SaaS playbooks to MCA funding or coaching offers.

## Vertical Packs in This Folder

- `agency/` — Service-business marketing (consulting, agencies, OASIS AI)
- `coaching/` — Coach / consultant offers (Conaugh personal brand component)
- `creator/` — Personal-brand-driven creators (DJ Conaugh, Nostalgic adjacents)
- `ecommerce/` — D2C product brands (Nostalgic Requests product line)
- `local-service/` — Geo-targeted service businesses (PropFlow tenant base)
- `saas/` — Self-serve SaaS (PropFlow, OASIS B2B tier)

## When to Apply Which Pack

Look up the brand in `brain/clients/<brand>.md`. The brand profile names the primary vertical(s). Pull the pack's `README.md` and any `playbook-*.md` it contains, and bind them to your campaign plan before invoking content-creator or ad-strategist.

## Cross-Pack Rules

- **SunBiz Funding** is regulated lending — the `lending-industry` skill (top-level) overrides anything in the verticals packs. Compliance language wins.
- **Conaugh personal brand** spans creator + coaching — pull both packs for top-of-funnel content, prefer coaching's offer architecture for the bottom.
- **OASIS AI** is agency + saas — agency for early-stage clients buying engagements, saas for self-serve when the platform ships.

## Maven-specific adaptation

This skill is universally applicable across all 5 brands Maven manages. When a new vertical is needed (e.g. PropFlow expands into a new property class), add the pack folder and its README before campaigning into it. Per-vertical canon citations should live in `brain/verticals/<vertical>.md` with framework links back to `brain/MARKETING_CANON.md`.
