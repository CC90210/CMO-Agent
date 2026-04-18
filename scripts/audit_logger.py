"""
Campaign audit logging — tracks every change made via the API.
==============================================================
Appends structured JSON Lines records to data/audit/audit_log.jsonl.
Each line is one self-contained AuditEntry serialised as JSON.

Standalone usage:
    python scripts/audit_logger.py

Import usage:
    from scripts.audit_logger import AuditLogger

    auditor = AuditLogger()
    auditor.log_action(
        action="pause",
        entity_type="campaign",
        entity_id="120213...",
        details={"reason": "CPL above threshold"},
        previous_values={"status": "ACTIVE"},
    )
    print(auditor.generate_audit_report(days=7))
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("audit_logger")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_AUDIT_DIR = _PROJECT_ROOT / "data" / "audit"
_AUDIT_FILE = _AUDIT_DIR / "audit_log.jsonl"

# Valid action and entity type constants for documentation/validation
VALID_ACTIONS = {"create", "update", "pause", "resume", "delete"}
VALID_ENTITY_TYPES = {"campaign", "adset", "ad", "creative", "budget", "audience"}

# ---------------------------------------------------------------------------
# Credential loading (mirrors meta_ads_engine.py pattern)
# ---------------------------------------------------------------------------


def _load_env_agents() -> dict[str, str]:
    """
    Parse KEY=VALUE pairs from .env.agents at the project root.
    Skips blank lines and comment lines.
    """
    env_path = _PROJECT_ROOT / ".env.agents"
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
# AuditEntry dataclass
# ---------------------------------------------------------------------------


@dataclass
class AuditEntry:
    timestamp: str
    action: str         # 'create', 'update', 'pause', 'resume', 'delete'
    entity_type: str    # 'campaign', 'adset', 'ad', 'creative'
    entity_id: str
    details: dict
    user: str
    previous_values: Optional[dict] = None

    def to_dict(self) -> dict:
        """Serialise to a plain dict (suitable for JSON output)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEntry":
        """Deserialise from a plain dict."""
        return cls(
            timestamp=data["timestamp"],
            action=data["action"],
            entity_type=data["entity_type"],
            entity_id=data["entity_id"],
            details=data.get("details", {}),
            user=data.get("user", "unknown"),
            previous_values=data.get("previous_values"),
        )


# ---------------------------------------------------------------------------
# AuditLogger
# ---------------------------------------------------------------------------


