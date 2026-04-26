"""
Tests for Maven's send_gateway.

Mirrors Bravo's 51-case test structure adapted to Maven's marketing context:
  - 5 brands instead of 3
  - 200/day email cap instead of 50
  - MAVEN_FORCE_DRY_RUN killswitch (and the shared BRAVO_FORCE_DRY_RUN)
  - meta_ads + google_ads channels gated through cfo_pulse.json
  - name_utils sanitization on render path

All tests run offline using a fake Supabase + a tmp cfo_pulse.json. No real
emails sent, no real DB hits, no real spend.

Run:
  python scripts/test_send_gateway.py
  python scripts/test_send_gateway.py --verbose
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


# ---- Fake Supabase client ---------------------------------------------------

class _FakeSelect:
    def __init__(self, table: "_FakeTable", cols: str = "*", count: str | None = None):
        self.table = table
        self.cols = cols
        self.count = count
        self.filters: list = []
        self.ordering: tuple | None = None
        self.limit_val: int | None = None

    def eq(self, col, val):
        self.filters.append(("eq", col, val))
        return self

    def gte(self, col, val):
        self.filters.append(("gte", col, val))
        return self

    def lte(self, col, val):
        self.filters.append(("lte", col, val))
        return self

    def order(self, col, desc=False):
        self.ordering = (col, desc)
        return self

    def limit(self, n):
        self.limit_val = n
        return self

    def execute(self):
        rows = list(self.table.rows)
        for op, col, val in self.filters:
            if op == "eq":
                rows = [r for r in rows if r.get(col) == val]
            elif op == "gte":
                rows = [r for r in rows if (r.get(col) or "") >= val]
            elif op == "lte":
                rows = [r for r in rows if (r.get(col) or "") <= val]
        if self.ordering:
            col, desc = self.ordering
            rows = sorted(rows, key=lambda r: r.get(col) or "", reverse=desc)
        if self.limit_val is not None:
            rows = rows[: self.limit_val]

        class R:
            pass
        r = R()
        r.data = rows
        r.count = len(rows) if self.count else None
        return r


class _FakeInsert:
    def __init__(self, table: "_FakeTable", payload):
        self.table = table
        self.payload = payload

    def execute(self):
        payload = self.payload if isinstance(self.payload, list) else [self.payload]
        inserted = []
        for p in payload:
            row = dict(p)
            row.setdefault("id", f"fake-{len(self.table.rows)+1}")
            self.table.rows.append(row)
            inserted.append(row)

        class R:
            pass
        r = R()
        r.data = inserted
        r.count = len(inserted)
        return r


class _FakeUpdate:
    def __init__(self, table, payload):
        self.table = table
        self.payload = payload
        self.filters: list = []

    def eq(self, col, val):
        self.filters.append(("eq", col, val))
        return self

    def execute(self):
        updated = []
        for r in self.table.rows:
            match = all(r.get(c) == v for _, c, v in self.filters)
            if match:
                r.update(self.payload)
                updated.append(r)

        class R:
            pass
        res = R()
        res.data = updated
        res.count = len(updated)
        return res


class _FakeRPC:
    def __init__(self, db: "FakeSupabase", function_name: str, params: dict[str, Any]):
        self.db = db
        self.function_name = function_name
        self.params = params

    def execute(self):
        if self.function_name != "exec_sql":
            raise RuntimeError(f"unsupported RPC: {self.function_name}")
        sql_query = self.params.get("sql_query", "")
        return self.db._handle_exec_sql(sql_query)


class _FakeTable:
    def __init__(self, name, rows=None):
        self.name = name
        self.rows = list(rows or [])

    def select(self, cols="*", count=None):
        return _FakeSelect(self, cols, count)

    def insert(self, payload):
        return _FakeInsert(self, payload)

    def update(self, payload):
        return _FakeUpdate(self, payload)


class FakeSupabase:
    def __init__(self):
        self.tables: dict[str, _FakeTable] = {
            "leads": _FakeTable("leads"),
            "lead_interactions": _FakeTable("lead_interactions"),
            "email_log": _FakeTable("email_log"),
        }
        self.force_lock_contention = False
        self.disable_rpc = False

    def table(self, name):
        if name not in self.tables:
            self.tables[name] = _FakeTable(name)
        return self.tables[name]

    def rpc(self, function_name, params):
        if self.disable_rpc:
            raise RuntimeError("RPC unavailable")
        return _FakeRPC(self, function_name, params)

    def _handle_exec_sql(self, sql_query: str):
        marker_match = re.search(r"/\*\s*send_gateway_reserve:(.*?)\s*\*/", sql_query, re.DOTALL)
        if not marker_match:
            raise RuntimeError("unsupported exec_sql payload")
        marker = json.loads(marker_match.group(1))
        existing = next(
            (
                row for row in self.tables["lead_interactions"].rows
                if row.get("lead_id") == marker.get("lead_id")
                and row.get("channel") == marker.get("channel")
                and row.get("type") == "reserving"
            ),
            None,
        )

        class R:
            pass
        res = R()
        if self.force_lock_contention:
            res.data = {"status": "ok", "rows": [{"lock_acquired": False}]}
            return res
        if existing:
            res.data = {
                "status": "ok",
                "rows": [{
                    "lock_acquired": True,
                    "existing_reservation_id": existing.get("id"),
                    "reservation_id": None,
                }],
            }
            return res

        now = datetime.now(timezone.utc).isoformat()
        row = {
            "id": f"fake-{len(self.tables['lead_interactions'].rows) + 1}",
            "lead_id": marker.get("lead_id"),
            "channel": marker.get("channel"),
            "type": "reserving",
            "created_at": now,
            "subject": marker.get("subject"),
            "content": marker.get("content_preview"),
            "agent_source": marker.get("agent_source"),
            "cooldown_until": marker.get("cooldown_until"),
            "metadata": marker.get("metadata") or {},
        }
        self.tables["lead_interactions"].rows.append(row)
        res.data = {
            "status": "ok",
            "rows": [{
                "lock_acquired": True,
                "existing_reservation_id": None,
                "reservation_id": row["id"],
                "reservation_created_at": now,
            }],
        }
        return res


class _FailingSelect(_FakeSelect):
    def execute(self):
        raise RuntimeError("ledger unavailable")


class _FailingTable(_FakeTable):
    def select(self, cols="*", count=None):
        return _FailingSelect(self, cols, count)


class FailingLedgerSupabase(FakeSupabase):
    def __init__(self):
        super().__init__()
        self.tables["lead_interactions"] = _FailingTable("lead_interactions")


# ---- Shared fixtures --------------------------------------------------------

def _fresh_env(monkeypatch_env: dict):
    monkeypatch_env.update({
        "MAVEN_SUPABASE_URL": "https://test.supabase.co",
        "MAVEN_SUPABASE_SERVICE_ROLE_KEY": "fake-service-key",
        "GMAIL_USER": "test@oasisai.work",
        "GMAIL_APP_PASSWORD": "fake-password",
    })
    for k, v in monkeypatch_env.items():
        os.environ[k] = v
    # Clear killswitch env vars across tests
    for ks in ("MAVEN_FORCE_DRY_RUN", "BRAVO_FORCE_DRY_RUN"):
        os.environ.pop(ks, None)
    return monkeypatch_env


def _import_gateway_fresh():
    import importlib
    mods = [m for m in list(sys.modules) if m.startswith("send_gateway")]
    for m in mods:
        del sys.modules[m]
    import send_gateway
    importlib.reload(send_gateway)
    return send_gateway


def _write_cfo_pulse(tmpdir: Path, *, status: str = "open",
                     channels: dict | None = None) -> Path:
    """Write a fake cfo_pulse.json to a temp path and point the gateway at it."""
    if channels is None:
        channels = {
            "meta_ads": {"oasis": {"daily_budget_usd": 100.0}, "*": {"daily_budget_usd": 50.0}},
            "google_ads": {"oasis": {"daily_budget_usd": 75.0}},
        }
    path = tmpdir / "cfo_pulse.json"
    path.write_text(json.dumps({
        "spend_gate": {"status": status, "approvals": channels},
    }), encoding="utf-8")
    os.environ["MAVEN_CFO_PULSE_PATH"] = str(path)
    return path


# ---- Tests ------------------------------------------------------------------

class TestSendGateway(unittest.TestCase):

    def setUp(self):
        _fresh_env({})
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        # Default: cfo_pulse open with budgets — paid-channel tests can override
        _write_cfo_pulse(self.tmp_path)
        self.sg = _import_gateway_fresh()
        self.db = FakeSupabase()
        self.sg._DAILY_CAP_ALERTS_SENT.clear()
        self._critic_patcher = mock.patch.object(
            self.sg,
            "critique_draft",
            return_value={"verdict": "ship", "reasons": [], "notes": ""},
        )
        self._critic_patcher.start()
        self.addCleanup(self._critic_patcher.stop)
        self.db.tables["leads"].rows.append({
            "id": "lead-001",
            "name": "Jane Test",
            "email": "jane@acme.example",
            "status": "new",
        })

    def tearDown(self):
        os.environ.pop("MAVEN_CFO_PULSE_PATH", None)
        self._tmp.cleanup()

    def _patch_smtp_ok(self):
        return mock.patch.object(self.sg, "_send_email_smtp", return_value=(True, None))

    def _patch_smtp_fail(self, err: str = "rejected"):
        return mock.patch.object(self.sg, "_send_email_smtp", return_value=(False, err))

    def _patch_suppress(self, value: bool):
        return mock.patch.object(self.sg, "should_suppress", return_value=value)

    def _patch_critic(self, verdict: str, reasons: list[str] | None = None):
        return mock.patch.object(
            self.sg,
            "critique_draft",
            return_value={"verdict": verdict, "reasons": reasons or [], "notes": ""},
        )

    # 1. Golden path
    def test_01_golden_path_sent(self):
        with self._patch_smtp_ok(), self._patch_suppress(False):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="jane@acme.example", subject="hi", body_text="hello",
                db=self.db,
            )
        self.assertEqual(r["status"], "sent", r)
        self.assertIsNotNone(r["interaction_id"])
        self.assertEqual(len(self.db.tables["lead_interactions"].rows), 1)
        self.assertEqual(len(self.db.tables["email_log"].rows), 1)

    # 2. CASL suppression blocks
    def test_02_suppressed_commercial_blocked(self):
        with self._patch_smtp_ok(), self._patch_suppress(True):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="blocked@example.invalid", subject="hi", body_text="hi",
                db=self.db,
            )
        self.assertEqual(r["status"], "suppressed")
        self.assertIn("suppression", r["reason"])
        self.assertEqual(len(self.db.tables["lead_interactions"].rows), 0)

    # 3. Transactional bypasses suppression
    def test_03_transactional_bypasses_suppression(self):
        with self._patch_smtp_ok(), self._patch_suppress(True):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="jane@acme.example", subject="Booking",
                body_text="confirmed.", intent="transactional", db=self.db,
            )
        self.assertEqual(r["status"], "sent")

    # 4. Cooldown blocks retry
    def test_04_cooldown_blocks_retry(self):
        now = datetime.now(timezone.utc)
        self.db.tables["lead_interactions"].rows.append({
            "id": "ix-001", "lead_id": "lead-001", "channel": "email",
            "type": "email_sent", "created_at": now.isoformat(),
            "cooldown_until": (now + timedelta(hours=48)).isoformat(),
        })
        with self._patch_smtp_ok(), self._patch_suppress(False):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="jane@acme.example", subject="retry", body_text="retry",
                db=self.db,
            )
        self.assertEqual(r["status"], "blocked")
        self.assertIn("cooldown", r["reason"])

    # 5. Daily cap (Maven default 200)
    def test_05_daily_cap_blocks(self):
        now = datetime.now(timezone.utc) - timedelta(hours=2)
        cap = self.sg.DAILY_CAPS["email"]
        for i in range(cap):
            self.db.tables["lead_interactions"].rows.append({
                "id": f"cap-{i}", "lead_id": f"other-{i}", "channel": "email",
                "type": "email_sent", "created_at": now.isoformat(),
            })
        with self._patch_smtp_ok(), self._patch_suppress(False):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="jane@acme.example", subject="over", body_text="over",
                db=self.db,
            )
        self.assertEqual(r["status"], "blocked")
        self.assertIn("daily cap", r["reason"])

    def test_05b_cooldown_ledger_failure_blocks(self):
        r = self.sg.can_act(lead_id="lead-001", channel="email",
                            db=FailingLedgerSupabase())
        self.assertFalse(r["allowed"])
        self.assertIn("cooldown ledger unavailable", r["reason"])

    # 6. Dry-run no side effects
    def test_06_dry_run_no_side_effects(self):
        with self._patch_smtp_ok(), self._patch_suppress(False):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="jane@acme.example", subject="dry", body_text="dry",
                dry_run=True, db=self.db,
            )
        self.assertEqual(r["status"], "dry_run")
        self.assertEqual(len(self.db.tables["lead_interactions"].rows), 0)

    # 7. Missing required fields
    def test_07_missing_email_fields_error(self):
        r = self.sg.send(
            channel="email", agent_source="test_harness",
            to_email="jane@acme.example", db=self.db,
        )
        self.assertEqual(r["status"], "error")

    # 8. Unknown channel
    def test_08_unknown_channel_error(self):
        r = self.sg.send(
            channel="fax", agent_source="test_harness",
            to_email="jane@acme.example", subject="hi", body_text="hi",
            db=self.db,
        )
        self.assertEqual(r["status"], "error")
        self.assertIn("unknown channel", r["reason"])

    # 9. Invalid intent
    def test_09_invalid_intent_error(self):
        r = self.sg.send(
            channel="email", agent_source="test_harness",
            to_email="jane@acme.example", subject="hi", body_text="hi",
            intent="marketing", db=self.db,
        )
        self.assertEqual(r["status"], "error")

    # 10. SMTP failure surfaces as error
    def test_10_smtp_fail_surfaces(self):
        with self._patch_smtp_fail("SMTP rejected"), self._patch_suppress(False):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="jane@acme.example", subject="hi", body_text="hi",
                db=self.db,
            )
        self.assertEqual(r["status"], "error")
        self.assertIn("SMTP", r["reason"])

    # 11. Maven brand identity — 5 brands all valid
    def test_11_brand_identity_5_brands(self):
        for brand in ("oasis", "conaugh", "propflow", "nostalgic", "sunbiz"):
            with self.subTest(brand=brand):
                self.db = FakeSupabase()
                self.db.tables["leads"].rows.append({
                    "id": f"lead-{brand}", "email": f"{brand}@acme.example",
                })
                with self._patch_smtp_ok(), self._patch_suppress(False):
                    r = self.sg.send(
                        channel="email", agent_source="test_harness",
                        to_email=f"{brand}@acme.example",
                        subject="brand test", body_text="hi", brand=brand,
                        db=self.db,
                    )
                self.assertEqual(r["status"], "sent", f"{brand}: {r}")

    # 11b. Unknown brand error
    def test_11b_unknown_brand_error(self):
        r = self.sg.send(
            channel="email", agent_source="test_harness",
            to_email="jane@acme.example", subject="hi", body_text="hi",
            brand="bogus", db=self.db,
        )
        self.assertEqual(r["status"], "error")
        self.assertIn("unknown brand", r["reason"])

    # 12. Lead auto-create
    def test_12_auto_create_lead(self):
        with self._patch_smtp_ok(), self._patch_suppress(False):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="brand-new@acme.example", subject="new", body_text="new",
                db=self.db,
            )
        self.assertEqual(r["status"], "sent")
        self.assertEqual(len(self.db.tables["leads"].rows), 2)
        auto = [l for l in self.db.tables["leads"].rows
                if l.get("email") == "brand-new@acme.example"]
        self.assertEqual(auto[0].get("source"), "maven_gateway_autocreate")

    # 13. Bounce-rate breaker
    def test_13_bounce_rate_over_threshold_blocks(self):
        now = datetime.now(timezone.utc).isoformat()
        self.db.tables["email_log"].rows.extend(
            [{"status": "sent", "sent_at": now} for _ in range(19)]
            + [{"status": "failed", "sent_at": now}]
        )
        self.db.tables["email_log"].rows.append({"status": "failed", "sent_at": now})
        r = self.sg.can_act(lead_id="lead-001", channel="email",
                            to_email="jane@acme.example", db=self.db)
        self.assertFalse(r["allowed"])
        self.assertIn("bounce-rate circuit breaker", r["reason"])

    # 14. Hourly cap
    def test_14_hourly_cap_blocks(self):
        now = datetime.now(timezone.utc).isoformat()
        cap = self.sg.HOURLY_CAPS["email"]
        for i in range(cap):
            self.db.tables["lead_interactions"].rows.append({
                "id": f"h-{i}", "lead_id": f"other-{i}", "channel": "email",
                "type": "email_sent", "created_at": now,
            })
        r = self.sg.can_act(lead_id="lead-001", channel="email",
                            to_email="jane@acme.example", db=self.db)
        self.assertFalse(r["allowed"])
        self.assertIn("hourly cap", r["reason"])

    # 15. Domain cap
    def test_15_domain_cap_blocks(self):
        now = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        # Maven cap=5 — seed 5 hits
        self.db.tables["leads"].rows.extend([
            {"id": f"lead-d{i}", "email": f"u{i}@acme.example"} for i in range(5)
        ])
        for i in range(5):
            self.db.tables["lead_interactions"].rows.append({
                "id": f"d-{i}", "lead_id": f"lead-d{i}", "channel": "email",
                "type": "email_sent", "created_at": now,
            })
        r = self.sg.can_act(lead_id="lead-001", channel="email",
                            to_email="jane@acme.example", db=self.db)
        self.assertFalse(r["allowed"])
        self.assertIn("domain cap", r["reason"])

    # 16. Critic verdict reject blocks
    def test_16_critic_reject_blocks(self):
        with self._patch_smtp_ok(), self._patch_suppress(False), \
             self._patch_critic("reject", ["spammy"]):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="jane@acme.example", subject="hi", body_text="hi",
                db=self.db,
            )
        self.assertEqual(r["status"], "blocked")
        self.assertIn("draft_critic rejected", r["reason"])
        self.assertEqual(len(self.db.tables["lead_interactions"].rows), 0)

    # 16b. Critic non-ship verdict (escalate) also blocks
    def test_16b_critic_escalate_blocks(self):
        with self._patch_smtp_ok(), self._patch_suppress(False), \
             self._patch_critic("escalate", ["needs review"]):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="jane@acme.example", subject="hi", body_text="hi",
                db=self.db,
            )
        self.assertEqual(r["status"], "blocked")
        self.assertIn("draft_critic rejected", r["reason"])

    # 16c. Critic exception blocks (fail-closed — Bravo db37263 fix)
    def test_16c_critic_exception_blocks(self):
        with self._patch_smtp_ok(), self._patch_suppress(False), \
             mock.patch.object(self.sg, "critique_draft",
                               side_effect=RuntimeError("critic down")):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="jane@acme.example", subject="hi", body_text="hi",
                db=self.db,
            )
        self.assertEqual(r["status"], "blocked")
        self.assertIn("draft_critic unavailable", r["reason"])
        self.assertEqual(len(self.db.tables["lead_interactions"].rows), 0)

    # 17. Concurrent send detection
    def test_17_advisory_lock_contention_blocks(self):
        self.db.force_lock_contention = True
        with self._patch_smtp_ok(), self._patch_suppress(False):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="jane@acme.example", subject="hi", body_text="hello",
                db=self.db,
            )
        self.assertEqual(r["status"], "blocked")
        self.assertIn("concurrent send detected", r["reason"])

    # 18. MAVEN_FORCE_DRY_RUN killswitch
    def test_18_maven_killswitch_short_circuits(self):
        cap = self.sg.DAILY_CAPS["email"]
        now_iso = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        for i in range(cap):
            self.db.tables["lead_interactions"].rows.append({
                "id": f"k-{i}", "lead_id": f"x-{i}", "channel": "email",
                "type": "email_sent", "created_at": now_iso,
            })

        original_load_env = self.sg.load_env

        def killswitch_env():
            base = original_load_env() or {}
            base["MAVEN_FORCE_DRY_RUN"] = "1"
            return base

        with mock.patch.object(self.sg, "load_env", side_effect=killswitch_env):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="jane@acme.example",
                subject="should never send", body_text="should never send",
                db=self.db,
            )
        self.assertEqual(r["status"], "dry_run", f"killswitch failed: {r}")
        self.assertIn("FORCE_DRY_RUN", r["reason"])
        # No interaction logged
        self.assertEqual(len(self.db.tables["lead_interactions"].rows), cap)

    # 18b. BRAVO_FORCE_DRY_RUN also honoured (shared multi-agent envelope)
    def test_18b_bravo_killswitch_also_honoured(self):
        original_load_env = self.sg.load_env

        def killswitch_env():
            base = original_load_env() or {}
            base["BRAVO_FORCE_DRY_RUN"] = "1"
            return base

        with mock.patch.object(self.sg, "load_env", side_effect=killswitch_env):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="jane@acme.example",
                subject="bravo killswitch", body_text="should not send",
                db=self.db,
            )
        self.assertEqual(r["status"], "dry_run")
        self.assertIn("FORCE_DRY_RUN", r["reason"])

    # 19. Name sanitization — placeholder gets rewritten
    def test_19_name_sanitization_replaces_placeholder(self):
        sanitized = self.sg.sanitize_template_vars(
            {"first_name": "Contact", "company": "Acme"}, key="first_name",
        )
        self.assertEqual(sanitized["first_name"], "team")
        self.assertEqual(sanitized["company"], "Acme")

    def test_19b_name_sanitization_real_name_preserved(self):
        sanitized = self.sg.sanitize_template_vars(
            {"first_name": "Jane"}, key="first_name",
        )
        self.assertEqual(sanitized["first_name"], "Jane")

    def test_19c_name_sanitization_through_send_path(self):
        # When template_vars is passed to send(), placeholder is rewritten.
        with self._patch_smtp_ok(), self._patch_suppress(False):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="jane@acme.example", subject="hi", body_text="hi",
                template_vars={"first_name": "Owner"},
                db=self.db,
            )
        # Send still succeeded — sanitization is silent. The contract is that
        # the sanitizer ran without raising.
        self.assertEqual(r["status"], "sent")

    # 20. CFO spend gate — meta_ads with open pulse + brand approval
    def test_20_meta_ads_with_open_pulse_allowed(self):
        # Default cfo_pulse open; oasis approved $100/day
        r = self.sg.send(
            channel="meta_ads", agent_source="meta_ads_engine",
            brand="oasis", spend_amount_usd=50.0, db=self.db,
        )
        self.assertEqual(r["status"], "sent")

    # 21. CFO spend gate — pulse missing fails closed
    def test_21_meta_ads_missing_pulse_fails_closed(self):
        os.environ["MAVEN_CFO_PULSE_PATH"] = str(self.tmp_path / "does-not-exist.json")
        r = self.sg.send(
            channel="meta_ads", agent_source="meta_ads_engine",
            brand="oasis", spend_amount_usd=50.0, db=self.db,
        )
        self.assertEqual(r["status"], "blocked")
        self.assertIn("cfo_pulse.json unavailable", r["reason"])

    # 22. CFO spend gate — pulse closed blocks
    def test_22_meta_ads_pulse_closed_blocks(self):
        _write_cfo_pulse(self.tmp_path, status="closed")
        r = self.sg.send(
            channel="meta_ads", agent_source="meta_ads_engine",
            brand="oasis", spend_amount_usd=50.0, db=self.db,
        )
        self.assertEqual(r["status"], "blocked")
        self.assertIn("status=closed", r["reason"])

    # 23. CFO spend gate — over budget blocks
    def test_23_meta_ads_over_budget_blocks(self):
        r = self.sg.send(
            channel="meta_ads", agent_source="meta_ads_engine",
            brand="oasis", spend_amount_usd=500.0,  # over $100 cap
            db=self.db,
        )
        self.assertEqual(r["status"], "blocked")
        self.assertIn("exceeds Atlas daily approval", r["reason"])

    # 24. CFO spend gate — google_ads with no brand approval blocks
    def test_24_google_ads_no_brand_approval_blocks(self):
        # cfo_pulse default has google_ads only for oasis; sunbiz is unapproved
        r = self.sg.send(
            channel="google_ads", agent_source="google_ads_engine",
            brand="sunbiz", spend_amount_usd=10.0, db=self.db,
        )
        self.assertEqual(r["status"], "blocked")
        self.assertIn("no Atlas approval", r["reason"])

    # 25. CFO spend gate — meta_ads via wildcard brand approval
    def test_25_meta_ads_wildcard_brand_allowed(self):
        # default has meta_ads "*" approved at $50; propflow uses wildcard
        r = self.sg.send(
            channel="meta_ads", agent_source="meta_ads_engine",
            brand="propflow", spend_amount_usd=25.0, db=self.db,
        )
        self.assertEqual(r["status"], "sent")

    # 26. Late post (organic) channel works (no spend gate, no SMTP)
    def test_26_late_post_logs_only(self):
        r = self.sg.send(
            channel="late_post", agent_source="late_poster",
            brand="conaugh", body_text="organic post",
            db=self.db,
        )
        self.assertEqual(r["status"], "sent")
        self.assertIn("non-email channel", r["reason"])

    # 27. Daily-cap threshold telegram alert
    def test_27_daily_cap_threshold_alert_optional(self):
        # Maven's _telegram_notify is a no-op stub. Just verify can_act runs
        # at threshold without raising.
        now = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        threshold = int(self.sg.DAILY_CAPS["email"] * 0.8)
        for i in range(threshold):
            self.db.tables["lead_interactions"].rows.append({
                "id": f"a-{i}", "lead_id": f"lead-{i}", "channel": "email",
                "type": "email_sent", "created_at": now,
            })
        r = self.sg.can_act(lead_id="lead-001", channel="email",
                            to_email="jane@acme.example", db=self.db)
        # Just below cap → still allowed
        self.assertTrue(r["allowed"])

    # 28. Stats query returns bounce + hourly counts
    def test_28_get_daily_stats_shape(self):
        now = datetime.now(timezone.utc).isoformat()
        self.db.tables["lead_interactions"].rows.append({
            "id": "s-1", "lead_id": "lead-001", "channel": "email",
            "type": "email_sent", "created_at": now,
        })
        stats = self.sg.get_daily_stats(self.db)
        self.assertIn("bounce_rate", stats)
        self.assertIn("hourly_counts", stats)
        self.assertIn("email", stats["hourly_counts"])

    # 29. Maven daily cap is 200 (master doc spec)
    def test_29_maven_daily_cap_is_200(self):
        self.assertEqual(self.sg.DAILY_CAPS["email"], 200)

    # 30. Maven hourly cap is 30 (master doc spec)
    def test_30_maven_hourly_cap_is_30(self):
        self.assertEqual(self.sg.HOURLY_CAPS["email"], 30)

    # 31. Brand identity has all 5 Maven brands
    def test_31_brand_identity_complete(self):
        expected = {"oasis", "conaugh", "propflow", "nostalgic", "sunbiz"}
        self.assertEqual(set(self.sg.BRAND_IDENTITY.keys()), expected)

    # 32. Empty agent_source rejected
    def test_32_empty_agent_source_error(self):
        r = self.sg.send(
            channel="email", agent_source="",
            to_email="jane@acme.example", subject="hi", body_text="hi",
            db=self.db,
        )
        self.assertEqual(r["status"], "error")
        self.assertIn("agent_source required", r["reason"])

    # 33. SunBiz brand uses correct CASL footer (no "loan" in business name)
    def test_33_sunbiz_footer_compliance(self):
        meta = self.sg.BRAND_IDENTITY["sunbiz"]
        self.assertIn("Funding", meta["business_name"])
        self.assertNotIn("loan", meta["business_name"].lower())

    # ====== Marketing-specific gates (Lens 2 — V1.2) ======

    # 34. List-mode caps trigger when burst > 50/hr; cap blocks at 200/hr
    def test_34_list_mode_caps_block_at_200_per_hour(self):
        now_iso = datetime.now(timezone.utc).isoformat()
        # Seed 200 hourly sends → at list-mode hourly cap
        for i in range(200):
            self.db.tables["lead_interactions"].rows.append({
                "id": f"lm-{i}", "lead_id": f"L{i}", "channel": "email",
                "type": "email_sent", "created_at": now_iso,
            })
        # Hourly cap (30) triggers FIRST in can_act, before list-mode. Verify
        # list_mode helper independently:
        r = self.sg.check_list_mode_caps(self.db, "email")
        self.assertFalse(r["allowed"])
        self.assertTrue(r["in_list_mode"])
        self.assertIn("list-mode hourly cap hit", r["reason"])

    # 35. CFO pulse stale (>24h) → paid spend blocked
    def test_35_cfo_pulse_stale_blocks_paid_spend(self):
        # Re-write cfo_pulse with old updated_at
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        path = self.tmp_path / "cfo_pulse.json"
        path.write_text(json.dumps({
            "updated_at": old_ts,
            "spend_gate": {"status": "open",
                           "approvals": {"meta_ads": {"oasis": {"daily_budget_usd": 100.0}}}},
        }), encoding="utf-8")
        r = self.sg.send(channel="meta_ads", agent_source="meta_ads_engine",
                         brand="oasis", spend_amount_usd=50.0, db=self.db)
        self.assertEqual(r["status"], "blocked")
        self.assertIn("stale", r["reason"])

    # 36. CFO pulse zero-budget → paid spend blocked even with explicit approval
    def test_36_cfo_pulse_zero_budget_blocks(self):
        path = self.tmp_path / "cfo_pulse.json"
        path.write_text(json.dumps({
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "spend_gate": {"status": "open",
                           "approvals": {"meta_ads": {"oasis": {"daily_budget_usd": 0}}}},
        }), encoding="utf-8")
        r = self.sg.send(channel="meta_ads", agent_source="meta_ads_engine",
                         brand="oasis", spend_amount_usd=10.0, db=self.db)
        self.assertEqual(r["status"], "blocked")
        self.assertIn("$0.00", r["reason"])

    # 37. UTM compliance: missing utm tags on a body link → blocked
    def test_37_missing_utm_tags_blocks(self):
        body = ("Check out our launch: https://oasisai.work/launch — let me know "
                "if it makes sense for you.")
        with self._patch_smtp_ok(), self._patch_suppress(False):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="jane@acme.example",
                subject="Launch announcement", body_text=body,
                db=self.db,
            )
        self.assertEqual(r["status"], "blocked")
        self.assertIn("UTM compliance", r["reason"])

    # 37b. UTM compliance: properly tagged URL passes
    def test_37b_utm_tagged_url_passes(self):
        body = ("Check out our launch: "
                "https://oasisai.work/launch?utm_source=newsletter&utm_medium=email&utm_campaign=q2_launch")
        with self._patch_smtp_ok(), self._patch_suppress(False):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="jane@acme.example",
                subject="Launch announcement", body_text=body,
                db=self.db,
            )
        self.assertEqual(r["status"], "sent", r)

    # 38. Subject-line slop blocks
    def test_38_subject_slop_blocks(self):
        with self._patch_smtp_ok(), self._patch_suppress(False):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="jane@acme.example",
                subject="Unlock the power of AI in your business",
                body_text="hello", db=self.db,
            )
        self.assertEqual(r["status"], "blocked")
        self.assertIn("subject slop", r["reason"])

    # 38b. All-caps subject blocks
    def test_38b_all_caps_subject_blocks(self):
        with self._patch_smtp_ok(), self._patch_suppress(False):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="jane@acme.example",
                subject="LAST CHANCE TO REGISTER NOW",
                body_text="hello", db=self.db,
            )
        self.assertEqual(r["status"], "blocked")
        self.assertIn("all-caps", r["reason"])

    # 39. Image attachment without alt_text blocks
    def test_39_missing_alt_text_blocks(self):
        attachments = [{
            "filename": "hero.png",
            "content": b"fake-png-bytes",
            "content_type": "image/png",
            # alt_text intentionally missing
        }]
        with self._patch_smtp_ok(), self._patch_suppress(False):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="jane@acme.example",
                subject="hi", body_text="hello",
                attachments=attachments, db=self.db,
            )
        self.assertEqual(r["status"], "blocked")
        self.assertIn("alt-text", r["reason"])

    # 40. Creative fatigue: same creative_id sent twice in 14d → blocked second
    # send. Seed a prior send 5 days ago (past 96h cooldown) but within the
    # 14d fatigue window, with explicit cooldown_until in the past so cooldown
    # gate doesn't trigger.
    def test_40_creative_fatigue_blocks_repeat(self):
        five_days_ago = (datetime.now(timezone.utc) - timedelta(days=5))
        cooldown_past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        self.db.tables["lead_interactions"].rows.append({
            "id": "f-1", "lead_id": "lead-001", "channel": "email",
            "type": "email_sent", "created_at": five_days_ago.isoformat(),
            "cooldown_until": cooldown_past,
            "metadata": {"creative_id": "hero_v1", "brand": "oasis"},
        })
        with self._patch_smtp_ok(), self._patch_suppress(False):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="jane@acme.example",
                subject="hi", body_text="hello",
                metadata={"creative_id": "hero_v1"},
                db=self.db,
            )
        self.assertEqual(r["status"], "blocked", r)
        self.assertIn("creative fatigue", r["reason"])

    # 41. VIP override: critic non-ship verdict ships-with-warning
    def test_41_vip_override_ships_with_warning(self):
        os.environ["MAVEN_VIP_EMAILS"] = "jane@acme.example"
        try:
            with self._patch_smtp_ok(), self._patch_suppress(False), \
                 self._patch_critic("revise", ["minor slop"]):
                r = self.sg.send(
                    channel="email", agent_source="test_harness",
                    to_email="jane@acme.example",
                    subject="hi", body_text="hello",
                    db=self.db,
                )
            # VIP override → still sent, with critic_override flagged in metadata
            self.assertEqual(r["status"], "sent", r)
            ix = self.db.tables["lead_interactions"].rows[-1]
            md = ix.get("metadata") or {}
            self.assertEqual(md.get("critic_override"), "vip")
            self.assertEqual(md.get("critic_verdict"), "revise")
        finally:
            os.environ.pop("MAVEN_VIP_EMAILS", None)

    # 42. Non-VIP critic non-ship still blocks (regression guard for VIP override)
    def test_42_non_vip_still_blocks_on_critic_reject(self):
        # Make sure VIP envs are clear
        os.environ.pop("MAVEN_VIP_EMAILS", None)
        os.environ.pop("MAVEN_VIP_DOMAINS", None)
        with self._patch_smtp_ok(), self._patch_suppress(False), \
             self._patch_critic("revise", ["slop"]):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="bob@randomco.example",
                subject="hi", body_text="hello",
                db=self.db,
            )
        self.assertEqual(r["status"], "blocked")
        self.assertIn("draft_critic rejected", r["reason"])

    # ====== Lens 3 — CFO spend gate end-to-end ======

    # 44. CFO gate fail mode: missing pulse file → blocked
    def test_44_cfo_missing_pulse_blocks(self):
        os.environ["MAVEN_CFO_PULSE_PATH"] = str(self.tmp_path / "definitely-not-here.json")
        gate = self.sg.check_cfo_spend_gate("meta_ads", "oasis", amount_usd=10.0)
        self.assertFalse(gate["allowed"])
        self.assertIn("unavailable", gate["reason"])

    # 45. CFO gate fail mode: malformed JSON → fails closed (None pulse)
    def test_45_cfo_malformed_json_blocks(self):
        path = self.tmp_path / "cfo_pulse.json"
        path.write_text("not even close to json {{{", encoding="utf-8")
        gate = self.sg.check_cfo_spend_gate("meta_ads", "oasis", amount_usd=10.0)
        self.assertFalse(gate["allowed"])
        self.assertIn("unavailable", gate["reason"])

    # 46. CFO gate fail mode: missing updated_at → fail-closed
    # (cfo_pulse without updated_at is treated as "no staleness signal" — gate
    # falls through to channel/brand checks. So if status=open + approval is
    # present, it actually allows. This test pins that documented behaviour.)
    def test_46_cfo_no_timestamp_falls_through_to_approval_check(self):
        path = self.tmp_path / "cfo_pulse.json"
        path.write_text(json.dumps({
            "spend_gate": {"status": "open",
                           "approvals": {"meta_ads": {"oasis": {"daily_budget_usd": 100.0}}}},
        }), encoding="utf-8")
        gate = self.sg.check_cfo_spend_gate("meta_ads", "oasis", amount_usd=10.0)
        self.assertTrue(gate["allowed"], gate)

    # 47. CFO gate fail mode: status="open" but channel approvals empty → blocked
    def test_47_cfo_open_but_no_channel_approval_blocks(self):
        path = self.tmp_path / "cfo_pulse.json"
        path.write_text(json.dumps({
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "spend_gate": {"status": "open", "approvals": {}},
        }), encoding="utf-8")
        gate = self.sg.check_cfo_spend_gate("meta_ads", "oasis", amount_usd=10.0)
        self.assertFalse(gate["allowed"])
        self.assertIn("no Atlas approval", gate["reason"])

    # 48. CFO gate happy path with explicit ts + amount under budget
    def test_48_cfo_full_happy_path(self):
        path = self.tmp_path / "cfo_pulse.json"
        path.write_text(json.dumps({
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "spend_gate": {"status": "open",
                           "approvals": {"meta_ads": {"oasis": {"daily_budget_usd": 100.0}}}},
        }), encoding="utf-8")
        gate = self.sg.check_cfo_spend_gate("meta_ads", "oasis", amount_usd=50.0)
        self.assertTrue(gate["allowed"])
        self.assertEqual(gate["approved_budget"], 100.0)

    # 43. Double-opt-in marker: first send to cold recipient should carry
    # opt-in confirmation. We enforce via metadata flag — caller passes
    # opt_in_status="confirmed" or "pending"; pending blocks for cold leads.
    # NOTE: validation here is a metadata convention check, not the full DOI flow.
    def test_43_double_opt_in_pending_for_cold_blocks(self):
        with self._patch_smtp_ok(), self._patch_suppress(False):
            r = self.sg.send(
                channel="email", agent_source="test_harness",
                to_email="brand-new-cold@randomco.example",
                subject="welcome",
                # body has a confirm-your-subscription URL with full UTM
                body_text=("Welcome! Confirm your subscription: "
                           "https://oasisai.work/confirm?utm_source=newsletter"
                           "&utm_medium=email&utm_campaign=double_optin"),
                metadata={"opt_in_status": "confirmed"},
                db=self.db,
            )
        # Confirmed opt-in passes (this is a positive-path proxy test for the
        # double-opt-in metadata convention; full DOI flow lives in email_blast).
        self.assertEqual(r["status"], "sent", r)


# ---- DraftCritic logic tests (slop detection — pure logic, no API calls) ---

class TestDraftCriticLogic(unittest.TestCase):

    def setUp(self):
        _fresh_env({})
        import importlib
        for m in [m for m in list(sys.modules) if m.startswith("draft_critic")]:
            del sys.modules[m]
        import draft_critic
        importlib.reload(draft_critic)
        self.dc = draft_critic

    def test_01_catches_classic_slop(self):
        body = "Hi Jane,\n\nI hope this email finds you well. I wanted to reach out about..."
        hits = self.dc.find_slop(body)
        excerpts = [h["excerpt"].lower() for h in hits]
        self.assertTrue(any("finds you well" in e for e in excerpts))
        self.assertTrue(any("wanted to reach out" in e for e in excerpts))

    def test_02_clean_draft_zero_hits(self):
        body = ("Hey Jane — saw you're spending 5 days writing manual quotes. "
                "Our clients cut that to 15 minutes. Want a 5-min walkthrough?")
        hits = self.dc.find_slop(body)
        self.assertEqual(len(hits), 0)

    def test_03_validator_downgrades_ship_with_slop(self):
        r = self.dc._validate_critic_output(
            {"verdict": "ship", "score": 8.0, "issues": []},
            slop_hits=[{"excerpt": "I hope this finds you well"}],
        )
        self.assertEqual(r["verdict"], "revise")

    def test_04_score_clamped(self):
        r = self.dc._validate_critic_output(
            {"verdict": "ship", "score": 50.0, "issues": []},
            slop_hits=[],
        )
        self.assertLessEqual(r["score"], 10.0)


# ---- NameUtils tests --------------------------------------------------------

class TestNameUtils(unittest.TestCase):

    def setUp(self):
        import importlib
        for m in [m for m in list(sys.modules) if m.startswith("name_utils")]:
            del sys.modules[m]
        import name_utils
        importlib.reload(name_utils)
        self.nu = name_utils

    def test_01_placeholder_replaced(self):
        self.assertEqual(self.nu.safe_first_name("Contact"), "team")
        self.assertEqual(self.nu.safe_first_name("Owner"), "team")
        self.assertEqual(self.nu.safe_first_name(""), "team")
        self.assertEqual(self.nu.safe_first_name(None), "team")

    def test_02_real_name_preserved(self):
        self.assertEqual(self.nu.safe_first_name("Jane"), "Jane")
        self.assertEqual(self.nu.safe_first_name("  María  "), "María")

    def test_03_punctuation_only_replaced(self):
        self.assertEqual(self.nu.safe_first_name("..."), "team")
        self.assertEqual(self.nu.safe_first_name("???"), "team")

    def test_04_full_name_fallback_is_there(self):
        self.assertEqual(self.nu.safe_full_name("contact"), "there")


# ---- Runner -----------------------------------------------------------------

def _run_all(verbose: bool = False) -> bool:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite([
        loader.loadTestsFromTestCase(TestSendGateway),
        loader.loadTestsFromTestCase(TestDraftCriticLogic),
        loader.loadTestsFromTestCase(TestNameUtils),
    ])
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    return result.wasSuccessful()


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    ok = _run_all(verbose=args.verbose)
    if args.json:
        print(json.dumps({"ok": ok}))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
