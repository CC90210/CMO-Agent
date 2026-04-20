---
name: lead-management
version: 2.0.0
description: "End-to-end lead lifecycle: capture -> qualify -> nurture -> handoff. Lead scoring, CRM architecture, automation rules, re-engagement, SLA windows, multi-touch attribution. Industry-standard methodology (Ross, Holmes, Hormozi, Sandler, Miner) + vertical pack extensions."
metadata:
  category: operations
  universal: true
  vertical_extensions: [agency, saas, ecommerce, coaching, creator, local-service]
triggers: [lead, leads, pipeline, crm, funnel, qualify, nurture, mql, sql, cpl, cpql, cac, attribution, handoff]
canon_references: [ross-predictable-revenue, holmes-buyer-pyramid, hormozi-lead-flows, miner-nepq]
canon_source: brain/MARKETING_CANON.md
---
# LEAD MANAGEMENT — The Full Lifecycle

How Maven captures, qualifies, nurtures, and hands off leads. Industry-standard methodology; brand-specific at the vertical-pack + client-profile layer.

**Canonical sources**:
- Aaron Ross — *Predictable Revenue* (cold outbound / SDR separation)
- Chet Holmes — *The Ultimate Sales Machine* (Dream 100 + buyer pyramid)
- Alex Hormozi — *$100M Leads* (4 core lead channels)
- David Sandler — Sandler Pain Funnel
- Jason Lemkin — SaaStr pipeline velocity
- Jeremy Miner — NEPQ question flow

---

## The 5-Stage Lifecycle

```
STAGE 1  CAPTURE    form / DM / reply / ad click / referral
STAGE 2  QUALIFY    ICP fit, budget, intent, timeline, authority
STAGE 3  NURTURE    content, sequences, retargeting, 1:1
STAGE 4  HANDOFF    MQL -> SQL -> sales call -> close
STAGE 5  POST-SALE  delivery, expansion, referral, win-back
```

Each stage: entry criteria, exit criteria, SLA, automation rules, owning agent.

---

## Stage 1: CAPTURE

### Hormozi's 4 core flows

| Channel | Cost | Scalability | CPL range | Best for |
|---------|------|-------------|-----------|----------|
| Warm outreach (referrals) | Free | Low | ~$0 | Sub-$50K MRR |
| Post content (organic) | Time | High | $0 scaling | Thought leadership |
| Paid ads (Meta/Google) | Money | Very high | $15-$150/qualified | Scale phase |
| Cold outreach (email/LI/DM) | Time+tools | Medium | $20-$80/qualified | B2B agency, SaaS |

Rule: start with 2 of 4. Never chase all 4 until each is producing.

### Capture tooling (build order)

