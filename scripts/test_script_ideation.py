"""Tests for scripts/script_ideation.py.

Run: python scripts/test_script_ideation.py

Covers the parts of the ideation pipeline that can fail silently:
  - Foundation loading (graceful degradation when files missing)
  - Sibling-pulse signal loading (missing repos, malformed JSON)
  - Prompt assembly (every required section appears)
  - Claude API integration shape (mocked — no network, no credits)
  - Subcommand dispatch (generate / list / view)
  - Output writer (data/ideation/<timestamp>.md schema)

Dependency-free harness — no pytest required, runs anywhere Python runs.
"""
from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import script_ideation  # noqa: E402


class _Block:
    """Minimal stand-in for an Anthropic content block (has .text)."""
    def __init__(self, text: str):
        self.text = text


class _FakeResponse:
    def __init__(self, text: str):
        self.content = [_Block(text)]


class _FakeAnthropicClient:
    """Captures the call args so tests can assert on the prompt + model."""
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.captured = {}

        outer = self

        class _Messages:
            def create(self, model, max_tokens, messages):
                outer.captured["model"] = model
                outer.captured["max_tokens"] = max_tokens
                outer.captured["messages"] = messages
                # Return a deterministic fake response so save_run can write it
                return _FakeResponse(
                    "### 1. Mock idea\n"
                    "- **Pillar**: ceo_log\n"
                    "- **Format**: short_video\n"
                    "- **Hook**: This is a mocked idea.\n"
                )

        self.messages = _Messages()


# ============================================================================
# Foundation loading
# ============================================================================

class TestLoadFoundation(unittest.TestCase):
    """`load_foundation()` reads 5 files; each missing → empty string, no crash."""

    def test_returns_all_5_keys_even_when_files_missing(self):
        # Point PROJECT_ROOT at an empty temp dir
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(script_ideation, "PROJECT_ROOT", Path(tmp)):
                f = script_ideation.load_foundation()
        self.assertEqual(set(f.keys()),
                         {"soul", "writing", "marketing_canon",
                          "content_bible", "video_production_bible"})
        # All empty strings (files don't exist)
        self.assertTrue(all(v == "" for v in f.values()))

    def test_reads_files_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "brain").mkdir()
            (root / "brain" / "SOUL.md").write_text("Maven's identity\n", encoding="utf-8")
            (root / "brain" / "WRITING.md").write_text("Voice rules\n", encoding="utf-8")
            (root / "brain" / "MARKETING_CANON.md").write_text("10 pillars\n", encoding="utf-8")
            (root / "brain" / "CONTENT_BIBLE.md").write_text("Pillars + hooks\n", encoding="utf-8")
            (root / "brain" / "VIDEO_PRODUCTION_BIBLE.md").write_text(
                "\n".join(f"line {i}" for i in range(120)), encoding="utf-8")
            with mock.patch.object(script_ideation, "PROJECT_ROOT", root):
                f = script_ideation.load_foundation()
        self.assertEqual(f["soul"], "Maven's identity")
        self.assertEqual(f["writing"], "Voice rules")
        # video_production_bible is line-capped at 80
        self.assertLessEqual(len(f["video_production_bible"].split("\n")), 80)


# ============================================================================
# Sibling pulse loading
# ============================================================================

class TestLoadCurrentSignal(unittest.TestCase):
    """`load_current_signal()` reads 3 sibling pulse JSONs without crashing."""

    def test_missing_repos_return_none_each(self):
        with tempfile.TemporaryDirectory() as tmp:
            sibling_repos = {
                "bravo": Path(tmp) / "doesnotexist_bravo",
                "atlas": Path(tmp) / "doesnotexist_atlas",
                "aura":  Path(tmp) / "doesnotexist_aura",
            }
            with mock.patch.object(script_ideation, "SIBLING_REPOS", sibling_repos):
                signal = script_ideation.load_current_signal()
        self.assertEqual(signal, {"bravo": None, "atlas": None, "aura": None})

    def test_reads_valid_pulses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for agent, fname in (("bravo", "ceo_pulse.json"),
                                 ("atlas", "cfo_pulse.json"),
                                 ("aura",  "aura_pulse.json")):
                pulse_dir = root / agent / "data" / "pulse"
                pulse_dir.mkdir(parents=True)
                (pulse_dir / fname).write_text(
                    json.dumps({"session_note": f"{agent} working"}),
                    encoding="utf-8")
            sibling_repos = {
                "bravo": root / "bravo",
                "atlas": root / "atlas",
                "aura":  root / "aura",
            }
            with mock.patch.object(script_ideation, "SIBLING_REPOS", sibling_repos):
                signal = script_ideation.load_current_signal()
        self.assertEqual(signal["bravo"]["session_note"], "bravo working")
        self.assertEqual(signal["atlas"]["session_note"], "atlas working")
        self.assertEqual(signal["aura"]["session_note"],  "aura working")

    def test_malformed_json_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pulse_dir = root / "bravo" / "data" / "pulse"
            pulse_dir.mkdir(parents=True)
            (pulse_dir / "ceo_pulse.json").write_text("{ broken json", encoding="utf-8")
            sibling_repos = {"bravo": root / "bravo", "atlas": root / "x", "aura": root / "y"}
            with mock.patch.object(script_ideation, "SIBLING_REPOS", sibling_repos):
                signal = script_ideation.load_current_signal()
        self.assertIsNone(signal["bravo"])  # malformed → None, not crash


