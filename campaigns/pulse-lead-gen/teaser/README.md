# PULSE — Instagram DM Automation (Built Different)

> sent this before the call so you're not walking in blind.
> no fluff below — just what the system actually does and what we'll cover.

---

## what is PULSE

it's a full IG DM automation stack that replaces ManyChat. built on Next.js 14, Turso (SQLite edge DB), n8n for workflow orchestration, and Claude API for the AI layer.

the difference: ManyChat does keyword matching and broadcasts. PULSE runs a NEPQ-trained conversation pipeline that classifies inbound intent, moves leads through a 6-stage sales sequence, handles 13 objection types with custom rebuttal logic, and knows when to shut up and hand off to a human.

---

## system architecture

```
Instagram DM / Comment
        │
        ▼
┌──────────────────────────────────────────────────────┐
│                    META Webhooks                     │
│   /api/webhook  ←──── comment triggers + DMs ──────  │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│               n8n Orchestration Layer                │
│                                                      │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────┐  │
│  │  Comment    │   │  Broadcast   │   │  Cron    │  │
│  │  Trigger    │   │  Scheduler   │   │  Workers │  │
│  │  Workflow   │   │  Workflow    │   │  (stale/ │  │
│  └──────┬──────┘   └──────┬───────┘   │  follow) │  │
│         │                 │           └──────────┘  │
└─────────┼─────────────────┼───────────────────────┘
          │                 │
          ▼                 ▼
┌──────────────────────────────────────────────────────┐
│               PULSE API (Next.js 14)                 │
│                                                      │
│  /api/ai/reply ──► Doctrine Engine                   │
│                         │                            │
│              ┌──────────┼──────────┐                 │
│              ▼          ▼          ▼                 │
│         Classifier  Pipeline   Responder             │
│         (Haiku)     State       (Sonnet)             │
│                     Machine                          │
│                         │                            │
│              ┌──────────┼──────────┐                 │
│              ▼          ▼          ▼                 │
│         voice-rules  objections  stage-defs          │
│         (CC's tone)  (13 types)  (NEPQ 6-stage)      │
└──────────────────────────┬───────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────┐
│                    Turso (libSQL)                    │
│                                                      │
│  dm_threads        dm_messages      stage_transitions│
│  subscribers       tags             broadcasts       │
│  icp_configs       objection_history accounts        │
│  comment_triggers  sequences        follow_up_queue  │
└──────────────────────────────────────────────────────┘
                           │
                           ▼
              Meta Graph API (send DMs back)
```

---

## feature breakdown vs ManyChat

| capability | ManyChat | PULSE |
|---|---|---|
| comment → DM trigger | yes (keyword only) | yes (keyword + AI intent) |
| subscriber management | yes | yes |
| tags | yes | yes |
| broadcasts | yes | yes |
| DM sequences / drip | yes | yes |
| conversation AI | no (flow builder only) | yes — Claude Sonnet |
| NEPQ sales pipeline | no | yes — 6 active stages |
| objection handling | no | yes — 13 classified types |
| ICP filtering | no | yes — niche / region / follower min |
| friend mode (no-pitch) | no | yes — zero selling behavior |
| bot-check detection | no | yes — honest disclosure reframe |
| stage audit trail | no | yes — full transition log |
| stale lead cron | no | yes — 14-day auto-dead |
| human handoff signals | no | yes — pending_ai_draft flag |
| multi-account | yes | yes |
| pricing | $15-$299/mo per account | self-hosted, your infra |

---

## what we'll cover on the call

- **the doctrine layer** — how the 6-stage pipeline actually works, what a conversation looks like start to finish, and what the AI is deciding at each step
- **the objection tree** — 13 classified objection types (price, timing, trust, spouse, tried-before, bot-check, etc.) with NEPQ rebuttal logic baked in
- **your specific setup** — Meta app config, Turso DB, n8n workflow, Vercel deploy — what it takes to go live
- **what you'd customize** — ICP config, voice rules, system prompt, your booking link
- **the handoff protocol** — how it knows to stop replying and hand a thread to you

---

## loom video (record this before sending)

**length target:** 60-90 seconds. no longer.

**pre-record setup:**
- open the PULSE dashboard at your local/staging URL (two browser tabs: threads list + a live thread)
- have a test conversation running with at least 3 exchanges visible
- screen record at 1080p, no camera needed, or phone-selfie style on iPhone (more personal)

---

**script:**

> **[0:00-0:08] — pattern interrupt hook**
>
> "so ManyChat charges you per contact to send keyword-triggered messages. this does that — plus runs a full sales conversation on autopilot."

> **[0:08-0:25] — show the threads dashboard**
>
> "this is the dashboard. every thread has a stage — opener, qualify, pain, solution, objection. the AI moves the conversation through each one based on what the prospect actually says, not keywords."
>
> [click into a thread — show the message history]
>
> "see this? they came in from a comment trigger. the AI opened, asked one question, they mentioned their problem, and it's already in the pain stage."

> **[0:25-0:45] — show the doctrine layer (briefly)**
>
> "under the hood there's a 6-stage NEPQ pipeline — Jeremy Miner's framework — baked into the Claude system prompt. 13 objection types. voice rules that stop it from ever sounding like a bot."
>
> [show the objections table or a quick flash of the doctrine dashboard if you built it]
>
> "if they say 'I tried automation before and it didn't work' — it knows that objection, it knows the root cause, it knows exactly what to do."

> **[0:45-1:10] — show comment triggers + broadcasts**
>
> "comment triggers work exactly like ManyChat — someone comments a keyword on your reel, they get a DM. you can see the triggers here."
>
> [flash comment-triggers page]
>
> "broadcasts, tags, subscriber management — all there. same features, different engine underneath."

> **[1:10-1:30] — CTA**
>
> "on our call I'll walk you through what it takes to get this live on your account — Meta app setup, the database, n8n config. probably 30 min to deploy if you've done Vercel before."
>
> "link below to grab a time. if you've got questions before then just reply to this."

---

*questions before the call — just reply to the email.*
