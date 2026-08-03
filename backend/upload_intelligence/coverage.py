"""POS vs settlement date coverage calculation."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from backend.upload_intelligence.models import CoverageReport


def _parse(d: str | None) -> date | None:
    if not d:
        return None
    try:
        return datetime.strptime(d[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def compute_coverage(
    *,
    pos_from: str | None,
    pos_to: str | None,
    settlement_from: str | None,
    settlement_to: str | None,
) -> CoverageReport:
    """
    Coverage = settlement span ∩ POS span / POS span (by calendar days).

    Missing range is the POS tail (or head) not covered by settlement.
    """
    pf, pt = _parse(pos_from), _parse(pos_to)
    sf, st = _parse(settlement_from), _parse(settlement_to)

    if pf is None or pt is None or pt < pf:
        return CoverageReport(
            pos_from=pos_from,
            pos_to=pos_to,
            settlement_from=settlement_from,
            settlement_to=settlement_to,
            coverage_pct=0.0,
            missing_from=None,
            missing_to=None,
            missing_days=0,
        )

    pos_days = (pt - pf).days + 1
    if sf is None or st is None or st < sf:
        return CoverageReport(
            pos_from=pos_from,
            pos_to=pos_to,
            settlement_from=settlement_from,
            settlement_to=settlement_to,
            coverage_pct=0.0,
            missing_from=pos_from,
            missing_to=pos_to,
            missing_days=pos_days,
        )

    overlap_start = max(pf, sf)
    overlap_end = min(pt, st)
    if overlap_end < overlap_start:
        covered = 0
    else:
        covered = (overlap_end - overlap_start).days + 1

    coverage_pct = round(100.0 * covered / pos_days, 1)

    # Prefer reporting POS days after settlement end (common payout lag)
    missing_from: str | None = None
    missing_to: str | None = None
    missing_days = 0
    if st < pt:
        miss_start = st + timedelta(days=1)
        if miss_start <= pt:
            missing_from = miss_start.isoformat()
            missing_to = pt.isoformat()
            missing_days = (pt - miss_start).days + 1
    elif sf > pf:
        miss_end = sf - timedelta(days=1)
        if pf <= miss_end:
            missing_from = pf.isoformat()
            missing_to = miss_end.isoformat()
            missing_days = (miss_end - pf).days + 1

    return CoverageReport(
        pos_from=pos_from,
        pos_to=pos_to,
        settlement_from=settlement_from,
        settlement_to=settlement_to,
        coverage_pct=coverage_pct,
        missing_from=missing_from,
        missing_to=missing_to,
        missing_days=missing_days,
    )
