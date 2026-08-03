"""Match an order to the applicable commercial agreement version."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from backend.agreement_engine.models import Agreement, AgreementStore


class AgreementMatcher:
    """Select active agreement applicable to platform / outlet / order date."""

    def match(
        self,
        store: AgreementStore | None,
        *,
        platform: str | None,
        outlet: str | None = None,
        order_date: date | None = None,
    ) -> Agreement | None:
        if store is None:
            return None
        agreement = store.active()
        if agreement is None:
            return None
        if not self._platform_ok(agreement, platform):
            return None
        if not self._outlet_ok(agreement, outlet):
            return None
        if not self._date_ok(agreement, order_date):
            return None
        return agreement

    @staticmethod
    def _platform_ok(agreement: Agreement, platform: str | None) -> bool:
        if not agreement.platform:
            # Platform UNKNOWN on agreement — still usable if approved/active
            return True
        if not platform:
            return True
        return agreement.platform.lower() in str(platform).lower() or str(platform).lower() in agreement.platform.lower()

    @staticmethod
    def _outlet_ok(agreement: Agreement, outlet: str | None) -> bool:
        if not agreement.outlets:
            return True
        if not outlet:
            return True
        target = outlet.strip().lower()
        return any(target == o.strip().lower() or target in o.strip().lower() for o in agreement.outlets)

    @staticmethod
    def _date_ok(agreement: Agreement, order_date: date | None) -> bool:
        if order_date is None:
            return True
        if agreement.effective_from and order_date < agreement.effective_from:
            return False
        if agreement.effective_to and order_date > agreement.effective_to:
            return False
        return True

    @staticmethod
    def parse_order_date(value: Any) -> date | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        text = str(value).strip()
        if not text or text in {"—", "-"}:
            return None
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None
