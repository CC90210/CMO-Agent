---
tags: [canon, framework, saas, growth, product-market-fit]
canon_pillar: balfour-4-fits
canon_tier: modern-saas-growth
author: Brian Balfour
works: [Reforge (2016-present), "Why Product Market Fit Isn't Enough" (essay series)]
influences: [ellis-pmf-engine, chen-cold-start, verna-growth-loops]
influenced_by: [moore-crossing-chasm, christensen-jobs-to-be-done]
---

# Brian Balfour — The 4 Fits Framework

> *"Product-Market Fit alone is a myth. You need four fits — and they compound multiplicatively, not additively."*

Balfour (former VP Growth at HubSpot, founder of Reforge) rewrote the product-market-fit conversation by showing that PMF is *necessary but not sufficient*. You also need Market-Channel Fit, Model-Channel Fit, and Model-Product Fit. If any one fails, the whole growth system collapses — regardless of how good your product is.

This is the modern SaaS canon, and it applies directly to Maven's work on OASIS, PropFlow, and Nostalgic.

---

## The 4 Fits

### 1. Product-Market Fit
Right product for the right market. Sean Ellis's original "40% would be very disappointed" test is the classic diagnostic (see [[ellis-pmf-engine]]).
- **Apply:** OASIS has PMF in the DM-automation niche for sub-$2M service businesses. PropFlow does NOT yet have PMF — pre-beta. Nostalgic has weak PMF — small-volume DJ request niche.
- **Question to ask:** if we took this away, would users scream? How many? How loudly?

### 2. Market-Channel Fit
The channels you can reach your market through, at acceptable CAC.
- **Apply:** OASIS's market (owner-operators of service businesses) is reachable via Meta Reels + LinkedIn + warm intro + Skool community. Not reachable at scale via Google Search (low search intent for "AI automation agency"). PropFlow's market (PM firms) reachable via LinkedIn + real-estate podcasts + direct outbound; NOT Meta Reels.
- **Question to ask:** for the market we've picked, what channels actually deliver buyers at a CAC that lets the unit economics work?

### 3. Model-Channel Fit
Your monetization model must match the channels you use.
- **High-ACV ($5K+) models** — need high-intent / high-touch channels (sales-led, warm intro, SEO for high-intent keywords, outbound). Performance ads rarely work at high ACV except for retargeting.
- **Low-ACV ($5-$50/mo) models** — need high-volume channels (paid ads, SEO content, virality). Sales-led kills you.
- **Apply:** OASIS at $2-5K/mo retainer = sales-led + warm + LinkedIn + content. PropFlow at $50-200/mo SaaS = paid ads + SEO + free trial + self-serve.
- **Apply anti-pattern:** charging $49/mo and trying to acquire via sales calls. The economics can't work.

### 4. Model-Product Fit
Your product must deliver value at a cadence that matches how you charge.
- **Monthly subscriptions** — product must deliver value continuously (not once, at onboarding).
- **Annual contracts** — product must demonstrate value in the first 30-90 days or churn spikes.
- **One-time purchase** — product must be "complete" — continued updates become unpaid labor.
- **Apply:** OASIS retainer model requires monthly value delivery (new campaigns, new automations). If CC delivers 90% of value in month 1 and then coasts, churn follows.

---

## The Compounding Failure Mode

Balfour's key insight is that the 4 fits **multiply**. If any is at 0, overall system = 0.

$$ Growth = PMF \times MCF \times MChF \times MPF $$

Even 3 fits at 90% with one at 20% = 0.146, or 14.6% of potential growth. This is why "great product, no growth" and "great channel, no retention" happen.

**Diagnosis:** when growth stalls, score each fit 0-10. The lowest is the bottleneck. Don't work on any other fit until that one's above 7.

---

## Why This Matters for Maven

Maven is the marketing layer across all 4 fits:
- **PMF** — Maven runs the research ([[marketing-research/SKILL]]) that diagnoses PMF
- **Market-Channel Fit** — Maven picks the channels + tests them
- **Model-Channel Fit** — Maven warns when pricing and channel economics misalign
- **Model-Product Fit** — Maven surfaces churn/retention data back to product (Bravo's domain)

If Maven only works on ads + content, it's optimizing ONE variable in a four-variable equation.

---

## The 4-Fit Audit (run per brand quarterly)

| Fit | OASIS (score 0-10) | PropFlow | Nostalgic |
|-----|--------------------|----------|-----------|
| Product-Market Fit | TBD (pulse data needed) | 3 (pre-beta) | 5 (low-volume) |
| Market-Channel Fit | TBD | TBD | 4 (CC content only) |
| Model-Channel Fit | TBD | TBD | 6 (per-request fee) |
| Model-Product Fit | TBD | N/A | 7 (one-time event) |

Action item: fill this table with actual scores next quarterly review. Lowest score = Q3 focus area.

---

## Related Canon

- [[MARKETING_CANON]] — canon hub
- [[ellis-pmf-engine]] — Sean Ellis's PMF survey, the Fit #1 diagnostic
- [[moore-crossing-chasm]] — Moore's adoption curve is the Market layer Balfour built on
- [[chen-cold-start]] — Andrew Chen's network-effects complement to Balfour
- [[dunford-positioning]] — Dunford's positioning work is what makes PMF + MCF testable
- [[sharp-how-brands-grow]] — Sharp's growth laws apply within the Fit #2 layer

## Application Hooks

- [[marketing-research/SKILL]]
- [[competitive-intelligence/SKILL]]
- [[budget-optimization/SKILL]]
- [[audience-targeting/SKILL]]

## Obsidian Links
- [[MARKETING_CANON]] | [[INDEX]] | [[ellis-pmf-engine]] | [[moore-crossing-chasm]] | [[dunford-positioning]] | [[propflow]]
