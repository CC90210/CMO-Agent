"""
Tests for instagram_engine._send_dm_reply — verify every outbound DM
goes through send_gateway and respects killswitch / cap / critic gates.

Inbound DM read paths are intentionally not gated; only outbound replies.

Run:
  python scripts/test_instagram_engine.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


class _FakePage:
    """Minimal Playwright page stub: returns a fake textbox + records keystrokes."""

    url = "https://www.instagram.com/direct/t/test/"

    def __init__(self, has_textbox: bool = True):
        self._has_textbox = has_textbox
        self.typed: list[str] = []
        self.keys: list[str] = []
        self.keyboard = self  # self serves as keyboard

    def query_selector(self, _selector: str):
        if not self._has_textbox:
            return None

        class Box:
            def click(self_inner):  # noqa: N805
                return None

            def is_visible(self_inner):  # noqa: N805
                return True

            def scroll_into_view_if_needed(self_inner, timeout=3000):  # noqa: N805
                return None
        return Box()

    def wait_for_selector(self, _selector: str, timeout: int = 4000, state: str = "visible"):
        return self.query_selector(_selector)

    def evaluate(self, _script: str):
        # _dismiss_ig_prompts uses evaluate; tests don't care about its result
        return False

    def screenshot(self, path: str = ""):
        return None

    def type(self, text: str, delay: int = 0):
        self.typed.append(text)

    def press(self, key: str):
        self.keys.append(key)


def _import_engine_fresh():
    import importlib
    for m in [m for m in list(sys.modules) if m.startswith("instagram_engine")]:
        del sys.modules[m]
    import instagram_engine
    importlib.reload(instagram_engine)
    return instagram_engine


class TestInstagramEngineDMGate(unittest.TestCase):

    def setUp(self):
        self.ie = _import_engine_fresh()
        # Speed up tests by neutering time.sleep
        self._sleep_patch = mock.patch.object(self.ie, "time")
        mock_time = self._sleep_patch.start()
        mock_time.sleep = lambda *_a, **_k: None
        self.addCleanup(self._sleep_patch.stop)

    def _patch_gate(self, status: str, reason: str = ""):
        import send_gateway
        return mock.patch.object(
            send_gateway, "send",
            return_value={
                "status": status, "reason": reason,
                "lead_id": None, "interaction_id": None,
                "cooldown_until": None, "daily_count": None,
            },
        )

    # 1. Golden path — gate dry_run-ok, DM is typed + Enter pressed
    def test_01_golden_path_sends(self):
        page = _FakePage(has_textbox=True)
        with self._patch_gate("dry_run", "dry_run=True, nothing sent"):
            ok = self.ie._send_dm_reply(page, "hey there", recipient="alice")
        self.assertTrue(ok)
        self.assertIn("hey there", page.typed)
        self.assertIn("Enter", page.keys)

    # 2. Gate blocks (critic reject) → no typing, no Enter
    def test_02_critic_reject_blocks(self):
        page = _FakePage(has_textbox=True)
        with self._patch_gate("blocked", "draft_critic rejected: slop"):
            ok = self.ie._send_dm_reply(page, "Hi there!! GAME-CHANGING offer", recipient="bob")
        self.assertFalse(ok)
        self.assertEqual(page.typed, [])
        self.assertEqual(page.keys, [])

    # 3. Killswitch dry_run reason short-circuits
    def test_03_killswitch_short_circuits(self):
        page = _FakePage(has_textbox=True)
        with self._patch_gate("dry_run", "MAVEN_FORCE_DRY_RUN engaged — killswitch"):
            ok = self.ie._send_dm_reply(page, "test", recipient="carol")
        self.assertFalse(ok)
        self.assertEqual(page.typed, [])

    # 4. Daily cap exceeded → blocked
    def test_04_daily_cap_blocks(self):
        page = _FakePage(has_textbox=True)
        with self._patch_gate("blocked", "daily cap hit: 30/30 instagram_dm actions today"):
            ok = self.ie._send_dm_reply(page, "follow up", recipient="dave")
        self.assertFalse(ok)
        self.assertEqual(page.typed, [])

    # 5. Per-recipient cooldown blocks repeat sends
    def test_05_per_recipient_cooldown_blocks(self):
        page = _FakePage(has_textbox=True)
        with self._patch_gate("blocked", "cooldown active until 2026-04-27T12:00:00+00:00"):
            ok = self.ie._send_dm_reply(page, "second message", recipient="alice")
        self.assertFalse(ok)

    # 6. Recipient hash is stable per username (lead_id derivation)
    def test_06_recipient_hash_stable(self):
        page = _FakePage(has_textbox=True)
        captured = []

        def fake_send(**kwargs):
            captured.append(kwargs)
            return {"status": "dry_run", "reason": "ok",
                    "lead_id": kwargs.get("lead_id"), "interaction_id": None,
                    "cooldown_until": None, "daily_count": None}

        import send_gateway
        with mock.patch.object(send_gateway, "send", side_effect=fake_send):
            self.ie._send_dm_reply(page, "msg1", recipient="alice")
            self.ie._send_dm_reply(page, "msg2", recipient="alice")
            self.ie._send_dm_reply(page, "msg3", recipient="bob")

        alice_ids = [c["lead_id"] for c in captured if c["metadata"]["recipient"] == "alice"]
        bob_ids = [c["lead_id"] for c in captured if c["metadata"]["recipient"] == "bob"]
        self.assertEqual(len(set(alice_ids)), 1, "alice lead_id should be stable")
        self.assertNotEqual(alice_ids[0], bob_ids[0], "different recipients → different lead_ids")
        # lead_id must be a valid UUID — Supabase rejects anything else.
        import uuid as _uuid
        _uuid.UUID(alice_ids[0])
        _uuid.UUID(bob_ids[0])


def _run_all(verbose=False):
    loader = unittest.TestLoader()
    suite = unittest.TestSuite([loader.loadTestsFromTestCase(TestInstagramEngineDMGate)])
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
