# INTERACTION PROTOCOL — Logging & Communication Standards

---

## Logging Tiers

### Tier 1: Session Log (Every Session)
**File:** `memory/SESSION_LOG.md`
- Date, duration, key actions taken
- Campaigns created/modified
- Performance metrics pulled
- Decisions made
- Format: `## YYYY-MM-DD\n- [action]\n- [action]`

### Tier 2: Campaign Tracker (Every Campaign Change)
**File:** `memory/CAMPAIGN_TRACKER.md`
- Campaign name, platform, status, budget, targeting summary
- Key metrics snapshot
- Optimization history

### Tier 3: Decision Log (Every Significant Decision)
**File:** `memory/DECISIONS.md`
- What was decided
- Why (data/reasoning)
- Alternatives considered
- Expected impact

### Tier 4: Error Log (Every Error)
**File:** `memory/MISTAKES.md`
- What happened
- Root cause
- Fix applied
- Prevention strategy

---

## Communication Standards

### Campaign Status Updates
```
Platform: [Google/Meta]
Campaign: [name]
Status: [ACTIVE/PAUSED/LEARNING/REJECTED]
Spend: $X.XX (today) / $X.XX (total)
Results: X leads at $X.XX CPL
CTR: X.X% | CPC: $X.XX | Conversions: X
```

### Optimization Reports
```
Issue: [what's underperforming]
Data: [specific metrics]
Action: [what we're changing]
Expected Impact: [projected improvement]
```

### Error Reports
```
Error: [what failed]
Platform: [Google/Meta/MCP]
Cause: [root cause]
Impact: [what's affected]
Fix: [what was done or needs to be done]
```

---

## Proactive Alerts (Trigger Automatically)

| Condition | Alert |
|-----------|-------|
| Ad rejected by platform | Immediate alert + reason + fix suggestion |
| CPL > 2x target | Budget pause recommendation |
| CTR < 0.5% | Creative refresh recommendation |
| Daily budget exhausted before noon | Pacing issue alert |
| API token expiring within 7 days | Token renewal reminder |
| Campaign in "Learning" phase > 7 days | Learning phase stuck alert |
| No impressions in 24 hours | Delivery issue investigation |
