# CAPABILITIES — Complete Tool Inventory

> All tools available to Maven (CMO) across all interfaces.

---

## MCP Servers (8 Total)

### 1. Google Ads MCP
- **Status:** PENDING SETUP
- **Server:** `google-ads-mcp` (community: grantweston/google-ads-mcp-complete or custom)
- **Capabilities:** Campaign CRUD, Ad Group CRUD, Ad CRUD, Keyword management, GAQL reporting, Budget management, Asset upload
- **Auth:** Developer token + OAuth2 (client_id, client_secret, refresh_token) + customer_id
- **Fallback:** Direct `google-ads` Python SDK (v29.2.0)

### 2. Meta Ads MCP
- **Status:** PENDING SETUP
- **Server:** `meta-ads-mcp` (pipeboard-co/meta-ads-mcp or custom)
- **Capabilities:** Campaign CRUD, Ad Set CRUD, Ad CRUD, Creative management, Audience management, Insights/reporting, Media upload
- **Auth:** System user access token + app_id + app_secret + ad_account_id
- **Fallback:** Direct `facebook-business` Python SDK (v22.0)

### 3. Playwright MCP
- **Status:** AVAILABLE
- **Server:** `@playwright/mcp@latest`
- **Capabilities:** Browser navigation, screenshots, form filling, clicking, JavaScript evaluation
- **Use:** Fallback for operations not supported by APIs, visual verification of ads

### 4. Context7 MCP
- **Status:** AVAILABLE
- **Server:** `@upstash/context7-mcp@latest`
- **Capabilities:** Library documentation lookup, code examples
- **Use:** Look up Google Ads API or Meta API documentation on demand

### 5. Memory MCP
- **Status:** AVAILABLE
- **Server:** `@modelcontextprotocol/server-memory`
- **Capabilities:** Knowledge graph CRUD (entities, relations, observations)
- **Use:** Persistent campaign knowledge, audience insights, optimization learnings

### 6. Sequential Thinking MCP
- **Status:** AVAILABLE
- **Server:** `@modelcontextprotocol/server-sequential-thinking`
- **Capabilities:** Structured multi-step reasoning
- **Use:** Complex campaign strategy, budget allocation, optimization decisions

### 7. n8n MCP
- **Status:** AVAILABLE (if n8n instance running)
- **Server:** `n8n-mcp` (via wrapper script)
- **Capabilities:** Workflow search, execution, details
- **Use:** Automated reporting, scheduled campaign checks, alert workflows

### 8. Late MCP
- **Status:** AVAILABLE (if configured)
- **Server:** `late-sdk[mcp]` (via wrapper script)
- **Capabilities:** Social media posting, account management, cross-posting
- **Use:** Organic social media content alongside paid ads

---

## Python SDK Tools (Fallback Layer)

### Google Ads Python SDK
- **Package:** `google-ads` (v29.2.0)
- **API Version:** v23.1 (latest)
- **Key Services:**
  - `CampaignService` — Campaign CRUD
  - `AdGroupService` — Ad Group CRUD
  - `AdGroupAdService` — Ad CRUD
  - `AdGroupCriterionService` — Keyword/targeting CRUD
  - `CampaignBudgetService` — Budget management
  - `GoogleAdsService.SearchStream` — GAQL reporting
  - `AssetService` — Media asset management
  - `BatchJobService` — Bulk operations
  - `BiddingStrategyService` — Bid strategy management

### Meta Marketing Python SDK
- **Package:** `facebook-business` (v22.0)
- **API Version:** Graph API v22.0
- **Key Classes:**
  - `AdAccount` — Account-level operations
  - `Campaign` — Campaign CRUD
  - `AdSet` — Ad Set CRUD
  - `Ad` — Ad CRUD
  - `AdCreative` — Creative management
  - `AdImage` — Image upload/management
  - `AdVideo` — Video upload/management
  - `CustomAudience` — Audience management
  - `AdsInsights` — Performance reporting

---

## Native IDE/CLI Tools

### Claude Code (Opus 4.6)
- Read, Write, Edit, Glob, Grep, Bash
- Agent (sub-agent orchestration)
- TodoWrite (task tracking)
- WebSearch, WebFetch

### Antigravity IDE
- All Claude Code tools + IDE-specific features
- Workflow commands (`.agents/workflows/`)
- Rules and customization

### Gemini CLI
- File operations, web search
- Speed-optimized for quick tasks

