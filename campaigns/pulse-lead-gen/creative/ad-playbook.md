---
tags: [campaign, pulse, lead-gen, meta-ads, reels, creative]
campaign: pulse-lead-gen
offer: free github repo in exchange for 30-min call
created: 2026-04-18
owner: CC
---

# PULSE Lead-Gen Ad Playbook

## Strategy

**WHO.** Two stacked audiences, not one. Primary: agency owners 25–45 running IG-based DM funnels for clients — they've been paying ManyChat $99–$399/mo per workspace, they're technical enough to know n8n exists, and they've hit the wall where ManyChat's pricing scales faster than their margin. They don't want another SaaS; they want the stack. Secondary: coaches, course creators, and personal brands at 5k–100k followers who manually reply to DMs at 1am because their VA can't qualify leads well enough. They don't care about the repo — they care that "the guy who built it" is on the call. Both buy the same ad, but for different reasons: the agency wants sovereignty, the creator wants the operator.

**WHY THIS WORKS.** The "I built my own" authority play is the cleanest status signal in the setter/automation space right now. ManyChat ads are everywhere and they all feel the same — templated, affiliate-flavored, "unlock leads on autopilot" energy. A 22-year-old founder showing the actual repo, the actual n8n graph, the actual Turso console — that's proof, not a pitch. The free repo is the hook, but the real offer is the call. Giving the code away reverses the usual "gate the thing, sell the call" model: people expect to pay for the asset and pay for the call. Flip it. The repo is free because the repo alone won't make them money — the 30 minutes will. That asymmetry reads as confidence, not desperation. It also filters: anyone who books already thinks in code + systems, which is exactly the OASIS ICP.

**WHERE TO RUN.** Meta Reels first, placement-exclusive — it's the cheapest CPM for this audience in Q2 2026 and the vertical format doesn't require a re-cut for TikTok/YT Shorts later. Start with one Advantage+ audience stack (custom interests: ManyChat, n8n, Zapier, Claude, Next.js + lookalike from existing OASIS email list). Week 2: expand to IG Stories with the same creatives letterboxed. Week 3: port the top-performing Reel to YouTube Shorts with a UTM-tagged short link — Shorts audience skews more technical, longer attention span, better for the repo angle. Do NOT run on Facebook Feed. Do NOT run on Audience Network. Do NOT boost organic posts — build from Ads Manager so UTMs and pixel events stay clean.

---

## Hook Variant 1 — AUTHORITY

**Angle.** "I built my own so I stopped paying ManyChat." Founder-as-proof. The status move is showing the repo exists, not selling it.

### 15-sec Reel

| Sec | Shot | CC speaks | On-screen text | B-roll |
|-----|------|-----------|----------------|--------|
| 0.0–1.5 | Tight on CC, no intro, mid-sentence energy | "ManyChat was billing me $347 a month so i just built my own." | — | — |
| 1.5–4.0 | Cut to laptop screen, VS Code open, `pulse/` repo tree visible, cursor flicks through `lib/doctrine/voice-rules.ts` | "took a weekend." | lower-third: `pulse/ — next.js + turso + n8n + claude` | screen-recording, real cursor motion |
| 4.0–7.5 | Cut to n8n canvas, the DM-intake workflow with 8-ish nodes, CC's cursor hovers one | "this is the thing that replies to every DM, qualifies the lead, books the call." | — | real n8n workflow, not a mock |
| 7.5–10.0 | Cut back to CC, same framing as 0.0 | "i'm giving the whole repo away." | "free repo" (bottom, small, sans-serif) | — |
| 10.0–13.5 | Cut to Turso console showing live conversations table scrolling | "book a 30-min call, tell me what you're trying to automate, repo's yours." | — | real data, blur sensitive handles |
| 13.5–15.0 | Cut back to CC, dead-center, neutral | "link's in the bio." | — | — |

**Audio.** No music bed. CC's voice only. Cuts are hard — no crossfades, no whooshes.

