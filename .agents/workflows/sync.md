---
description: End-of-session sync — update state, tasks, session log, capture patterns, and commit to git.
---

// turbo-all

# /sync — End-of-Session Sync

## When to Use
Use `/sync` at the end of every session to persist all learnings and state.

## Steps

1. **Update State** — Edit `brain/STATE.md` with current status, campaigns, infrastructure health.

2. **Update Tasks** — Edit `memory/ACTIVE_TASKS.md` — mark done, add new, reprioritize.

3. **Append Session Log** — `memory/SESSION_LOG.md`:
   ```
   ## YYYY-MM-DD — [Summary]
   **Actions:** [list]
   **Decisions:** [any]
   **Next Session:** [priorities]
   ```

4. **Capture Learnings:**
   - New patterns → `memory/PATTERNS.md` (tag `[PROBATIONARY]`)
   - Errors → `memory/MISTAKES.md` with root cause
   - Reflections → `memory/SELF_REFLECTIONS.md`

5. **Self-Healing Check** — Memory consistent? Campaign data fresh? Issues to flag?

6. **Git Commit:**
   ```bash
   git add [specific files] && git commit -m "advantage: sync — session YYYY-MM-DD"
   ```

7. **Confirm:** "Memory synced. [X] files updated, [Y] learnings captured."

## Example Usage
**User:** `/sync`
**Agent:** "Memory synced. 4 files updated, 2 patterns captured. Session saved."
