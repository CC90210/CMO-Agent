---
description: Systematic 4-phase debugging — investigate, pattern analysis, hypothesis testing, and documented resolution.
---

// turbo-all

# /debug — Systematic Debugging

## When to Use
Use `/debug` when something is broken, erroring, or not working as expected.

## Steps

1. **Phase 1 — Investigate:**
   a) Read the FULL error message
   b) Identify source: Google Ads API? Meta API? MCP? Local?
   c) Check error code against platform docs (use Context7)
   d) Check `memory/MISTAKES.md` for known issues
   e) Try to reproduce

2. **Phase 2 — Pattern Analysis:**
   a) Has this happened before? (search MISTAKES.md)
   b) What fixed it last time?
   c) Platform-wide outage? (check status pages via Playwright)
   d) Compare working vs. broken: what's different?

3. **Phase 3 — Hypothesis & Test:**
   a) Form 2-3 hypotheses based on evidence
   b) Rank by likelihood
   c) Test most likely first
   d) If wrong → next hypothesis
   e) After 3 fails → STOP, escalate to user

4. **Phase 4 — Fix & Document:**
   a) Apply fix
   b) Verify fix works (re-run the operation)
   c) Log to `memory/MISTAKES.md`:
      ```
      ### YYYY-MM-DD — [Title]
      What: [description] | Cause: [root cause]
      Fix: [applied] | Prevention: [how to avoid]
      ```

## Red Flags — STOP and reconsider:
- Proposing fix before investigating → Go to Phase 1
- Multiple rapid fixes without understanding → Go to Phase 2
- Same error after 3 attempts → Escalate to user

## Example Usage
**User:** `/debug`
**Agent:** "What's the error?" → Investigates → "Root cause: [X]. Fixed by [Y]. Verified working. Logged."
