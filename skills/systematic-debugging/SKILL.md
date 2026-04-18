# SKILL: Systematic Debugging

> 4-Phase root cause analysis for API errors, campaign issues, and infrastructure problems.

---

## Phase 1: Investigate
1. Read the FULL error message (don't skip details)
2. Identify the source: Google Ads API? Meta API? MCP? Local?
3. Check error code against platform documentation
4. Check `memory/MISTAKES.md` for known issues
5. Reproduce the error (can you trigger it again?)

## Phase 2: Pattern Analysis
1. Has this happened before? (search MISTAKES.md)
2. What was the fix last time?
3. Is this a known platform issue? (check status pages)
4. Are similar operations succeeding? (isolate the variable)
5. Compare working vs. broken: what's different?

## Phase 3: Hypothesis & Test
1. Form 2-3 hypotheses based on evidence
2. Rank by likelihood
3. Test the most likely hypothesis first
4. If wrong, move to next hypothesis
5. After 3 failed hypotheses → escalate to user

## Phase 4: Fix & Document
1. Apply the fix
2. Verify the fix works (re-run the operation)
3. Log to `memory/MISTAKES.md`:
   - What happened
   - Root cause
   - Fix applied
   - Prevention strategy
4. Update any relevant skill files

## Red Flags (Stop and Reconsider)
- Proposing a fix before investigating → STOP, go to Phase 1
- Multiple rapid fixes without understanding → STOP, go to Phase 2
- Same error after 3 fix attempts → STOP, escalate to user
- Architectural symptoms (everything is broken) → STOP, run full health check

## Common Error Categories

### Authentication Errors
- Wrong API key/token → Check `.env.agents`
- Expired token → Refresh token flow
- Insufficient permissions → Check scopes/permissions
- Wrong account ID → Verify customer_id / ad_account_id

### API Errors
- Rate limited → Implement backoff, reduce request frequency
- Invalid request → Check parameter names, types, formats
- Resource not found → Verify IDs, check if resource was deleted
- Policy violation → Read violation details, fix compliance issue

### MCP Errors
- Server not responding → Check if MCP process is running
- Tool not found → Verify MCP config, restart server
- Timeout → Increase timeout or fall back to SDK
- Environment variable missing → Check wrapper script
