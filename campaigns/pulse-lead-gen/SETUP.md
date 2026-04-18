# PULSE — Clone and Run (30-Minute Setup Guide)

> zero context assumed. follow in order.

---

## prerequisites

- Node.js 18+
- a Vercel account (free tier works)
- a Turso account (free tier works — 500 DB limit, plenty for one account)
- an n8n cloud account (free tier: 5 active workflows, enough to start)
- a Meta Developer account with a Facebook Page or Instagram Business account
- an Anthropic API key (claude.ai → API keys)

---

## step 1 — clone the repo

```bash
git clone https://github.com/CC90210/ig-setter-pro.git
cd ig-setter-pro
npm install
```

---

## step 2 — Turso database

**create the database:**

```bash
# install Turso CLI
curl -sSfL https://get.tur.so/install.sh | bash

# log in
turso auth login

# create your DB
turso db create pulse-db

# get the connection URL
turso db show pulse-db --url
# → libsql://pulse-db-<your-org>.turso.io

# create an auth token
turso db tokens create pulse-db
# → eyJ...  (save this)
```

**run migrations:**

```bash
# copy the URL and token into your shell temporarily
export TURSO_DATABASE_URL="libsql://pulse-db-<your-org>.turso.io"
export TURSO_AUTH_TOKEN="eyJ..."

# run migrations (applies all files in /migrations in order)
npm run db:migrate
```

if `db:migrate` isn't in package.json, run the SQL files manually via the Turso shell:
```bash
turso db shell pulse-db < migrations/001_initial.sql
turso db shell pulse-db < migrations/002_doctrine.sql
# etc — run all files in /migrations in numeric order
```

---

## step 3 — environment variables

copy the example file:

```bash
cp .env.example .env.local
```

fill in every value:

```env
# Turso
TURSO_DATABASE_URL=libsql://pulse-db-<your-org>.turso.io
TURSO_AUTH_TOKEN=eyJ...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Meta (filled in step 5)
META_APP_SECRET=
META_VERIFY_TOKEN=any_random_string_you_pick
META_PAGE_ACCESS_TOKEN=

# App
NEXTAUTH_SECRET=any_random_string_32_chars_min
NEXTAUTH_URL=https://your-vercel-url.vercel.app
```

---

## step 4 — n8n cloud setup

1. sign up at **cloud.n8n.io** (free tier)
2. create a new workflow — name it "PULSE Comment Trigger"
3. import the workflow file: in your repo, look at `n8n/` directory — there are JSON workflow exports
4. in n8n: **Settings → n8n API** → create an API key
5. add your n8n cloud URL and API key to `.env.local`:

```env
N8N_WEBHOOK_URL=https://your-instance.n8n.cloud/webhook/...
N8N_API_KEY=n8n_api_...
```

**workflow wiring:**
- the comment trigger workflow listens for a webhook from Meta, parses the comment payload, calls your PULSE API at `/api/comment-webhook`, and sends the DM back via the Graph API
- the broadcast workflow calls `/api/broadcasts/send` on a schedule
- the stale-lead cron calls `/api/cron/stale` daily

you can import the pre-built workflows from `n8n/` in the repo — they just need your webhook URLs and credentials filled in.

---

## step 5 — Meta app creation

this is the longest step. read it fully before starting.

**5a. create a Meta Developer app**

1. go to **developers.facebook.com → My Apps → Create App**
2. app type: **Business**
3. add products: **Messenger** and **Instagram Graph API**

**5b. connect your Instagram account**

1. in the app dashboard: **Instagram → Basic Display → Add Instagram Testers**
2. add your Instagram Business account as a tester
3. go to your Instagram account settings → Apps and Websites → Tester Invites → accept it
4. back in the app: **Instagram → Instagram Graph API → Generate Token** for your account
5. copy the long-lived page access token → this is your `META_PAGE_ACCESS_TOKEN`

**5c. get the app secret**

App Dashboard → Settings → Basic → App Secret → Show → copy it → `META_APP_SECRET`

**5d. set up the webhook**

1. App Dashboard → Webhooks → Instagram → Subscribe
2. callback URL: `https://your-vercel-url.vercel.app/api/webhook`
3. verify token: whatever you put in `META_VERIFY_TOKEN` in `.env.local`
4. subscribe to: **messages**, **messaging_postbacks**, **comments**

Meta will do a GET request to your webhook to verify — your app needs to be deployed (step 6) before this works. come back and do 5d after deploying.

**5e. get your Instagram account ID**

