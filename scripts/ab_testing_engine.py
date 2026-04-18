# -*- coding: utf-8 -*-
"""
SunBiz Funding - A/B Testing & Budget Optimization Engine
==========================================================
Bayesian optimization via Facebook's Ax platform (ax-platform).
Falls back to heuristic-based optimization when ax-platform is not installed.

Capabilities:
  - Budget allocation across campaigns (Bayesian or weighted-score heuristic)
  - Creative test suggestion (Thompson sampling or round-robin fallback)
  - Statistical significance testing (z-test for proportions)
  - Actionable optimization recommendations (pause/scale/test)

Dependencies (optional — fallback activates automatically):
    pip install ax-platform torch

Usage:
    from scripts.ab_testing_engine import ABTestingEngine

    engine = ABTestingEngine()
    recs = engine.get_optimization_recommendations(campaigns_data)
"""

from __future__ import annotations

import io
import logging
import math
import random
import sys
from dataclasses import dataclass, field
from typing import Optional

# Ensure UTF-8 output on Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("ab_testing_engine")

# ---------------------------------------------------------------------------
# Ax availability check — graceful degradation
# ---------------------------------------------------------------------------

try:
    from ax.api.client import Client as AxClient
    from ax.api.configs import RangeParameterConfig

    AX_AVAILABLE = True
    log.info("ax-platform detected — Bayesian optimization enabled.")
except ImportError:
    AX_AVAILABLE = False
    log.warning(
        "ax-platform not installed. Using heuristic optimization. "
        "Install with: pip install ax-platform"
    )

# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass
class CampaignMetrics:
    """Snapshot of a single campaign's performance metrics."""

    campaign_id: str
    name: str
    spend: float                   # USD, total spend
    impressions: int
    clicks: int
    conversions: int
    ctr: float                     # click-through rate (0–1)
    cpc: float                     # cost per click (USD)
    conversion_rate: float         # conversions / clicks (0–1)
    cost_per_lead: float           # USD
    current_budget: float          # daily budget (USD)


@dataclass
class BudgetRecommendation:
    """Recommended budget for a single campaign."""

    campaign_id: str
    name: str
    current_budget: float
    recommended_budget: float
    change_pct: float              # positive = increase, negative = decrease
    rationale: str


@dataclass
class CreativeSuggestion:
    """Next creative variant to test."""

    headline: str
    description: str
    image_key: str
    rationale: str
    priority: int                  # 1 = highest priority


@dataclass
class SignificanceResult:
    """Statistical significance test result."""

    is_significant: bool
    p_value: float
    confidence_pct: float
    winner: str                    # "control", "variant", or "inconclusive"
    lift_pct: float                # variant lift over control (conversion rate)
    recommendation: str


@dataclass
class OptimizationRecommendation:
    """A single actionable recommendation for a campaign."""

    campaign_id: str
    name: str
    action: str                    # "pause", "scale", "test", "monitor", "optimize_bid"
    reason: str
    priority: int                  # 1 = urgent, 2 = important, 3 = low
    suggested_budget_change_pct: Optional[float] = None
    suggested_test: Optional[CreativeSuggestion] = None


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------


