"""Validate / normalize agreement rules; support manual overrides."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from backend.agreement_engine.models import Agreement, AgreementRules, AgreementStatus


class AgreementValidator:
    """
    Validate extracted rules and apply manual edits.

    Low-confidence / missing fields remain UNKNOWN — never invent values.
    """

    def validate(self, agreement: Agreement, *, as_of: date | None = None) -> list[str]:
        findings: list[str] = []
        today = as_of or date.today()
        rules = agreement.rules

        if rules.platform.unknown or not rules.platform.value:
            findings.append("Platform is UNKNOWN — configure manually.")
        if rules.commission_pct.unknown or rules.commission_pct.value is None:
            findings.append("Commission % is UNKNOWN — configure manually.")

        eff = agreement.effective_from or (
            rules.effective_date.value if isinstance(rules.effective_date.value, date) else None
        )
        exp = agreement.effective_to or (
            rules.expiry_date.value if isinstance(rules.expiry_date.value, date) else None
        )
        if eff and exp and exp < eff:
            findings.append("Expiry date is before effective date.")
        if exp and exp < today:
            agreement.status = AgreementStatus.EXPIRED
            findings.append("Agreement is expired.")
        elif agreement.approved and agreement.status != AgreementStatus.EXPIRED:
            agreement.status = AgreementStatus.VERIFIED
        elif agreement.status not in {AgreementStatus.EXPIRED, AgreementStatus.VERIFIED}:
            agreement.status = AgreementStatus.PENDING_REVIEW

        # Sync header fields from rules when known
        if not rules.platform.unknown and rules.platform.value:
            agreement.platform = str(rules.platform.value).lower()
        if not rules.restaurant_name.unknown and rules.restaurant_name.value:
            agreement.restaurant = str(rules.restaurant_name.value)
        if isinstance(rules.effective_date.value, date) and not rules.effective_date.unknown:
            agreement.effective_from = rules.effective_date.value
        if isinstance(rules.expiry_date.value, date) and not rules.expiry_date.unknown:
            agreement.effective_to = rules.expiry_date.value

        return findings

    def apply_manual_overrides(
        self,
        agreement: Agreement,
        overrides: Mapping[str, Any],
    ) -> Agreement:
        """User-configured fields replace extraction (confidence = 1.0)."""
        for key, raw in overrides.items():
            if key in {"outlets", "version", "status", "approved"}:
                continue
            value = self._coerce(key, raw)
            try:
                agreement.rules.set_field(
                    key,
                    value,
                    confidence=1.0 if value is not None else 0.0,
                    source_snippet="manual_override",
                    unknown_threshold=0.55,
                )
            except KeyError:
                continue
        if "outlets" in overrides and isinstance(overrides["outlets"], list):
            agreement.outlets = [str(x) for x in overrides["outlets"]]
        if "version" in overrides and overrides["version"] is not None:
            agreement.version = str(overrides["version"])
        if overrides.get("approved") is True:
            agreement.approved = True
        self.validate(agreement)
        return agreement

    @staticmethod
    def _coerce(key: str, raw: Any) -> Any:
        if raw is None or raw == "" or str(raw).upper() == "UNKNOWN":
            return None
        if key in {"commission_pct", "payment_mechanism_fee", "tds", "tcs", "packaging_charges", "delivery_charges"}:
            try:
                return Decimal(str(raw).replace("%", "").strip())
            except (InvalidOperation, ValueError):
                return None
        if key.endswith("_date") or key in {"agreement_date", "effective_date", "expiry_date"}:
            if isinstance(raw, date):
                return raw
            text = str(raw)[:10]
            try:
                return date.fromisoformat(text)
            except ValueError:
                return None
        if key == "platform":
            return str(raw).strip().lower()
        return raw
