"""
Tests for late_publisher.py — verify every publish path goes through
send_gateway and respects killswitch / cap / critic gates.

Run:
  python scripts/test_late_publisher.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


class _FakeUpdate:
    def __init__(self, store, payload):
        self.store, self.payload = store, payload
        self.filters = []

    def eq(self, col, val):
        self.filters.append((col, val))
        return self

    def execute(self):
        self.store.append({"payload": self.payload, "filters": self.filters})

        class R:
            data = []
            count = 0
        return R()


class _FakeTable:
    def __init__(self):
        self.updates: list = []

    def update(self, payload):
        return _FakeUpdate(self.updates, payload)


class _FakeClient:
    def __init__(self):
        self.tables = {"content_calendar": _FakeTable()}

    def table(self, name):
        return self.tables.setdefault(name, _FakeTable())


def _import_publisher_fresh():
    import importlib
    for m in [m for m in list(sys.modules) if m.startswith("late_publisher")]:
        del sys.modules[m]
    import late_publisher
    importlib.reload(late_publisher)
    return late_publisher


def _row(content_id="c-1", platform="x", body="hello world", title=None, brand="oasis"):
    return {
        "id": content_id, "platform": platform, "body": body,
        "title": title, "brand": brand,
    }


class TestLatePublisher(unittest.TestCase):

    def setUp(self):
        self.lp = _import_publisher_fresh()
        self.client = _FakeClient()
        # Account map stub so resolve_account_id returns something non-empty.
        self.lp._account_map_cache = {"x": "acc_x", "instagram": "acc_ig"}
        # Suppress notifications during tests
        self._notify_patcher = mock.patch.object(self.lp, "notify", return_value=None)
        self._notify_patcher.start()
        self.addCleanup(self._notify_patcher.stop)

    def _patch_publish_ok(self):
        return mock.patch.object(self.lp, "publish_via_late",
                                 return_value=(True, "late_post_123", ""))

    def _patch_gate(self, status: str, reason: str = ""):
        # Patch the gateway send() the publisher imports lazily — easiest path
        # is to patch `send_gateway.send` directly so the import inside
        # _publish_row resolves to our stub.
        import send_gateway
        return mock.patch.object(
            send_gateway, "send",
            return_value={
                "status": status, "reason": reason,
                "lead_id": None, "interaction_id": None,
                "cooldown_until": None, "daily_count": None,
            },
        )

    # 1. Golden path — gate dry_run-ok, publish succeeds
    def test_01_golden_path_publishes(self):
        with self._patch_gate("dry_run", "dry_run=True, nothing sent"), self._patch_publish_ok():
            r = self.lp._publish_row(self.client, _row(), as_json=True)
        self.assertEqual(r["status"], "posted", r)
        self.assertEqual(r["late_post_id"], "late_post_123")

    # 2. Gate blocks → publisher returns blocked, never calls publish_via_late
    def test_02_gate_blocks_no_publish(self):
        with self._patch_gate("blocked", "draft_critic rejected: spammy"), \
             mock.patch.object(self.lp, "publish_via_late") as pub_mock:
            r = self.lp._publish_row(self.client, _row(), as_json=True)
        self.assertEqual(r["status"], "blocked")
        self.assertIn("draft_critic rejected", r["error"])
        pub_mock.assert_not_called()

    # 3. Killswitch (gate returns dry_run with FORCE_DRY_RUN reason) short-circuits
    def test_03_killswitch_dry_run_short_circuits(self):
        with self._patch_gate("dry_run", "MAVEN_FORCE_DRY_RUN engaged — killswitch"), \
             mock.patch.object(self.lp, "publish_via_late") as pub_mock:
            r = self.lp._publish_row(self.client, _row(), as_json=True)
        self.assertEqual(r["status"], "dry_run")
        pub_mock.assert_not_called()

    # 4. Cap exceeded (gate blocks with daily-cap reason)
    def test_04_daily_cap_blocks(self):
        with self._patch_gate("blocked", "daily cap hit: 50/50 social actions today"), \
             mock.patch.object(self.lp, "publish_via_late") as pub_mock:
            r = self.lp._publish_row(self.client, _row(), as_json=True)
        self.assertEqual(r["status"], "blocked")
        self.assertIn("daily cap", r["error"])
        pub_mock.assert_not_called()

    # 5. Character-limit pre-check still rejects before gate
    def test_05_char_limit_rejects_before_gate(self):
        long_body = "x" * 500  # exceeds x's 280-char limit
        with mock.patch.object(self.lp, "publish_via_late") as pub_mock:
            r = self.lp._publish_row(self.client, _row(body=long_body), as_json=True)
        self.assertEqual(r["status"], "failed")
        self.assertIn("Exceeds", r["error"])
        pub_mock.assert_not_called()


def _run_all(verbose=False):
    loader = unittest.TestLoader()
    suite = unittest.TestSuite([loader.loadTestsFromTestCase(TestLatePublisher)])
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    return runner.run(suite).wasSuccessful()


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args()
    sys.exit(0 if _run_all(args.verbose) else 1)


if __name__ == "__main__":
    main()