class ABTestingEngine:
    """
    A/B Testing & Budget Optimization Engine for SunBiz Funding campaigns.

    Uses Bayesian optimization (Ax) when available; falls back to
    heuristic scoring when ax-platform is not installed.
    """

    # Thresholds for recommendation logic
    _PAUSE_THRESHOLD_CPL = 150.0       # cost-per-lead above this -> pause candidate
    _SCALE_THRESHOLD_CPL = 40.0        # cost-per-lead below this -> scale candidate
    _MIN_SPEND_FOR_SIGNAL = 20.0       # minimum spend before acting ($)
    _MIN_IMPRESSIONS_FOR_SIGNAL = 500  # minimum impressions before acting
    _SIGNIFICANCE_LEVEL = 0.95         # 95 % confidence required

    def __init__(self) -> None:
        self._ax_client: Optional[AxClient] = None if not AX_AVAILABLE else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def optimize_budget_allocation(
        self,
        campaigns: list[CampaignMetrics],
        total_budget: float,
    ) -> list[BudgetRecommendation]:
        """
        Recommend how to redistribute *total_budget* across campaigns.

        Uses Bayesian optimization (Ax) when available; otherwise applies a
        weighted-score heuristic based on CTR, CPC, and conversion rate.

        Args:
            campaigns:    List of CampaignMetrics with current performance data.
            total_budget: Total daily budget pool to allocate (USD).

        Returns:
            List of BudgetRecommendation, one per campaign.
        """
        if not campaigns:
            return []

        if AX_AVAILABLE:
            return self._optimize_budget_ax(campaigns, total_budget)
        return self._optimize_budget_heuristic(campaigns, total_budget)

    def suggest_creative_test(
        self,
        base_creative: dict,
        variations: list[dict],
        prior_results: Optional[list[dict]] = None,
    ) -> CreativeSuggestion:
        """
        Suggest which creative variation to test next.

        Uses Thompson sampling when Ax is available; otherwise selects the
        least-tested variation (exploration-first round-robin).

        Args:
            base_creative:  Dict with keys: headline, description, image_key.
            variations:     List of dicts with keys: headline, description,
                            image_key.  Each may also carry 'impressions' and
                            'conversions' from prior runs.
            prior_results:  Optional list of past test dicts with keys:
                            variant_index, conversions, impressions.

        Returns:
            CreativeSuggestion for the next test to run.
        """
        if not variations:
            return CreativeSuggestion(
                headline=base_creative.get("headline", ""),
                description=base_creative.get("description", ""),
                image_key=base_creative.get("image_key", ""),
                rationale="No variations provided — retesting base creative.",
                priority=3,
            )

        if AX_AVAILABLE and prior_results:
            return self._suggest_creative_ax(base_creative, variations, prior_results)
        return self._suggest_creative_heuristic(variations, prior_results)

    def analyze_test_results(
        self,
        control_metrics: dict,
        variant_metrics: dict,
    ) -> SignificanceResult:
        """
        Two-proportion z-test: is the variant's conversion rate significantly
        different from the control?

        Args:
            control_metrics: Dict with keys: impressions (int), conversions (int).
            variant_metrics: Dict with keys: impressions (int), conversions (int).

        Returns:
            SignificanceResult with p_value, confidence, winner, and recommendation.
        """
        n_c = int(control_metrics.get("impressions", 0))
        x_c = int(control_metrics.get("conversions", 0))
        n_v = int(variant_metrics.get("impressions", 0))
        x_v = int(variant_metrics.get("conversions", 0))

        if n_c == 0 or n_v == 0:
            return SignificanceResult(
                is_significant=False,
                p_value=1.0,
                confidence_pct=0.0,
                winner="inconclusive",
                lift_pct=0.0,
                recommendation="Insufficient data — gather at least 500 impressions per variant.",
            )

        p_c = x_c / n_c
        p_v = x_v / n_v
        p_pool = (x_c + x_v) / (n_c + n_v)

        # Avoid division by zero when pooled rate is 0 or 1
        if p_pool in (0.0, 1.0):
            return SignificanceResult(
                is_significant=False,
                p_value=1.0,
                confidence_pct=0.0,
                winner="inconclusive",
                lift_pct=0.0,
                recommendation="No conversions recorded in either variant yet.",
            )

        se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_c + 1 / n_v))
        z = (p_v - p_c) / se if se > 0 else 0.0

        # Approximate two-tailed p-value from z-score
        p_value = 2 * (1 - _norm_cdf(abs(z)))
        confidence_pct = (1 - p_value) * 100

        lift_pct = ((p_v - p_c) / p_c * 100) if p_c > 0 else 0.0
        is_significant = confidence_pct >= (self._SIGNIFICANCE_LEVEL * 100)

        if not is_significant:
            winner = "inconclusive"
            recommendation = (
                f"Results not yet significant ({confidence_pct:.1f}% confidence). "
                "Continue the test — aim for 95% confidence before deciding."
            )
        elif p_v > p_c:
            winner = "variant"
            recommendation = (
                f"Variant wins with {confidence_pct:.1f}% confidence "
                f"({lift_pct:+.1f}% lift). Deploy the variant and pause control."
            )
        else:
            winner = "control"
            recommendation = (
                f"Control wins with {confidence_pct:.1f}% confidence "
                f"({abs(lift_pct):.1f}% drop for variant). Keep control, discard variant."
            )

        return SignificanceResult(
            is_significant=is_significant,
            p_value=round(p_value, 4),
            confidence_pct=round(confidence_pct, 2),
            winner=winner,
            lift_pct=round(lift_pct, 2),
            recommendation=recommendation,
        )

    def get_optimization_recommendations(
        self,
        campaigns_data: list[dict],
    ) -> list[OptimizationRecommendation]:
        """
        Analyze all campaign data and return prioritized, actionable recommendations.

        Recommendations cover:
          - Pausing underperformers (high CPL, low CTR)
          - Scaling winners (low CPL, good CTR)
          - Suggesting A/B tests for mid-tier campaigns
          - Flagging campaigns with insufficient data

        Args:
            campaigns_data: List of dicts.  Each dict must contain at minimum:
                campaign_id, name, spend, impressions, clicks, conversions,
                ctr, cpc, conversion_rate, cost_per_lead, current_budget.

        Returns:
            List of OptimizationRecommendation sorted by priority (ascending).
        """
        recommendations: list[OptimizationRecommendation] = []

        for raw in campaigns_data:
            metrics = _dict_to_metrics(raw)
            rec = self._evaluate_campaign(metrics)
            if rec:
                recommendations.append(rec)

        # Sort by priority then by cost_per_lead desc (worst first)
        recommendations.sort(key=lambda r: r.priority)
        return recommendations

    # ------------------------------------------------------------------
    # Budget allocation — Ax (Bayesian) path
    # ------------------------------------------------------------------

    def _optimize_budget_ax(
        self,
        campaigns: list[CampaignMetrics],
        total_budget: float,
    ) -> list[BudgetRecommendation]:
        """
        Use Ax's SOBOL + GPEI loop to find the budget split that minimises
        blended cost-per-lead across campaigns.
        """
        try:
            ax_client = AxClient()

            # Define one parameter per campaign: fraction of total_budget (0.05–0.80)
            param_configs = [
                RangeParameterConfig(
                    name=f"budget_{c.campaign_id}",
                    bounds=(0.05, 0.80),
                    parameter_type="float",
                )
                for c in campaigns
            ]

            ax_client.configure_experiment(parameters=param_configs, name="budget_allocation")
            # Minimise blended CPL — the "-" prefix signals minimisation in the new API
            ax_client.configure_optimization(objective="-blended_cpl")

            # Run a lightweight 10-trial optimization loop
            for _ in range(10):
                # get_next_trials returns {trial_index: params_dict}
                trial_map = ax_client.get_next_trials(max_trials=1)
                if not trial_map:
                    break
                trial_index, trial_params = next(iter(trial_map.items()))

                # Normalise fractions so they sum to 1
                total_fraction = sum(trial_params.values()) or 1.0  # type: ignore[arg-type]
                normalised = {k: v / total_fraction for k, v in trial_params.items()}  # type: ignore[union-attr]

                # Simulate blended CPL for this allocation
                blended_cpl = _simulate_blended_cpl(campaigns, normalised, total_budget)

                ax_client.complete_trial(
                    trial_index=trial_index,
                    raw_data={"blended_cpl": blended_cpl},
                )

            # get_best_parameterization returns (params, values, trial_index, model_key)
            best_params, _values, _trial_idx, _model_key = ax_client.get_best_parameterization()

            # Normalise best params
            total_fraction = sum(best_params.values()) or 1.0  # type: ignore[arg-type]
            normalised_best = {k: v / total_fraction for k, v in best_params.items()}  # type: ignore[union-attr]

            return _build_budget_recs(campaigns, normalised_best, total_budget, method="Bayesian (Ax)")

        except Exception as exc:  # pylint: disable=broad-except
            log.warning("Ax optimization failed (%s) — falling back to heuristic.", exc)
            return self._optimize_budget_heuristic(campaigns, total_budget)

    # ------------------------------------------------------------------
    # Budget allocation — heuristic path
    # ------------------------------------------------------------------

    def _optimize_budget_heuristic(
        self,
        campaigns: list[CampaignMetrics],
        total_budget: float,
    ) -> list[BudgetRecommendation]:
        """
        Weighted-score heuristic:
          score = (CTR_weight × ctr) + (CPC_weight × 1/cpc) + (CVR_weight × conversion_rate)

        Campaigns with no spend receive a minimum floor allocation (5 %).
        """
        scores: dict[str, float] = {}
        for c in campaigns:
            ctr_score = c.ctr * 40.0
            cpc_score = (1.0 / c.cpc * 10.0) if c.cpc > 0 else 0.0
            cvr_score = c.conversion_rate * 50.0
            scores[c.campaign_id] = max(ctr_score + cpc_score + cvr_score, 0.01)

        total_score = sum(scores.values()) or 1.0
        fractions = {cid: s / total_score for cid, s in scores.items()}
        id_map = {c.campaign_id: f"budget_{c.campaign_id}" for c in campaigns}
        normalised = {f"budget_{cid}": frac for cid, frac in fractions.items()}
        return _build_budget_recs(campaigns, normalised, total_budget, method="Heuristic (weighted score)")

    # ------------------------------------------------------------------
    # Creative suggestion — Ax (Thompson sampling) path
    # ------------------------------------------------------------------

    def _suggest_creative_ax(
        self,
        base_creative: dict,
        variations: list[dict],
        prior_results: list[dict],
    ) -> CreativeSuggestion:
        """
        Thompson sampling: pick the arm with the highest sampled conversion rate
        from a Beta(alpha, beta) posterior.
        """
        try:
            # Build Beta posteriors: alpha = conversions+1, beta = failures+1
            posteriors: list[tuple[float, float]] = []
            for i, _ in enumerate(variations):
                conversions = 0
                impressions = 0
                for result in prior_results:
                    if result.get("variant_index") == i:
                        conversions += result.get("conversions", 0)
                        impressions += result.get("impressions", 0)
                alpha = conversions + 1
                beta_param = max(impressions - conversions, 0) + 1
                posteriors.append((alpha, beta_param))

            # Sample from each Beta posterior and pick the best
            samples = [random.betavariate(a, b) for a, b in posteriors]
            best_idx = samples.index(max(samples))
            chosen = variations[best_idx]

            return CreativeSuggestion(
                headline=chosen.get("headline", ""),
                description=chosen.get("description", ""),
                image_key=chosen.get("image_key", ""),
                rationale=(
                    f"Thompson sampling selected variation {best_idx} "
                    f"(sampled CVR: {samples[best_idx]:.4f})."
                ),
                priority=1,
            )
        except Exception as exc:  # pylint: disable=broad-except
            log.warning("Thompson sampling failed (%s) — using round-robin.", exc)
            return self._suggest_creative_heuristic(variations, prior_results)

    # ------------------------------------------------------------------
    # Creative suggestion — heuristic path
    # ------------------------------------------------------------------

    def _suggest_creative_heuristic(
        self,
        variations: list[dict],
        prior_results: Optional[list[dict]],
    ) -> CreativeSuggestion:
        """Pick the least-tested variation (minimum impressions seen so far)."""
        impression_counts: dict[int, int] = {i: 0 for i in range(len(variations))}
        if prior_results:
            for result in prior_results:
                idx = result.get("variant_index", -1)
                if idx in impression_counts:
                    impression_counts[idx] += result.get("impressions", 0)

        least_tested_idx = min(impression_counts, key=impression_counts.get)  # type: ignore[arg-type]
        chosen = variations[least_tested_idx]

        return CreativeSuggestion(
            headline=chosen.get("headline", ""),
            description=chosen.get("description", ""),
            image_key=chosen.get("image_key", ""),
            rationale=(
                f"Exploration: variation {least_tested_idx} has the fewest impressions "
                f"({impression_counts[least_tested_idx]}) — prioritising data collection."
            ),
            priority=2,
        )

    # ------------------------------------------------------------------
    # Campaign evaluation
    # ------------------------------------------------------------------

    def _evaluate_campaign(
        self,
        metrics: CampaignMetrics,
    ) -> Optional[OptimizationRecommendation]:
        """Evaluate a single campaign and return a recommendation if warranted."""

        insufficient_data = (
            metrics.spend < self._MIN_SPEND_FOR_SIGNAL
            or metrics.impressions < self._MIN_IMPRESSIONS_FOR_SIGNAL
        )

        if insufficient_data:
            return OptimizationRecommendation(
                campaign_id=metrics.campaign_id,
                name=metrics.name,
                action="monitor",
                reason=(
                    f"Insufficient data (spend: ${metrics.spend:.2f}, "
                    f"impressions: {metrics.impressions:,}). "
                    "Gather more data before acting — minimum $20 spend and 500 impressions."
                ),
                priority=3,
            )

        if metrics.cost_per_lead > self._PAUSE_THRESHOLD_CPL:
            return OptimizationRecommendation(
                campaign_id=metrics.campaign_id,
                name=metrics.name,
                action="pause",
                reason=(
                    f"Cost per lead ${metrics.cost_per_lead:.2f} exceeds pause threshold "
                    f"(${self._PAUSE_THRESHOLD_CPL:.0f}). "
                    "Pausing prevents further budget waste."
                ),
                priority=1,
                suggested_budget_change_pct=-100.0,
            )

        if metrics.cost_per_lead <= self._SCALE_THRESHOLD_CPL and metrics.ctr > 0.01:
            return OptimizationRecommendation(
                campaign_id=metrics.campaign_id,
                name=metrics.name,
                action="scale",
                reason=(
                    f"Strong performer: CPL ${metrics.cost_per_lead:.2f}, "
                    f"CTR {metrics.ctr * 100:.2f}%. "
                    "Increase budget by 20–30% while CPL holds."
                ),
                priority=1,
                suggested_budget_change_pct=25.0,
            )

        if metrics.ctr < 0.005:
            test_suggestion = CreativeSuggestion(
                headline="Grow Your Business with Working Capital",
                description="See if you qualify for up to $500K in business funding. Apply now.",
                image_key="growth_capital_hero",
                rationale="Low CTR suggests creative fatigue — test a new headline and image.",
                priority=1,
            )
            return OptimizationRecommendation(
                campaign_id=metrics.campaign_id,
                name=metrics.name,
                action="test",
                reason=(
                    f"Low CTR ({metrics.ctr * 100:.2f}%) indicates creative fatigue or "
                    "poor audience-message alignment. Test fresh creative variants."
                ),
                priority=2,
                suggested_test=test_suggestion,
            )

        # Mid-tier: monitor or minor bid adjustment
        return OptimizationRecommendation(
            campaign_id=metrics.campaign_id,
            name=metrics.name,
            action="optimize_bid",
            reason=(
                f"Mid-tier performance: CPL ${metrics.cost_per_lead:.2f}, "
                f"CTR {metrics.ctr * 100:.2f}%. "
                "Consider tightening bid cap by 10% to improve efficiency."
            ),
            priority=3,
            suggested_budget_change_pct=-10.0,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _norm_cdf(z: float) -> float:
    """Approximate standard normal CDF using the Abramowitz & Stegun method."""
    # Abramowitz & Stegun approximation — accurate to ~7 decimal places
    if z < 0:
        return 1.0 - _norm_cdf(-z)
    k = 1.0 / (1.0 + 0.2316419 * z)
    poly = k * (
        0.319381530
        + k * (-0.356563782 + k * (1.781477937 + k * (-1.821255978 + k * 1.330274429)))
    )
    return 1.0 - (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z * z) * poly


def _simulate_blended_cpl(
    campaigns: list[CampaignMetrics],
    normalised_fractions: dict[str, float],
    total_budget: float,
) -> float:
    """
    Estimate blended CPL for a given budget allocation.
    Assumes CPL is inversely proportional to budget (more spend -> more leads
    via higher bids and reach) with diminishing returns modelled as sqrt.
    """
    total_leads = 0.0
    for c in campaigns:
        key = f"budget_{c.campaign_id}"
        frac = normalised_fractions.get(key, 0.0)
        allocated = frac * total_budget
        # Simple model: leads ≈ sqrt(allocated) * baseline_conversion_signal
        baseline = (c.conversions / c.spend) if c.spend > 0 else 0.01
        leads = math.sqrt(max(allocated, 0.0)) * baseline
        total_leads += leads

    return total_budget / total_leads if total_leads > 0 else 9999.0


def _build_budget_recs(
    campaigns: list[CampaignMetrics],
    normalised: dict[str, float],
    total_budget: float,
    method: str,
) -> list[BudgetRecommendation]:
    """Convert a normalised fraction map into BudgetRecommendation objects."""
    recs: list[BudgetRecommendation] = []
    for c in campaigns:
        key = f"budget_{c.campaign_id}"
        frac = normalised.get(key, 1.0 / len(campaigns))
        recommended = round(frac * total_budget, 2)
        change_pct = (
            ((recommended - c.current_budget) / c.current_budget * 100)
            if c.current_budget > 0
            else 0.0
        )
        direction = "increase" if change_pct >= 0 else "decrease"
        recs.append(
            BudgetRecommendation(
                campaign_id=c.campaign_id,
                name=c.name,
                current_budget=c.current_budget,
                recommended_budget=recommended,
                change_pct=round(change_pct, 1),
                rationale=(
                    f"{method}: {direction} daily budget by {abs(change_pct):.1f}% "
                    f"(${c.current_budget:.2f} -> ${recommended:.2f})."
                ),
            )
        )
    return recs


def _dict_to_metrics(raw: dict) -> CampaignMetrics:
    """Safely coerce a raw dict into a CampaignMetrics object."""
    impressions = int(raw.get("impressions", 0))
    clicks = int(raw.get("clicks", 0))
    conversions = int(raw.get("conversions", 0))
    spend = float(raw.get("spend", 0.0))

    ctr = float(raw.get("ctr", clicks / impressions if impressions > 0 else 0.0))
    cpc = float(raw.get("cpc", spend / clicks if clicks > 0 else 0.0))
    conversion_rate = float(
        raw.get("conversion_rate", conversions / clicks if clicks > 0 else 0.0)
    )
    cost_per_lead = float(
        raw.get("cost_per_lead", spend / conversions if conversions > 0 else 9999.0)
    )

    return CampaignMetrics(
        campaign_id=str(raw.get("campaign_id", "unknown")),
        name=str(raw.get("name", "Unknown Campaign")),
        spend=spend,
        impressions=impressions,
        clicks=clicks,
        conversions=conversions,
        ctr=ctr,
        cpc=cpc,
        conversion_rate=conversion_rate,
        cost_per_lead=cost_per_lead,
        current_budget=float(raw.get("current_budget", 0.0)),
    )


# ---------------------------------------------------------------------------
# Standalone demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    engine = ABTestingEngine()

    # ------------------------------------------------------------------
    # Sample campaign data
    # ------------------------------------------------------------------
    sample_campaigns = [
        {
            "campaign_id": "camp_001",
            "name": "Growth Capital — Broad US",
            "spend": 420.50,
            "impressions": 52000,
            "clicks": 780,
            "conversions": 14,
            "ctr": 0.015,
            "cpc": 0.54,
            "conversion_rate": 0.018,
            "cost_per_lead": 30.04,
            "current_budget": 50.00,
        },
        {
            "campaign_id": "camp_002",
            "name": "Consolidation — Restaurant Owners",
            "spend": 310.00,
            "impressions": 38000,
            "clicks": 190,
            "conversions": 2,
            "ctr": 0.005,
            "cpc": 1.63,
            "conversion_rate": 0.011,
            "cost_per_lead": 155.00,
            "current_budget": 40.00,
        },
        {
            "campaign_id": "camp_003",
            "name": "Fast Funding — Retail",
            "spend": 95.00,
            "impressions": 8200,
            "clicks": 210,
            "conversions": 5,
            "ctr": 0.026,
            "cpc": 0.45,
            "conversion_rate": 0.024,
            "cost_per_lead": 19.00,
            "current_budget": 30.00,
        },
    ]

    print("\n" + "=" * 60)
    print("  SunBiz Funding - A/B Testing Engine Demo")
    print("=" * 60)

    # Budget allocation
    print("\n--- Budget Allocation (total $120/day) ---")
    metrics_list = [_dict_to_metrics(c) for c in sample_campaigns]
    budget_recs = engine.optimize_budget_allocation(metrics_list, total_budget=120.0)
    for rec in budget_recs:
        print(f"  {rec.name}: {rec.rationale}")

    # Statistical significance
    print("\n--- A/B Test Significance ---")
    result = engine.analyze_test_results(
        control_metrics={"impressions": 2000, "conversions": 40},
        variant_metrics={"impressions": 2000, "conversions": 58},
    )
    print(f"  Winner: {result.winner}  |  Confidence: {result.confidence_pct}%")
    print(f"  Lift: {result.lift_pct:+.1f}%  |  p-value: {result.p_value}")
    print(f"  Recommendation: {result.recommendation}")

    # Creative suggestion
    print("\n--- Next Creative Test ---")
    base = {
        "headline": "Working Capital for Your Business",
        "description": "See if you qualify for funding.",
        "image_key": "hero_default",
    }
    variations = [
        {"headline": "Up to $500K for Your Business", "description": "No credit pull required. Apply today.", "image_key": "hero_v1"},
        {"headline": "Consolidate & Grow — Fast Approval", "description": "Private lending solutions tailored to you.", "image_key": "hero_v2"},
        {"headline": "Your Business Deserves Better Capital", "description": "Check your options in 60 seconds.", "image_key": "hero_v3"},
    ]
    prior = [
        {"variant_index": 0, "impressions": 1200, "conversions": 18},
        {"variant_index": 1, "impressions": 300, "conversions": 4},
    ]
    suggestion = engine.suggest_creative_test(base, variations, prior_results=prior)
    print(f"  Test next: \"{suggestion.headline}\"")
    print(f"  Rationale: {suggestion.rationale}")

    # Full optimization recommendations
    print("\n--- Optimization Recommendations ---")
    recs = engine.get_optimization_recommendations(sample_campaigns)
    for rec in recs:
        budget_note = (
            f"  Budget change: {rec.suggested_budget_change_pct:+.0f}%"
            if rec.suggested_budget_change_pct is not None
            else ""
        )
        print(f"  [{rec.action.upper()}] {rec.name} (priority {rec.priority})")
        print(f"    {rec.reason}{budget_note}")

    print("\n" + "=" * 60)
