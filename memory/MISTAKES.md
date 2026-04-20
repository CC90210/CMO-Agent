# MISTAKES — Error Log & Root Cause Analysis

> Log every error with root cause and prevention strategy.
> Protocol 4 of `skills/self-improvement-protocol/SKILL.md` writes here.

---

### 2026-04-19 — AdVantage-era single-client thinking inherited into Maven V1.0
**What happened:** Maven inherited 20 skills from the SunBiz/AdVantage V2.0 era. Several skills hardcoded SunBiz-specific copy, compliance rules, and examples into the skill body itself (e.g. `ad-copywriting/SKILL.md` opens with "High-converting ad copy for SunBiz Funding's MCA consolidation"). This creates two failure modes: (1) when running the same skill for OASIS / PropFlow / Nostalgic / CC-personal, the skill self-primes for the wrong brand; (2) the repo looks like a SunBiz-marketing agent rather than a multi-client CMO.
**Root cause (5 Whys):**
1. Why are the skills SunBiz-hardcoded? → They were written when SunBiz was the only client.
2. Why weren't they abstracted on migration? → The V1.0 split prioritized getting Maven operational, not refactoring every skill.
3. Why is that risky? → When CC uses `/campaign-create` for OASIS, Maven's defaults skew MCA-flavored.
4. Why didn't we catch it sooner? → No `canon_references` frontmatter enforced universality.
5. Why was there no canon enforcement? → `brain/MARKETING_CANON.md` didn't exist until Bravo shipped it 2026-04-19.
**Fix applied:** Injected `canon_references` + `canon_source` into every skill's frontmatter via `scripts/_inject_canon_refs.py`. Added `universal: true` + a note that SunBiz-era examples are legacy. Moved SunBiz operational playbook into a client-specific file (`MAXIMIZATION_GUIDE.md` retitled as SunBiz playbook). Extracted SunBiz compliance rules fully into `brain/clients/sunbiz-funding.md`.
**Prevention:** (1) Every new skill created by Maven MUST include `canon_references` in frontmatter before commit — enforced at review time. (2) Client-specific copy goes in `brain/clients/<brand>.md`, never in a skill body. (3) On every session start, Protocol 1 HEAL scans for SunBiz-hardcoding drift in non-client files.
**Severity:** HIGH (product-architecture risk for Business-in-a-Box clonability)

### 2026-04-19 — Paid launch without Atlas gate (historical pattern — preventable)
**What happened:** Risk logged pre-emptively. Prior AdVantage V2.0 era lacked a formal spend-gate between CMO work and CFO approval. A Meta / Google campaign could in principle launch without Atlas acknowledging runway impact.
**Root cause:** No structural check in the workflow — only social convention.
**Fix applied:** Pulse protocol now explicit (see `CLAUDE.md` Rule 2). `cmo_pulse.json` carries `spend_request_cad` + `spend_approved_by_atlas`; campaigns do NOT launch until `cfo_pulse.json` acknowledges. Promoted the pattern in `memory/PATTERNS.md` to `[VALIDATED]`.
**Prevention:** Every campaign creation workflow (see `agents/ad-strategist.md`, `skills/campaign-creation/SKILL.md`) reads `data/pulse/cfo_pulse.json` BEFORE any API call to Meta / Google. Wrapper scripts `scripts/meta-ads-mcp-wrapper.cmd` + `scripts/google-ads-mcp-wrapper.cmd` should add a pulse-check preflight before the first authenticated call.
**Severity:** HIGH (direct runway impact if missed)

### 2026-04-19 — Skill frontmatter drift (18 of 30 skills missing frontmatter)
**What happened:** When inspected, 18 of 29 original skills had no YAML frontmatter at all — no `name`, no `triggers`, no `canon_references`. This degrades Maven's ability to auto-select skills from natural-language queries and prevents the skill activation scoring from working (see Protocol 2).
**Root cause:** Skill-file convention wasn't enforced during initial repo seeding.
**Fix applied:** `scripts/_inject_canon_refs.py` prepended minimal frontmatter (name + canon_references + universal:true + note) to every skill that lacked it.
**Prevention:** Skills template (`skills/SKILL_TEMPLATE.md` — to be created when next skill is added) includes mandatory frontmatter fields. Session-start Protocol 1 scan: `grep -L '^---' skills/*/SKILL.md` → if any hits, flag to CC before any other work.
**Severity:** MEDIUM (functionality degradation, not data loss)

## Template
```
### YYYY-MM-DD — [Error Title]
**What happened:** [description]
**Root cause (5 Whys):**
  1. ...
  2. ...
  3. ...
  4. ...
  5. ...
**Fix applied:** [what was done]
**Prevention:** [how to avoid in future]
**Severity:** [LOW/MEDIUM/HIGH/CRITICAL]
```
