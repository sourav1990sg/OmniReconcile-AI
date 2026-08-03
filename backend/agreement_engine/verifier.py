"""Commercial verification — independent of platform financial math."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

from backend.agreement_engine.matcher import AgreementMatcher
from backend.agreement_engine.models import (
    Agreement,
    AgreementStore,
    CommercialVerificationResult,
    DisplayStatus,
    VerificationLevel,
)

COMMISSION_TOLERANCE_PCT = Decimal("0.50")  # absolute % points


@dataclass
class OrderCommercialResult:
    verification_level: VerificationLevel
    display_status: DisplayStatus
    commercial_result: CommercialVerificationResult
    commercial_remarks: str
    agreement_version: str | None = None
    agreement_status: str | None = None
    agreement_id: str | None = None

    def to_api_fields(self) -> dict[str, Any]:
        return {
            "Verification Level": self.verification_level.value,
            "Display Status": self.display_status.value,
            "Commercial Verification Result": self.commercial_result.value,
            "Commercial Remarks": self.commercial_remarks,
            "Agreement Version": self.agreement_version,
            "Agreement Status": self.agreement_status,
            "Agreement ID": self.agreement_id,
        }


# Standard remarks from sprint spec
REMARK_SETTLEMENT_ONLY = (
    "Platform settlement calculation verified. Commercial agreement not available."
)
REMARK_AGREEMENT_OK = (
    "Settlement calculation and uploaded commercial agreement verified."
)
REMARK_AGREEMENT_VIOLATION = (
    "Settlement matches platform calculation but differs from uploaded commercial agreement."
)
REMARK_PAYMENT_MISMATCH = "Settlement calculation itself does not reconcile."


class AgreementVerifier:
    """
    Enrich one reconciliation API row with commercial verification.

    Does not recompute platform payouts — reads Financial Status / Status only.
    """

    def __init__(self, store: AgreementStore | None = None) -> None:
        self._store = store
        self._matcher = AgreementMatcher()

    def verify_row(
        self,
        row: Mapping[str, Any],
        *,
        agreement: Agreement | None = None,
    ) -> OrderCommercialResult:
        financial_status = str(
            row.get("Financial Status") or row.get("Status") or ""
        ).upper()
        business_status = str(row.get("Status") or "").upper()

        if business_status == "CANCELLED" or financial_status == "CANCELLED":
            return OrderCommercialResult(
                verification_level=VerificationLevel.CANCELLED,
                display_status=DisplayStatus.CANCELLED,
                commercial_result=CommercialVerificationResult.SKIPPED,
                commercial_remarks="Order is cancelled.",
            )
        if business_status == "PENDING":
            return OrderCommercialResult(
                verification_level=VerificationLevel.PENDING,
                display_status=DisplayStatus.PENDING,
                commercial_result=CommercialVerificationResult.SKIPPED,
                commercial_remarks="Order not found in uploaded settlement reports.",
            )
        if business_status == "NOT_RECONCILED":
            return OrderCommercialResult(
                verification_level=VerificationLevel.NOT_RECONCILED,
                display_status=DisplayStatus.NOT_RECONCILED,
                commercial_result=CommercialVerificationResult.SKIPPED,
                commercial_remarks="Order not reconciled against settlement.",
            )

        settlement_ok = financial_status in {
            "FINANCIALLY_RECONCILED",
            "RECONCILED",
        }
        settlement_fail = financial_status in {
            "FINANCIAL_DISCREPANCY",
            "AMOUNT_MISMATCH",
        }

        if settlement_fail or (
            not settlement_ok and row.get("Matched") and financial_status
        ):
            if settlement_fail:
                return OrderCommercialResult(
                    verification_level=VerificationLevel.PAYMENT_MISMATCH,
                    display_status=DisplayStatus.PAYMENT_MISMATCH,
                    commercial_result=CommercialVerificationResult.SKIPPED,
                    commercial_remarks=REMARK_PAYMENT_MISMATCH,
                    agreement_version=agreement.version if agreement else None,
                    agreement_status=agreement.status.value if agreement else None,
                    agreement_id=agreement.agreement_id if agreement else None,
                )

        # Unmatched / other → keep pending-like unless matched settlement_ok
        if not row.get("Matched"):
            return OrderCommercialResult(
                verification_level=VerificationLevel.NOT_RECONCILED
                if business_status == "NOT_RECONCILED"
                else VerificationLevel.PENDING,
                display_status=DisplayStatus.NOT_RECONCILED
                if business_status == "NOT_RECONCILED"
                else DisplayStatus.PENDING,
                commercial_result=CommercialVerificationResult.SKIPPED,
                commercial_remarks=str(row.get("Remarks") or "Not matched."),
            )

        if not settlement_ok:
            return OrderCommercialResult(
                verification_level=VerificationLevel.PAYMENT_MISMATCH,
                display_status=DisplayStatus.PAYMENT_MISMATCH,
                commercial_result=CommercialVerificationResult.SKIPPED,
                commercial_remarks=REMARK_PAYMENT_MISMATCH,
            )

        # Settlement verified — optional commercial layer
        if agreement is None:
            return OrderCommercialResult(
                verification_level=VerificationLevel.SETTLEMENT_VERIFIED,
                display_status=DisplayStatus.PAYMENT_MATCH,
                commercial_result=CommercialVerificationResult.NOT_AVAILABLE,
                commercial_remarks=REMARK_SETTLEMENT_ONLY,
            )

        violation = self._commercial_mismatch(row, agreement)
        if violation:
            return OrderCommercialResult(
                verification_level=VerificationLevel.AGREEMENT_VIOLATION,
                display_status=DisplayStatus.AGREEMENT_VIOLATION,
                commercial_result=CommercialVerificationResult.VIOLATION,
                commercial_remarks=f"{REMARK_AGREEMENT_VIOLATION} {violation}".strip(),
                agreement_version=agreement.version,
                agreement_status=agreement.status.value,
                agreement_id=agreement.agreement_id,
            )

        return OrderCommercialResult(
            verification_level=VerificationLevel.AGREEMENT_VERIFIED,
            display_status=DisplayStatus.VERIFIED_BY_AGREEMENT,
            commercial_result=CommercialVerificationResult.PASS,
            commercial_remarks=REMARK_AGREEMENT_OK,
            agreement_version=agreement.version,
            agreement_status=agreement.status.value,
            agreement_id=agreement.agreement_id,
        )

    def enrich_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for row in rows:
            platform = row.get("Platform")
            outlet = row.get("Outlet")
            order_date = self._matcher.parse_order_date(row.get("Date"))
            agreement = self._matcher.match(
                self._store,
                platform=str(platform) if platform else None,
                outlet=str(outlet) if outlet else None,
                order_date=order_date,
            )
            result = self.verify_row(row, agreement=agreement)
            row.update(result.to_api_fields())
            # Preserve Sprint 6A Financial Status; Remarks for commercial display
            if result.commercial_remarks:
                row["Commercial Remarks"] = result.commercial_remarks
                # Do not overwrite financial Explanation; set Display Remarks
                row["Display Remarks"] = result.commercial_remarks
        return rows

    def _commercial_mismatch(self, row: Mapping[str, Any], agreement: Agreement) -> str:
        """Return reason string if commercial terms violated; else empty."""
        reasons: list[str] = []
        rules = agreement.rules

        # Commission % vs implied rate from breakdown
        if not rules.commission_pct.unknown and rules.commission_pct.value is not None:
            agreed = Decimal(str(rules.commission_pct.value))
            implied = self._implied_commission_pct(row)
            if implied is not None and abs(implied - agreed) > COMMISSION_TOLERANCE_PCT:
                reasons.append(
                    f"Commission {implied}% vs agreement {agreed}%."
                )

        # Platform identity
        if not rules.platform.unknown and rules.platform.value:
            row_plat = str(row.get("Platform") or "").lower()
            agr_plat = str(rules.platform.value).lower()
            if row_plat and agr_plat not in row_plat and row_plat not in agr_plat:
                reasons.append(f"Platform {row_plat} vs agreement {agr_plat}.")

        return " ".join(reasons)

    @staticmethod
    def _implied_commission_pct(row: Mapping[str, Any]) -> Decimal | None:
        bd = row.get("Financial Breakdown") or {}
        if not isinstance(bd, dict):
            return None
        commission = bd.get("commission")
        base = bd.get("gross_order_value") or bd.get("components", {})
        if isinstance(base, dict):
            base = base.get("commissionable_value") or base.get("net_order_value") or bd.get(
                "gross_order_value"
            )
        try:
            c = Decimal(str(commission))
            b = Decimal(str(base))
        except Exception:  # noqa: BLE001
            return None
        if b <= 0:
            return None
        return (c / b * Decimal("100")).quantize(Decimal("0.01"))
