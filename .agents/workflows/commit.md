---
description: Smart git commit with secret scanning, referential integrity checks, and capability count verification.
---

// turbo-all

# /commit — Smart Git Commit

## When to Use
Use `/commit` to safely commit changes with pre-commit integrity checks.

## Steps

1. **Pre-Commit Checks:**

   a) **Secret Scan** — Search staged files for exposed credentials:
      ```bash
      git diff --cached | grep -iE "(sk_|Bearer|token=|password|secret|api_key|access_token)"
      ```
      If found → ABORT and alert user.

   b) **Referential Integrity** — Verify referenced files exist.

   c) **Capability Count** — Verify documented counts match actual:
      - Agents: `ls agents/ | wc -l` vs. AGENTS.md count
      - Skills: `ls skills/ | wc -l` vs. CAPABILITIES.md count
      - Workflows: `ls .agents/workflows/ | wc -l` vs. documented count

2. **Stage Changes** — `git add [specific files]` (never `git add -A`).

3. **Commit:**
   ```bash
   git commit -m "advantage: [type] — [description]"
   ```
   Types: sync, feat, fix, refactor, docs, config

4. **Verify** — `git status && git log -1 --oneline`

## Example Usage
**User:** `/commit`
**Agent:** "Pre-checks: No secrets. All refs valid. 14 agents (matches). Committed: advantage: feat — new Q1 campaign."
