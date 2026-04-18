# SKILL: SEO & AEO (Search Engine + Answer Engine Optimization)

> Keyword research, Quality Score optimization, landing page SEO, and AI-ready content strategies for MCA consolidation.

---

## Overview
This skill covers search optimization for both traditional search engines (SEO) and AI answer engines (AEO). For SunBiz Funding's MCA business, SEO directly impacts Google Ads Quality Score (lowering CPC) and organic visibility, while AEO ensures SunBiz appears in AI-generated answers about MCA consolidation.

## SEO for Google Ads (Quality Score)

Google Ads Quality Score (1-10) directly impacts CPC and ad position. Three factors:

| Factor | Weight | How to Optimize |
|--------|--------|----------------|
| **Ad Relevance** | ~33% | Match ad headline keywords to search query. Include MCA consolidation terms in headlines. |
| **Expected CTR** | ~33% | Compelling copy with consolidation hooks, strong CTA, ad extensions (sitelinks, callouts). |
| **Landing Page Experience** | ~33% | Fast JotForm load (<3s), mobile-friendly, relevant MCA content matching ad promise. |

### Quality Score Improvement Process
1. Pull keyword-level Quality Score via GAQL:
   ```sql
   SELECT ad_group_criterion.keyword.text,
          ad_group_criterion.quality_info.quality_score,
          ad_group_criterion.quality_info.creative_relevance_status,
          ad_group_criterion.quality_info.post_click_quality_score,
          ad_group_criterion.quality_info.search_predicted_ctr
   FROM keyword_view
   WHERE ad_group_criterion.quality_info.quality_score IS NOT NULL
   ```
2. Identify keywords with QS < 6
3. For each: diagnose which factor is "Below Average"
4. Apply targeted fix (ad copy, landing page, or CTR improvement)
5. Monitor weekly

## Keyword Research Framework

### Step 1: Seed Keywords
Start from MCA consolidation and business funding terms:
```
MCA consolidation, merchant cash advance consolidation, MCA buyout,
reverse consolidation, business funding, working capital,
MCA debt relief, reduce daily payments, consolidate MCA positions
```

### Step 2: Expand
- Google Keyword Planner (via API or manually)
- "People Also Ask" from Google SERPs
- Related searches at bottom of Google results
- Competitor keywords (via SEMrush/Ahrefs or Playwright scraping)
- Long-tail variations: "MCA consolidation for [industry]", "how to consolidate [number] MCA positions"

### Step 3: Categorize by Intent
| Intent | Example | Funnel Stage | CPC Range |
|--------|---------|-------------|-----------|
| Transactional | "MCA consolidation" | Bottom | High ($8-20) |
| Commercial | "best MCA consolidation companies" | Mid | Medium ($5-12) |
| Informational | "what is MCA consolidation" | Top | Low ($1-5) |
| Navigational | "SunBiz Funding" | Bottom | Low ($1-2) |

### Step 4: Prioritize
Score = (Monthly Volume x Conversion Likelihood) / Competition
- High-intent + low competition = immediate targets
- High-volume + high competition = long-term targets
- Low-intent = content marketing / educational content only

### Step 5: Negative Keywords
Build exclusion list to prevent wasted spend:
```
Tier 1 (Always exclude): free, grant, forgiveness, charity, government, jobs, certification, course
Tier 2 (Unless relevant): student, personal, payday, car, mortgage, auto
Tier 3 (Brand protection): scam, complaint, review (monitor but don't always exclude)
Tier 4 (Disambiguation): MCA meaning medical, MCA artery, MCA exam
```

## Landing Page SEO Audit Checklist

### Technical SEO
- [ ] JotForm loads in <3 seconds (test via Playwright)
- [ ] Mobile-responsive (test viewport via Playwright)
- [ ] HTTPS enabled
- [ ] No broken links (404s)
- [ ] Proper URL structure with UTM parameters

### On-Page SEO (if website/landing page exists beyond JotForm)
- [ ] Title tag includes "MCA Consolidation" (50-60 chars)
- [ ] Meta description with consolidation hook (150-160 chars)
- [ ] H1 heading includes primary MCA keyword
- [ ] Content matches ad promise (message match)
- [ ] Internal links to educational MCA content
- [ ] Image alt tags present
- [ ] Schema markup (Organization, FAQPage, FinancialProduct)

### MCA-Specific Requirements
- [ ] Company name (SunBiz Funding) visible
- [ ] "Merchant Cash Advance products are not loans" disclaimer
- [ ] "Subject to underwriting approval" disclaimer
- [ ] Clear CTA above the fold → JotForm
- [ ] Privacy policy linked
- [ ] State-specific disclosures (CA APR-equivalent, NY Commercial Finance)
- [ ] TCPA consent language on all forms

## AEO (Answer Engine Optimization)

### What is AEO?
Optimizing content so AI assistants (Google AI Overview, ChatGPT, Perplexity, etc.) reference SunBiz Funding when users ask MCA-related questions.

### AEO Strategies
1. **FAQ Content** — Create FAQ pages answering common MCA questions
   - "What is MCA consolidation?"
   - "How do I reduce my daily MCA payments?"
   - "Can I consolidate multiple merchant cash advances?"
   - "What is a leverage ratio for MCA?"
   - "How does MCA buyout work?"

2. **Structured Data (Schema.org)**
   ```json
   {
     "@context": "https://schema.org",
     "@type": "FinancialProduct",
     "name": "MCA Consolidation",
     "description": "Multi-phase consolidation strategy for overleveraged merchants",
     "provider": {"@type": "Organization", "name": "SunBiz Funding"}
   }
   ```

3. **Featured Snippet Targeting**
   - Answer MCA questions in 40-60 words (snippet-length)
   - Use lists and tables (Google prefers structured answers)
   - Place answer immediately after the H2 question heading

4. **E-E-A-T Signals** (Experience, Expertise, Authoritativeness, Trustworthiness)
   - Author bios with financial credentials
   - Citations to regulatory sources (CFPB, state regulators)
   - Case studies and merchant testimonials
   - Industry certifications and memberships

## Content Pillars for SEO
1. **Educational:** "How to Calculate Your Leverage Ratio" — informational traffic
2. **Case Studies:** "How We Took a Business from 4 Positions to 1" — social proof + long-tail
3. **Expose:** "The Truth About Stacking MCAs" — hooks overleveraged merchants
4. **Comparison:** "Bank vs. MCA vs. Consolidation" — commercial intent traffic

## SEO Reporting Format
```
=== SEO Report ===
Keyword Coverage: X high-intent | X medium | X low-intent
Avg Quality Score: X.X/10
Landing Page Score: X/10
AEO Readiness: X/10

TOP KEYWORDS (by potential):
| Keyword | Volume | Competition | Current QS | Action |

ISSUES:
1. [issue + fix]
2. [issue + fix]

RECOMMENDATIONS:
1. [specific action + expected impact]

MCA COMPLIANCE: [verified / issues found]
```
