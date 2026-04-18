"""
SunBiz Funding — Performance Reporter
========================================
Pulls Meta Ads performance data and formats it into clean human-readable
reports. Uses MetaAdsEngine for all API calls — no direct HTTP calls here.

Usage:
    from scripts.meta_ads_engine import MetaAdsEngine
    from scripts.performance_reporter import PerformanceReporter

    engine = MetaAdsEngine()
    reporter = PerformanceReporter(engine)
    print(reporter.generate_report_text())

Or standalone:
    python scripts/performance_reporter.py
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger("performance_reporter")

# ---------------------------------------------------------------------------
# Insight field defaults
# ---------------------------------------------------------------------------

_DEFAULT_FIELDS = [
    "campaign_name",
    "impressions",
    "reach",
    "clicks",
    "ctr",
    "cpc",
    "cpm",
    "spend",
    "actions",
    "cost_per_action_type",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_float(value: object, default: float = 0.0) -> float:
    """Convert a value to float without raising on None or empty string."""
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _lead_count(actions: list[dict]) -> int:
    """Extract lead count from Meta's actions array."""
    if not actions:
        return 0
    for action in actions:
        if action.get("action_type") in ("lead", "onsite_conversion.lead_grouped"):
            return int(_safe_float(action.get("value", 0)))
    return 0


def _cost_per_lead(cost_per_action: list[dict]) -> Optional[float]:
    """Extract cost-per-lead from Meta's cost_per_action_type array."""
    if not cost_per_action:
        return None
    for item in cost_per_action:
        if item.get("action_type") in ("lead", "onsite_conversion.lead_grouped"):
            return _safe_float(item.get("value"))
    return None


def _fmt_currency(value: float) -> str:
    return f"${value:,.2f}"


def _fmt_pct(value: float) -> str:
    return f"{value:.2f}%"


def _divider(width: int = 55) -> str:
    return "-" * width


def _header(title: str, width: int = 55) -> str:
    return f"{'=' * width}\n  {title}\n{'=' * width}"


# ---------------------------------------------------------------------------
# PerformanceReporter
# ---------------------------------------------------------------------------