# ============================================================================
# Prompt assembly
# ============================================================================

class TestBuildPrompt(unittest.TestCase):
    """`build_prompt()` must include every required section + the spec values."""

    def _foundation(self):
        return {
            "soul": "Maven SOUL content",
            "writing": "Maven WRITING content",
            "marketing_canon": "Maven CANON content",
            "content_bible": "Maven BIBLE content",
            "video_production_bible": "Maven VIDEO content",
        }

    def _signal(self):
        return {
            "bravo": {"session_note": "Shipped feature X", "recent_shipped": ["A", "B"]},
            "atlas": {"session_note": "Reviewed Q2 spend"},
            "aura":  {"session_note": "CC in deep work mode"},
        }

    def test_includes_all_foundation_blocks(self):
        prompt = script_ideation.build_prompt(
            foundation=self._foundation(),
            signal=self._signal(),
            count=10, pillar="any", fmt="short_video", topic=None,
        )
        for marker in ["SOUL", "WRITING", "CANON", "BIBLE", "VIDEO PRODUCTION BIBLE"]:
            self.assertIn(marker, prompt, f"missing section {marker}")

    def test_includes_spec_values(self):
        prompt = script_ideation.build_prompt(
            foundation=self._foundation(),
            signal=self._signal(),
            count=15, pillar="ceo_log", fmt="short_video",
            topic="Bennett rev share",
        )
        self.assertIn("Count: 15", prompt)
        self.assertIn("ceo_log", prompt)
        self.assertIn("short_video", prompt)
        self.assertIn("Bennett rev share", prompt)

    def test_includes_sibling_pulse_summaries(self):
        prompt = script_ideation.build_prompt(
            foundation=self._foundation(),
            signal=self._signal(),
            count=10, pillar="any", fmt="any", topic=None,
        )
        self.assertIn("Shipped feature X", prompt)
        self.assertIn("Reviewed Q2 spend", prompt)
        self.assertIn("CC in deep work mode", prompt)

    def test_handles_missing_pulse_signal_gracefully(self):
        prompt = script_ideation.build_prompt(
            foundation=self._foundation(),
            signal={"bravo": None, "atlas": None, "aura": None},
            count=5, pillar="any", fmt="any", topic=None,
        )
        self.assertIn("CURRENT BUSINESS / LIFE SIGNAL", prompt)
        # No crash — empty signal block is OK

    def test_output_format_block_present(self):
        prompt = script_ideation.build_prompt(
            foundation=self._foundation(),
            signal=self._signal(),
            count=10, pillar="any", fmt="any", topic=None,
        )
        self.assertIn("OUTPUT FORMAT", prompt)
        self.assertIn("Hook", prompt)
        self.assertIn("Beat sheet", prompt)
        self.assertIn("CTA", prompt)


# ============================================================================
# Claude API call (mocked — no network, no credits)
# ============================================================================