```bash
curl "https://graph.facebook.com/v19.0/me/accounts?access_token=YOUR_PAGE_TOKEN"
# find your Instagram Business Account ID in the response
```

you'll need this to seed the `accounts` table in Turso:

```bash
turso db shell pulse-db
INSERT INTO accounts (id, instagram_account_id, display_name, access_token, is_active)
VALUES ('acc_01', 'YOUR_IG_ACCOUNT_ID', 'your-handle', 'YOUR_PAGE_TOKEN', 1);
```

---

## step 6 — Vercel deploy

```bash
# install Vercel CLI if you don't have it
npm i -g vercel

# deploy
vercel

# follow prompts — link to your Vercel account, create new project
# when asked for environment variables, paste all values from .env.local
```

or connect via Vercel dashboard:
1. vercel.com → New Project → Import from GitHub
2. select `ig-setter-pro`
3. Environment Variables → add all values from `.env.local`
4. Deploy

once deployed, copy your production URL and:
- update `NEXTAUTH_URL` in Vercel env vars to match
- go back to step 5d and register the webhook with the production URL

---

## step 7 — verify it's working

```bash
# hit the status endpoint
curl https://your-vercel-url.vercel.app/api/status
# should return { ok: true }

# send a test DM from a Meta test user account
# check Turso for a new dm_threads row
turso db shell pulse-db "SELECT * FROM dm_threads LIMIT 5;"
```

---

## common pitfalls

**Meta test user role — "can't send DMs to this account"**

your Instagram account needs to be in the app as a tester AND you need to send the DM *from* a separate test user account, not the account itself. go to App Dashboard → Roles → Test Users → create one, log in with it on another device or browser, and send the DM from there. Meta blocks the account from DMing itself.

**messages landing in the Message Requests folder, not primary inbox**

this happens when the recipient hasn't interacted with the sender before. Meta puts cold DMs from non-followers into Requests. your webhook still fires — but if you're checking the Instagram app and wondering why you don't see the reply, check Requests. on the API side, you need the `instagram_manage_messages` permission approved (for production — test users bypass this).

**Turso `libsql://` vs `https://` protocol gotcha**

the Turso client library uses `libsql://` as the protocol in `TURSO_DATABASE_URL`. if you accidentally paste `https://` (which is what the Turso dashboard shows in some views), the client will fail silently or throw a confusing auth error. always use `libsql://` in `.env`. the Turso CLI `--url` flag gives you the right format — copy from there, not from the browser URL bar.

**n8n webhook URL changes on free tier**

n8n cloud free tier assigns a subdomain. if you restart your workflow or change settings, the webhook URL can regenerate. if your Meta webhooks stop firing, check that the n8n webhook URL in your Meta app subscription still matches. pin it: in n8n, use a static webhook path in the Webhook node settings.

**Meta webhook verify fails on first subscribe**

Meta sends a GET with `hub.challenge` to your webhook URL. your app must respond with the challenge value. this only works if the app is live (deployed to Vercel). you can't test this locally unless you use ngrok. if you get a 404 or timeout, check that your Vercel deployment is live and that `META_VERIFY_TOKEN` in Vercel env vars matches exactly what you typed into the Meta webhook form.

**`NEXTAUTH_URL` mismatch in production**

Next.js Auth checks that the request origin matches `NEXTAUTH_URL`. if you deploy to a preview URL and then promote to production without updating this env var, auth will break. always update `NEXTAUTH_URL` in Vercel to match your actual production domain.

**Anthropic rate limits on cold traffic spikes**

if you're running a broadcast to 500+ subscribers and every reply triggers a Claude call, you'll hit rate limits fast. the classify step uses Haiku (cheap, fast) and the respond step uses Sonnet (slower). set `ANTHROPIC_MAX_RETRIES=3` and `ANTHROPIC_TIMEOUT=30000` in your env. for large broadcasts, the n8n workflow should have a rate-limiter node between the subscriber loop and the API call.

---

## ICP config (optional but recommended)

once the account is seeded, set your ideal customer profile so the AI knows who to qualify:

```bash
turso db shell pulse-db
INSERT INTO icp_configs (id, account_id, target_niches, allowed_regions, min_followers)
VALUES (
  'icp_01',
  'acc_01',
  '["hvac","plumbing","wellness","personal training","real estate"]',
  '["CA","US"]',
  500
);
```

the classifier will check inbound leads against this and move out-of-ICP threads to `closed_lost` automatically.

---

questions: reply to the email or DM @konamak on Instagram.