class PerformanceReporter:
    """
    Generates formatted performance reports from Meta Ads data.

    All report methods return clean text strings — no JSON, no raw dicts.
    The generate_report_text() method bundles all reports into one output.
    """

    def __init__(self, engine) -> None:  # engine: MetaAdsEngine
        self.engine = engine

    # ------------------------------------------------------------------
    # Data fetchers
    # ------------------------------------------------------------------

    def _get_campaign_insights(self, date_preset: str) -> list[dict]:
        """
        Fetch account-level insights broken down by campaign.
        Returns a flat list of insight rows, each enriched with campaign metadata.
        """
        campaigns = self.engine.get_all_campaigns()
        if not campaigns:
            return []

        rows: list[dict] = []
        for campaign in campaigns:
            try:
                insights = self.engine.get_insights(
                    object_id=campaign["id"],
                    date_preset=date_preset,
                    fields=_DEFAULT_FIELDS,
                )
                if insights:
                    row = dict(insights[0])
                    # Enrich with campaign metadata not always in insight response
                    row.setdefault("campaign_name", campaign["name"])
                    row["campaign_id"] = campaign["id"]
                    row["campaign_status"] = campaign["status"]
                    row["daily_budget_usd"] = campaign.get("daily_budget_usd")
                    row["lifetime_budget_usd"] = campaign.get("lifetime_budget_usd")
                    rows.append(row)
                else:
                    # Campaign exists but has no data for this period
                    rows.append({
                        "campaign_name": campaign["name"],
                        "campaign_id": campaign["id"],
                        "campaign_status": campaign["status"],
                        "daily_budget_usd": campaign.get("daily_budget_usd"),
                        "lifetime_budget_usd": campaign.get("lifetime_budget_usd"),
                        "impressions": "0",
                        "clicks": "0",
                        "ctr": "0",
                        "cpc": "0",
                        "spend": "0",
                        "actions": [],
                        "cost_per_action_type": [],
                    })
            except RuntimeError as exc:
                log.warning("Could not fetch insights for campaign %s: %s", campaign["id"], exc)

        return rows

    # ------------------------------------------------------------------
    # Report methods
    # ------------------------------------------------------------------

    def daily_report(self) -> str:
        """Today's metrics across all campaigns."""
        rows = self._get_campaign_insights("today")
        if not rows:
            return "No campaign data available for today."

        lines = [_header("DAILY REPORT — " + _today_str())]
        for row in rows:
            lines.append(_divider())
            lines.append(f"  Campaign : {row.get('campaign_name', 'N/A')}")
            lines.append(f"  Status   : {row.get('campaign_status', 'N/A')}")
            lines.append(f"  Spend    : {_fmt_currency(_safe_float(row.get('spend', 0)))}")
            lines.append(f"  Impr.    : {int(_safe_float(row.get('impressions', 0))):,}")
            lines.append(f"  Clicks   : {int(_safe_float(row.get('clicks', 0))):,}")
            lines.append(f"  CTR      : {_fmt_pct(_safe_float(row.get('ctr', 0)))}")
            lines.append(f"  CPC      : {_fmt_currency(_safe_float(row.get('cpc', 0)))}")
            leads = _lead_count(row.get("actions", []))
            cpl = _cost_per_lead(row.get("cost_per_action_type", []))
            lines.append(f"  Leads    : {leads}")
            lines.append(f"  CPL      : {_fmt_currency(cpl) if cpl else 'N/A'}")
        lines.append("=" * 55)
        return "\n".join(lines)

    def campaign_comparison(self, date_preset: str = "last_7d") -> str:
        """Side-by-side comparison table of all campaigns."""
        rows = self._get_campaign_insights(date_preset)
        if not rows:
            return f"No campaign data available for {date_preset}."

        col_w = 22
        header_row = (
            f"  {'Campaign':<{col_w}} {'Spend':>8} {'Impr':>8} "
            f"{'Clicks':>7} {'CTR':>7} {'CPC':>7} {'Leads':>6}"
        )

        lines = [
            _header(f"CAMPAIGN COMPARISON — {date_preset.upper()}"),
            header_row,
            _divider(len(header_row)),
        ]

        for row in rows:
            name = str(row.get("campaign_name", ""))
            truncated_name = name[:col_w] if len(name) > col_w else name
            spend = _safe_float(row.get("spend", 0))
            impr = int(_safe_float(row.get("impressions", 0)))
            clicks = int(_safe_float(row.get("clicks", 0)))
            ctr = _safe_float(row.get("ctr", 0))
            cpc = _safe_float(row.get("cpc", 0))
            leads = _lead_count(row.get("actions", []))
            lines.append(
                f"  {truncated_name:<{col_w}} "
                f"{_fmt_currency(spend):>8} "
                f"{impr:>8,} "
                f"{clicks:>7,} "
                f"{_fmt_pct(ctr):>7} "
                f"{_fmt_currency(cpc):>7} "
                f"{leads:>6}"
            )

        lines.append("=" * 55)
        return "\n".join(lines)

    def top_performer(self, date_preset: str = "last_7d") -> str:
        """Identifies the best campaign by CTR and by CPC."""
        rows = self._get_campaign_insights(date_preset)
        active_rows = [
            r for r in rows
            if _safe_float(r.get("impressions", 0)) > 0
        ]
        if not active_rows:
            return f"No active campaign data for {date_preset}."

        best_ctr = max(active_rows, key=lambda r: _safe_float(r.get("ctr", 0)))
        # For CPC, lower is better — exclude zero CPC (no clicks)
        rows_with_cpc = [r for r in active_rows if _safe_float(r.get("cpc", 0)) > 0]
        best_cpc = (
            min(rows_with_cpc, key=lambda r: _safe_float(r.get("cpc", 0)))
            if rows_with_cpc else None
        )

        lines = [_header(f"TOP PERFORMERS — {date_preset.upper()}")]
        lines.append("")
        lines.append("  Best CTR:")
        lines.append(f"    Campaign : {best_ctr.get('campaign_name', 'N/A')}")
        lines.append(f"    CTR      : {_fmt_pct(_safe_float(best_ctr.get('ctr', 0)))}")
        lines.append(f"    Spend    : {_fmt_currency(_safe_float(best_ctr.get('spend', 0)))}")
        lines.append(f"    Clicks   : {int(_safe_float(best_ctr.get('clicks', 0))):,}")

        if best_cpc:
            lines.append("")
            lines.append("  Lowest CPC:")
            lines.append(f"    Campaign : {best_cpc.get('campaign_name', 'N/A')}")
            lines.append(f"    CPC      : {_fmt_currency(_safe_float(best_cpc.get('cpc', 0)))}")
            lines.append(f"    Spend    : {_fmt_currency(_safe_float(best_cpc.get('spend', 0)))}")
            lines.append(f"    Clicks   : {int(_safe_float(best_cpc.get('clicks', 0))):,}")

        leads_rows = [r for r in active_rows if _lead_count(r.get("actions", [])) > 0]
        if leads_rows:
            best_leads = max(leads_rows, key=lambda r: _lead_count(r.get("actions", [])))
            lines.append("")
            lines.append("  Most Leads:")
            lines.append(f"    Campaign : {best_leads.get('campaign_name', 'N/A')}")
            lines.append(f"    Leads    : {_lead_count(best_leads.get('actions', []))}")
            cpl = _cost_per_lead(best_leads.get("cost_per_action_type", []))
            lines.append(f"    CPL      : {_fmt_currency(cpl) if cpl else 'N/A'}")

        lines.append("=" * 55)
        return "\n".join(lines)

    def underperformers(
        self,
        threshold_ctr: float = 1.0,
        date_preset: str = "last_7d",
    ) -> str:
        """
        Flag campaigns below the CTR threshold that have enough impressions
        to be statistically relevant (>500 impressions).

        Args:
            threshold_ctr: CTR percentage floor (default 1.0%).
            date_preset: Date range to evaluate.

        Returns:
            Formatted text listing underperforming campaigns with suggestions.
        """
        rows = self._get_campaign_insights(date_preset)
        flagged = [
            r for r in rows
            if _safe_float(r.get("impressions", 0)) >= 500
            and _safe_float(r.get("ctr", 0)) < threshold_ctr
        ]

        lines = [_header(f"UNDERPERFORMERS — CTR < {threshold_ctr}% ({date_preset.upper()})")]
        if not flagged:
            lines.append(f"  No campaigns below {threshold_ctr}% CTR with 500+ impressions.")
        else:
            for row in flagged:
                lines.append(_divider())
                lines.append(f"  Campaign  : {row.get('campaign_name', 'N/A')}")
                lines.append(f"  CTR       : {_fmt_pct(_safe_float(row.get('ctr', 0)))} (threshold: {threshold_ctr}%)")
                lines.append(f"  Impr.     : {int(_safe_float(row.get('impressions', 0))):,}")
                lines.append(f"  Spend     : {_fmt_currency(_safe_float(row.get('spend', 0)))}")
                lines.append("  Actions   : Consider refreshing ad creative or adjusting copy.")
        lines.append("=" * 55)
        return "\n".join(lines)

    def budget_pacing(self, date_preset: str = "last_7d") -> str:
        """
        Shows spend vs budget for each campaign to identify over/under-pacing.
        Only campaigns with a known budget are evaluated.
        """
        rows = self._get_campaign_insights(date_preset)

        lines = [_header(f"BUDGET PACING — {date_preset.upper()}")]
        any_budget = False

        for row in rows:
            daily_budget = row.get("daily_budget_usd")
            lifetime_budget = row.get("lifetime_budget_usd")
            spend = _safe_float(row.get("spend", 0))

            if daily_budget is not None:
                budget_display = f"${daily_budget:.2f}/day"
                pacing_pct = (spend / daily_budget * 100) if daily_budget > 0 else 0
                any_budget = True
            elif lifetime_budget is not None:
                budget_display = f"${lifetime_budget:.2f} lifetime"
                pacing_pct = (spend / lifetime_budget * 100) if lifetime_budget > 0 else 0
                any_budget = True
            else:
                continue

            pacing_label = (
                "ON PACE" if 80 <= pacing_pct <= 120
                else "UNDER-PACING" if pacing_pct < 80
                else "OVER-PACING"
            )

            lines.append(_divider())
            lines.append(f"  Campaign : {row.get('campaign_name', 'N/A')}")
            lines.append(f"  Budget   : {budget_display}")
            lines.append(f"  Spend    : {_fmt_currency(spend)}")
            lines.append(f"  Pacing   : {pacing_pct:.1f}% — {pacing_label}")

        if not any_budget:
            lines.append("  No campaigns with budget data found.")
        lines.append("=" * 55)
        return "\n".join(lines)

    def generate_report_text(
        self,
        date_preset: str = "last_7d",
        ctr_threshold: float = 1.0,
    ) -> str:
        """
        Generate a full performance report bundling all report sections.

        Args:
            date_preset: Date range for all sections except daily_report.
            ctr_threshold: CTR floor for underperformer detection.

        Returns:
            Multi-section text report as a single string.
        """
        now_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        sections = [
            f"SUNBIZ FUNDING — META ADS PERFORMANCE REPORT",
            f"Generated: {now_str}",
            f"Period: {date_preset}",
            "",
            self.daily_report(),
            "",
            self.campaign_comparison(date_preset),
            "",
            self.top_performer(date_preset),
            "",
            self.underperformers(threshold_ctr=ctr_threshold, date_preset=date_preset),
            "",
            self.budget_pacing(date_preset),
        ]
        return "\n".join(sections)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _today_str() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Allow running from any working directory
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from scripts.meta_ads_engine import MetaAdsEngine  # noqa: E402 (local import after path fix)

    engine = MetaAdsEngine()
    reporter = PerformanceReporter(engine)
    report = reporter.generate_report_text()
    print(report)