class TestCallClaude(unittest.TestCase):

    def test_passes_model_and_prompt_correctly(self):
        fake_client = _FakeAnthropicClient(api_key="test-key")
        # Patch the import inside call_claude
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with mock.patch("anthropic.Anthropic", return_value=fake_client):
                env = {"ANTHROPIC_API_KEY": "test-key"}
                result = script_ideation.call_claude("test prompt", env)
        self.assertIn("Mock idea", result)
        self.assertEqual(fake_client.captured["max_tokens"], 4000)
        self.assertEqual(fake_client.captured["messages"][0]["content"], "test prompt")

    def test_uses_default_model_when_env_unset(self):
        fake_client = _FakeAnthropicClient()
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            os.environ.pop("CLAUDE_MODEL", None)
            with mock.patch("anthropic.Anthropic", return_value=fake_client):
                script_ideation.call_claude("prompt", {"ANTHROPIC_API_KEY": "test-key"})
        # Default should be the current generation Sonnet
        self.assertTrue(fake_client.captured["model"].startswith("claude-sonnet-4"),
                        f"unexpected default model: {fake_client.captured['model']}")

    def test_env_override_for_model(self):
        fake_client = _FakeAnthropicClient()
        with mock.patch("anthropic.Anthropic", return_value=fake_client):
            env = {"ANTHROPIC_API_KEY": "test-key", "CLAUDE_MODEL": "claude-opus-4-7"}
            script_ideation.call_claude("prompt", env)
        self.assertEqual(fake_client.captured["model"], "claude-opus-4-7")

    def test_missing_api_key_exits(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                script_ideation.call_claude("prompt", {})


# ============================================================================
# Output writer
# ============================================================================

class TestSaveRun(unittest.TestCase):

    def test_writes_to_data_ideation_with_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(script_ideation, "PROJECT_ROOT", Path(tmp)):
                out = script_ideation.save_run(
                    prompt="test prompt body",
                    response="### 1. Idea one\n",
                    meta={"count": 5, "pillar": "ceo_log",
                          "format": "short_video", "topic": None},
                )
            self.assertTrue(out.exists())
            content = out.read_text(encoding="utf-8")
            self.assertIn("count: 5", content)
            self.assertIn("pillar: ceo_log", content)
            self.assertIn("format: short_video", content)
            self.assertIn("Idea one", content)
            self.assertIn("Prompt that produced this run", content)

    def test_filename_is_iso_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(script_ideation, "PROJECT_ROOT", Path(tmp)):
                out = script_ideation.save_run(
                    prompt="p", response="r",
                    meta={"count": 1, "pillar": "any", "format": "any"},
                )
            stem = out.stem
            # YYYYMMDDTHHMMSSZ — 16 chars
            self.assertEqual(len(stem), 16)
            self.assertTrue(stem.endswith("Z"))


# ============================================================================
# CLI dispatch
# ============================================================================

class TestCLI(unittest.TestCase):
    """`generate` calls call_claude + save_run; `list` and `view` work on stored runs."""

    def test_list_returns_empty_when_no_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(script_ideation, "PROJECT_ROOT", Path(tmp)):
                import argparse
                args = argparse.Namespace(limit=10)
                # Capture stdout
                from io import StringIO
                buf = StringIO()
                with mock.patch("sys.stdout", buf):
                    script_ideation.cmd_list(args, output_json=False)
                self.assertIn("no ideation runs yet", buf.getvalue())

    def test_list_returns_runs_in_reverse_chrono(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data" / "ideation").mkdir(parents=True)
            (root / "data" / "ideation" / "20260101T000000Z.md").write_text("a")
            (root / "data" / "ideation" / "20260601T000000Z.md").write_text("b")
            (root / "data" / "ideation" / "20260301T000000Z.md").write_text("c")
            with mock.patch.object(script_ideation, "PROJECT_ROOT", root):
                import argparse
                args = argparse.Namespace(limit=10)
                from io import StringIO
                buf = StringIO()
                with mock.patch("sys.stdout", buf):
                    script_ideation.cmd_list(args, output_json=True)
                payload = json.loads(buf.getvalue())
                self.assertEqual(payload["runs"],
                                 ["20260601T000000Z", "20260301T000000Z",
                                  "20260101T000000Z"])

    def test_view_missing_timestamp_exits(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(script_ideation, "PROJECT_ROOT", Path(tmp)):
                import argparse
                args = argparse.Namespace(timestamp="20260101T000000Z")
                with self.assertRaises(SystemExit):
                    script_ideation.cmd_view(args, output_json=False)


# ============================================================================
# Constant sanity
# ============================================================================

class TestConstants(unittest.TestCase):
    def test_pillar_options_includes_3_daily_pillars(self):
        for required in ["sobriety_log", "quote_drop", "ceo_log", "any"]:
            self.assertIn(required, script_ideation.PILLAR_OPTIONS)

    def test_format_options_includes_video_formats(self):
        for required in ["short_video", "long_video", "carousel", "thread", "any"]:
            self.assertIn(required, script_ideation.FORMAT_OPTIONS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
