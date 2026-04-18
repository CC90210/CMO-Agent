---
tags: [credentials, env, security]
---

# Maven's Credential Structure

> How to populate `.env.agents` + what each group of keys does.
> Reference template: `.env.agents.template` (committed, safe, zero values).
> Real file: `.env.agents` (gitignored, never commit).

## Why Maven has its own env (not SunBiz's)

Maven was split from the SunBiz-Marketing codebase. The original `.env.agents` inherited from that split had **SunBiz client credentials** (MCA Meta ad account, SunBiz Gmail blast, SunBiz JotForm). Those belong to the client, not Maven.

**The fix:**
- Maven's `.env.agents` now contains CC's own credentials (OASIS, personal brand, PropFlow, Nostalgic)
- SunBiz client creds stay in `C:\Users\User\Marketing-Agent\.env.agents` (the SunBiz-Marketing repo)
- Maven shells out to SunBiz-Marketing via subprocess when running legacy SunBiz work — never imports SunBiz creds into its own process

## Three Credential Categories

### 1. Shared infrastructure (same across all 4 agents)

Inherited from Bravo's `.env.agents`. Maven does NOT own these — it pulls live copies and updates when Bravo rotates them.

| Key | Purpose |
|-----|---------|
| `ANTHROPIC_API_KEY` | Claude API (all Maven reasoning) |
| `GEMINI_API_KEY` | Google Imagen for image generation |
| `ELEVENLABS_API_KEY` | Voice synthesis for video content |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Git operations |
| `VERCEL_TOKEN` | Deploy Maven-owned frontends |
| `FIRECRAWL_API_KEY` | Web scraping for competitive intel |
| `LATE_API_KEY` | Zernio/Late for social post scheduling |
| `N8N_API_URL` / `N8N_API_KEY` / `N8N_BEARER_TOKEN` | Workflow automation |
| `BRAVO_SUPABASE_*` | Shared cross-agent DB (`phctllmtsogkovoilwos`) — 38 tables, Maven writes rows tagged `agent='maven'` |

### 2. Per-client Supabase (Maven reads for marketing context)

| Scope | Keys | What Maven uses them for |
|-------|------|--------------------------|
| OASIS AI Platform | `OASIS_SUPABASE_*` | Read client signups / usage for retention campaigns |
| Nostalgic Requests | `NOSTALGIC_SUPABASE_*` | Drive marketing off real DJ/event data |
| PropFlow | (future) | When product goes live |

Maven never writes to these — they're each app's own sovereign DB. Maven READS for context.

### 3. Maven-specific ad + posting credentials (CC's OWN accounts)

**These are placeholders you fill in as you create each account.** They are CC's own brand ad accounts — NOT SunBiz's.

#### OASIS AI Meta Ads — primary
```
OASIS_META_APP_ID=
OASIS_META_APP_SECRET=
OASIS_META_ACCESS_TOKEN=
OASIS_META_AD_ACCOUNT_ID=
OASIS_META_PAGE_ID=
OASIS_META_PIXEL_ID=
```
Where: developers.facebook.com → create Meta app → System User → grant ads_management scope.
When: before launching the pulse-lead-gen campaign.

#### OASIS AI Google Ads
```
OASIS_GOOGLE_ADS_DEVELOPER_TOKEN=
OASIS_GOOGLE_ADS_CUSTOMER_ID=
OASIS_GOOGLE_ADS_CLIENT_ID=
OASIS_GOOGLE_ADS_CLIENT_SECRET=
OASIS_GOOGLE_ADS_REFRESH_TOKEN=
```
Where: ads.google.com → API access → apply for developer token.
When: if/when Google Search becomes a channel (lower priority than Meta for OASIS).

#### PropFlow Meta Ads
```
PROPFLOW_META_*
```
Fill when PropFlow beta ships and a launch campaign is planned.

#### Nostalgic Requests Shopify
```
NOSTALGIC_SHOPIFY_STORE=
NOSTALGIC_SHOPIFY_ACCESS_TOKEN=
```
Where: Shopify admin → Apps → Develop apps → Storefront API access.
When: if Maven needs to render product ads via the Shopify connector in `ad-engine/`.

### What is NOT in Maven's env

SunBiz Funding client credentials. These live in the SunBiz-Marketing repo:
- `C:\Users\User\Marketing-Agent\.env.agents`
- Keys: `META_APP_ID`, `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`, `META_PAGE_ID`, `GOOGLE_ADS_CUSTOMER_ID`, `JOTFORM_FORM_ID`, SunBiz Gmail blast credentials, compliance URLs, etc.

When Maven needs to run a SunBiz campaign (maintenance mode only), it shells out:
```python
import subprocess
# Load SunBiz env in subprocess; never import into Maven's own process
subprocess.run(
    ["python", "scripts/email_outbound.py", "--campaign", "xyz"],
    cwd=r"C:\Users\User\Marketing-Agent",
    env={}  # uses SunBiz-Marketing's .env.agents via dotenv
)
```

## Security Rules

1. **Never commit `.env.agents`** — gitignored. `.env.agents.template` is committable (zero values).
2. **Never import SunBiz credentials into Maven's process.** Shell-out only.
3. **Rotate shared creds at Bravo** — if `ANTHROPIC_API_KEY` rotates, update Bravo's env first, then copy to Maven + Atlas + Aura. The shared creds originate in Bravo.
4. **Supabase write restrictions**: Maven's queries to the shared DB must always include `agent='maven'` and (if touching resident data) `resident='cc'|'shared'`. See `brain/SHARED_DB.md` + `ROOMMATE_AGENT_PROTOCOL.md` for the RLS model.
5. **No client creds commingled**: every client Maven serves should get its own `CLIENT_*` prefix in the env so revocation is surgical.

## How to bootstrap on a fresh clone

```bash
cd C:\Users\User\CMO-Agent
cp .env.agents.template .env.agents
# Fill in values. Start with:
#   1. Shared creds (copy from Bravo's .env.agents)
#   2. Platform-specific when you create each account
```

## Re-running the migration

If CC rotates or adds shared creds in Bravo and wants them pushed to Maven:
```bash
python C:\Users\User\Business-Empire-Agent\scripts\build_maven_env.py
```
Backs up current Maven env to `.env.agents.sunbiz_inherited_backup` (gitignored), writes fresh env from Bravo. Delete the backup once verified.

## Related Docs

- `.env.agents.template` — the committable version; update here when you add new keys
- `../Business-Empire-Agent/brain/C_SUITE_ARCHITECTURE.md` — overall governance
- `brain/SHARED_DB.md` — Supabase conventions
- `brain/clients/sunbiz-funding.md` — SunBiz client profile (Maven maintains in legacy mode)