### Meta Static (1080x1080)

**Variant A — caption-style (looks organic):**
- Headline: `i stopped paying manychat $347/mo`
- Body: `built my own DM automation in a weekend. next.js, turso, n8n, claude. giving the repo away free if you book a 30-min call — just wanna know what you're automating.`
- CTA button: `Learn More`
- Visual: screenshot of VS Code, `pulse/` folder expanded, no filter, slight tilt like a phone photo

**Variant B — bold-claim:**
- Headline: `FREE REPO: the DM bot that replaced my $347/mo ManyChat bill`
- Body: `next.js + turso + n8n + claude. production code, not a template. yours free when you book a call.`
- CTA button: `Sign Up`
- Visual: clean split — left half terminal with `pulse/ main ✓`, right half n8n node graph

### IG Bio CTA swap

```
22. building PULSE — the DM bot i use instead of manychat
free repo → [link]
```

---

## Hook Variant 2 — CURIOSITY

**Angle.** Open loop — something's broken about the way everyone's doing this. Don't name it until the payoff.

### 15-sec Reel

| Sec | Shot | CC speaks | On-screen text | B-roll |
|-----|------|-----------|----------------|--------|
| 0.0–2.0 | CC looking off-camera, then back — pattern interrupt, quiet | "nobody talks about what manychat actually costs you." | — | — |
| 2.0–4.0 | Cut to a ManyChat billing screenshot (real, redacted), zoom into the $ line | "it's not the $99." | arrow pointing at `$347.00 USD` | — |
| 4.0–7.0 | Cut to CC, walking toward camera, handheld | "it's the fact that every flow you build lives on their rails. you don't own it." | — | — |
| 7.0–10.5 | Cut to VS Code, scrolling through `pulse/app/api/ig/webhook/route.ts` | "so i built one that lives on mine." | lower-third: `your meta app. your db. your keys.` | real code, real filename |
| 10.5–13.0 | Cut back to CC | "i'm giving it away. 30-min call, tell me what you're building." | — | — |
| 13.0–15.0 | Hold on CC, no text | "link's in the bio." | — | — |

**Audio.** One quiet synth pad starting at 7.0s, cuts out at 13.0s. No drop.

### Meta Static (1080x1080)

**Variant A — caption-style:**
- Headline: `the part of manychat nobody mentions`
- Body: `every flow you build — it lives on their servers. you don't own it. you rent it. here's what i did instead (+ the repo, free, if you book a call).`
- CTA button: `Learn More`
- Visual: two side-by-side phone mockups — left one ManyChat dashboard with a lock icon, right one a terminal with `git clone pulse` — no graphic styling, just the screenshots

**Variant B — bold-claim:**
- Headline: `YOU DON'T OWN YOUR MANYCHAT FLOWS`
- Body: `you rent them. month after month. i open-sourced the alternative — next.js, your keys, your database. free when you book.`
- CTA button: `Download`
- Visual: black background, white monospace text reading `rm -rf manychat` with a blinking cursor

### IG Bio CTA swap

```
you don't own your manychat flows. i built something you do own.
free repo → [link]
```

---

## Hook Variant 3 — PROOF

**Angle.** Show the numbers. Don't claim, demonstrate. This is the ad that converts the skeptic who's already seen 40 "I built X" reels this week.

### 15-sec Reel

| Sec | Shot | CC speaks | On-screen text | B-roll |
|-----|------|-----------|----------------|--------|
| 0.0–2.0 | Cut cold into the Turso console — live `conversations` table, rows updating | "this is my DM bot. last 24 hours." | `turso db — live` (top left) | real console |
| 2.0–5.0 | Zoom into one row, highlight `stage: booked` and `qualification_score: 0.87` | "38 DMs in. 11 qualified. 4 booked calls." | numbers animate on as CC says them | — |
| 5.0–8.0 | Cut to Calendly/Cal.com admin view, 4 bookings visible for today | "zero of those replies were me." | — | real bookings, blur names |
| 8.0–10.5 | Cut to CC, casual, no frame change | "the whole thing is a github repo. next.js, turso, n8n, claude." | — | — |
| 10.5–13.0 | Cut to `pulse/` repo on github.com, CC's cursor on the README | "i'm giving it away if you hop on a 30-min call." | — | real repo page |
| 13.0–15.0 | Cut back to CC | "link's in bio." | — | — |

