"""
Tests for content_pipeline.generate_captions — verify per-platform character
limit enforcement (x=280, threads=500, instagram=2200, linkedin=3000,
tiktok=4000) so a long transcript never produces a caption over the
platform's hard limit.

Run:
  python scripts/test_content_pipeline.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _import_pipeline_fresh():
    import importlib
    for m in [m for m in list(sys.modules) if m.startswith("content_pipeline")]:
        del sys.modules[m]
    import content_pipeline
    importlib.reload(content_pipeline)
    return content_pipeline


class TestCaptionLimits(unittest.TestCase):

    def setUp(self):
        self.cp = _import_pipeline_fresh()
        # Generate captions from a long transcript so truncation is exercised
        # on every platform.
        long_transcript = "This is a long-form transcript about AI automation. " * 100
        self.captions = self.cp.generate_captions(long_transcript, topic="AI automation")

    def test_01_x_under_280(self):
        self.assertLessEqual(len(self.captions["x"]), 280, self.captions["x"])

    def test_02_threads_under_500(self):
        self.assertLessEqual(len(self.captions["threads"]), 500)

    def test_03_instagram_under_2200(self):
        self.assertLessEqual(len(self.captions["instagram"]), 2200)

    def test_04_linkedin_under_3000(self):
        self.assertLessEqual(len(self.captions["linkedin"]), 3000)

    def test_05_tiktok_under_4000(self):
        self.assertLessEqual(len(self.captions["tiktok"]), 4000)

    def test_06_youtube_shorts_under_100(self):
        self.assertLessEqual(len(self.captions["youtube_shorts"]), 100)

    def test_07_facebook_present(self):
        self.assertIn("facebook", self.captions)
        self.assertGreater(len(self.captions["facebook"]), 0)

    def test_08_threads_in_output(self):
        # Regression guard — V1.1 did not produce a threads key.
        self.assertIn("threads", self.captions)

    def test_09_x_assembly_no_overflow_on_short_input(self):
        # The prior bug: `base + " " + hashtags[:25]` could push past 280
        # when len(base) < 250. Verify with a short-but-near-cap base.
        captions = self.cp.generate_captions("a" * 240, topic="AI automation")
        self.assertLessEqual(len(captions["x"]), 280)

    def test_10_empty_transcript_safe(self):
        captions = self.cp.generate_captions("", topic=None)
        for plat, text in captions.items():
            self.assertLessEqual(len(text), self.cp.PLATFORM_CAPTION_LIMITS[plat])


def _run_all(verbose=False):
    loader = unittest.TestLoader()
    suite = unittest.TestSuite([loader.loadTestsFromTestCase(TestCaptionLimits)])
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
