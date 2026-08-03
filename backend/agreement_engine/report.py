"""Agreement coverage and executive report builders."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Sequence

from backend.agreement_engine.models import CommercialVerificationResult, VerificationLevel


@dataclass
class AgreementCoverageReport:
    orders_verified_by_agreement: int = 0
    orders_verified_by_settlement: int = 0
    agreement_violations: int = 0
    payment_mismatches: int = 0
    unknown_agreement_terms: int = 0
    agreement_available: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_coverage(
    rows: Sequence[dict[str, Any]],
    *,
    unknown_terms: int = 0,
    agreement_available: bool = False,
) -> AgreementCoverageReport:
    report = AgreementCoverageReport(
        unknown_agreement_terms=unknown_terms,
        agreement_available=agreement_available,
    )
    for row in rows:
        level = str(row.get("Verification Level") or "")
        if level == VerificationLevel.AGREEMENT_VERIFIED.value:
            report.orders_verified_by_agreement += 1
        elif level == VerificationLevel.SETTLEMENT_VERIFIED.value:
            report.orders_verified_by_settlement += 1
        elif level == VerificationLevel.AGREEMENT_VIOLATION.value:
            report.agreement_violations += 1
        elif level == VerificationLevel.PAYMENT_MISMATCH.value:
            report.payment_mismatches += 1
    return report


def build_executive_report(row: dict[str, Any]) -> dict[str, str]:
    """
    Separate Settlement Verification vs Commercial Agreement Verification.
    """
    financial = str(row.get("Financial Status") or row.get("Status") or "")
    settlement = (
        "PASS"
        if financial in {"FINANCIALLY_RECONCILED", "RECONCILED"}
        else ("FAIL" if financial in {"FINANCIAL_DISCREPANCY", "AMOUNT_MISMATCH"} else "N/A")
    )
    commercial = str(
        row.get("Commercial Verification Result")
        or CommercialVerificationResult.NOT_AVAILABLE.value
    )
    return {
        "Settlement Verification": settlement,
        "Commercial Agreement": commercial,
    }
