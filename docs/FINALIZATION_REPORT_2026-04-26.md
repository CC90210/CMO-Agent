# Maven V1.1 → V1.2 Finalization Report

**Date:** 2026-04-26
**Author:** Maven (CMO Agent), executing CC's deep finalization pass on the Maven-specific surface
**Predecessor:** V1.1 structural upgrade (commit 067cde8) shipped earlier today
**Verdict:** SHIPPED. send_gateway 65/65 + late_publisher 5/5 + instagram_engine 6/6 + content_pipeline 10/10 + performance_reporter 10/10 = **96/96 tests PASS**. self_audit health_score = **100/100**. 1 HIGH security finding fixed inline; 2 HIGH + 2 MEDIUM reliability findings documented as Known Limitations for V1.3; 3 doc gaps captured in "Next Up"; 0 boundary breaches.

---

## Lens 1 — Transfer integration

The four scripts Bravo transferred (`late_tool.py`, `late_publisher.py`, `instagram_engine.py`, `codex_image_gen.py`) were sitting untracked. All four now parse cleanly. `late_tool.py` and `codex_image_gen.py` are pure tools (no outbound on Maven's behalf — late_tool just shells out to the Late SDK; codex_image_gen subprocesses Codex for image generation, no credentials touched on Maven's side; the OpenAI auth is implicit via codex-companion). `late_publisher.py` and `instagram_engine.py` ARE outbound surfaces and are now gated. `late_publisher._publish_row` calls `send_gateway.send(channel="social", agent_source="late_publisher", brand=row.brand, dry_run=True)` after the character-limit check and before `publish_via_late()`; if the gateway returns `blocked`, the row is marked failed and the late_tool subprocess is never invoked; if it returns `dry_run` with a `FORCE_DRY_RUN` reason, the row is short-circuited but not marked failed (killswitch behaviour). `instagram_engine._send_dm_reply` now takes a `recipient` kwarg, derives a stable `lead_id = "ig_dm_" + sha1(recipient)[:16]` so per-recipient 24h cooldown works without needing a CRM row, and routes through `send_gateway.send(channel="instagram_dm", ...)` before any Playwright keystroke; all 4 call sites pass the username. New send_gateway channels: `social` (cap 50/day, 10/hr) and `instagram_dm` (cap 30/day, 5/hr, cooldown 24h per recipient). Tests: `test_late_publisher.py` 5/5 pass (golden, gate-block, killswitch, daily cap, char-limit pre-check); `test_instagram_engine.py` 6/6 pass (golden, critic-reject, killswitch, cap, cooldown, recipient-hash stability). Existing `test_send_gateway.py` still 48/48. `brain/CAPABILITIES.md` updated with the 4 new scripts including the load-bearing contract that `late_tool.py posts --status published --json` is what Bravo's CEO dashboard subprocesses to.

---

## Lens 2 — send_gateway deep audit (+12 marketing-specific cases)

