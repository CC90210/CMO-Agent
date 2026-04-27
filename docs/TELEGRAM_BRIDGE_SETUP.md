# Maven Telegram Bridge — Setup & Smoke Checklist

**Bridge file:** `telegram_agent.js` (V1.0)
**PM2 config:** `ecosystem.config.js`
**Process name:** `maven-telegram`
**Distinct from:** `bravo-telegram`, `atlas-telegram` — three bots, three tokens, no polling conflict.

---

## One-time setup (CC, ~10 min)

### 1. Create the bot

In Telegram, message [@BotFather](https://t.me/BotFather):

```
/newbot
```

Suggested name: `CC Maven CMO Bot`. Username can be anything ending in `bot` (e.g. `cc_maven_cmo_bot`).

BotFather replies with a token. Copy it.

### 2. Get your Telegram chat ID

Message [@userinfobot](https://t.me/userinfobot). It replies with your numeric ID.

### 3. Add to `.env.agents` (CMO-Agent root)

```
MAVEN_TELEGRAM_BOT_TOKEN=<token from BotFather>
MAVEN_TELEGRAM_CHAT_ID=<your numeric ID>
```

(Alternatively, leave `MAVEN_TELEGRAM_CHAT_ID` blank — the bridge will auto-register the first user who messages it and persist the ID.)

### 4. Per-machine repo paths (Mac only — Windows defaults are correct)

```
BRAVO_REPO=/Users/<you>/Business-Empire-Agent
ATLAS_REPO=/Users/<you>/APPS/CFO-Agent
AURA_REPO=/Users/<you>/AURA
MAVEN_REPO=/Users/<you>/CMO-Agent
```

### 5. Install dependencies (one-time)

```bash
cd C:/Users/User/CMO-Agent       # or your Mac path
npm install
```

### 6. Register with PM2

```bash
pm2 start ecosystem.config.js
pm2 save                          # persist across reboots
pm2 status                        # confirm maven-telegram online
pm2 logs maven-telegram --lines 30
```

The bridge runs a startup health check on every boot:
- `getMe` against Telegram (200 = token valid)
- A tiny ping against Anthropic (200 = `ANTHROPIC_API_KEY` valid)

Both failures show in `pm2 logs maven-telegram` AND ping the chat directly.

---

## 4-prompt smoke test (CC's phone)

Send each from Telegram and verify the response:

### 1. "Hey, who are you?"

**Expect:** Maven introduces itself as CMO of CC's 4-agent C-Suite, names Bravo (CEO) and Atlas (CFO) and Aura (Life), explains its marketing-surface ownership.

### 2. "What's our current ad spend this week?"

**Expect:** Maven reads `data/pulse/cfo_pulse.json` (Atlas's spend gate), shows status + age, lists approvals per channel/brand. Optionally pulls Meta/Google insights via `performance_reporter.py` if asked. Does NOT launch anything.

### 3. "Post a tweet about today's Bennett win"

**Expect:** Maven drafts via `script_ideation.py` or directly via Claude, runs `draft_critic`, shows preview. If destructive, outputs `⚠️ CONFIRM: ...` — bridge intercepts and shows ✅/❌ buttons. Only on ✅ does the actual `late_publisher.py` / `late_tool.py` call fire.

### 4. "Launch the new creative on Meta"

**Expect:** `PAID_LAUNCH_PATTERN` matches → bridge reads `cfo_pulse.json` BEFORE spawning Claude:
- If pulse missing / stale (>24h) / status≠open → 🚫 **REFUSED**, posts to Atlas's inbox.
- Else → shows approval card with status, age, approvals JSON, ✅/❌ buttons.
- On ✅: posts to Bravo + Atlas inboxes ("launching paid campaign — approved by CC"), then spawns Claude with CFO-cleared followup.

---

## Slash commands (already wired, no spawn)

| Command | What it does |
|---|---|
| `/help` | List of commands |
| `/status` | Pulse summary across Bravo / Atlas / Aura / Maven |
| `/spend` | Atlas spend-gate summary (cfo_pulse.json approvals per channel/brand) |
| `/campaigns` | `send_gateway --json stats` |
| `/killswitch` | Sets `MAVEN_FORCE_DRY_RUN=1` in this process (persist via `.env.agents`) |
| `/unleash` | Removes the killswitch from this process |
| `/pulse` | `state_sync.py --note "..."` to refresh `cmo_pulse.json` |
| `/sync` | Full state_sync with `--mem0` |
| `/audit` | `self_audit.py --json` health summary |
| `/tests` | Runs all 7 Python test files + `test_c_suite_context.js`, reports per-suite pass/fail |
| `/inbox` | `agent_inbox.py list --to maven` — unread cross-agent messages |
| `/post bravo|atlas|aura subject || body` | Cross-repo `agent_inbox.py post` |
| `/clear` | Clear conversation history for this chat |
| `/whoami` | Show your Telegram user/chat ID |

---

## Troubleshooting

**`pm2 status` shows maven-telegram errored**
→ `pm2 logs maven-telegram --lines 50`. Top causes:
- `MAVEN_TELEGRAM_BOT_TOKEN missing` → finish step 3 above.
- `Cannot find module 'dotenv'` → `npm install`.
- `409 Conflict` → another bridge instance is polling the same token. Either kill the duplicate (`pm2 delete maven-telegram` then `pm2 start ecosystem.config.js`) or this is the dual-machine case and the second instance correctly went dormant.

**Bridge says "Telegram getMe FAILED HTTP 401"**
→ Token is wrong or revoked. Re-issue via BotFather (`/token`) and update `.env.agents`, then `pm2 restart maven-telegram`.

**"Anthropic API FAILED HTTP 401"**
→ `ANTHROPIC_API_KEY` is bad. Update `.env.agents`, then `pm2 restart maven-telegram`.

**Killswitch in chat shows ENGAGED but you didn't engage it**
→ Check `.env.agents` for `MAVEN_FORCE_DRY_RUN=1`. Remove the line and `pm2 restart maven-telegram`.

**Sibling pulse shows ⚠ STALE for Atlas**
→ Atlas's `cfo_pulse.json` hasn't been refreshed in 24h. Have Atlas run its own state_sync. Until then, paid launches are HARD-REFUSED at the bridge.

---

## Architecture (one paragraph)

The bridge requires `scripts/c_suite_context.js` (copied verbatim from Bravo, byte-identical, exercised by `scripts/test_c_suite_context.js` — 38/38 PASS) for `SIBLING_REPOS` resolution and `readSiblingRepo`. It wraps `loadSiblingPulses` with a Maven-perspective version that iterates `[bravo, atlas, aura]`. Tier classifier prioritizes marketing T0 keywords (post, tweet, campaign, ROAS, image, video, caption, …) and demotes coding-task verbs back to T2. Paid-launch detection is a string match BEFORE Claude spawn — the bridge runs the CFO gate independently of Claude so even a hallucinating model can't bypass it. PM2 process name is `maven-telegram`; lock file `tmp/maven_telegram.lock.json` prevents dual-instance polling on the same machine. Logs at `memory/telegram_bridge.log`.