**Audio.** No music. Keyboard clicks + notification sound ("ping") at 2.0, 3.5, 5.0s as each number lands.

### Meta Static (1080x1080)

**Variant A — caption-style:**
- Headline: `38 DMs → 11 qualified → 4 booked. last 24 hours.`
- Body: `i didn't reply to any of them. it's a repo i wrote called PULSE — next.js, turso, n8n, claude. free if you book a call and show me what you're automating.`
- CTA button: `Learn More`
- Visual: a single screenshot of the Turso `conversations` table, 6 rows visible, `stage` column highlighted with `booked` in green — the rest untouched, unstyled

**Variant B — bold-claim:**
- Headline: `4 BOOKED CALLS. ZERO HUMAN REPLIES.`
- Body: `24 hours. one open-source repo. next.js + turso + n8n + claude. i'll give you the code when you book.`
- CTA button: `Sign Up`
- Visual: a bar chart, no fancy styling — black bars on white, labels `sent / qualified / booked`, numbers `38 / 11 / 4`

### IG Bio CTA swap

```
4 booked calls in 24h. zero human replies. repo's free → [link]
```

---

## Hook Variant 4 — CONTRARIAN

**Angle.** Challenge the category. Everyone's selling automation. CC's position: most of the "AI DM bots" you've seen are garbage, and here's why.

### 15-sec Reel

| Sec | Shot | CC speaks | On-screen text | B-roll |
|-----|------|-----------|----------------|--------|
| 0.0–2.5 | CC, blunt, no smile | "most AI DM bots are trash. i'll show you why." | — | — |
| 2.5–5.0 | Cut to a real ManyChat flow builder with branching IF/THEN nodes sprawling | "this is what they ship. keyword triggers. scripted trees." | highlight 3 boxes with red outline | screen record |
| 5.0–8.0 | Cut to CC | "people don't DM you in keywords. they ramble. they ask 3 things at once." | — | — |
| 8.0–11.0 | Cut to a terminal running `pulse` locally, Claude response streaming in real-time to a fake inbound DM | "so i built one that actually reads what they said." | lower-third: `claude-powered. stage-aware. dm-native.` | live stream, real tokens |
| 11.0–13.5 | Cut back to CC | "repo's free. book a call, it's yours." | — | — |
| 13.5–15.0 | Hold on CC, deadpan | "or keep using keyword triggers. up to you." | — | — |

**Audio.** No music. The terminal stream at 8.0–11.0 has typing sound.

### Meta Static (1080x1080)

**Variant A — caption-style:**
- Headline: `keyword triggers aren't ai.`
- Body: `they're IF/THEN statements with a dashboard. i built a real one — claude reads the DM, figures out the stage, writes the reply. repo's free when you book.`
- CTA button: `Learn More`
- Visual: two columns — left labeled "ManyChat," shows a keyword tree diagram; right labeled "PULSE," shows a single arrow labeled "claude reads it."

**Variant B — bold-claim:**
- Headline: `STOP CALLING KEYWORD TRIGGERS "AI"`
- Body: `IF user_says("hi") THEN send("welcome!") isn't intelligence. PULSE is. it's free — book a call, get the repo.`
- CTA button: `Download`
- Visual: pseudo-code on black background, `if` / `then` in red, a line below reads `// this is not ai` in white

### IG Bio CTA swap

```
keyword triggers aren't ai. built a real one. repo's free → [link]
```

---

## /pulse-ad-launch — Workflow (8 steps)

