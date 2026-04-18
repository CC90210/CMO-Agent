# Email: Full Delivery (fires after the call)

**trigger:** Calendar event ends (call date/time passes)
**send:** within 30 minutes of call end time
**merge tags:** `{{first_name}}`, `{{call_date}}`, `{{meet_link}}`

---

**subject:** everything from the call + next step

---

hey {{first_name}}

good call.

here's everything in one place so you're not hunting for it:

**the repo**
github.com/CC90210/ig-setter-pro — self-contained, MIT licensed. clone it and it's yours.

**30-min setup guide**
covers Turso, n8n cloud, Meta app creation, Vercel deploy, and the common pitfalls (message requests folder, libsql:// vs https://, Meta test user roles). step-by-step, no assumed context.

[PULSE SETUP.md](https://your-link-here) ← swap for hosted URL

**the doctrine layer**
the NEPQ pipeline, objection tree, and voice rules are in `lib/doctrine/` — that's where you'd tune the AI to match your voice and your ICP.

**what's next**

if you want to get live this week: start with the setup guide, get the Vercel deploy done, then ping me when you hit the Meta webhook step — that one catches everyone the first time and I'll just walk you through it.

if you're still thinking it through: no rush. reply with any questions and I'll answer them straight.

if you want OASIS to handle the full setup and onboarding: that's a conversation too. depends what your time's worth vs the lift.

either way you've got the system. do something with it.

— Conaugh McKenna
OASIS AI Solutions
oasisai.work
[book time](https://calendly.com/konamak)