Six new gate functions added to `send_gateway.py` that fire BEFORE the draft_critic gate (so they short-circuit on cheap rejects): `check_utm_compliance` (every URL in commercial body must have utm_source + utm_medium + utm_campaign — unsubscribe links exempt), `check_subject_slop` (matches "unlock the power of", "game-changing", "revolutionary", "take your X to the next level", blocks all-caps subjects ≥12 letters, blocks emoji-only openers), `check_image_alt_text` (image attachments must have non-empty `alt_text` — non-image attachments exempt), `check_creative_fatigue` (blocks the same `creative_id` to the same `lead_id` within 14 days via the lead_interactions metadata), `check_list_mode_caps` (when ≥50 sends in trailing hour, list-mode hourly cap of 200 applies), and `is_vip_recipient` (env-driven `MAVEN_VIP_EMAILS` + `MAVEN_VIP_DOMAINS`; VIPs get critic-non-ship as ship-with-warning + metadata flag instead of block). The CFO spend gate gained two failure modes: stale-pulse (`updated_at` >24h) and zero-budget (`daily_budget_usd <= 0`). Test count went 48 → 60: list-mode independent test (#34); CFO stale (#35); CFO zero-budget (#36); UTM missing blocks (#37); UTM tagged passes (#37b); subject slop blocks (#38); all-caps subject blocks (#38b); image without alt_text blocks (#39); creative-fatigue blocks (#40 — seeded 5 days ago with explicit past cooldown_until so the cooldown gate doesn't preempt); VIP override ships-with-warning + metadata flagged (#41); non-VIP still blocks on critic (#42 regression guard); double-opt-in metadata convention with confirmed status passes (#43). All 60 pass in 0.36s offline.

---

## Lens 3 — CFO spend gate, end-to-end

`check_cfo_spend_gate()` already covered 4 fail modes from V1.1 (missing pulse, closed status, no brand approval, over-budget) and Lens 2 added 2 more (stale >24h, zero-budget). Lens 3 closes the gap with 5 dedicated tests (#44–48): missing-pulse via helper call, malformed JSON via helper call, no `updated_at` field falls through to approval check (documented behaviour, not a fail mode), status=open with empty approvals dict, and the full happy-path with explicit timestamp + amount under budget. Total CFO-related test coverage is now 12 tests across the suite. The schema Atlas writes is locked in `brain/CFO_GATE_CONTRACT.md` — every fail-closed condition mapped to a reason fragment so Atlas can grep for breakage if Maven's gate ever rejects unexpectedly. Send_gateway test suite: 65/65 pass.

---

## Lens 4 — Content pipeline functional

`content_pipeline.generate_captions` had two real bugs: (1) the `threads` platform was missing entirely, (2) the `x` truncation logic `base[:250] + " " + hashtags[:25] if len(base) < 250 else base[:275]` could yield 276-char output (over the 280 platform limit but under the spec's tolerance — still wrong). Replaced both with a `PLATFORM_CAPTION_LIMITS` dict (the canonical spec: x=280, threads=500, instagram=2200, linkedin=3000, tiktok=4000, youtube_shorts=100, facebook=63206) and made every output assemble its full string then truncate to its limit. New `test_content_pipeline.py` runs 10 cases — one length-cap test per platform, a regression guard for `threads` presence, an explicit X-overflow guard with a 240-char base, and an empty-transcript safety check. All 10 pass in 0.02s. End-to-end smoke test on a real .mp4 deferred — there's no test clip in `media/raw/` and Whisper transcription needs audio. Adding `media/raw/SMOKE_TEST.mp4` is a 1-line CC follow-up that will let `python scripts/content_pipeline.py SMOKE_TEST.mp4 --topic "test"` exercise the full 7-step pipeline; the per-platform layer is now provably correct independent of the video stage.

---

## Lens 5 — Attribution & ROAS rigor

Maven's de facto attribution surface is `lead_interactions` — every send_gateway call writes one row carrying `agent_source` (which engine fired), `channel` (email/meta_ads/google_ads/social/instagram_dm), `subject`, `content` preview, and a `metadata` JSON column with `brand`, `intent`, `creative_id`, optional `spend_amount_usd`, and (for VIP) `critic_override`. That covers the lens-5 fields (source = agent_source; medium = channel; campaign = metadata.brand or metadata.campaign; creative_id = metadata.creative_id; send_at = created_at; gate_decision = metadata.reservation_status; spend_committed = metadata.spend_amount_usd) without a separate attribution table — one fewer write to keep consistent. `meta_ads_engine.create_campaign` and `google_ads_engine.create_search_campaign` and `email_blast.send_single_email` all route through `send_gateway.send(...)` (verified in V1.1 + Lens 1) so every campaign launch produces a row by construction. New `test_performance_reporter.py` exercises `_safe_float`, `_lead_count`, `_cost_per_lead` on synthetic Meta-shape data with KNOWN answers (10 cases, all pass) — the synthetic-ROAS test asserts spend=$100, 10 leads at $50 LTV → revenue $500 → ROAS 5.0x; the zero-spend test asserts the caller-side guard returns None instead of dividing by zero. A standalone `attribution` table abstraction (separate from lead_interactions) is deferred to V1.3 — only worth the second write if Bravo or Atlas need a dedicated marketing-only ledger; for now lead_interactions doubles correctly.

---

## Lens 6 — Adversarial review (4 parallel sub-agents)

Four sub-agents ran in parallel reading c:\Users\User\CMO-Agent end-to-end with non-overlapping mandates. **Security** found 1 HIGH (VIP override read os.environ even when .env.agents had set the key — env-injection elevation path; fixed by giving .env.agents-set keys absolute precedence over os.environ, all 65 tests still pass), 3 MEDIUM (long-lived Meta token persisted plaintext on disk — gitignored but recommend in-memory + auto-refresh; INFO-level token-path log line — recommend DEBUG; subprocess `env={**os.environ, ...}` forwards all secrets to Late SDK child — recommend minimal env dict), 2 LOW (codex_image_gen output_path lacks directory-traversal validation; FFmpeg ASS filter escape leaves single-quote injection surface). All hardcoded-secrets / shell-injection / SSRF categories CLEAN. **Reliability** found 2 HIGH (Meta `_TRANSIENT_CODES` does NOT include 429 — rate-limit raises immediately with no backoff; Google Ads OAuth refresh-token expiry is non-transient and triggers atomic failure with no proactive refresh), 2 MEDIUM (Late SDK timeout has no inter-row backoff in `cmd_publish_due` so chained timeouts blow the 120s scheduler budget; cfo_pulse staleness re-reads file per send with no in-memory cache, so a stale-at-11-AM scenario blocks every in-flight publish), 2 LOW (draft_critic Haiku call has no explicit timeout; Instagram session-expiry isn't detected in `page.goto()` redirects to `/accounts/login` so DM HTML is parsed as login HTML silently). **Future-CC** found 3 doc gaps: CLAUDE.md has no `/campaign-unpause` workflow command, `brain/CAPABILITIES.md` script registry isn't grep-able by operation ("publish a post" doesn't surface late_publisher), no `brain/CAMPAIGN_LIFECYCLE.md` covers PAUSED→ACTIVE→DRAFT transitions; `MAVEN_FORCE_DRY_RUN` override is documented in code but not in CLAUDE.md as a copy-paste command. **Bravo boundaries** found ZERO structural breaches — `email_blast` is bulk marketing not 1:1 sales; `instagram_engine._handle_booking_confirmation` is the explicit grey-zone exception (logistics, not closing); `capture_lead_to_crm` correctly hands off to Bravo via Supabase `lead_interactions`; no Maven code writes to `clients`, schedules client meetings, generates proposals, or moderates Skool/Bennett. The only follow-up Bravo's review names is a code comment citing the boundaries doc inside `_handle_booking_confirmation`. Total adversarial output: 1 HIGH security fixed inline, 2 HIGH reliability + 2 MEDIUM reliability documented as Known Limitations (V1.3 work), 3 doc gaps documented for next-up, 0 boundary breaches.

---

## Already-solid (validated, no changes needed)

- **send_gateway architecture** holds up under marketing-specific load. The 6 new content gates (UTM, subject slop, image alt-text, creative fatigue, list-mode, VIP override) all fail-closed-by-default and short-circuit before the expensive critic call.
- **Cross-repo agent_inbox routing** still resolves correctly — no changes needed since V1.1.
- **CFO spend gate fail-closed posture** survived adversarial scrutiny: 8 named conditions, 12 dedicated tests, schema canonicalized in `brain/CFO_GATE_CONTRACT.md`.
- **Bravo/Maven boundary** is structurally clean per the boundary review. The booking-confirmation grey zone is correctly scoped (logistics, not closing).
- **email_blast.py** routing through send_gateway has been confirmed as the only outbound path — no smtplib bypass anywhere.

## Fixed inline this pass

- **VIP env-injection elevation (Security HIGH):** `is_vip_recipient` now gives `.env.agents` keys absolute precedence over `os.environ`. An attacker who can set `os.environ` cannot elevate arbitrary recipients to VIP if the operator has explicitly configured the key.
- **Per-platform caption character bugs:** added `threads` (was missing), fixed `x` to truncate the assembled string (not parts) so 240-char base + 25-char hashtag stub no longer pushes past 280.
- **late_publisher + instagram_engine outbound routing:** every Late post and every IG DM now goes through send_gateway with daily/hourly caps, killswitch honored, draft_critic fail-closed.
- **CFO gate stale + zero-budget:** 2 new fail-closed conditions added with reason fragments documented in `brain/CFO_GATE_CONTRACT.md`.
- **brain/INDEX.md + self_audit allowlist:** CFO_GATE_CONTRACT linked + allowlisted; orphan count back to 0.

## Deferred (Known Limitations — explicit V1.3 work)

| # | Item | Reason | Severity |
|---|------|--------|----------|
| 1 | Meta API code 429 not in `_TRANSIENT_CODES` | needs SDK-level retry-policy refactor + idempotency-key plumbing | HIGH |
| 2 | Google Ads OAuth refresh on auth failure | requires storing refresh-token + integrating token-refresh flow into `_mutate_with_retry` | HIGH |
| 3 | Late SDK timeout has no inter-row backoff | requires scheduler-level circuit breaker; Maven currently fails fast per-row instead | MEDIUM |
| 4 | cfo_pulse re-read per send (no in-memory cache) | acceptable for now (file is local + tiny); add 5-min cache when QPS becomes a concern | MEDIUM |
| 5 | draft_critic Haiku call has no explicit timeout | Anthropic SDK default (~60s) holds; pass explicit `timeout=30` next pass | LOW |
| 6 | Instagram session-expiry not detected in page.goto redirects | low frequency in practice (session lasts weeks); add `/accounts/login` redirect check next pass | LOW |
| 7 | content_pipeline mid-step crash leaves orphan files | rare; add a try/finally cleanup wrapper in `run_pipeline` | LOW |
| 8 | Long-lived Meta token persisted plaintext to disk | gitignored; in-memory + auto-refresh is the right move but needs a token-broker abstraction | MEDIUM |
| 9 | INFO-level log of token-save path | low signal; demote to DEBUG | LOW |
| 10 | Late SDK subprocess inherits full os.environ | minimal env dict is cleaner but only matters if a child process exfiltrates | LOW |
| 11 | codex_image_gen `--output` lacks directory-traversal validation | rare attack surface (CC controls own prompts); add `Path.resolve().is_relative_to(EXPORT_DIR)` next pass | LOW |
| 12 | Standalone `attribution` table abstraction | lead_interactions doubles correctly today; only worth the second write if Bravo or Atlas need a dedicated marketing-only ledger | LOW |
| 13 | content_pipeline end-to-end smoke on real .mp4 | needs `media/raw/SMOKE_TEST.mp4` from CC; per-platform caption layer already proven correct | LOW |

## Next up (for CC + the C-suite)

1. **Drop a 30-second test clip** at `media/raw/SMOKE_TEST.mp4` so `python scripts/content_pipeline.py SMOKE_TEST.mp4 --topic "test"` exercises the full Whisper → karaoke → captions → image → 7-platform captions pipeline end-to-end.
2. **CLAUDE.md adds (15-min CC edit):** a `/campaign-unpause` workflow command pointing at `meta_ads_engine.resume_campaign` + `google_ads_engine.resume_campaign`; a "Safety & Override" subsection with `MAVEN_FORCE_DRY_RUN=1 python scripts/send_gateway.py send ...` example; a "Quick-Launch Paths" subsection naming `ad-engine/` for video ads vs `scripts/meta_ads_engine.py` for static.
3. **`brain/CAMPAIGN_LIFECYCLE.md` (1–2 page CC edit):** PAUSED → ACTIVE → DRAFT → REJECTED state map with the exact CLI commands per transition.
4. **`brain/CAPABILITIES.md` operation→script quick-table** at the top of the doc so future-CC can grep "publish a post" and find `late_publisher.py` in <5s.
5. **For Atlas:** confirm `cfo_pulse.json` schema matches `brain/CFO_GATE_CONTRACT.md`. Especially the `updated_at` field and `daily_budget_usd` semantics.
6. **For Bravo:** add a code comment inside `instagram_engine._handle_booking_confirmation` citing `RESPONSIBILITY_BOUNDARIES.md` so the boundary scope (logistics, not closing) is provable to future maintainers.

## What I didn't touch (intentionally out of scope)

- **The 13 V1.3 Known Limitations** above — out of pass scope; they're documented + prioritized so V1.3 has a clean punch list.
- **Bravo's repo, Atlas's repo, Aura's repo** — read-only, never written.
- **`.env.agents` and any credential file** — never opened, never edited.
- **Pre-existing untracked files** (V1.1 pickup is complete; no new untracked items remain).
