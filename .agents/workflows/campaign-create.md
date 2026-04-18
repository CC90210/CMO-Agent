---
description: Full campaign creation wizard — platform selection, strategy, SEO keywords, copy, creative, compliance check, and launch.
---

// turbo-all

# /campaign-create — Full Campaign Creation Wizard

## When to Use
Use `/campaign-create` when starting a new ad campaign from scratch on Google Ads, Meta Ads, or both.

## Steps

1. **Gather Requirements** — Ask user (if not provided):
   a) Platform: Google Ads, Meta Ads, or Both?
   b) Objective: Lead generation, brand awareness, traffic?
   c) Budget: Daily budget? Duration?
   d) Audience: Geographic area? Specific targeting?
   e) Creative: Images/videos available? Text only?
   f) Landing page: URL where clicks go?

2. **Load Context** — Read silently:
   - `brain/CLIENT.md` for company context
   - `brain/STATE.md` for current campaigns
   - `skills/campaign-creation/SKILL.md` for process
   - `skills/lending-industry/SKILL.md` for compliance rules

3. **Build Strategy** — Using ad-strategist agent:
   - Define campaign structure and naming convention
   - Set budget allocation across platforms
   - Define target audience (respecting credit ad restrictions)
   - Plan A/B testing variants

4. **SEO & Keyword Research** — Using seo-specialist agent:
   - Research high-intent lending keywords
   - Analyze search volume and competition
   - Integrate keywords into ad copy and targeting
   - Audit landing page for SEO/AEO readiness

5. **Create Ad Copy** — Using content-creator agent:
   - Generate 5+ headline variants (keyword-optimized)
   - Generate 3+ description variants
   - Define CTA (Apply Now, Get a Quote, Learn More)
   - Compliance check ALL copy

6. **Handle Media** — Using media-manager + video-editor agents:
   - Images → optimize dimensions, upload to platform
   - Videos → trim, add captions, format for platform specs
   - No media → recommend text-only or stock options

7. **Build Campaign via API** — Using platform specialist agents:
   a) Create campaign (PAUSED state)
   b) Create ad groups/ad sets with targeting
   c) Add keywords (Google) or interests (Meta)
   d) Create ads with copy and creative
   e) Read-back to verify structure

8. **Compliance Review:**
   - [ ] Meta: `special_ad_categories: ['CREDIT']` present?
   - [ ] Meta: No restricted targeting (age/gender/zip)?
   - [ ] Google: Lending disclosures in ad or landing page?
   - [ ] Copy: No guaranteed approval language?
   - [ ] Landing page: Has required disclosures?

9. **Present Summary** — Campaign name, platform, budget, targeting, ad count, compliance status.

10. **Launch (with user approval)** — Set ACTIVE, log to tracker, set 24h check-in, update STATE.md.

## Example Usage
**User:** `/campaign-create`
**Agent:** "What platform — Google Ads, Meta Ads, or both? Daily budget and goal?"
