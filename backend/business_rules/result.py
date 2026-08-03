"""Business rule classification outcomes."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ReconciliationStatus(str, Enum):
    """Supported business-rule statuses (classification only)."""

    RECONCILED = "RECONCILED"  # legacy alias
    FINANCIALLY_RECONCILED = "FINANCIALLY_RECONCILED"
    PENDING = "PENDING"
    NOT_RECONCILED = "NOT_RECONCILED"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"  # legacy alias
    FINANCIAL_DISCREPANCY = "FINANCIAL_DISCREPANCY"
    CANCELLED = "CANCELLED"
    DUPLICATE_SETTLEMENT = "DUPLICATE_SETTLEMENT"
    MANUAL_REVIEW = "MANUAL_REVIEW"


@dataclass(frozen=True)
class BusinessRuleResult:
    """Classification result for one reconciliation row."""

    order_id: str
    platform: str | None
    status: ReconciliationStatus
    remarks: str
    recommendation: str
    matched: bool
    source_pos_document: str | None = None
    source_settlement_document: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


@dataclass
class BusinessRulesReport:
    """Full classification output for a reconciliation report."""

    results: list[BusinessRuleResult] = field(default_factory=list)
    status_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status_summary": dict(self.status_counts),
            "total": len(self.results),
            "results": [r.to_dict() for r in self.results],
        }
