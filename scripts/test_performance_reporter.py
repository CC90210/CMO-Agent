"""
Tests for performance_reporter math helpers — verify _safe_float, _lead_count,
_cost_per_lead on synthetic Meta-shape data with KNOWN answers.

Also verifies derived ROAS = revenue / spend on a controlled fixture.

Run:
  python scripts/test_performance_reporter.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _import_reporter_fresh():
    import importlib
    for m in [m for m in list(sys.modules) if m.startswith("performance_reporter")]:
        del sys.modules[m]
    import performance_reporter
    importlib.reload(performance_reporter)
    return performance_reporter


class TestPerformanceReporterMath(unittest.TestCase):

    def setUp(self):
        self.pr = _import_reporter_fresh()

    def test_01_safe_float_handles_none(self):
        self.assertEqual(self.pr._safe_float(None), 0.0)

    def test_02_safe_float_handles_empty_string(self):
        self.assertEqual(self.pr._safe_float(""), 0.0)

    def test_03_safe_float_parses_string_number(self):
        self.assertEqual(self.pr._safe_float("123.45"), 123.45)

    def test_04_lead_count_meta_lead_action(self):
        actions = [
            {"action_type": "link_click", "value": "100"},
            {"action_type": "lead", "value": "12"},
        ]
        self.assertEqual(self.pr._lead_count(actions), 12)

    def test_05_lead_count_onsite_conversion(self):
        actions = [{"action_type": "onsite_conversion.lead_grouped", "value": "7"}]
        self.assertEqual(self.pr._lead_count(actions), 7)

    def test_06_lead_count_empty(self):
        self.assertEqual(self.pr._lead_count([]), 0)
        self.assertEqual(self.pr._lead_count(None), 0)

    def test_07_cpl_extracted(self):
        cpa = [{"action_type": "lead", "value": "8.33"}]
        self.assertEqual(self.pr._cost_per_lead(cpa), 8.33)

    def test_08_cpl_missing_returns_none(self):
        cpa = [{"action_type": "link_click", "value": "0.50"}]
        self.assertIsNone(self.pr._cost_per_lead(cpa))

    def test_09_synthetic_roas_known_answer(self):
        # Synthetic insights row: spend=$100, 10 leads, $50 avg LTV
        # → CPL = $10, ROAS = $500 revenue / $100 spend = 5.0x
        synthetic_row = {
            "spend": "100.00",
            "actions": [{"action_type": "lead", "value": "10"}],
            "cost_per_action_type": [{"action_type": "lead", "value": "10.00"}],
        }
        spend = self.pr._safe_float(synthetic_row["spend"])
        leads = self.pr._lead_count(synthetic_row["actions"])
        cpl = self.pr._cost_per_lead(synthetic_row["cost_per_action_type"])
        avg_ltv = 50.0
        revenue = leads * avg_ltv
        roas = revenue / spend if spend else 0.0
        self.assertEqual(spend, 100.0)
        self.assertEqual(leads, 10)
        self.assertEqual(cpl, 10.0)
        self.assertEqual(revenue, 500.0)
        self.assertEqual(roas, 5.0)

    def test_10_zero_spend_safe(self):
        # ROAS-equivalent calculation must not divide by zero.
        synthetic_row = {"spend": "0", "actions": [], "cost_per_action_type": []}
        spend = self.pr._safe_float(synthetic_row["spend"])
        leads = self.pr._lead_count(synthetic_row["actions"])
        # Caller-side guard: zero spend → ROAS undefined, return 0 or None.
        roas = (leads * 50.0) / spend if spend > 0 else None
        self.assertEqual(spend, 0.0)
        self.assertIsNone(roas)


def _run_all(verbose=False):
    loader = unittest.TestLoader()
    suite = unittest.TestSuite([loader.loadTestsFromTestCase(TestPerformanceReporterMath)])
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
