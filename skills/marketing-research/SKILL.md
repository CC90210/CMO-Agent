---
name: marketing-research
version: 1.0.0
description: "Systematic market, audience, competitor, and trend research. Diagnosis-before-prescription (Ritson). Non-leading customer interviews (Fitzpatrick). Audience discovery without survey bias (Fishkin). Positioning research before copy (Dunford)."
canon_references: [ritson-diagnosis, dunford-positioning, fishkin-sparktoro, fitzpatrick-mom-test]
canon_source: brain/MARKETING_CANON.md
metadata:
  category: research
  universal: true
  tier: full
triggers: [research, audience, icp, interview, mom test, sparktoro, reddit, competitive audit, trend, keyword research, seo research, aeo research, voc, voice of customer, content gap]
---

# MARKETING RESEARCH — Diagnose Before You Prescribe

> **Ritson's iron law:** no strategy without diagnosis, no tactics without strategy. If Maven cannot answer "who exactly is this for, why do they care, and what do they currently do instead," no campaign runs.

## Canonical Voices

- **Rob Fitzpatrick** — *The Mom Test* (2013). Customer interviews without polite lies. Ask about lives and problems, not your solution.
- **Rand Fishkin** — SparkToro + *Lost and Founder*. Audience intelligence sourced from where people actually hang out, not from survey panels.
- **Mark Ritson** — Mini MBA in Marketing. Research → strategy → tactics. Segmentation + targeting + positioning are research outputs, not brainstorm outputs.
- **April Dunford** — *Obviously Awesome*. Positioning emerges from 5 research inputs: alternatives, unique attributes, value, best-fit customer, market category.
- **Clayton Christensen / Tony Ulwick** — Jobs-to-be-Done interviews. What job did they hire the product to do?

---

## The 5 Research Lenses Maven Uses

Every research brief picks at least 2 of 5. Never 1. Never 0.

| Lens | Question | Primary method | Output |
|------|----------|----------------|--------|
| **Audience** | Who buys and where do they actually hang out? | SparkToro + Reddit ethnography + sales-call listen-backs | `brain/research/<brand>-audience.md` |
| **Competitive** | Who are they comparing us to, and why? | Facebook Ad Library, Meta Creative Hub, AppFigures, G2/Capterra review mining | `brain/research/<brand>-competitors.md` |
| **Keyword / AEO** | What are they searching + asking AI? | GSC + Ahrefs/SEMrush + Perplexity/ChatGPT prompt-mining + People Also Ask | `brain/research/<brand>-keywords.md` |
| **Voice-of-customer** | What do they literally say when the pain is fresh? | Mom-Test interviews (5-10 per brand) + sales-call transcripts + review mining | `brain/research/<brand>-voc.md` |
| **Trend** | What's shifting in buying behavior / platform / macro? | Google Trends + subreddit growth velocity + newsletter intake (Lenny, Not Boring, Stratechery) | `brain/research/<brand>-trends.md` |

---

## Protocol 1 — Mom-Test Interviews (Fitzpatrick)

**Run when:** new brand positioning, new offer design, new ICP hypothesis, or close rate drops below target for 2+ weeks.

### Setup
- Recruit 5-10 people who've made a buying decision in the last 90 days (theirs OR a competitor's)
- 30-minute call. Recorded with consent. Transcribed via Whisper (see `scripts/render_video.py` pipeline for Whisper integration).

### The 3 Mom-Test rules
1. **Talk about their life, not your idea.** Never pitch. Never validate.
2. **Ask about specifics in the past, not opinions about the future.**
3. **Talk less, listen more.**

### The 7 questions (memorize)
1. Tell me about the last time you [problem area].
2. What was the hardest part about [problem]?
3. Why was that hard?
4. What, if anything, have you done to try to solve this?
5. What don't you love about the solutions you've tried?
6. (If they name a competitor) What does [competitor] do that you wish was better?
7. (At the end only) Who else should I talk to about this?

