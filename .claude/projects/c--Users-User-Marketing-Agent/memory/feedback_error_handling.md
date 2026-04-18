---
name: feedback_error_handling
description: User feedback on API errors, testing, and communication style
type: feedback
---

- NEVER test APIs speculatively - verify parameters are correct BEFORE making calls
- If an API call fails, STOP and diagnose - do not retry blindly
- When giving instructions, provide EXACT URLs and file paths - never vague directions
- Don't over-explain before acting - answer first, then work
- User wants full agentic control - minimize manual steps
- When errors occur, fix the root cause, don't just retry
- Keep responses concise - user can read diffs and code
