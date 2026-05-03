# PULSE — Where We Left Off

**Last session: 2026-05-02**
**State: PARKED. Daemon stopped. Will resume when DM volume warrants it.**

---

## ✅ What works (proven live this session)

- **Real Chrome via `channel="chrome"` defeats IG bot detection** — this was the breakthrough. Playwright bundled Chromium gets fingerprinted; system Chrome looks like a normal user.
- **End-to-end auto-replies confirmed working live:**
  - `@ccmusicc03` got `"haha yoo not much man, what's good with you"` (CONVO)
  - `@ccmusicc03` got `"ya for sure, what are you trying to do with it..."` (CONVO with full context)
  - `@ccmusicc03` got `"what's the project?"` (BOOKING intent)
  - `@ccmckennaa.ai` got `"bet i'll book something"`
  - `@ccmckennaa.ai` got `"Okay, wow."`
- **Doctrine pulls 30 messages of history + Brand Context + voice rules** → context-aware Claude replies
- **PULSE webhook** stores threads/messages, returns `auto_send_enabled` + `doctrine.draft`, dedupes correctly even on stacked catch-up pushes
- **Heartbeat → sidebar status indicator** (DAEMON ONLINE / DEGRADED / OFFLINE pill in PULSE)
- **Friend / Archive / Delete buttons** on every conversation header
- **Comment → DM Triggers** UI + Python poller (untested live; built and ready)
- **New-follower welcome** (snapshot first run, then DM new follows; tested detection)
- **High-intent Telegram alerts** (BOOKING / PRICING / PAYMENT)

---

## ⚠️ Known limits (don't restart blind, fix these first)

1. **Test account got rate-limited / DM-blocked.** Symptom: "message chat is blocked" in IG UI. We hammered `@ccmckennaa` from `@CC` and `@Cc` test accounts ~50+ times. IG's anti-spam kicked in. **Wait 24-72h before next test, OR use different test accounts.**

2. **Chrome shows "unsupported command-line flag" yellow infobar** when daemon launches it. Cosmetic — does not affect functionality. The `--disable-blink-features=AutomationControlled` flag we pass triggers the warning but is required for IG to render conversations.

3. **First-run requires manual login click-through** in the visible Chrome window when IG flags the new device. After that, session persists in `tmp/ig-browser/` forever.

4. **Brand Context may need refinement.** The doctrine sometimes generates short/casual replies when a fuller answer is warranted. Iterate `system_prompt` in PULSE Settings as you see real conversations.

5. **Cron jobs in `/api/cron/*` (send-outreach, check-bookings, stale-leads) are NOT scheduled.** They're idle endpoints. Wire to vercel.json crons when you want proactive outbound.

---

## 🚀 To resume (when DM volume picks up)

```powershell
cd C:\Users\User\CMO-Agent
.\scripts\start_pulse_daemon.ps1
```

Single command. Runs preflight checks (Chrome, .env, PULSE reachable, kills stale daemons), launches detached, prints the PID + tail command.

**Within 60-120s, https://ig-setter-pro.vercel.app/ sidebar shows DAEMON ONLINE (mint pulse).**

Full runbook: `OPERATIONS.md`

---

## 🐛 Bucket list — finish before serious production use

| Priority | Item | Why |
|---|---|---|
| HIGH | Headless real Chrome (after first manual login in visible mode) | So daemon runs invisibly in background; less screen real estate |
| HIGH | VPS deployment with Xvfb | Don't want CC's laptop = single point of failure |
| MED | Conversation panel mount detection — retry on empty state with longer wait | Edge case where IG renders empty briefly |
| MED | Move SunBiz / OASIS welcome + brand context out of `accounts.system_prompt` into per-account proper config | Multi-account scaling |
| MED | Wire Vercel `/api/cron/*` routes to vercel.json crons | Proactive outreach + booking checks + stale-lead nudges |
| LOW | Test the comment-to-DM trigger system live (built but never end-to-end tested) | When you want lead-magnet DMs from post comments |
| LOW | "Mark as friend" / "Archive" tested from PULSE UI live | Built but only PATCH endpoint verified, not the click flow |
| LOW | Telegram intent alerts wired to your specific phone | Code exists, needs `MAVEN_TELEGRAM_BOT_TOKEN` + chat ID |

---

## 📁 Where everything lives

### Critical files to know
- `scripts/instagram_engine.py` — daemon (3500+ lines; THE engine)
- `scripts/start_pulse_daemon.ps1` — single-command launcher with preflight
- `OPERATIONS.md` — full ops runbook
- `tmp/ig-browser/` — persistent Chrome profile (IG session — DO NOT delete)
- `tmp/ig_daemon.log` — last run's log
- `.env.agents` — credentials + PULSE wiring (gitignored)

### Recent commits worth knowing (in order)
- `816f0e0` — stealth flags (insufficient alone)
- `0598c8b` — Playwright native mouse click
- `c0bc75a` — profile→Message bypass
- `2f284e4` — CDP support (alternative path)
- `11a4c42` — **`channel="chrome"` REAL CHROME** ← the actual fix
- `b03c187` — heartbeat + sidebar status
- `8ba6640` — startup script + OPERATIONS.md
- (this commit) — minimal Chrome args + this status doc

---

## 💰 What this cost to build

Every layer of the production stack is in place:
- 6-stage NEPQ doctrine
- Brand-context-aware Claude replies (30-msg history)
- send_gateway: killswitch / 30-day cap / per-recipient cooldown / draft critic
- Multi-tier conversation-open recovery
- Real Chrome bot-detection bypass
- Heartbeat + sidebar status
- Friend / Archive / Delete controls
- Comment → DM triggers
- New-follower welcome flow
- Catch-up window for downtime recovery
- Notified-log auto-pruning
- Telegram intent alerts

Rebuild cost from scratch: ~5-7 days of focused work. Don't lose it.

---

## TL;DR for future-you

**The bot works.** Real Chrome. Doctrine. Brand context. Multi-turn conversations. Auto-reply. Manual override. Heartbeat. All proven live.

**The bot is parked** because we hammered the test account into IG's anti-spam wall. Real DM volume from real prospects won't trigger that — it's specific to a test account sending the same message 50 times in 30 min.

**To restart:** `.\scripts\start_pulse_daemon.ps1` and watch the sidebar go ONLINE.

**To deploy seriously:** finish the VPS + headless real-Chrome work in the bucket list above.
