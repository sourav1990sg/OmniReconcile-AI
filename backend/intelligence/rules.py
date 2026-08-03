"""Deterministic thresholds and helpers for the Business Intelligence engine."""

from __future__ import annotations

from typing import Any

from backend.analytics.models import AnalyticsReport, PlatformSummary
from backend.intelligence.models import Severity

# Commission gap between platforms (percentage points of commission/GOV)
COMMISSION_GAP_MEDIUM_PP = 1.5
COMMISSION_GAP_HIGH_PP = 3.0

# Recoverable concentration at a single outlet
RECOVERABLE_SHARE_MEDIUM = 25.0
RECOVERABLE_SHARE_HIGH = 40.0

# Absolute recoverable triggers (INR)
RECOVERABLE_MEDIUM = 5_000.0
RECOVERABLE_HIGH = 25_000.0

# Settlement coverage floors
COVERAGE_LOW = 95.0
COVERAGE_CRITICAL = 90.0

# Agreement
VIOLATION_MEDIUM = 1
VIOLATION_HIGH = 5

# Operations
CANCELLED_SHARE_MEDIUM = 5.0
CANCELLED_SHARE_HIGH = 10.0
PENDING_SHARE_MEDIUM = 5.0
PENDING_SHARE_HIGH = 12.0
PAYMENT_MATCH_LOW = 90.0

# Platform mix imbalance
REVENUE_SHARE_DOMINANT = 65.0

SEVERITY_RANK: dict[Severity, int] = {
    "Low": 1,
    "Medium": 2,
    "High": 3,
    "Critical": 4,
}


def platform_by_name(report: AnalyticsReport) -> dict[str, PlatformSummary]:
    return {p.platform: p for p in report.platform_summary}


def commission_gap_pp(report: AnalyticsReport) -> tuple[str, str, float]:
    """Return (higher_platform, lower_platform, gap_pp). Gap = commission% difference."""
    cmp_ = report.platform_comparison
    sw = cmp_.swiggy_commission_pct
    zo = cmp_.zomato_commission_pct
    gap = abs(sw - zo)
    if sw >= zo:
        return "Swiggy", "Zomato", gap
    return "Zomato", "Swiggy", gap


def recoverable_outlet_share(report: AnalyticsReport) -> tuple[str | None, float, float]:
    """Top recoverable outlet, its amount, and % of total recoverable."""
    total = float(report.financial_summary.recoverable or 0.0)
    name = report.top_performers.highest_recoverable_amount
    if not name or total <= 0:
        return name, 0.0, 0.0
    outlet = next((o for o in report.outlet_summary if o.outlet == name), None)
    if not outlet:
        return name, 0.0, 0.0
    amount = float(outlet.recoverable_amount)
    share = round((amount / total) * 100, 1) if total else 0.0
    return name, amount, share


def severity_from_gap(gap_pp: float) -> Severity:
    if gap_pp >= COMMISSION_GAP_HIGH_PP:
        return "High"
    if gap_pp >= COMMISSION_GAP_MEDIUM_PP:
        return "Medium"
    return "Low"


def severity_from_recoverable(amount: float, share_pct: float) -> Severity:
    if amount >= RECOVERABLE_HIGH or share_pct >= RECOVERABLE_SHARE_HIGH:
        return "High"
    if amount >= RECOVERABLE_MEDIUM or share_pct >= RECOVERABLE_SHARE_MEDIUM:
        return "Medium"
    if amount > 0:
        return "Low"
    return "Low"


def severity_from_coverage(pct: float) -> Severity | None:
    if pct < COVERAGE_CRITICAL:
        return "Critical"
    if pct < COVERAGE_LOW:
        return "High"
    return None


def confidence_for_metrics(*values: Any) -> float:
    """Deterministic confidence: 1.0 when all supporting values present, else lower."""
    if not values:
        return 0.7
    missing = sum(1 for v in values if v is None or v == "" or v == 0)
    if missing == 0:
        return 1.0
    if missing == 1:
        return 0.85
    return 0.7


def pct_of(part: float | int, whole: float | int) -> float:
    w = float(whole)
    if w <= 0:
        return 0.0
    return round((float(part) / w) * 100, 2)