class AuditLogger:
    """
    Append-only audit trail for all campaign API operations.

    Every mutation should call log_action() immediately after the API call
    succeeds so that previous_values can be supplied for rollback reference.
    """

    def __init__(self, audit_file: Optional[Path] = None) -> None:
        """
        Args:
            audit_file: Override the default audit file path.
                        Primarily useful for tests.
        """
        self.audit_file: Path = audit_file or _AUDIT_FILE
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)
        log.info("AuditLogger ready — file: %s", self.audit_file)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def log_action(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        details: dict,
        user: str = "claude",
        previous_values: Optional[dict] = None,
    ) -> AuditEntry:
        """
        Append one audit record to the log file.

        Args:
            action:          One of: create, update, pause, resume, delete.
            entity_type:     One of: campaign, adset, ad, creative, budget, audience.
            entity_id:       The Meta API object ID (e.g. campaign ID).
            details:         Free-form dict describing what changed (new values).
            user:            Who triggered the action. Defaults to 'claude'.
            previous_values: Snapshot of values before the change (for rollback).

        Returns:
            The AuditEntry that was written.
        """
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            user=user,
            previous_values=previous_values,
        )

        try:
            with self.audit_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry.to_dict(), default=str) + "\n")
            log.info(
                "Audit logged: [%s] %s %s by %s",
                action.upper(), entity_type, entity_id, user,
            )
        except OSError as exc:
            log.error("Failed to write audit entry: %s", exc)

        return entry

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def _read_all_entries(self) -> list[AuditEntry]:
        """
        Read and parse every line from the audit log file.
        Malformed lines are skipped with a warning.
        """
        if not self.audit_file.exists():
            return []

        entries: list[AuditEntry] = []
        with self.audit_file.open(encoding="utf-8") as fh:
            for line_num, raw_line in enumerate(fh, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entries.append(AuditEntry.from_dict(data))
                except (json.JSONDecodeError, KeyError, TypeError) as exc:
                    log.warning("Skipping malformed audit line %d: %s", line_num, exc)

        return entries

    def get_campaign_history(self, campaign_id: str) -> list[AuditEntry]:
        """
        Return all audit entries for a specific campaign ID.

        Args:
            campaign_id: The Meta campaign ID to filter by.

        Returns:
            List of AuditEntry objects, ordered oldest to newest.
        """
        all_entries = self._read_all_entries()
        return [
            e for e in all_entries
            if e.entity_id == campaign_id
            or e.details.get("campaign_id") == campaign_id
        ]

    def get_recent_actions(self, hours: int = 24) -> list[AuditEntry]:
        """
        Return audit entries from the last N hours.

        Args:
            hours: Lookback window in hours. Default 24.

        Returns:
            List of AuditEntry objects within the time window.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        results: list[AuditEntry] = []

        for entry in self._read_all_entries():
            try:
                entry_dt = datetime.fromisoformat(entry.timestamp)
                # Normalise to UTC if naive
                if entry_dt.tzinfo is None:
                    entry_dt = entry_dt.replace(tzinfo=timezone.utc)
                if entry_dt >= cutoff:
                    results.append(entry)
            except ValueError:
                pass

        return results

    def get_actions_by_type(self, action_type: str) -> list[AuditEntry]:
        """
        Return all audit entries matching a specific action type.

        Args:
            action_type: One of: create, update, pause, resume, delete.

        Returns:
            List of matching AuditEntry objects.
        """
        normalised = action_type.lower().strip()
        return [e for e in self._read_all_entries() if e.action == normalised]

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_audit_report(self, days: int = 7) -> str:
        """
        Generate a plain-text summary of all changes in the last N days.

        Args:
            days: Lookback window in days. Default 7.

        Returns:
            Multi-line formatted string.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        all_entries = self._read_all_entries()

        recent: list[AuditEntry] = []
        for entry in all_entries:
            try:
                entry_dt = datetime.fromisoformat(entry.timestamp)
                if entry_dt.tzinfo is None:
                    entry_dt = entry_dt.replace(tzinfo=timezone.utc)
                if entry_dt >= cutoff:
                    recent.append(entry)
            except ValueError:
                pass

        if not recent:
            return (
                f"SunBiz Funding — Audit Report (last {days} days)\n"
                "=" * 50 + "\n"
                "No activity recorded in this period.\n"
            )

        # Aggregate by action type
        action_counts: dict[str, int] = {}
        entity_counts: dict[str, int] = {}
        for entry in recent:
            action_counts[entry.action] = action_counts.get(entry.action, 0) + 1
            entity_counts[entry.entity_type] = entity_counts.get(entry.entity_type, 0) + 1

        lines: list[str] = [
            f"SunBiz Funding — Audit Report (last {days} days)",
            "=" * 50,
            f"Generated : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            f"Period    : {cutoff.strftime('%Y-%m-%d')} to today",
            f"Total     : {len(recent)} action(s)",
            "",
            "By action type:",
        ]
        for action, count in sorted(action_counts.items()):
            lines.append(f"  {action:<12} {count}")

        lines.append("")
        lines.append("By entity type:")
        for entity, count in sorted(entity_counts.items()):
            lines.append(f"  {entity:<12} {count}")

        lines.append("")
        lines.append("Detailed log (newest first):")
        lines.append("-" * 50)

        for entry in reversed(recent):
            lines.append(
                f"  [{entry.timestamp[:19]}]  {entry.action.upper():<8}  "
                f"{entry.entity_type:<10}  ID: {entry.entity_id}  by: {entry.user}"
            )
            if entry.details:
                for k, v in entry.details.items():
                    lines.append(f"      {k}: {v}")
            if entry.previous_values:
                lines.append(f"      previous: {entry.previous_values}")
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Rollback reference
    # ------------------------------------------------------------------

    def rollback_info(self, campaign_id: str) -> str:
        """
        Show what was changed and what the previous values were for a campaign.
        This is informational only — no actual rollback is performed here.

        Args:
            campaign_id: The Meta campaign ID.

        Returns:
            Formatted string describing each reversible change.
        """
        history = self.get_campaign_history(campaign_id)

        if not history:
            return f"No audit history found for campaign ID: {campaign_id}"

        lines: list[str] = [
            f"Rollback Reference — Campaign {campaign_id}",
            "=" * 50,
            f"Total recorded changes: {len(history)}",
            "",
        ]

        reversible: list[AuditEntry] = [
            e for e in reversed(history)
            if e.previous_values and e.action in {"update", "pause", "resume"}
        ]

        if not reversible:
            lines.append("No reversible changes found (no previous_values recorded).")
        else:
            lines.append("Reversible changes (most recent first):")
            lines.append("")
            for entry in reversible:
                lines.append(
                    f"  [{entry.timestamp[:19]}]  {entry.action.upper()}  by {entry.user}"
                )
                lines.append("  To revert, restore:")
                for k, v in (entry.previous_values or {}).items():
                    lines.append(f"    {k} = {v!r}")
                lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def total_entries(self) -> int:
        """Return the total number of entries in the audit log."""
        return len(self._read_all_entries())


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------


def _run_demo() -> None:
    """Write sample entries and print a report."""
    auditor = AuditLogger()

    print()
    print("=" * 50)
    print("  AuditLogger Demo")
    print("=" * 50)

    # Write a few sample entries
    auditor.log_action(
        action="create",
        entity_type="campaign",
        entity_id="120200000000001",
        details={"name": "SunBiz — MCA Consolidation Q1", "objective": "OUTCOME_LEADS"},
        user="claude",
    )
    auditor.log_action(
        action="update",
        entity_type="campaign",
        entity_id="120200000000001",
        details={"daily_budget_usd": 50.00},
        user="claude",
        previous_values={"daily_budget_usd": 30.00},
    )
    auditor.log_action(
        action="pause",
        entity_type="campaign",
        entity_id="120200000000001",
        details={"reason": "CPL above $150 threshold"},
        user="claude",
        previous_values={"status": "ACTIVE"},
    )

    print()
    print(auditor.generate_audit_report(days=1))
    print()
    print(auditor.rollback_info("120200000000001"))
    print(f"Total entries in log: {auditor.total_entries()}")
    print("=" * 50)
    print()


if __name__ == "__main__":
    _run_demo()
