"""
Real-time campaign monitoring, anomaly detection, and alerting system.
=======================================================================
Wraps a MetaAdsEngine instance to provide scheduled health checks,
anomaly detection, budget pacing alerts, CTR/CPC deviation alerts,
disapproved-ad checks, and token-expiry warnings.

Standalone usage:
    python scripts/monitoring.py

Import usage:
    from scripts.monitoring import CampaignMonitor
    monitor = CampaignMonitor(engine)
    alerts = monitor.check_all_campaigns()
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("monitoring")

# ---------------------------------------------------------------------------
# Credential loading (mirrors meta_ads_engine.py pattern)
# ---------------------------------------------------------------------------


def _load_env_agents() -> dict[str, str]:
    """
    Parse KEY=VALUE pairs from .env.agents at the project root.
    Skips blank lines and comment lines.
    """
    env_path = Path(__file__).resolve().parent.parent / ".env.agents"
    if not env_path.exists():
        raise FileNotFoundError(
            f".env.agents not found at {env_path}. "
            "Copy .env.agents.template and fill in your credentials."
        )
    creds: dict[str, str] = {}
    with env_path.open(encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            creds[key.strip()] = value.strip()
    return creds


# ---------------------------------------------------------------------------
# Alert dataclass
# ---------------------------------------------------------------------------


@dataclass
class Alert:
    severity: str          # 'critical', 'warning', 'info'
    campaign_name: str
    metric: str
    message: str
    recommendation: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# CampaignMonitor
# ---------------------------------------------------------------------------


class CampaignMonitor:
    """
    Real-time health monitor for Meta Ads campaigns.

    All check methods return a (possibly empty) list of Alert objects.
    check_all_campaigns() runs every check and aggregates results.
    """

    def __init__(self, engine: object) -> None:
        """
        Args:
            engine: A MetaAdsEngine instance. Typed as object to avoid a
                    circular import; runtime behaviour relies on duck typing.
        """
        self.engine = engine

    # ------------------------------------------------------------------
    # Master runner
    # ------------------------------------------------------------------

    def check_all_campaigns(self) -> list[Alert]:
        """
        Run all health checks and return a combined list of alerts.
        Checks are run in order; failures in one check do not abort others.
        """
        alerts: list[Alert] = []

        checks: list[Callable[[], list[Alert]]] = [
            self.check_token_expiry,
            self.check_disapproved_ads,
            self.check_budget_pacing,
            self.check_ctr_drops,
            self.check_cpc_spikes,
        ]

        for check_fn in checks:
            try:
                results = check_fn()
                alerts.extend(results)
            except Exception as exc:  # noqa: BLE001 — intentional broad catch for monitoring resilience
                log.warning("Check %s raised an error: %s", check_fn.__name__, exc)
                alerts.append(
                    Alert(
                        severity="warning",
                        campaign_name="SYSTEM",
                        metric="check_error",
                        message=f"Health check '{check_fn.__name__}' failed: {exc}",
                        recommendation="Investigate the error in monitoring.py logs.",
                    )
                )

        log.info("check_all_campaigns complete — %d alert(s) generated.", len(alerts))
        return alerts

    # ------------------------------------------------------------------
    # Anomaly detection
    # ------------------------------------------------------------------

    def detect_anomalies(self, lookback_days: int = 7) -> list[Alert]:
        """
        Compare today's spend to the N-day rolling average.
        Flags any campaign that deviates by more than 30%.

        Args:
            lookback_days: Number of days to build the baseline average.

        Returns:
            List of Alert objects for anomalous campaigns.
        """
        alerts: list[Alert] = []
        campaigns = self.engine.get_all_campaigns()

        for campaign in campaigns:
            if campaign["status"] != "ACTIVE":
                continue

            try:
                today_rows = self.engine.get_insights(campaign["id"], date_preset="today")
                baseline_rows = self.engine.get_insights(
                    campaign["id"], date_preset=f"last_{lookback_days}d"
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("Could not fetch insights for campaign %s: %s", campaign["id"], exc)
                continue

            today_spend = _extract_spend(today_rows)
            baseline_spend = _extract_spend(baseline_rows)

            if baseline_spend == 0 or today_spend == 0:
                continue

            daily_avg = baseline_spend / lookback_days
            if daily_avg == 0:
                continue

            deviation_pct = abs(today_spend - daily_avg) / daily_avg * 100

            if deviation_pct > 30:
                direction = "above" if today_spend > daily_avg else "below"
                severity = "critical" if deviation_pct > 60 else "warning"
                alerts.append(
                    Alert(
                        severity=severity,
                        campaign_name=campaign["name"],
                        metric="spend_anomaly",
                        message=(
                            f"Today's spend ${today_spend:.2f} is {deviation_pct:.1f}% "
                            f"{direction} the {lookback_days}-day daily average "
                            f"${daily_avg:.2f}."
                        ),
                        recommendation=(
                            "Review campaign budget and bid settings. "
                            "Check for sudden audience or creative changes."
                        ),
                    )
                )

        return alerts

    # ------------------------------------------------------------------
    # Budget pacing
    # ------------------------------------------------------------------

    def check_budget_pacing(self) -> list[Alert]:
        """
        Check whether each active campaign is on pace with its daily budget.

        Alerts:
            - Underspending: <50% of expected spend at current time of day.
            - Overspending:  >120% of expected spend.

        Returns:
            List of Alert objects.
        """
        alerts: list[Alert] = []
        now = datetime.now(timezone.utc)
        fraction_of_day = (now.hour * 3600 + now.minute * 60 + now.second) / 86400
        if fraction_of_day == 0:
            fraction_of_day = 0.01  # avoid division by zero at midnight

        campaigns = self.engine.get_all_campaigns()

        for campaign in campaigns:
            if campaign["status"] != "ACTIVE":
                continue

            daily_budget = campaign.get("daily_budget_usd")
            if not daily_budget:
                continue  # lifetime-budget campaigns are not pacing-checked here

            try:
                rows = self.engine.get_insights(campaign["id"], date_preset="today")
            except Exception as exc:  # noqa: BLE001
                log.warning("Could not fetch today's insights for %s: %s", campaign["id"], exc)
                continue

            actual_spend = _extract_spend(rows)
            expected_spend = daily_budget * fraction_of_day

            if expected_spend == 0:
                continue

            pacing_ratio = actual_spend / expected_spend

            if pacing_ratio < 0.5:
                alerts.append(
                    Alert(
                        severity="warning",
                        campaign_name=campaign["name"],
                        metric="budget_pacing",
                        message=(
                            f"Underspending: ${actual_spend:.2f} actual vs "
                            f"${expected_spend:.2f} expected "
                            f"({pacing_ratio * 100:.1f}% of pace)."
                        ),
                        recommendation=(
                            "Check audience size, ad approval status, and bid competitiveness. "
                            "Consider widening targeting or increasing bids."
                        ),
                    )
                )
            elif pacing_ratio > 1.2:
                alerts.append(
                    Alert(
                        severity="critical",
                        campaign_name=campaign["name"],
                        metric="budget_pacing",
                        message=(
                            f"Overspending: ${actual_spend:.2f} actual vs "
                            f"${expected_spend:.2f} expected "
                            f"({pacing_ratio * 100:.1f}% of pace)."
                        ),
                        recommendation=(
                            "Review bid strategy and frequency caps. "
                            "Consider reducing daily budget or adding budget caps."
                        ),
                    )
                )

        return alerts

    # ------------------------------------------------------------------
    # CTR drops
    # ------------------------------------------------------------------

    def check_ctr_drops(self, threshold_pct: float = 30.0) -> list[Alert]:
        """
        Alert if a campaign's CTR dropped more than threshold_pct% vs yesterday.

        Args:
            threshold_pct: Percentage drop that triggers an alert.

        Returns:
            List of Alert objects.
        """
        alerts: list[Alert] = []
        campaigns = self.engine.get_all_campaigns()

        for campaign in campaigns:
            if campaign["status"] != "ACTIVE":
                continue

            try:
                today_rows = self.engine.get_insights(
                    campaign["id"],
                    date_preset="today",
                    fields=["impressions", "clicks", "ctr"],
                )
                yesterday_rows = self.engine.get_insights(
                    campaign["id"],
                    date_preset="yesterday",
                    fields=["impressions", "clicks", "ctr"],
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("Could not fetch CTR data for %s: %s", campaign["id"], exc)
                continue

            today_ctr = _extract_float(today_rows, "ctr")
            yesterday_ctr = _extract_float(yesterday_rows, "ctr")

            if yesterday_ctr == 0 or today_ctr == 0:
                continue

            drop_pct = (yesterday_ctr - today_ctr) / yesterday_ctr * 100

            if drop_pct >= threshold_pct:
                severity = "critical" if drop_pct >= 50 else "warning"
                alerts.append(
                    Alert(
                        severity=severity,
                        campaign_name=campaign["name"],
                        metric="ctr",
                        message=(
                            f"CTR dropped {drop_pct:.1f}%: "
                            f"today {today_ctr:.3f}% vs yesterday {yesterday_ctr:.3f}%."
                        ),
                        recommendation=(
                            "Refresh ad creative. Check for audience fatigue or ad disapprovals. "
                            "Review creative rotation settings."
                        ),
                    )
                )

        return alerts

    # ------------------------------------------------------------------
    # CPC spikes
    # ------------------------------------------------------------------

    def check_cpc_spikes(self, threshold_pct: float = 50.0) -> list[Alert]:
        """
        Alert if a campaign's CPC spiked more than threshold_pct% vs yesterday.

        Args:
            threshold_pct: Percentage increase that triggers an alert.

        Returns:
            List of Alert objects.
        """
        alerts: list[Alert] = []
        campaigns = self.engine.get_all_campaigns()

        for campaign in campaigns:
            if campaign["status"] != "ACTIVE":
                continue

            try:
                today_rows = self.engine.get_insights(
                    campaign["id"],
                    date_preset="today",
                    fields=["clicks", "spend", "cpc"],
                )
                yesterday_rows = self.engine.get_insights(
                    campaign["id"],
                    date_preset="yesterday",
                    fields=["clicks", "spend", "cpc"],
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("Could not fetch CPC data for %s: %s", campaign["id"], exc)
                continue

            today_cpc = _extract_float(today_rows, "cpc")
            yesterday_cpc = _extract_float(yesterday_rows, "cpc")

            if yesterday_cpc == 0 or today_cpc == 0:
                continue

            spike_pct = (today_cpc - yesterday_cpc) / yesterday_cpc * 100

            if spike_pct >= threshold_pct:
                severity = "critical" if spike_pct >= 100 else "warning"
                alerts.append(
                    Alert(
                        severity=severity,
                        campaign_name=campaign["name"],
                        metric="cpc",
                        message=(
                            f"CPC spiked {spike_pct:.1f}%: "
                            f"today ${today_cpc:.2f} vs yesterday ${yesterday_cpc:.2f}."
                        ),
                        recommendation=(
                            "Check auction competition. Review bid strategy and bid caps. "
                            "Evaluate audience overlap with other campaigns."
                        ),
                    )
                )

        return alerts

    # ------------------------------------------------------------------
    # Disapproved ads
    # ------------------------------------------------------------------

    def check_disapproved_ads(self) -> list[Alert]:
        """
        Scan all ads for DISAPPROVED effective_status.

        Returns:
            One Alert per disapproved ad found.
        """
        alerts: list[Alert] = []

        try:
            ads = self.engine.get_all_ads()
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not fetch ads for disapproval check: %s", exc)
            return alerts

        for ad in ads:
            if ad.get("effective_status", "").upper() == "DISAPPROVED":
                alerts.append(
                    Alert(
                        severity="critical",
                        campaign_name=ad.get("name", ad["id"]),
                        metric="ad_status",
                        message=(
                            f"Ad '{ad.get('name', ad['id'])}' (ID: {ad['id']}) "
                            "is DISAPPROVED and not serving."
                        ),
                        recommendation=(
                            "Review Meta's rejection reason in Ads Manager. "
                            "Check copy for policy violations (no guarantee language, "
                            "no 'loan' terminology, correct special ad category)."
                        ),
                    )
                )

        return alerts

    # ------------------------------------------------------------------
    # Token expiry
    # ------------------------------------------------------------------

    def check_token_expiry(self, days_warning: int = 7) -> list[Alert]:
        """
        Warn if the Meta access token expires within days_warning days.
        Uses the /debug_token endpoint to inspect expiry.

        Args:
            days_warning: Days before expiry to trigger a warning.

        Returns:
            List of Alert objects (0 or 1 items).
        """
        alerts: list[Alert] = []

        try:
            import requests as req_lib

            engine = self.engine
            app_id = getattr(engine, "app_id", "")
            app_secret = getattr(engine, "app_secret", "")
            token = getattr(engine, "token", "")

            if not app_id or not app_secret:
                alerts.append(
                    Alert(
                        severity="info",
                        campaign_name="SYSTEM",
                        metric="token_expiry",
                        message="Cannot check token expiry: META_APP_ID or META_APP_SECRET not set.",
                        recommendation="Add META_APP_ID and META_APP_SECRET to .env.agents.",
                    )
                )
                return alerts

            resp = req_lib.get(
                "https://graph.facebook.com/debug_token",
                params={
                    "input_token": token,
                    "access_token": f"{app_id}|{app_secret}",
                },
                timeout=15,
            )
            body: dict = resp.json()
            data: dict = body.get("data", {})
            expires_at: Optional[int] = data.get("expires_at")

            if expires_at is None:
                # Token has no expiry (system user token)
                alerts.append(
                    Alert(
                        severity="info",
                        campaign_name="SYSTEM",
                        metric="token_expiry",
                        message="Token has no expiry date — likely a non-expiring system user token.",
                        recommendation="No action required.",
                    )
                )
                return alerts

            expiry_dt = datetime.fromtimestamp(expires_at, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            days_left = (expiry_dt - now).days

            if days_left <= 0:
                alerts.append(
                    Alert(
                        severity="critical",
                        campaign_name="SYSTEM",
                        metric="token_expiry",
                        message=f"Meta access token EXPIRED at {expiry_dt.date()}.",
                        recommendation=(
                            "Run engine.refresh_token() immediately or generate a new token "
                            "via the Meta developer portal."
                        ),
                    )
                )
            elif days_left <= days_warning:
                alerts.append(
                    Alert(
                        severity="warning",
                        campaign_name="SYSTEM",
                        metric="token_expiry",
                        message=(
                            f"Meta access token expires in {days_left} day(s) "
                            f"on {expiry_dt.date()}."
                        ),
                        recommendation=(
                            "Run engine.refresh_token() to extend to a 60-day long-lived token."
                        ),
                    )
                )

        except Exception as exc:  # noqa: BLE001
            log.warning("Token expiry check failed: %s", exc)
            alerts.append(
                Alert(
                    severity="warning",
                    campaign_name="SYSTEM",
                    metric="token_expiry",
                    message=f"Could not verify token expiry: {exc}",
                    recommendation="Manually verify token validity in the Meta developer portal.",
                )
            )

        return alerts

    # ------------------------------------------------------------------
    # Alert summary
    # ------------------------------------------------------------------

    def generate_alert_summary(self) -> str:
        """
        Run all checks and return a formatted plain-text summary.

        Returns:
            Multi-line string suitable for printing or emailing.
        """
        alerts = self.check_all_campaigns()

        if not alerts:
            return (
                "SunBiz Funding — Campaign Monitor\n"
                "==================================\n"
                "All systems healthy. No alerts.\n"
            )

        critical = [a for a in alerts if a.severity == "critical"]
        warnings = [a for a in alerts if a.severity == "warning"]
        infos = [a for a in alerts if a.severity == "info"]

        lines: list[str] = [
            "SunBiz Funding — Campaign Monitor",
            "==================================",
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            f"Total alerts: {len(alerts)}  |  "
            f"Critical: {len(critical)}  |  "
            f"Warning: {len(warnings)}  |  "
            f"Info: {len(infos)}",
            "",
        ]

        for severity_label, group in [
            ("CRITICAL", critical),
            ("WARNING", warnings),
            ("INFO", infos),
        ]:
            if not group:
                continue
            lines.append(f"--- {severity_label} ({len(group)}) ---")
            for alert in group:
                lines.append(f"  Campaign : {alert.campaign_name}")
                lines.append(f"  Metric   : {alert.metric}")
                lines.append(f"  Message  : {alert.message}")
                lines.append(f"  Action   : {alert.recommendation}")
                lines.append(f"  Time     : {alert.timestamp}")
                lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Auto-pause underperformers
    # ------------------------------------------------------------------

    def auto_pause_underperformers(
        self,
        cpl_threshold: float = 150.0,
        confirm: bool = False,
    ) -> list[dict]:
        """
        Identify and optionally pause campaigns where cost-per-lead exceeds
        cpl_threshold.

        Args:
            cpl_threshold: Maximum acceptable cost per lead in USD.
            confirm: If False (default), returns candidates without pausing.
                     If True, actually calls engine.pause_campaign().

        Returns:
            List of dicts describing each underperforming campaign:
            {id, name, cpl, status, action_taken}.
        """
        results: list[dict] = []
        campaigns = self.engine.get_all_campaigns()

        for campaign in campaigns:
            if campaign["status"] != "ACTIVE":
                continue

            try:
                rows = self.engine.get_insights(
                    campaign["id"],
                    date_preset="last_7d",
                    fields=["spend", "actions", "cost_per_action_type"],
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("Could not fetch CPL data for %s: %s", campaign["id"], exc)
                continue

            cpl = _extract_cpl(rows)
            if cpl is None or cpl <= 0:
                continue

            if cpl > cpl_threshold:
                action_taken = "none"
                if confirm:
                    try:
                        self.engine.pause_campaign(campaign["id"])
                        action_taken = "paused"
                        log.info(
                            "Auto-paused campaign '%s' (CPL $%.2f > threshold $%.2f)",
                            campaign["name"], cpl, cpl_threshold,
                        )
                    except Exception as exc:  # noqa: BLE001
                        action_taken = f"pause_failed: {exc}"
                        log.error("Failed to pause campaign %s: %s", campaign["id"], exc)

                results.append({
                    "id": campaign["id"],
                    "name": campaign["name"],
                    "cpl": round(cpl, 2),
                    "cpl_threshold": cpl_threshold,
                    "status": campaign["status"],
                    "action_taken": action_taken,
                })

        return results


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _extract_spend(rows: list[dict]) -> float:
    """Sum the 'spend' field across insight rows."""
    total = 0.0
    for row in rows:
        try:
            total += float(row.get("spend", 0) or 0)
        except (TypeError, ValueError):
            pass
    return total


def _extract_float(rows: list[dict], field_name: str) -> float:
    """Extract the first non-zero float value of field_name from insight rows."""
    for row in rows:
        try:
            val = float(row.get(field_name, 0) or 0)
            if val > 0:
                return val
        except (TypeError, ValueError):
            pass
    return 0.0


def _extract_cpl(rows: list[dict]) -> Optional[float]:
    """
    Extract cost-per-lead from cost_per_action_type insight field.
    Returns None if lead action data is not present.
    """
    for row in rows:
        cpa_list = row.get("cost_per_action_type")
        if not isinstance(cpa_list, list):
            continue
        for entry in cpa_list:
            action_type = entry.get("action_type", "")
            if "lead" in action_type.lower():
                try:
                    return float(entry.get("value", 0) or 0)
                except (TypeError, ValueError):
                    pass
    return None


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------


def _run_monitor() -> None:
    """Instantiate engine, run all checks, and print the alert summary."""
    # Import here so monitoring.py can be imported without requiring the engine
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from meta_ads_engine import MetaAdsEngine  # type: ignore[import]

    engine = MetaAdsEngine()
    monitor = CampaignMonitor(engine)

    summary = monitor.generate_alert_summary()
    print()
    print(summary)

    underperformers = monitor.auto_pause_underperformers(cpl_threshold=150.0, confirm=False)
    if underperformers:
        print("--- CPL UNDERPERFORMERS (review before pausing) ---")
        for camp in underperformers:
            print(
                f"  {camp['name']}  |  CPL ${camp['cpl']:.2f}  |  "
                f"Threshold ${camp['cpl_threshold']:.2f}  |  Action: {camp['action_taken']}"
            )
        print()
        print("Re-run with confirm=True to auto-pause these campaigns.")
    else:
        print("No CPL underperformers above $150 threshold.")


if __name__ == "__main__":
    _run_monitor()
