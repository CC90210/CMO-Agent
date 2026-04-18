# SKILL: Self-Healing

> 5-Dimensional autonomous recovery and maintenance system.

---

## 5 Dimensions of Self-Healing

### Dimension 1: Memory Self-Healing
**Detect:** Contradictions between memory files, stale data, bloat
**Heal:**
- Contradictions → Resolve using most recent verified data
- Stale campaign data → Refresh from API
- Memory bloat → Archive old sessions, compress patterns
**Trigger:** After memory writes, session start, session end

### Dimension 2: Context Self-Healing
**Detect:** Outdated campaign references, wrong account IDs, stale metrics
**Heal:**
- Outdated campaign data → Pull fresh from API
- Wrong references → Correct from source of truth (API)
- Stale metrics → Flag as stale, pull fresh
**Trigger:** Before any campaign operation

### Dimension 3: Skill Self-Healing
**Detect:** Failed operations, declining success rates, unused skills
**Heal:**
- Repeated failures → Check if API changed, update skill documentation
- Low success rate → Investigate root cause, update approach
- Unused skills → No action (keep for future use)
**Trigger:** After failures, monthly review

### Dimension 4: Infrastructure Self-Healing
**Detect:** MCP failures, API auth issues, missing env vars, git issues
**Heal:**
- MCP down → Fall back to Python SDK
- Auth expired → Alert user for token refresh
- Missing env vars → Report which vars are missing
- Git conflicts → Report to user, suggest resolution
**Trigger:** Session start (health check), after MCP errors

### Dimension 5: Campaign Self-Healing
**Detect:** Rejected ads, learning phase stuck, delivery issues, budget anomalies
**Heal:**
- Rejected ad → Read rejection reason, suggest compliant alternative
- Learning stuck (>7 days) → Check if sufficient conversions, suggest broadening
- No delivery → Check targeting, budget, bid, ad status
- Budget anomaly → Alert user with recommended action
**Trigger:** Health check, daily monitoring

---

## Severity Tiers

### Tier 1: Auto-Fix (No User Approval Needed)
- Memory file formatting fixes
- Stale reference cleanup
- Session log compression
- Cache refresh

### Tier 2: Diagnose & Suggest
- MCP auth failures (suggest fix, user applies)
- Campaign delivery issues (diagnose, suggest fix)
- Performance degradation (analyze, suggest optimization)

### Tier 3: Deep Investigation
- Recurring API failures (root cause analysis)
- Systematic performance decline (full audit)
- Memory inconsistencies (cross-reference audit)

### Tier 4: Escalate to User
- Token rotation required
- Budget changes >20%
- Campaign structural changes
- Compliance concerns

---

## Self-Healing Checklist (Run at Session End)
- [ ] Memory files consistent? (no contradictions)
- [ ] Campaign data fresh? (within 24 hours)
- [ ] API tokens valid?
- [ ] All MCP servers responding?
- [ ] Any rejected ads?
- [ ] Any campaigns with unusual performance?
- [ ] Any error patterns emerging?
- [ ] Brain files up to date?
