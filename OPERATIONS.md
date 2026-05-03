# PULSE Operations Runbook

The Instagram DM automation has two pieces:

1. **PULSE dashboard** — Next.js app on Vercel (https://ig-setter-pro.vercel.app/) backed by Turso. Stores threads, messages, doctrine drafts, settings.
2. **Python daemon** — Playwright-driven Chrome on your local machine. Polls IG inbox + activity, talks to PULSE, sends auto-replies.

The two are fused via the PULSE webhook (`/api/webhook`) and the daemon-only endpoints (`/api/python/*`).

---

## Daily start (1 command)

In PowerShell:

```powershell
cd C:\Users\User\CMO-Agent
.\scripts\start_pulse_daemon.ps1
```

Preflight checks (Chrome installed, .env.agents complete, PULSE reachable, no stale daemons) run automatically. Real Chrome opens visibly, logs into IG with saved session, polls every 60–120s.

**Within 60–120s of launch, https://ig-setter-pro.vercel.app/ sidebar shows `DAEMON ONLINE` (mint green pulse).**

### Optional flags

```powershell
.\scripts\start_pulse_daemon.ps1 -Headless         # invisible Chrome (use after first manual login)
.\scripts\start_pulse_daemon.ps1 -PollMin 30 -PollMax 60   # faster polling (riskier)
```

---

## How the system works (data flow)

```
IG inbox / requests / activity-page
    ↓ Playwright real Chrome (channel="chrome")
Python daemon
    ├─→ POST /api/webhook        — pushes inbound + receives doctrine.draft
    ├─→ POST /api/python/heartbeat — every poll, dashboard liveness
    ├─→ GET  /api/python/outbox  — claims dashboard-approved sends
    ├─→ POST /api/python/outbox  — marks send sent/failed
    ├─→ GET  /api/python/triggers — active comment-to-DM triggers
    ├─→ POST /api/comment-webhook — scraped comments → match keyword → DM
    ├─→ POST /api/welcome-message/trigger — fetch welcome for new follower
    └─→ GET  /api/threads        — read archived handles (skip closed threads)
        ↓
PULSE (Vercel + Turso)
    - dm_threads, dm_messages, daily_stats
    - python_outbound_queue, comment_triggers, comment_events
    - subscribers, accounts (system_prompt, auto_send_enabled)
    - daemon_heartbeats
        ↓
Doctrine engine (lib/doctrine + lib/claude)
    - 30 messages of history
    - account.system_prompt (Brand Context)
    - 6-stage NEPQ pipeline + objection handling
    - friend mode if thread.is_friend = 1
    - Anthropic API → context-aware reply
```

---

## First-run setup checklist

1. `.env.agents` populated with:
   - `INSTAGRAM_USERNAME` + `INSTAGRAM_PASSWORD`
   - `PULSE_WEBHOOK_SECRET`, `PULSE_ACCOUNT_ID`, `PULSE_IG_PAGE_ID`
2. PULSE → Settings → **Brand Context** filled in (your linktree, calendar link, voice rules)
3. PULSE → Settings → **Welcome Message** filled in (new-follower DM)
4. Auto-Send toggle in PULSE sidebar set to ON
5. Run `.\scripts\start_pulse_daemon.ps1` — first launch will require manual IG login in the visible Chrome window if session isn't already saved
6. After manual login, daemon owns the session forever (saved in `tmp/ig-browser/`)

---

## Operations

### Verify daemon is healthy

| Signal | Where | Meaning |
|---|---|---|
| `DAEMON ONLINE` (mint, pulsing) | PULSE sidebar | Last heartbeat within 5min |
| `DAEMON DEGRADED` (amber) | PULSE sidebar | Last heartbeat 5–15min ago |
| `DAEMON OFFLINE` (red) | PULSE sidebar | No heartbeat in 15min+, restart needed |
| Tail log | `Get-Content tmp\ig_daemon.log -Wait -Tail 30` | Real-time poll output |
| Process | `Get-Process python` | Daemon should appear |

### Tail the live log

```powershell
Get-Content C:\Users\User\CMO-Agent\tmp\ig_daemon.log -Wait -Tail 30
```

### Stop daemon

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*instagram_engine*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

### Restart daemon

Just re-run `.\scripts\start_pulse_daemon.ps1`. It kills any existing daemon first.

---

## Settings & controls (PULSE dashboard)

| Where | What |
|---|---|
| Sidebar → Auto-Send toggle | Master switch. OFF = drafts saved to PULSE, replies don't auto-send |
| Sidebar → Daemon status | Live heartbeat indicator |
| Inbox → conversation header → **Friend** | Switch this thread to friend voice (no selling) |
| Inbox → conversation header → **Archive** | Mute Maven on this thread forever |
| Inbox → conversation header → **Delete** | Permanent thread removal |
| Inbox → Override panel | Manual reply (queues to python_outbound_queue) |
| Settings → **Brand Context** | Per-account `system_prompt` Maven uses on every reply |
| Settings → **Welcome Message** | Sent to new followers (NOT new DMs) |
| Triggers | Register IG post + keyword + DM message → daemon polls comments → DMs commenters |
| Doctrine | Stage analytics, conversion funnel |
| Analytics | Performance over time |

---

## Production-grade gates (all live)

Every outbound reply goes through `send_gateway`:
- **Killswitch**: env `MAVEN_FORCE_DRY_RUN=1` halts all sends
- **Daily cap**: 30 IG DMs per 24h per account
- **Per-recipient cooldown**: 24h between sends to the same handle
- **Draft critic**: rejects AI slop ("just wanted to", "circle back", etc.)
- **High-intent Telegram alert**: BOOKING/PRICING/PAYMENT pings your phone

Catch-up + safety:
- **Catch-up window**: only replies to inbound from last 6h on daemon restart
- **Notified-log pruning**: tmp/dm_notified.json drops entries >30d every poll
- **Archive skip**: handles with thread.status='closed' silently skipped
- **Spam blocklist**: env `IG_DM_BLOCKLIST` + built-in (whore/slut/spam/test)
- **Multi-message catch-up**: pushes ALL stacked inbound to PULSE so dm_messages stays truthful

---

## Troubleshooting

### "Daemon offline" in sidebar
1. Check process: `Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*instagram_engine*' }`
2. If empty → re-run `.\scripts\start_pulse_daemon.ps1`
3. If running → check `tmp\ig_daemon.log` for errors

### "no_input_found" in log
- Means real Chrome didn't render the conversation panel. Should be rare with `IG_BROWSER_CHANNEL=chrome`. If persistent, screenshot saved to `tmp\ig_no_input_<user>.png` — check what IG showed.
- Quick fix: restart daemon. Long-term: ensure you're using real Chrome (the script enforces it).

### IG login challenge (2FA, "unrecognized device")
- Run with `-Headless:$false` (default) so you SEE the prompt
- Click through it manually in the visible Chrome window
- Session is then saved; future runs work hands-free

### Webhook returning ok:false
- Tail log for `[ig-setter-pro] webhook reported failure: <message>`
- Check Vercel logs for the full stack trace
- Daemon's local fallback (`build_reply`) still works in degraded mode

### Want to wipe test data
```powershell
$secret = (Get-Content .env.agents | Select-String "^PULSE_WEBHOOK_SECRET=" | ForEach-Object { ($_ -split "=", 2)[1] })
Invoke-RestMethod -Uri "https://ig-setter-pro.vercel.app/api/admin/wipe-test-data" `
    -Method Post -Headers @{ "x-webhook-secret" = $secret }
```

### Deploy dashboard updates
```bash
cd C:\Users\User\APPS\ig-setter-pro
git push origin main   # Vercel auto-deploys in ~60s
```

---

## File map

### CMO-Agent (Python daemon)
- `scripts/instagram_engine.py` — daemon entry point, all polling logic
- `scripts/start_pulse_daemon.ps1` — launcher with preflight checks
- `scripts/send_gateway.py` — central send gate (cap, cooldown, killswitch, critic)
- `scripts/test_instagram_engine.py` — gate tests (6 cases)
- `tmp/ig-browser/` — persistent Chrome profile (IG session lives here)
- `tmp/ig_daemon.log` — live daemon log
- `tmp/dm_notified.json` — per-thread dedup state (auto-pruned 30d)
- `tmp/ig_followers_seen.json` — follower snapshot for welcome trigger
- `tmp/ig_comment_replied.json` — comment-trigger dedup
- `.env.agents` — credentials + PULSE wiring

### ig-setter-pro (PULSE dashboard)
- `app/api/webhook/route.ts` — daemon's primary push endpoint
- `app/api/python/heartbeat/route.ts` — daemon liveness
- `app/api/python/outbox/route.ts` — manual override queue
- `app/api/python/triggers/route.ts` — daemon-only trigger fetch
- `app/api/admin/wipe-test-data/route.ts` — bulk reset
- `app/api/admin/delete-thread/route.ts` — selective delete
- `lib/doctrine/` — stage machine + voice rules + objection handling
- `lib/claude/respond.ts` — Anthropic call with full transcript
- `components/Sidebar.tsx` — left nav + footer w/ daemon status
- `components/ConversationChain.tsx` — thread view w/ friend/archive/delete
- `components/DaemonStatus.tsx` — live heartbeat indicator
- `migrations/` — Turso schema (run via /api/admin/migrate)

---

## Production hardening summary (what's in place)

- Real Chrome via `channel="chrome"` (defeats IG bot detection)
- Heartbeat → dashboard daemon status indicator
- Webhook dedup response carries `auto_send_enabled` + `pending_ai_draft`
- Doctrine pulls 30 messages of history (~15 turns)
- Daemon prefers `doctrine.draft` over local `build_reply`
- Multi-attempt textbox locator with modal dismissal
- Conversation re-open via Playwright native mouse on stale panel
- Profile→Message bypass when inbox-open fails
- @handle resolution from conversation header (no more display-name confusion)
- All Playwright errors → screenshots in `tmp/`
- Friend mode + archive + delete from conversation header
- High-intent Telegram alerts (BOOKING/PRICING/PAYMENT)
- 6h catch-up window (won't reply to days-old DMs after downtime)
- Notified-log auto-pruning (30d)
- send_gateway: killswitch, 30/day cap, per-recipient cooldown, draft critic
- Comment-to-DM triggers (post URL + keyword + resource)
- New-follower welcome (snapshot first run, then DM new follows)
