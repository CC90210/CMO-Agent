---
title: MacBook Sync to V1.2
date: 2026-04-26
machine: Conaughs-MacBook-Air (darwin 23.6.0)
synced_by: Maven
---

# MacBook V1.2 Sync Report — 2026-04-26

## HEAD
Fast-forwarded `f54aaae → 84028c5` clean. Working tree clean post-sync.

```
84028c5 maven: pulse_client reads Atlas's spend_gate.status (matches CFO_PULSE_CONTRACT)
86bc39b maven: V1.1 -> V1.2 finalization — transfer integration, content gates, CFO contract, adversarial review
dd542c8 maven: V1.1 follow-up — orphan pickup, Obsidian graph wiring, secrets gitignore
067cde8 maven: V1.0 → V1.1 structural upgrade — frontmatter, send_gateway, delegation, boundaries
```

Plus one Mac-side maintenance commit on top:
- `242f35a` — drop `.env.agents.template` (replaced by live `.env.agents`)

## Tests — 96/96 PASS

| File | Count | Result |
|---|---|---|
| `test_send_gateway.py` | 65 | OK |
| `test_late_publisher.py` | 5 | OK |
| `test_instagram_engine.py` | 6 | OK |
| `test_content_pipeline.py` | 10 | OK |
| `test_performance_reporter.py` | 10 | OK |
| **Total** | **96** | **OK** |

All run under `/opt/homebrew/bin/python3.12`.

## Health — 100/100

```
agents       : 19/19  (frontmatter complete)
skills       : 54/54  (frontmatter complete)
scripts      : 39/39  (documented)
mcp_servers  : 6 in sync
send_gateway : tests pass
cmo_pulse    : fresh (0.0h)
orphans      : 0
warnings     : 0
```

## .env.agents — V1.2 keys added

Added to the bottom of `.env.agents` during this sync:

```
BRAVO_REPO=/Users/conaugh/bravo-live
MAVEN_REPO=/Users/conaugh/CMO-Agent
ATLAS_REPO=/Users/conaugh/APPS/CFO-Agent
AURA_REPO=/Users/conaugh/AURA
MAVEN_FORCE_DRY_RUN=0
DRAFT_CRITIC_ENABLED=1
UTM_COMPLIANCE_ENABLED=1
MAVEN_SUPABASE_URL=${BRAVO_SUPABASE_URL}
MAVEN_SUPABASE_SERVICE_ROLE_KEY=${BRAVO_SUPABASE_SERVICE_ROLE_KEY}
# MAVEN_VIP_EMAILS / MAVEN_VIP_DOMAINS deliberately commented:
# send_gateway treats the *presence* of MAVEN_VIP_EMAILS as opt-in to
# strict-mode VIP routing, so leaving it absent matches the intended
# default of "no overrides".
```

VIP keys remain commented on purpose — `send_gateway.py:539-543` treats key
presence (even empty) as opt-in to strict mode.

## Cross-repo routing — verified

Smoke-test message landed at:
```
/Users/conaugh/bravo-live/tmp/agent_inbox/inbox/3_2026-04-26T21-24-07-050233+00-00_bravo_4e4f9890cab8.json
```

## Mac-specific gotchas (worth recording)

1. **System python3 is 3.9.6.** V1.2 uses `str | None` and `frozenset[str]`
   syntax that needs ≥3.12. Use `/opt/homebrew/bin/python3.12` explicitly,
   or alias it. Don't rely on the bare `python3` on this machine.

2. **No real Bravo repo on this Mac.** `/Users/conaugh/bravo-live/` only
   contains `run.sh` + `windows.log` (looks like a launcher dir, not a
   clone). `BRAVO_REPO` is pointed at it so agent_inbox writes land
   somewhere predictable, but a real Bravo clone should replace this
   when CC sets up Bravo on Mac.

3. **Atlas + Aura repos absent.** `/Users/conaugh/APPS/CFO-Agent` and
   `/Users/conaugh/AURA` don't exist. `ATLAS_REPO` / `AURA_REPO` are wired
   to those paths so `agent_inbox post --to atlas|aura` will mkdir on
   first send — works for testing but means **we cannot read Atlas's
   spend_gate from this Mac yet**. CFO gate calls will hit the
   stale-pulse fail-closed path until Atlas is cloned here too.

4. **`.env.agents` shell-incompatible values.** Sourcing the file with
   `set -a && source .env.agents` triggers `daru: command not found` on
   line 67 (one of the existing values has unquoted parens or `$(...)`-
   like syntax). Python `dotenv` parses fine; only bash chokes. If a
   future script tries to `source` the env file, it'll need quoting.

5. **`.env.agents.template` removed from tracking** (commit `242f35a`).
   It's redundant once a live `.env.agents` exists.

6. **`agent_inbox.py` doesn't auto-load `.env.agents`.** It reads
   `BRAVO_REPO`/`MAVEN_REPO`/`ATLAS_REPO`/`AURA_REPO` only from
   `os.environ`, with Windows-path defaults baked in. On Mac, those
   defaults silently produce dir paths under whatever cwd you're in
   (mis-route to Maven's own inbox if you don't pre-export). Workarounds:
   - `set -a && source .env.agents && set +a` before invoking, or
   - inline: `BRAVO_REPO=... python3.12 scripts/agent_inbox.py …`
   Worth filing as a V1.3 follow-up: have `agent_inbox.py` call
   `dotenv.load_dotenv('.env.agents')` at module load.

## Ready to operate
This MacBook is fully caught up to V1.2. Send-gateway, draft-critic,
content-pipeline, late, and instagram engines all green. Mavenable.