---

## AI Image Generation Tools

### Gemini Imagen (Nano Banana)
- **Status:** Requires API key
- **Package:** `google-genai`
- **Models:** `gemini-2.0-flash-exp` (native image gen), `imagen-3.0-generate-002` (dedicated)
- **Use:** Generate professional ad creative images from text prompts — business lending ads, A/B test variants, all platform sizes
- **Script:** `scripts/imagen_generate.py`
- **Install:** `pip install google-genai Pillow`
- **API Key:** Get from https://aistudio.google.com/apikey → set `GEMINI_API_KEY` in `.env.agents`

---

## Video Production Tools

### FFmpeg
- **Status:** Requires installation
- **Use:** Video trimming, resizing, compression, caption burning, thumbnail extraction
- **Install:** `winget install ffmpeg` or download from ffmpeg.org

### Whisper (OpenAI)
- **Status:** Requires installation
- **Package:** `openai-whisper`
- **Use:** Auto-captioning / speech-to-text for video ads
- **Install:** `pip install openai-whisper`

---

## Billing & Payment (Ad Spend)

### Google Ads Billing
- **How it works:** Google bills the linked payment method (credit card, bank account) in the Google Ads account
- **API access:** `BillingSetupService` for viewing billing info, `InvoiceService` for invoice data
- **Budget control:** Set daily budgets via `CampaignBudgetService` — Google charges the payment method on file
- **Reporting:** `metrics.cost_micros` in GAQL gives exact spend data
- **Note:** The API does NOT process payments directly — it controls budgets, Google handles billing

### Meta Ads Billing
- **How it works:** Meta bills the payment method linked in Business Manager (credit card, PayPal, bank)
- **API access:** Read billing info via `/act_{id}/billing_events`, payment methods via `/act_{id}/payment_methods`
- **Budget control:** Set daily/lifetime budgets on campaigns and ad sets — Meta charges the payment method
- **Reporting:** `spend` field in Insights API gives exact spend data
- **Note:** The API does NOT process payments directly — it controls budgets, Meta handles billing

### Budget Management via API
Both platforms work the same way:
1. **Set budget** via API → Platform delivers ads up to that budget
2. **Platform bills** the payment method on file in the ad account
3. **We monitor** spend via reporting APIs (GAQL / Insights)
4. **We control** by adjusting budgets, pausing campaigns, or setting rules

---

## Tool Counts
- **MCP Servers:** 8 (2 pending setup, 6 available)
- **Python SDK Services:** 19 (Google: 9, Meta: 10)
- **AI Image Generation:** 1 (Gemini Imagen)
- **Video Tools:** 2 (FFmpeg, Whisper)
- **Native Tools:** 12+
- **Agents:** 19 (16 marketing-specific + 3 cross-cutting)
- **Skills:** 54 (32 marketing-specific + 22 cross-cutting from Bravo parity)
- **Workflows:** 11

## Maven Script Registry

The CMO repo's `scripts/` directory holds these executables. Each is invoked from a slash command, a sub-agent, or directly during operations.

### Send-safety chokepoint (V1.1)
- `send_gateway.py` — single outbound chokepoint for email, Meta Ads spend, Google Ads spend, Late posts. CASL, name-sanitization, daily/hourly caps, draft-critic gate, CFO spend gate. Tested by `test_send_gateway.py` (48 cases).
- `name_utils.py` — recipient-name placeholder defense (the "Hi Contact," fix).
- `casl_compliance.py` — suppression list, footer, List-Unsubscribe headers.
- `draft_critic.py` — adversarial Haiku reviewer; fail-closed gate.

### Delegation + ops (V1.1)
- `agent_inbox.py` — async cross-agent messaging (Bravo / Atlas / Aura / Codex).
- `codex_delegate.py` — Codex bridge for backend marketing work at scale.
- `state_sync.py` — end-of-session: STATE.md + SESSION_LOG.md + cmo_pulse.json.
- `self_audit.py` — health score (frontmatter + send_gateway tests + pulse freshness + orphans).

