"""Standard remarks and recommendations for business-rule classifications."""

from __future__ import annotations

from backend.business_rules.result import ReconciliationStatus

# Remarks (user-facing)
REMARK_CANCELLED = "Order is cancelled."
REMARK_RECONCILED = "Expected amount matches settled amount."
REMARK_FINANCIALLY_RECONCILED = (
    "Calculated settlement payout matches actual payout; platform deductions explained."
)
REMARK_AMOUNT_MISMATCH = "Settled amount differs from expected amount."
REMARK_FINANCIAL_DISCREPANCY = (
    "Unexplained difference between calculated payout and actual settlement payout."
)
REMARK_PENDING = "Order not found in uploaded settlement reports."
REMARK_NOT_RECONCILED = (
    "Order not found in uploaded settlement reports. Please verify settlement."
)
REMARK_DUPLICATE_SETTLEMENT = "Duplicate settlement entry for this order ID."
REMARK_MANUAL_REVIEW = "Unable to classify automatically; manual review required."
REMARK_UNMATCHED_SETTLEMENT = "Settlement order has no matching POS order."

# Recommendations
REC_CANCELLED = "No settlement action required for cancelled orders."
REC_RECONCILED = "No action required."
REC_FINANCIALLY_RECONCILED = "No action required — payout is explained by platform rules."
REC_AMOUNT_MISMATCH = "Investigate commission, discounts, or payout deductions."
REC_FINANCIAL_DISCREPANCY = (
    "Investigate unexplained payout gap after platform deductions; raise dispute if underpaid."
)
REC_PENDING = "Wait for the platform settlement cycle to complete, then re-run."
REC_NOT_RECONCILED = "Verify the order on the aggregator portal and re-upload settlements."
REC_DUPLICATE_SETTLEMENT = "Review duplicate payout rows and retain the correct settlement."
REC_MANUAL_REVIEW = "Escalate to finance operations for manual investigation."
REC_UNMATCHED_SETTLEMENT = "Confirm whether the POS export is missing this order."


def remarks_for(status: ReconciliationStatus, *, unmatched_settlement: bool = False) -> str:
    if unmatched_settlement and status == ReconciliationStatus.MANUAL_REVIEW:
        return REMARK_UNMATCHED_SETTLEMENT
    mapping = {
        ReconciliationStatus.CANCELLED: REMARK_CANCELLED,
        ReconciliationStatus.RECONCILED: REMARK_RECONCILED,
        ReconciliationStatus.FINANCIALLY_RECONCILED: REMARK_FINANCIALLY_RECONCILED,
        ReconciliationStatus.AMOUNT_MISMATCH: REMARK_AMOUNT_MISMATCH,
        ReconciliationStatus.FINANCIAL_DISCREPANCY: REMARK_FINANCIAL_DISCREPANCY,
        ReconciliationStatus.PENDING: REMARK_PENDING,
        ReconciliationStatus.NOT_RECONCILED: REMARK_NOT_RECONCILED,
        ReconciliationStatus.DUPLICATE_SETTLEMENT: REMARK_DUPLICATE_SETTLEMENT,
        ReconciliationStatus.MANUAL_REVIEW: REMARK_MANUAL_REVIEW,
    }
    return mapping[status]


def recommendation_for(
    status: ReconciliationStatus,
    *,
    unmatched_settlement: bool = False,
) -> str:
    if unmatched_settlement and status == ReconciliationStatus.MANUAL_REVIEW:
        return REC_UNMATCHED_SETTLEMENT
    mapping = {
        ReconciliationStatus.CANCELLED: REC_CANCELLED,
        ReconciliationStatus.RECONCILED: REC_RECONCILED,
        ReconciliationStatus.FINANCIALLY_RECONCILED: REC_FINANCIALLY_RECONCILED,
        ReconciliationStatus.AMOUNT_MISMATCH: REC_AMOUNT_MISMATCH,
        ReconciliationStatus.FINANCIAL_DISCREPANCY: REC_FINANCIAL_DISCREPANCY,
        ReconciliationStatus.PENDING: REC_PENDING,
        ReconciliationStatus.NOT_RECONCILED: REC_NOT_RECONCILED,
        ReconciliationStatus.DUPLICATE_SETTLEMENT: REC_DUPLICATE_SETTLEMENT,
        ReconciliationStatus.MANUAL_REVIEW: REC_MANUAL_REVIEW,
    }
    return mapping[status]
