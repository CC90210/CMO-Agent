# LONG TERM — Verified Persistent Facts

---

## Platform Facts

### Google Ads API
- API version: v23.1 (latest as of March 2026)
- Python SDK: `google-ads` v29.2.0
- Developer token access levels: Test (15K ops/day, test only), Basic (15K ops/day, production), Standard (unlimited)
- Auth: OAuth2 (client_id + client_secret + refresh_token) + developer_token + customer_id
- Official MCP server (googleads/google-ads-mcp) is READ-ONLY — cannot create/modify campaigns
- Community MCP server (grantweston/google-ads-mcp-complete) has write capabilities

### Meta Marketing API
- Graph API version: v22.0 (latest as of March 2026)
- Python SDK: `facebook-business` v22.0
- Auth: System user access token (non-expiring) + app_id + app_secret + ad_account_id
- Rate limits: Score-based (GET=1 point, POST=3 points), ~100K points/hour on Standard tier
- Lending ads MUST use special_ad_categories: ['CREDIT']
- Credit ads restrict targeting: no age, gender, zip code targeting
- MCP server: pipeboard-co/meta-ads-mcp (most mature, v1.0.20)

### Campaign Structures
- Google: Campaign → Ad Group → Ad (+ Keywords as AdGroupCriterion)
- Meta: Campaign → Ad Set → Ad (+ AdCreative linked to Ad)
- Both: Budgets can be set at campaign or ad group/set level

## Infrastructure Facts
- Windows MCP env vars: Must use .cmd wrapper scripts (JSON env blocks unreliable)
- Python venv location: `.venv/` in project root
- Credentials file: `.env.agents` (gitignored)