Budget: **$10/day per ad set**, 4 ad sets (one per hook variant) = **$40/day** total opening spend. Learning phase requires ~50 conversions per ad set before the algo stabilizes — at a booking-conversion rate of ~2%, that's 2,500 clicks per ad set, reachable at $10/day in ~10–14 days. Don't rush it.

1. **Pre-flight.** Meta Pixel + Conversions API firing on `/book` page view and `/book/confirmed`. UTMs on every ad (`utm_source=meta&utm_campaign=pulse-lead-gen&utm_content={{hook_variant}}`). Repo kept private until call booked — sent via confirmation email. If the repo is public the offer collapses.

2. **Audience stack.** One Advantage+ campaign, one ad set per hook variant. Custom interests: ManyChat, n8n, Zapier, Claude, OpenAI, Next.js, Supabase, Turso, Make.com. Lookalike 1% from OASIS email list (250+ contacts minimum, seed with Bennett's community if allowed). Exclude: existing OASIS customers, anyone who's booked in last 60 days.

3. **Creative upload.** Four Reels (one per hook), eight statics (two per hook). All creatives tagged in naming convention `pulse_{hook}_{format}_v1` — e.g., `pulse_authority_reel_v1`, `pulse_proof_static_bold_v1`. Always leave room for `_v2` etc.

4. **Launch day 1.** All 4 ad sets live, $10/day each. Do NOT touch for 72 hours. Meta's learning phase needs silence — every edit resets the learning signal.

5. **Day 3 check.** First real read. Metrics that matter, in order: (1) booking rate per $ spent, (2) CTR on Reels, (3) CPM. Ignore "engagement rate" — it's vanity on ad creative.

6. **Day 7 optimization gate.** Any ad set below 0.5% booking rate at $70 spent = **pause**. Any ad set above 1.5% booking rate = **double the budget to $20/day**. Winning creative gets duplicated with minor variants (different thumbnail, different first 2 seconds). Do not duplicate losers.

7. **Day 14 retargeting layer.** Turn on the retargeting audience (page-visitors who didn't book, last 14 days). Budget: $15/day to retargeting alone. Use the 10 copy variants below, rotated in 2 ad sets of 5 variants each.

8. **Kill criteria — hard.** Any single ad set spending $150+ cumulative with zero bookings = **kill it**, no debate. Full campaign spending $500+ with booking CAC over $60 (OASIS LTV floor is $2K, so $60 CAC is still 33x — but past $60 the math stops compounding fast enough) = **pause all, rebrief creative, rebuild hooks**. Don't optimize a bad offer with better targeting.

---

## Retargeting Copy — 10 variants

For people who hit `/book` and bounced. All 125 chars or less to fit Meta's primary-text sweet spot on mobile. Voice matches CC's DM rules — lowercase, no sales words, no "book a call" direct-ask.

1. `you looked at the pulse page and closed it. same repo, still free. 30 min, still on me.`
2. `the call slot is 30 minutes. the repo is mit-licensed. the only thing stopping you is you.`
3. `forgot about it? i didn't. repo's still sitting there with your name on it.`
4. `saw you check out the page. ask me anything on the call — don't have to book blind.`
5. `it's github + n8n + a claude prompt. you already know how to read it. just hop on for 30.`
6. `if you didn't book because you thought it was a pitch — it's not. i just want to see what you're automating.`
7. `two people booked after bouncing the first time. the repo doesn't care what day you show up.`
8. `the page loaded. you scrolled. something made you pause. what was it?`
9. `no upsell on the call. i don't even mention oasis unless you ask. it's a repo handoff + a chat.`
10. `the version of you that books this call is 4 clicks away from a working DM bot by friday.`

Rotation rule: 5 variants per ad set, 2 ad sets. Swap out the bottom-2 performers every 7 days. Keep (10) as a control — it's the strongest close and will likely be the winner.

---

*Only good things from now on.*
