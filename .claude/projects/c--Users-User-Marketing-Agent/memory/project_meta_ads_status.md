---
name: meta_ads_status
description: Current state of Meta ad campaigns and API setup for SunBiz Funding - last updated 2026-03-18
type: project
---

## Meta Ads Status (2026-03-18)

### STATUS: LIVE AND RUNNING
- App "SunBiz Ads Live" (ID: 956504317114012): PUBLISHED and LIVE
- Business verification: COMPLETE
- Payment method: Credit card added
- All 5 campaigns: ACTIVE and delivering
- Long-lived token saved at: .long_lived_token.txt (expires ~2026-05-17)

### What's Complete
- 5 campaigns: CREATED, ACTIVE, and delivering
- 5 ad sets: $100 lifetime budget each, 10-day duration, US targeting, LOWEST_COST_WITHOUT_CAP
- 5 ads: all passed creative review, now in delivery phase
- 5 images: uploaded to Meta with hashes
- Facebook Page "SB Funding Group" (ID: 1045845225275938): created and connected
- Privacy policy + data deletion pages: live on GitHub Pages
- App icon: uploaded successfully

### Campaign Names
1. Growth Capital
2. Consolidation
3. Fast Funding
4. Industry Targeted
5. Social Proof

### API Access
- Full ads_management, ads_read, business_management, pages_manage_ads permissions
- Token auto-exchanges to 60-day long-lived tokens
- App ID: 956504317114012 (SunBiz Ads Live)
- App Secret: 94025bfdce4401b95f8e971fb3bb0994
- Ad Account: act_2105091616729816
- Page: SB Funding Group (ID: 1045845225275938)
- JotForm: https://form.jotform.com/253155026259254

### Image Hashes (uploaded to Meta)
- consolidation_hero: 70bee2ae5c872ec998a7eb2255cc549f
- consolidation_split: 2e95b524210ff0f70d1e63ecf6ce0115
- consolidation_dashboard: 37b852cacaa62a918d368bf33275f6ef
- growth_ceo: e82162a8151eb37fcee8afd876070096
- story_transformation: 223d0465b18486198de238b808d52d2f

### Important Technical Notes
- Special Ad Category: FINANCIAL_PRODUCTS_SERVICES (not CREDIT)
- Ad set times: must use Unix timestamps (not ISO 8601)
- Ad sets: must include bid_strategy=LOWEST_COST_WITHOUT_CAP
- No Instagram account linked - use Facebook-only placements
- Daily spending limit: $50 (Meta-imposed for new accounts, increases over time)
- Long-lived token stored in .long_lived_token.txt (not .env.agents)

### Key Credentials (in .env.agents)
- META_AD_ACCOUNT_ID=act_2105091616729816
- META_PAGE_ID=1045845225275938
- META_APP_ID=956504317114012
