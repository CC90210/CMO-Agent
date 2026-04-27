"""
Tests for scripts/notify.py — Maven's Telegram notification surface.

Covers the cases that matter:
  - Missing token → graceful False, never raises
  - Missing chat IDs → graceful False, never raises
  - Blocked category → False without HTTP call
  - File log always written, even on Telegram failure
  - Token-precedence chain: MAVEN > BRAVO > generic TELEGRAM_BOT_TOKEN
  - notify_killswitch_engaged + notify_error wrappers

Run:
  python scripts/test_notify.py
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _import_notify_fresh():
    import importlib
    for m in [m for m in list(sys.modules) if m.startswith("notify")]:
        del sys.modules[m]
    import notify
    importlib.reload(notify)
    return notify


class TestNotify(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self.notify = _import_notify_fresh()
        # Redirect log writes to a tmp dir so the real memory/notify.log
        # isn't touched by tests.
        self.notify.NOTIFY_LOG = self.tmp_path / "notify.log"
        # Reset env cache for each test
        self.notify._env_cache = {}

    def tearDown(self):
        self._tmp.cleanup()

    def _stub_env(self, env: dict):
        """Bypass disk read of .env.agents and inject a synthetic env dict."""
        return mock.patch.object(self.notify, "_load_env", return_value=env)

    def test_01_missing_token_returns_false(self):
        with self._stub_env({}):
            ok = self.notify.notify("hello", category="campaign")
        self.assertFalse(ok)

    def test_02_missing_chat_ids_returns_false(self):
        with self._stub_env({"MAVEN_TELEGRAM_BOT_TOKEN": "fake-token"}):
            ok = self.notify.notify("hello", category="campaign")
        self.assertFalse(ok)

    def test_03_file_log_always_written(self):
        # Even with no token, the message hits the forensic log
        with self._stub_env({}):
            self.notify.notify("traceable msg", category="campaign")
        self.assertTrue(self.notify.NOTIFY_LOG.exists())
        content = self.notify.NOTIFY_LOG.read_text(encoding="utf-8")
        self.assertIn("traceable msg", content)
        self.assertIn("campaign", content)

    def test_04_blocked_category_short_circuits(self):
        env = {
            "MAVEN_TELEGRAM_BOT_TOKEN": "fake",
            "MAVEN_TELEGRAM_ALLOWED_USERS": "12345",
            "NOTIFY_BLOCKED_CATEGORIES": "campaign",
        }
        with self._stub_env(env), \
             mock.patch.object(self.notify, "_load_env", return_value=env), \
             mock.patch("requests.post") as post_mock:
            ok = self.notify.notify("blocked msg", category="campaign")
        self.assertFalse(ok)
        post_mock.assert_not_called()

    def test_05_force_overrides_block(self):
        env = {
            "MAVEN_TELEGRAM_BOT_TOKEN": "fake",
            "MAVEN_TELEGRAM_ALLOWED_USERS": "12345",
            "NOTIFY_BLOCKED_CATEGORIES": "campaign",
        }
        fake_resp = mock.Mock()
        fake_resp.json.return_value = {"ok": True}
        fake_resp.content = b"{}"
        fake_resp.status_code = 200
        with self._stub_env(env), \
             mock.patch("requests.post", return_value=fake_resp) as post_mock:
            ok = self.notify.notify("urgent", category="campaign", force=True)
        self.assertTrue(ok)
        post_mock.assert_called_once()

    def test_06_token_precedence_maven_wins(self):
        env = {
            "MAVEN_TELEGRAM_BOT_TOKEN": "maven-tok",
            "BRAVO_TELEGRAM_BOT_TOKEN": "bravo-tok",
            "TELEGRAM_BOT_TOKEN": "generic-tok",
            "MAVEN_TELEGRAM_ALLOWED_USERS": "12345",
        }
        captured_url = []
        def fake_post(url, **_kw):
            captured_url.append(url)
            r = mock.Mock(); r.json.return_value = {"ok": True}; r.content = b"{}"; r.status_code = 200
            return r
        with self._stub_env(env), mock.patch("requests.post", side_effect=fake_post):
            self.notify.notify("hello", category="campaign", force=True)
        self.assertTrue(any("maven-tok" in u for u in captured_url),
                        f"expected maven-tok URL, got {captured_url}")

    def test_07_falls_back_to_bravo_token_if_maven_absent(self):
        env = {
            "BRAVO_TELEGRAM_BOT_TOKEN": "bravo-tok",
            "MAVEN_TELEGRAM_ALLOWED_USERS": "12345",
        }
        captured_url = []
        def fake_post(url, **_kw):
            captured_url.append(url)
            r = mock.Mock(); r.json.return_value = {"ok": True}; r.content = b"{}"; r.status_code = 200
            return r
        with self._stub_env(env), mock.patch("requests.post", side_effect=fake_post):
            self.notify.notify("hello", category="campaign", force=True)
        self.assertTrue(any("bravo-tok" in u for u in captured_url))

    def test_08_silent_categories_send_with_disable_notification(self):
        env = {
            "MAVEN_TELEGRAM_BOT_TOKEN": "fake",
            "MAVEN_TELEGRAM_ALLOWED_USERS": "12345",
        }
        captured = []
        def fake_post(url, **kw):
            captured.append(kw.get("json", {}))
            r = mock.Mock(); r.json.return_value = {"ok": True}; r.content = b"{}"; r.status_code = 200
            return r
        with self._stub_env(env), mock.patch("requests.post", side_effect=fake_post):
            self.notify.notify("post live", category="content-published")
        self.assertTrue(captured)
        self.assertTrue(captured[0].get("disable_notification"))

    def test_09_loud_categories_send_with_sound(self):
        env = {
            "MAVEN_TELEGRAM_BOT_TOKEN": "fake",
            "MAVEN_TELEGRAM_ALLOWED_USERS": "12345",
        }
        captured = []
        def fake_post(url, **kw):
            captured.append(kw.get("json", {}))
            r = mock.Mock(); r.json.return_value = {"ok": True}; r.content = b"{}"; r.status_code = 200
            return r
        with self._stub_env(env), mock.patch("requests.post", side_effect=fake_post):
            self.notify.notify("CFO blocked spend", category="cfo-block")
        self.assertTrue(captured)
        self.assertFalse(captured[0].get("disable_notification"))

    def test_10_multiple_chat_ids_each_get_message(self):
        env = {
            "MAVEN_TELEGRAM_BOT_TOKEN": "fake",
            "MAVEN_TELEGRAM_ALLOWED_USERS": "111,222,333",
        }
        sent_to = []
        def fake_post(url, **kw):
            sent_to.append(kw.get("json", {}).get("chat_id"))
            r = mock.Mock(); r.json.return_value = {"ok": True}; r.content = b"{}"; r.status_code = 200
            return r
        with self._stub_env(env), mock.patch("requests.post", side_effect=fake_post):
            ok = self.notify.notify("broadcast", category="error", force=True)
        self.assertTrue(ok)
        self.assertEqual(sorted(sent_to), ["111", "222", "333"])

    def test_11_telegram_failure_surfaces_false_but_log_still_written(self):
        env = {
            "MAVEN_TELEGRAM_BOT_TOKEN": "fake",
            "MAVEN_TELEGRAM_ALLOWED_USERS": "12345",
        }
        fake_resp = mock.Mock()
        fake_resp.json.return_value = {"ok": False, "description": "bot blocked"}
        fake_resp.content = b"{}"
        fake_resp.status_code = 403
        with self._stub_env(env), mock.patch("requests.post", return_value=fake_resp):
            ok = self.notify.notify("blocked-by-user", category="error", force=True)
        self.assertFalse(ok)
        # File log still has the entry
        content = self.notify.NOTIFY_LOG.read_text(encoding="utf-8")
        self.assertIn("blocked-by-user", content)

    def test_12_killswitch_helper_force_loud(self):
        env = {
            "MAVEN_TELEGRAM_BOT_TOKEN": "fake",
            "MAVEN_TELEGRAM_ALLOWED_USERS": "12345",
        }
        captured = []
        def fake_post(url, **kw):
            captured.append(kw.get("json", {}))
            r = mock.Mock(); r.json.return_value = {"ok": True}; r.content = b"{}"; r.status_code = 200
            return r
        with self._stub_env(env), mock.patch("requests.post", side_effect=fake_post):
            ok = self.notify.notify_killswitch_engaged()
        self.assertTrue(ok)
        self.assertIn("MAVEN_FORCE_DRY_RUN", captured[0]["text"])
        self.assertFalse(captured[0].get("disable_notification"))

    def test_13_notify_does_not_raise_on_log_dir_missing(self):
        # Set log to a path whose parent doesn't exist; notify should still
        # complete without raising (the .mkdir handles parent creation).
        self.notify.NOTIFY_LOG = self.tmp_path / "deep" / "nested" / "notify.log"
        with self._stub_env({}):
            # Returns False (no token) but must not raise
            self.notify.notify("nested log path", category="campaign")
        self.assertTrue(self.notify.NOTIFY_LOG.exists())


def _run_all(verbose=False):
    loader = unittest.TestLoader()
    suite = unittest.TestSuite([loader.loadTestsFromTestCase(TestNotify)])
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
