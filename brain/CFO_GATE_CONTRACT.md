# CFO Spend Gate Contract

> The schema Atlas writes to `cfo_pulse.json` and Maven reads via
> `scripts/send_gateway.check_cfo_spend_gate()`. If Atlas changes any of these
> fields, Maven detects drift via `scripts/test_send_gateway.py` (cases
> #21–25, #35, #36, #44–48). Update both sides simultaneously or paid spend
> blocks empire-wide.

**Path:** `C:\Users\User\APPS\CFO-Agent\data\pulse\cfo_pulse.json`
**Override for tests:** `MAVEN_CFO_PULSE_PATH` env var

---

## Schema (canonical)

```json
{
  "updated_at": "2026-04-26T07:30:00+00:00",
  "spend_gate": {
    "status": "open",
    "updated_at": "2026-04-26T07:30:00+00:00",
    "approvals": {
      "meta_ads": {
        "oasis":     { "daily_budget_usd": 100.00 },
        "propflow":  { "daily_budget_usd":  50.00 },
        "*":         { "daily_budget_usd":  25.00 }
      },
      "google_ads": {
        "oasis":     { "daily_budget_usd":  75.00 },
        "sunbiz":    { "daily_budget_usd": 200.00 }
      }
    }
  }
}
```

### Field semantics

- `updated_at` (top-level OR inside `spend_gate`) — ISO 8601 UTC. If older
  than 24h, the gate fails closed with reason `"cfo_pulse.json stale"`. If
  unparseable, fails closed with reason `"unparseable"`. If absent, the
  staleness check is skipped (Atlas controls when to start enforcing it).
- `spend_gate.status` — must equal `"open"`. Any other value (`"closed"`,
  `"halt"`, `"freeze"`, missing) blocks all paid channels.
- `spend_gate.approvals.<channel>` — channel keys are exactly `meta_ads` or
  `google_ads`. Other channels (email, social, instagram_dm) do NOT consult
  this gate; they're under Maven's daily/hourly caps directly.
- `spend_gate.approvals.<channel>.<brand>` — brand keys match Maven's
  `BRAND_IDENTITY` (`oasis`, `conaugh`, `propflow`, `nostalgic`, `sunbiz`).
- `spend_gate.approvals.<channel>."*"` — wildcard fallback for brands not
  explicitly listed. Used by Maven to launch under "any-brand" approvals.
- `daily_budget_usd` — float USD. `<= 0` blocks (treated as "spend disabled
  for this channel/brand"). `> 0` and `>= amount_requested` allows.

---

## Fail-closed conditions (every "block" reason)

| # | Condition | Reason string fragment |
|---|-----------|------------------------|
| 1 | File doesn't exist | `cfo_pulse.json unavailable` |
| 2 | File is unreadable / not JSON | `cfo_pulse.json unavailable` (caught in `_read_cfo_pulse`) |
| 3 | `updated_at` present but older than 24h | `stale (Nh > 24h)` |
| 4 | `updated_at` unparseable | `updated_at unparseable` |
| 5 | `spend_gate.status != "open"` | `Atlas spend gate status=<value>` |
| 6 | No approval block for `<channel>` or `<channel>.<brand>` (and no `*`) | `no Atlas approval for channel=X brand=Y` |
| 7 | Approved budget present but `<= 0` | `Atlas approved budget for X/Y is $0.00 — spend disabled` |
| 8 | `amount_usd` requested exceeds approved daily budget | `requested $X.XX exceeds Atlas daily approval $Y.YY` |

---

## Known-good test fixtures

`scripts/test_send_gateway.py` writes synthetic pulse files matching this
schema. If a test starts failing after an Atlas-side change, look at the
following test indices for the fail mode:

- #21 missing pulse → block
- #22 status="closed" → block
- #23 over-budget → block
- #24 channel exists, brand absent, no wildcard → block
- #25 wildcard brand approval → allow
- #35 stale (>24h) → block
- #36 zero budget → block
- #44 missing pulse (helper-level) → block
- #45 malformed JSON → block
- #46 no `updated_at` field → falls through to approval check (allow if approved)
- #47 status open but `approvals = {}` → block
- #48 full happy path → allow

---

## Versioning

When Atlas changes the schema in a non-backwards-compatible way, increment
the contract version here AND in `cfo_pulse.json` as `schema_version`.
Maven will read `schema_version` and refuse to operate against an older
version it knows is stale.

**Current version: 1.0** (no `schema_version` key required yet — assumed 1.0).

---

## Related

- [[INDEX]] — vault home
- [[RESPONSIBILITY_BOUNDARIES]] — Atlas owns spend; Maven enforces the gate
- [[SHARED_DB]] — Supabase context (this contract is *file-based*, not DB)
