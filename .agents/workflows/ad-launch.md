---
description: Create and launch new ads within an existing campaign — copy, creative, compliance, and activation.
---

// turbo-all

# /ad-launch — Create and Launch Ads in Existing Campaign

## When to Use
Use `/ad-launch` when adding new ads to an existing campaign.

## Steps

1. **Identify Campaign** — Ask user which campaign. List active campaigns if unclear.

2. **Gather Creative Input:**
   a) Ad copy provided? If not → generate with content-creator agent
   b) Images/videos provided? If not → discuss options
   c) CTA preference? (Apply Now, Get a Quote, Learn More)

3. **Create Ad Copy** — Using content-creator + seo-specialist:
   - Write 3-5 headline variants (keyword-optimized)
   - Write 2-3 description variants
   - Optimize for platform character limits

4. **Process Media** — Using media-manager + video-editor:
   - Upload images/videos to platform
   - Videos: trim, caption, format for placements
   - Verify specs (dimensions, file size, duration)
   - Return asset IDs/hashes

5. **Create Ads via API** — Using platform specialist:
   a) Create ad creative(s) with copy + media
   b) Create ad(s) linked to campaign/ad group/ad set
   c) Set status to PAUSED initially
   d) Read-back to verify

6. **Compliance Check** — Lending disclosures, no prohibited language, CREDIT category.

7. **Launch (with user approval):**
   - Set ad status → ACTIVE
   - Log to `memory/CAMPAIGN_TRACKER.md`

## Example Usage
**User:** `/ad-launch`
**Agent:** "Which campaign? Here are your active campaigns: [list]"