### Telegram surface (V1.3)
- `notify.py` — programmatic Telegram alerts. Categories: campaign, cfo-block, brand-violation, draft-critic-block, daily-cap-threshold, killswitch, send-gateway-error, lead-captured, content-published, ab-test-winner, performance, error. Loud-by-default for blocks/errors, silent-by-default for high-volume content. Falls back to `BRAVO_TELEGRAM_BOT_TOKEN`/generic `TELEGRAM_BOT_TOKEN` if `MAVEN_TELEGRAM_BOT_TOKEN` is absent. Always writes `memory/notify.log` so nothing is lost when Telegram is down. Tested by `test_notify.py` (13 cases).
- `../telegram_agent.js` — Maven's standalone Telegram bridge. Distinct bot token from Bravo/Atlas (no polling conflict). Reads cross-agent pulse files at `BRAVO_REPO`/`ATLAS_REPO`/`AURA_REPO` (env overrides). Slash commands: `/status`, `/spend`, `/campaigns`, `/killswitch`, `/unleash`, `/pulse`, `/sync`, `/audit`, `/tests`, `/inbox`, `/post`. Plain text spawns Maven's Claude Code CLI. Lock file at `tmp/maven_telegram.lock.json` prevents dual-instance polling.

### Marketing engines
- `email_blast.py` — bulk marketing email (routes through send_gateway).
- `meta_ads_engine.py` — Meta Marketing API CRUD (spend gated through send_gateway).
- `google_ads_engine.py` — Google Ads SDK CRUD (spend gated through send_gateway).
- `meta_campaign_builder.py` — campaign-structure builder for Meta.
- `jotform_tracker.py` — JotForm submission polling.
- `late_tool.py` — Late SDK CLI (accounts, profiles, posts, create, cross-post). Bravo's CEO dashboard subprocesses to `posts --status published --json` — JSON output shape is a load-bearing contract.
- `late_publisher.py` — content_calendar publisher; gates every publish through send_gateway (channel="social"). Tested by `test_late_publisher.py` (5 cases).
- `instagram_engine.py` — Instagram DM auto-reply + booking confirmation via Playwright. Outbound DMs gated through send_gateway (channel="instagram_dm", per-recipient cooldown). Tested by `test_instagram_engine.py` (6 cases).
- `codex_image_gen.py` — content image generation via Codex/OpenAI (no credentials hardcoded; auth implicit via codex-companion).
- `ad_copy_generator.py` — copy generation pipeline.
- `ab_testing_engine.py` — A/B test management.
- `campaign_templates.py` — campaign-structure templates.
- `performance_reporter.py` — cross-platform reporting.
- `update_utm_links.py` — UTM hygiene.
- `audit_logger.py` — audit trail for all platform mutations.
- `cache_layer.py` — caching for platform reads.
- `monitoring.py` — heartbeat for the marketing daemons.
- `pulse_client.py` — read C-suite pulse files.
- `full_diagnostic.py` — end-to-end stack diagnostic.

### Content + creative
- `content_engine.py`, `content_pipeline.py`, `content_generator.py`, `content_repurposer.py`, `edit_content_v2.py` — content production pipeline.
- `script_ideation.py` — generates video/post script ideas grounded in `brain/CONTENT_BIBLE.md` (3 daily pillars + hook bank + 7 pacing rules), `brain/VIDEO_PRODUCTION_BIBLE.md`, `brain/MARKETING_CANON.md`, `brain/SOUL.md`, and live cross-agent pulse signal (Bravo / Atlas / Aura). Calls Claude Sonnet 4.6, writes to `data/ideation/<timestamp>.md`. CLI flags: `--count N`, `--pillar sobriety_log|quote_drop|ceo_log`, `--format short_video|long_video|post|carousel`, `--topic "<seed>"`. Tested by `test_script_ideation.py` (21 cases — foundation loading, pulse signal, prompt assembly, mocked API call, output writer, CLI dispatch).
- `generate_logo.py`, `save_logo.py` — brand logo generation.
- `imagen_generate.py` — Gemini Imagen ad creative.
- `generate_page_assets.py` — landing-page asset generation.
- `render_video.py` — video composition + caption rendering.

### Token + setup
- `generate_google_ads_token.py` — OAuth flow for Google Ads.
- `setup.py` — repo bootstrap.

---

## Related

- [[INDEX]] — vault home
- [[AGENTS]] — 16 sub-agents + routing
- [[MARKETING_CANON]] — framework library every skill references
- [[WRITING]] — writing/communication hub for every deliverable
- [[SHARED_DB]] — Supabase protocol
- [[ATTRIBUTION_MODEL]] — tracking pipeline

## Obsidian Links
- [[INDEX]] | [[SOUL]] | [[STATE]] | [[AGENTS]]