1. JotForm / Typeform — simplest
2. Calendly / Google Calendar appointments — direct booking (PULSE funnel)
3. Supabase `funnel_leads` table + webhook
4. HubSpot Free / Attio / Notion — when multi-stage pipelines are needed
5. PULSE (CC's IG DM automation) — auto-captured + stage-tagged

### Required metadata at capture

- captured_at
- source (channel + UTM)
- brand (which brand this is for)
- raw_context (what they said, where they came from)

---

## Stage 2: QUALIFY

### ICP-fit score (0-100)

Per-brand ICP in `brain/clients/<brand>.md`. Score dimensions:

| Dimension | Weight |
|-----------|--------|
| Industry match | 25 |
| Company size / revenue | 20 |
| Geographic fit | 10 |
| Decision-maker identified | 15 |
| Stated pain matches offer | 20 |
| Budget signal | 10 |

### Qualification frameworks (pick one per brand, do not mix)

- **BANT** — simplest, transactional B2B
- **MEDDIC** — complex B2B SaaS
- **CHAMP** — challenges-first (modern)
- **Sandler Pain Funnel** — high-ticket services

OASIS uses **CHAMP + Sandler** — at our stage, surfacing challenges drives the sale more than budget disclosure.

### Disqualification is a feature

- Non-ICP (wrong vertical/geo/hobby) -> archive politely, 1-line note
- ICP but wrong timing -> 90-day re-engage trigger
- Red flags (abuse, impossible expectations, extreme urgency) -> decline + refer out

---

## Stage 3: NURTURE

### 3 modes (pick per lead)

- **Content-led**: passive, low effort, low conv, large volume
- **Sequence-led**: triggered 5-email or 3-DM sequence, medium effort/conv (PULSE doctrine)
- **High-touch**: Tier-1 Dream-100 target, custom research + personal outreach, high conv

### Content cadence (Holmes Buyer Pyramid)

- 3% actively shopping -> offer content (case studies, pricing)
- 7% open -> education + angle
- 30% not thinking -> curiosity-spike content
- 30% don't think they need -> adjacent-problem content
- 30% know they don't need -> ignore

Calendar must mix. Do not over-index on the 3%.

### Automation rules

| Trigger | Action | Tool |
|---------|--------|------|
| Form submit | Welcome email <5min | `email_engine.py` |
| Calendar book | Pre-call teaser + 24h/1h reminders | PULSE `/api/cron/check-bookings` |
| No-show | Re-offer link politely | Sequence |
| MQL no action 7d | DM nudge | Auto |
| Stalled 21d | Pause -> quarterly re-engage | Auto |
| Lost deal | 90-day circle-back sequence | Auto |

---

## Stage 4: HANDOFF

### MQL -> SQL definitions (tune per brand)

OASIS example:
- **MQL** = ICP-fit + booked a discovery call + pre-call teaser email opened
- **SQL** = MQL + attended call + named a specific problem + acknowledged budget range OR agreed to proposal
- Time expiry: MQL -> 30 days. If no SQL conversion, demote to nurture.

### SLA windows (non-negotiable)

HBR study: 10x conversion drop after 5-min response delay.

- Inbound form response: <5 min
- DM response: <15 min (PULSE handles)
- Booked call confirmation: <2 min (immediate email + calendar attendee)
- Post-call follow-up: <2 hours (recap + next step)
- Proposal delivery: <24 hours after close-ready signal
- Proposal follow-up: day 2 + day 5 + day 12

### Handoff artifacts to Bravo/CC

- Lead profile (ICP score, source, qualification notes)
- Pre-call context (their stated problem in their words, relevant case studies to mention)
- Proposed NEPQ opening question specific to this lead
- Recommended offer tier (Starter / Pro / Custom)

---

## Stage 5: POST-SALE

- Onboarding milestones -> Supabase `leads.status=won`
- 90-day health check -> upsell window identification
- Cross-sell to sibling brands (PULSE -> cc-funnel -> full retainer)
- Referral ask at 30-day success mark

### Win-back sequence for lost deals

- Day 30: "what would need to change?"
- Day 90: case study addressing their objection
- Day 180: offer change (new pricing / guarantee / service)
- Day 365: cold touch

---

## Metrics (write to Supabase + cmo_pulse.json)

| Metric | Formula | OASIS target |
|--------|---------|--------------|
| CPL | spend / leads | <$30 |
| CPQL | spend / ICP-fit leads | <$60 |
| CAC | spend / customers closed | <$500 |
| Show rate | attended / booked | >70% |
| Close rate | customers / qualified calls | >25% |
| Time-to-close | median days capture->win | <21 |
| LTV by source | avg contract x retention months | double high performers, kill low |

### Alert thresholds

- CPL >2x target for 3 days -> pause campaign, diagnose
- Show rate <50% for 1 week -> audit pre-call sequence
- Time-to-close trending up -> tighten qualification
- LTV dropping for source X -> reallocate budget

---

## Vertical Extensions (pluggable)

Each pack at `skills/verticals/<vertical>/` adds specifics:
- **Agency**: retainer vs project qualification, scope-creep signals
- **SaaS**: free-trial -> paid conversion funnel, usage-based qualification
- **E-commerce**: abandoned cart flows, first-purchase LTV
- **Coaching**: webinar -> high-ticket sales call funnel
- **Creator**: audience-first qualification, sponsorship lead flow
- **Local service**: geo-radius filter, emergency-ticket SLA (much tighter than B2B)

Read the active vertical pack before setting up lead flow for a brand.

---

## Tooling Stack (priority order)

1. **Day 1**: Supabase `leads` + `lead_interactions` tables (already in shared DB)
2. **Week 1**: `scripts/lead_engine.py` for scoring + stage management
3. **Week 2-4**: Meta Pixel + Google Tag conversion tracking for paid attribution
4. **Month 2**: Multi-touch attribution — content_id -> lead_id -> deal_id
5. **Month 3+**: HubSpot Free or Attio only when manual DB becomes painful

Avoid premature tooling. Salesforce, Marketo, HighLevel = overkill below $500K ARR.

---

## PULSE Integration (CC's DM automation)

PULSE handles DM-specific capture / qualify / nurture for CC's personal brand + OASIS inbound. See:
- `ig-setter-pro/lib/doctrine/pipeline.ts` — stages (cold, opener, qualify, pain, solution, objection, book_call, booked)
- `ig-setter-pro/lib/doctrine/objections.ts` — 13 NEPQ-aligned rebuttals
- Turso schema parallel to Supabase `leads`

PULSE is the DM front-door for OASIS + CC personal brand specifically. Other brands (PropFlow, Nostalgic, client work) use separate capture channels.

---

## Playbook: "Run a lead-gen campaign for [brand]"

1. Read `brain/clients/<brand>.md` for ICP
2. Read vertical pack for channel recommendations
3. Read `data/pulse/cfo_pulse.json` for spend gate
4. Propose 2 channels x 2 campaigns x $X/day (respecting spend cap)
5. Write `spend_request` to `data/pulse/cmo_pulse.json`
6. Wait for Atlas approval in `cfo_pulse.json`
7. Execute: ad creative + landing page + capture form + nurture sequence
8. Monitor daily: CPL trending to target; pause kill-switch if 2x target for 3 days
9. Weekly: attribution review, reallocate
10. Monthly: cohort retention + LTV per source -> Bravo for strategic review

---

## Anti-Patterns to Reject

1. "More leads = more sales" -> volume without qualification wastes sales time. ICP fit > lead count.
2. "Just keep nurturing" -> low-intent leads do not convert. Archive with dignity.
3. "We'll follow up in a week" -> 5-min SLA or nothing.
4. "Let's buy HubSpot / Salesforce" below $500K ARR -> build with Supabase + markdown until pain demands otherwise.
5. "That lead didn't close, so it's dead" -> 90-day + 365-day re-engage. 30% of eventual closes come from re-engaged "dead" leads.

---

## Related

- [[MARKETING_CANON]] — frameworks this methodology rests on
- `skills/funnel-management/SKILL.md` — TOFU/MOFU/BOFU
- `skills/email-marketing/SKILL.md` — nurture execution
- `skills/competitive-intelligence/SKILL.md` — ICP refinement
- `skills/verticals/<vertical>/funnel-template.md` — vertical-specific funnel architectures
- `brain/clients/<brand>.md` — brand-specific ICP
- `brain/SHARED_DB.md` — Supabase `leads` + `lead_interactions` + `funnel_leads` schema
