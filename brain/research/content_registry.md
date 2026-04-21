---
tags: [registry, attribution, content, canon]
canon_references: [ritson-diagnosis, sharp-how-brands-grow, binet-field-long-short]
canon_source: brain/MARKETING_CANON.md
version: 1.0
---

# CONTENT REGISTRY — Canonical IDs for Every Published Piece

> Every piece of content Maven publishes gets a canonical ID logged here. Feeds `source_content_ids` in the shared Supabase `leads` table — see [[ATTRIBUTION_MODEL]].
> Without registration, attribution is guesswork. Without attribution, creative decisions are fashion.

---

## ID Convention

```
<type>:<brand>:<YYYY-MM-DD>:<slug>
```

For ads:
```
ad:<platform>:<campaign>:<adset>:<ad>
```

### Types
- `reel` — short-form video (IG Reels, TikTok, Shorts)
- `post` — feed post (LinkedIn, IG, X, FB)
- `email` — email broadcast or sequence entry
- `page` — landing page / sales page URL
- `ad` — paid ad (follow the ad-specific pattern above)
- `loom` — recorded walkthrough / demo
- `podcast` — episode appearance or own show
- `newsletter` — newsletter issue
- `dm` — DM reply sequence (for PULSE)

### Brands
- `oasis` — OASIS AI
- `cc-personal` — Conaugh McKenna personal
- `propflow` — PropFlow
- `nostalgic` — Nostalgic Requests
- `sunbiz` — SunBiz Funding (legacy)

---

## How to Register a New Piece

1. Publish the piece.
2. Assign the ID per the convention above.
3. Append an entry to this file in the appropriate brand section below.
4. Tag every downstream touchpoint (UTM, ad metadata, lead capture) with the same ID.
5. When a lead is captured, populate `leads.source_content_ids` with the matching IDs.

Schema detail lives in [[ATTRIBUTION_MODEL]].

---

## Registry

### OASIS

_(empty — first OASIS piece registration pending pulse-lead-gen launch)_

Expected first entries (campaign pulse-lead-gen, pending Atlas spend gate):
- `ad:meta:pulse-lead-gen:<adset>:<ad>` — Meta Reel ad variants
- `page:oasis:2026-04-XX:pulse-lead-capture` — landing page for free PULSE repo
- `email:oasis:pulse-teaser:v1` — pre-call teaser email
- `email:oasis:pulse-full-delivery:v1` — repo delivery email

### CC Personal

_(empty — content engine active but not yet ID-registered. First 5 posts after today get retroactive IDs.)_

Example template entry:
```
## reel:cc-personal:2026-04-21:build-in-public-week-14
- Published: 2026-04-21
- Platform: instagram + tiktok + linkedin
- Brand: CC Personal
- Pillar: Build-in-public
- Hook: [quote the first 3 seconds]
- CTA: bio link → OASIS calendar
- Asset path: media/published/...
- Cross-brand assist: OASIS (top-of-funnel)
```

### PropFlow

_(empty — product pre-launch)_

### Nostalgic Requests

_(empty)_

### SunBiz (legacy)

_(daily email blast still runs from separate SunBiz-Marketing repo; legacy content IDs not backfilled)_

---

## Maintenance

- **Append-only.** Never delete an entry — content lives in the wild and keeps accumulating touches.
- **Auto-expire after 365 days** via `scripts/attribution_capture.py` (phase 4 of [[ATTRIBUTION_MODEL]] build) — moves stale entries to `brain/research/content_registry-archive.md`.
- **Weekly audit:** scan for content published without registration (gap = tracking broken).
- **Alert:** if >10 pieces published in a week with zero `source_content_ids` populated on captured leads, data capture is broken — fix before adding more content.

---

## Related

- [[ATTRIBUTION_MODEL]] — how these IDs drive the attribution model
- [[MARKETING_CANON]] — the canon that decides which content gets made in the first place
- [[WRITING]] — writing pipeline that terminates in registration
- [[SHARED_DB]] — Supabase schema the IDs feed into
- [[reporting-analytics/SKILL]] — dashboards that consume the registry

## Obsidian Links
- [[INDEX]] | [[ATTRIBUTION_MODEL]] | [[WRITING]] | [[SHARED_DB]]