### Anti-patterns (banned)
- "Would you use a product that..." (hypothetical — people lie)
- "Do you like this idea?" (bias — people are polite)
- "How much would you pay?" (their stated WTP is fiction; look at past spend instead)

### Output artifact (`brain/research/<brand>-voc.md`)
```markdown
# VOC — [brand] (interview round N, YYYY-MM-DD)

## Pattern: [short name]
- Quote: "..."  (verbatim)
- From: [ICP archetype], [interview date]
- Frequency: heard in X of N interviews
- Implication: [how this changes positioning/offer/copy]
```

Rule: if a pattern appears in **3+ of N interviews**, it's signal. Fewer, it's noise.

---

## Protocol 2 — Audience Discovery (Fishkin / SparkToro method)

**Run when:** starting a new brand, or current targeting is under-performing.

### The 3 questions SparkToro answers
1. What podcasts/YouTube channels/newsletters does our audience follow?
2. What hashtags/accounts/keywords do they use?
3. What websites do they visit + phrases do they use to self-describe?

### Tooling priority (cheapest first)
1. **Manual Reddit ethnography** — find 3 subreddits where the audience hangs out. Read top posts of last 30 days. Note recurring vocabulary. Free.
2. **Twitter/X advanced search** — search for pain-language phrases in quotes. Find who's saying them.
3. **SparkToro trial** — audience → keywords → follow-graph (paid; use only for brands at $3K+ MRR).
4. **Google Ads keyword planner + Ahrefs** — search-intent view.

### Red flags in audience research
- Audience is "everyone in X industry" → segment further or kill the brand
- Audience can't be found in 3 discoverable places → positioning is off, not audience
- All data comes from Google → you're missing dark-social (DMs, Slack, podcasts, in-person)

---

## Protocol 3 — Competitive Audit (Dunford + Ritson)

**Run when:** positioning any new brand, OR any existing brand's competitor just raised funding/changed pricing/launched a new category.

### The 4 competitor tiers
1. **Direct** — same category, same ICP (e.g., OASIS vs. other AI-automation agencies)
2. **Alternative categories** — different category, same job (e.g., OASIS vs. hiring a full-time VA)
3. **DIY / status quo** — what the customer does today WITHOUT anyone's help (critical — often the #1 competitor)
4. **Absence of action** — customer lives with the pain (even more critical at lower price points)

### Data sources
- **Ad creative**: Meta Ad Library (`https://www.facebook.com/ads/library/`) + TikTok Creative Center + Google Ads Transparency
- **Landing pages**: scrape + Dunford-analyze (what positioning statement can you reverse-engineer?)
- **Reviews**: G2 / Capterra / Trustpilot — sort by 2-star and 4-star (the gold zone; 5 and 1-star are often noise)
- **Pricing**: their pricing page + sales-call transcripts found on YouTube / founder pods
- **Positioning statements**: about page + LinkedIn company description + most recent press release

### Output format (`brain/research/<brand>-competitors.md`)
```markdown
## [Competitor name] — [direct / alternative / DIY]
- **Positioning (our read)**: [1-sentence]
- **Who they're FOR (best-fit customer)**: [description]
- **Who they're NOT for (explicit)**: [description]
- **Unique attributes they claim**: [list]
- **Pricing**: [tier structure]
- **What they do better than us**: [honest answer]
- **What we do better than them**: [honest answer]
- **Our positioning move vs. them**: [insight]
```

---

## Protocol 4 — Keyword + AEO Research

**Run when:** planning content pillar for a quarter, or building a landing page.

### SEO (existing)
- Google Search Console → existing ranking queries
- Ahrefs/SEMrush → competitor ranking queries + gap analysis
- Google Autocomplete + People Also Ask → long-tail + question-shape
- Forum mining (Reddit, Quora, niche Slacks) → long-tail pain language

### AEO (Answer Engine Optimization — new)
- Perplexity: query for your category + note the 5 sources cited
- ChatGPT / Claude: "What is the best X for Y?" → note whether your brand is mentioned
- Google AI Overviews: what's cited above the fold?
- **Optimization**: get cited as a source. Methods: original data, structured H2+definition pattern, clear citations on your own pages, Wikipedia-adjacent authoritative tone.

