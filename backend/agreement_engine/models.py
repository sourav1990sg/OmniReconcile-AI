"""Commercial agreement domain models (in-memory; no SQL dependency)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4


class AgreementStatus(str, Enum):
    VERIFIED = "Verified"
    PENDING_REVIEW = "Pending Review"
    EXPIRED = "Expired"
    DRAFT = "Draft"


class VerificationLevel(str, Enum):
    SETTLEMENT_VERIFIED = "SETTLEMENT_VERIFIED"
    AGREEMENT_VERIFIED = "AGREEMENT_VERIFIED"
    AGREEMENT_VIOLATION = "AGREEMENT_VIOLATION"
    PAYMENT_MISMATCH = "PAYMENT_MISMATCH"
    PENDING = "PENDING"
    NOT_RECONCILED = "NOT_RECONCILED"
    CANCELLED = "CANCELLED"


class DisplayStatus(str, Enum):
    PAYMENT_MATCH = "Payment Match"
    VERIFIED_BY_AGREEMENT = "Verified by Agreement"
    AGREEMENT_VIOLATION = "Agreement Violation"
    PAYMENT_MISMATCH = "Payment Mismatch"
    PENDING = "Pending"
    NOT_RECONCILED = "Not Reconciled"
    CANCELLED = "Cancelled"


class CommercialVerificationResult(str, Enum):
    NOT_AVAILABLE = "NOT AVAILABLE"
    PASS = "PASS"
    VIOLATION = "VIOLATION"
    SKIPPED = "SKIPPED"


@dataclass
class AgreementRuleField:
    """One extracted commercial term with confidence."""

    key: str
    value: Any = None
    confidence: float = 0.0
    source_snippet: str = ""
    unknown: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if isinstance(self.value, Decimal):
            payload["value"] = float(self.value)
        elif isinstance(self.value, (date, datetime)):
            payload["value"] = self.value.isoformat()
        return payload


@dataclass
class AgreementRules:
    """Structured commercial terms for one agreement version."""

    platform: AgreementRuleField = field(
        default_factory=lambda: AgreementRuleField(key="platform")
    )
    restaurant_name: AgreementRuleField = field(
        default_factory=lambda: AgreementRuleField(key="restaurant_name")
    )
    agreement_date: AgreementRuleField = field(
        default_factory=lambda: AgreementRuleField(key="agreement_date")
    )
    effective_date: AgreementRuleField = field(
        default_factory=lambda: AgreementRuleField(key="effective_date")
    )
    expiry_date: AgreementRuleField = field(
        default_factory=lambda: AgreementRuleField(key="expiry_date")
    )
    commission_pct: AgreementRuleField = field(
        default_factory=lambda: AgreementRuleField(key="commission_pct")
    )
    payment_mechanism_fee: AgreementRuleField = field(
        default_factory=lambda: AgreementRuleField(key="payment_mechanism_fee")
    )
    advertisement_terms: AgreementRuleField = field(
        default_factory=lambda: AgreementRuleField(key="advertisement_terms")
    )
    promo_cost_sharing: AgreementRuleField = field(
        default_factory=lambda: AgreementRuleField(key="promo_cost_sharing")
    )
    brand_pack: AgreementRuleField = field(
        default_factory=lambda: AgreementRuleField(key="brand_pack")
    )
    packaging_charges: AgreementRuleField = field(
        default_factory=lambda: AgreementRuleField(key="packaging_charges")
    )
    delivery_charges: AgreementRuleField = field(
        default_factory=lambda: AgreementRuleField(key="delivery_charges")
    )
    cancellation_policy: AgreementRuleField = field(
        default_factory=lambda: AgreementRuleField(key="cancellation_policy")
    )
    settlement_cycle: AgreementRuleField = field(
        default_factory=lambda: AgreementRuleField(key="settlement_cycle")
    )
    gst_rules: AgreementRuleField = field(
        default_factory=lambda: AgreementRuleField(key="gst_rules")
    )
    tds: AgreementRuleField = field(default_factory=lambda: AgreementRuleField(key="tds"))
    tcs: AgreementRuleField = field(default_factory=lambda: AgreementRuleField(key="tcs"))
    other_clauses: AgreementRuleField = field(
        default_factory=lambda: AgreementRuleField(key="other_clauses")
    )

    def fields(self) -> list[AgreementRuleField]:
        return [
            self.platform,
            self.restaurant_name,
            self.agreement_date,
            self.effective_date,
            self.expiry_date,
            self.commission_pct,
            self.payment_mechanism_fee,
            self.advertisement_terms,
            self.promo_cost_sharing,
            self.brand_pack,
            self.packaging_charges,
            self.delivery_charges,
            self.cancellation_policy,
            self.settlement_cycle,
            self.gst_rules,
            self.tds,
            self.tcs,
            self.other_clauses,
        ]

    def set_field(
        self,
        key: str,
        value: Any,
        *,
        confidence: float,
        source_snippet: str = "",
        unknown_threshold: float = 0.55,
    ) -> None:
        for f in self.fields():
            if f.key == key:
                f.value = value
                f.confidence = confidence
                f.source_snippet = source_snippet
                f.unknown = value is None or confidence < unknown_threshold
                return
        raise KeyError(key)

    def unknown_count(self) -> int:
        return sum(1 for f in self.fields() if f.unknown)

    def to_dict(self) -> dict[str, Any]:
        return {f.key: f.to_dict() for f in self.fields()}


@dataclass
class Agreement:
    """
    Commercial agreement record (in-memory model).

    Mirrors: Agreement / Rules / Version / Effective From-To / Platform / Restaurant / Outlets.
    """

    agreement_id: str = field(default_factory=lambda: str(uuid4()))
    version: str = "1"
    platform: str | None = None
    restaurant: str | None = None
    outlets: list[str] = field(default_factory=list)
    effective_from: date | None = None
    effective_to: date | None = None
    status: AgreementStatus = AgreementStatus.PENDING_REVIEW
    source_filename: str | None = None
    source_bytes_sha1: str | None = None
    rules: AgreementRules = field(default_factory=AgreementRules)
    extraction_notes: list[str] = field(default_factory=list)
    approved: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> dict[str, Any]:
        return {
            "agreement_id": self.agreement_id,
            "version": self.version,
            "platform": self.platform,
            "restaurant": self.restaurant,
            "outlets": list(self.outlets),
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "status": self.status.value,
            "source_filename": self.source_filename,
            "rules": self.rules.to_dict(),
            "unknown_terms": self.rules.unknown_count(),
            "extraction_notes": list(self.extraction_notes),
            "approved": self.approved,
            "created_at": self.created_at,
        }


@dataclass
class AgreementStore:
    """Session-scoped in-memory agreement registry."""

    agreements: dict[str, Agreement] = field(default_factory=dict)
    active_id: str | None = None

    def put(self, agreement: Agreement, *, make_active: bool = True) -> Agreement:
        self.agreements[agreement.agreement_id] = agreement
        if make_active:
            self.active_id = agreement.agreement_id
        return agreement

    def active(self) -> Agreement | None:
        if not self.active_id:
            return None
        return self.agreements.get(self.active_id)

    def to_dict(self) -> dict[str, Any]:
        active = self.active()
        return {
            "active_agreement_id": self.active_id,
            "count": len(self.agreements),
            "active": active.to_dict() if active else None,
            "agreements": [a.to_dict() for a in self.agreements.values()],
        }
