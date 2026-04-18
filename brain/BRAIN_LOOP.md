# BRAIN LOOP — 10-Step Reasoning Protocol

> Adapted from LATS (Language Agent Tree Search) + Reflexion (Shinn et al. 2023)
> Every non-trivial task flows through this protocol.

---

## The 10 Steps

### Step 1: ORIENT
Load context and establish situational awareness.
- Read `brain/SOUL.md` (identity, values, boundaries)
- Read `brain/STATE.md` (current campaigns, API health, focus)
- Read `brain/CLIENT.md` (SunBiz Funding — MCA consolidation context, ICP, goals)
- Identify: What platform? What campaign? What's the user's intent?

### Step 2: RECALL
Search memory for relevant prior experience.
- Check `memory/PATTERNS.md` for validated approaches
- Check `memory/MISTAKES.md` for known pitfalls
- Check `memory/SOP_LIBRARY.md` for standard procedures
- Check `memory/CAMPAIGN_TRACKER.md` for campaign history
- **Activation Score:** recency × 0.3 + frequency × 0.4 + confidence × 0.3

### Step 3: ASSESS
Evaluate confidence and determine approach complexity.
- **HIGH (0.8-1.0):** Validated pattern exists, proceed directly
- **MEDIUM (0.5-0.79):** Partial match, need verification
- **LOW (0.0-0.49):** No precedent, requires research/planning

### Step 4: PLAN (Multi-Hypothesis)
Generate 2-3 candidate approaches for MODERATE+ tasks.
```
Approach A: [description] — Feasibility: X/10, Risk: X/10, Effort: X/10
Approach B: [description] — Feasibility: X/10, Risk: X/10, Effort: X/10
Approach C: [description] — Feasibility: X/10, Risk: X/10, Effort: X/10
→ Selected: [A/B/C] because [reason]
```
- For TRIVIAL/SIMPLE tasks: Skip multi-hypothesis, just plan the single best approach

### Step 5: VERIFY
Cross-check plan against constraints BEFORE executing.
- Does this comply with lending ad regulations?
- Does this respect Meta Special Ad Category restrictions?
- Does this respect Google Ads policies for financial services?
- Does this stay within the approved budget?
- Is this reversible if it goes wrong?

### Step 6: EXECUTE
Take action, one tool call at a time.
- Use the correct MCP server or SDK for the platform
- Log each action for audit trail
- Verify each step before proceeding to next

### Step 7: REFLECT
Structured reflection on outcome.
```
Attempted: [what was done]
Result: [SUCCESS/PARTIAL/FAILURE]
Expected: [what should have happened]
Actual: [what actually happened]
Why: [root cause if different from expected]
```

### Step 8: STORE
Write learnings to persistent memory.
- New patterns → `memory/PATTERNS.md` (tag `[PROBATIONARY]`)
- Errors → `memory/MISTAKES.md` (root cause + prevention)
- Decisions → `memory/DECISIONS.md` (date + rationale)
- Campaign data → `memory/CAMPAIGN_TRACKER.md`

### Step 9: EVOLVE
Check for growth opportunities.
- Did this reveal a new SOP we should document?
- Is there a recurring task that should be automated via n8n?
- Should we update a skill file with new knowledge?
- Is there a new pattern worth tracking?

### Step 10: HEAL
Run self-healing checks.
- Memory contradictions? → Resolve
- Stale campaign data? → Refresh
- API tokens expiring? → Alert user
- Broken references? → Fix

---

## Complexity Routing

| Complexity | Steps Used | Example |
|-----------|-----------|---------|
| **Trivial** | 1-3, 6 | Check campaign status |
| **Simple** | 1-3, 5-6 | Pause an ad, change budget |
| **Moderate** | 1-8 | Create new ad set, optimize targeting |
| **Complex** | All 10 | Full campaign strategy + launch |
| **Architectural** | All 10 + user approval at Step 4 | New platform integration, major budget change |

---

## Confidence Scoring

| Score | Meaning | Action |
|-------|---------|--------|
| 0.95-1.0 | Verified fact (API confirmed) | Execute immediately |
| 0.8-0.94 | High confidence (3+ successful uses) | Execute with verification |
| 0.5-0.79 | Medium confidence (1-2 observations) | Execute with caution, verify |
| 0.2-0.49 | Low confidence (single observation) | Research first, then execute |
| 0.0-0.19 | Speculation | Do NOT execute, research or ask user |

---

## Failure Recovery

1. First failure → Reflect (Step 7), try next ranked approach from Step 4
2. Second failure → Deep investigation, check memory/MISTAKES.md for similar issues
3. Third failure → STOP. Escalate to user with full diagnostic:
   - What was attempted (all 3 approaches)
   - What failed and why
   - Recommended next steps
   - Do NOT retry without user guidance