### Output (`brain/research/<brand>-keywords.md`)
```markdown
## Keyword: "[phrase]"
- **Intent**: informational / navigational / transactional / comparison
- **Monthly volume**: N
- **Ranking difficulty**: low/med/high
- **Competitor ranking**: [names + positions]
- **Content angle to win it**: [short description]
- **Buyer-pyramid match** (Holmes): 3% / 7% / 30% / 30% / 30%
```

---

## Protocol 5 — Trend Monitoring

### Weekly scan (Sunday 30 minutes)
- Google Trends for 3 brand-relevant keywords — rising vs. flat
- Subreddit activity — new subreddits in the niche? velocity changes?
- Newsletter intake (pick 3-5 maximum): Lenny's Newsletter, Not Boring, Stratechery, Marketing Week (Ritson), Katelyn Bourgoin's Why We Buy
- Twitter/X list of 20 canonical voices (Dunford, Hormozi, Sharp, Miner, Welsh, Koe, Goins)

### Anti-pattern
Chasing every trend. Only act on a trend when you have audience research showing YOUR audience is moving. Most trends are fashion; Ritson's anti-canon applies.

---

## Integration With Other Skills

| Skill | How research feeds it |
|-------|----------------------|
| `brand-guidelines` | Audience + competitive research set brand codes + voice |
| `ad-copywriting` | VoC quotes become hooks. Sutherland: customer's-own-words > our-clever-words |
| `campaign-creation` | Keyword + audience + competitor research defines targeting + angle before launch |
| `content-engine` | Holmes buyer-pyramid mix comes from research (which % is actively shopping?) |
| `competitive-intelligence` | Sibling skill — this one adds upstream discovery; CI adds ongoing monitoring |
| `persona-content-creator` | ICP profiles come from VoC interviews, not imagination |
| `lead-management` | ICP scoring weights set by audience research |

---

## When Maven Runs This Skill Without Being Asked

- Starting any new campaign for a brand where `brain/research/<brand>-voc.md` doesn't exist → block on research
- Rewriting positioning for any brand → 5-interview VoC round first
- Proposing a new content pillar → keyword + audience research first
- Any "why isn't this converting" diagnosis → Mom-Test interviews with 3 lost deals

---

## Anti-Patterns to Reject

1. **"We already know our audience"** → then show the research doc. If there isn't one, we don't know.
2. **"Surveys instead of interviews"** → surveys give stated preferences. Interviews give revealed preferences via past behavior. Interviews win.
3. **"Competitor X is doing Y so we should too"** → fashion, not strategy. Dunford + Ritson both reject this.
4. **"One persona fits all segments"** → if one persona works for >1 segment, the segments aren't real.
5. **"Research is slow, let's just launch"** → the slowest campaign is the one that launches with wrong positioning and rebuilds in month 3.

---

## Metrics for this skill's success

- **Positioning documents written per brand**: target = 1 per brand, reviewed quarterly
- **VoC interviews completed per brand per quarter**: target = 5 minimum
- **Keyword gaps closed**: target = 3 per month per active content brand
- **Campaign launches with research citation**: target = 100% (every campaign brief must cite at least one research artifact)

---

## Related

- [[MARKETING_CANON]] — the grounded framework library
- [[competitive-intelligence/SKILL]] — ongoing CI monitoring (this skill is upstream discovery)
- [[persona-content-creator/SKILL]] — persona docs built FROM research output
- [[brand-guidelines/SKILL]] — brand codes derived from audience research
- [[content_registry]] — published pieces that came out of this research
- [[WRITING]] — where research output feeds into copy
- `brain/research/` — output artifacts live here, one folder per brand

## Obsidian Links
- [[INDEX]] | [[MARKETING_CANON]] | [[WRITING]] | [[content_registry]] | [[competitive-intelligence/SKILL]]
