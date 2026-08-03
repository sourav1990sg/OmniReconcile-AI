"""
Business Rules & Exception Engine.

Classifies :class:`ReconciliationReport` rows. Does **not** reconcile or
recalculate amounts.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import date, datetime
from typing import Mapping, Protocol, Sequence

from backend.business_rules.classifiers import OrderFacts, StatusClassifier
from backend.business_rules.remarks import recommendation_for, remarks_for
from backend.business_rules.result import (
    BusinessRuleResult,
    BusinessRulesReport,
    ReconciliationStatus,
)
from backend.business_rules.rules import BusinessRulesConfig
from backend.ingestion.logging_utils import log_with_context
from backend.reconciliation.result import ReconciliationReport, ReconciliationResult

logger = logging.getLogger(__name__)


class DatasetMetadataLike(Protocol):
    """Settlement (or POS) metadata used for period-coverage checks."""

    start_date: str | None
    end_date: str | None


class BusinessRulesEngine:
    """
    Apply configurable business rules to a reconciliation report.

    Parameters
    ----------
    config:
        Platform delay / tolerance configuration (JSON-loaded or injected).
    """

    def __init__(
        self,
        config: BusinessRulesConfig | None = None,
        *,
        as_of: date | None = None,
    ) -> None:
        self._config = config or BusinessRulesConfig.load()
        self._as_of = as_of or date.today()
        self._classifier = StatusClassifier(self._config)

    def classify(
        self,
        report: ReconciliationReport,
        *,
        settlement_metadata: DatasetMetadataLike | None = None,
        order_facts: Mapping[str, OrderFacts] | Sequence[OrderFacts] | None = None,
    ) -> BusinessRulesReport:
        """
        Classify every row in ``report``.

        ``order_facts`` supplies cancelled flag, order date, and platform when
        not present on the reconciliation row alone.
        """
        facts_map = self._index_facts(order_facts)
        matched_ids = {row.order_id for row in report.matched}

        results: list[BusinessRuleResult] = []
        for row in report.matched:
            results.append(
                self._classify_row(
                    row,
                    bucket="matched",
                    facts=facts_map.get(row.order_id),
                    settlement_metadata=settlement_metadata,
                    matched_ids=matched_ids,
                )
            )
        for row in report.unmatched_pos:
            results.append(
                self._classify_row(
                    row,
                    bucket="unmatched_pos",
                    facts=facts_map.get(row.order_id),
                    settlement_metadata=settlement_metadata,
                    matched_ids=matched_ids,
                )
            )
        for row in report.unmatched_settlement:
            results.append(
                self._classify_row(
                    row,
                    bucket="unmatched_settlement",
                    facts=facts_map.get(row.order_id),
                    settlement_metadata=settlement_metadata,
                    matched_ids=matched_ids,
                )
            )

        counts = Counter(r.status.value for r in results)
        log_with_context(
            logger,
            logging.INFO,
            "Business rules classification complete",
            as_of=self._as_of.isoformat(),
            total=len(results),
            **{f"status_{k}": v for k, v in sorted(counts.items())},
        )
        return BusinessRulesReport(results=results, status_counts=dict(counts))

    def _classify_row(
        self,
        row: ReconciliationResult,
        *,
        bucket: str,
        facts: OrderFacts | None,
        settlement_metadata: DatasetMetadataLike | None,
        matched_ids: set[str],
    ) -> BusinessRuleResult:
        platform = (facts.platform if facts and facts.platform else None) or row.platform
        cancelled = bool(facts.cancelled) if facts else False
        order_date = facts.order_date if facts else None
        unmatched_settlement = bucket == "unmatched_settlement"

        if bucket == "matched":
            status = self._classifier.classify_matched(
                cancelled=cancelled,
                difference=row.difference,
                platform=platform,
                financial_status=getattr(row, "financial_status", None),
            )
        elif bucket == "unmatched_pos":
            status = self._classifier.classify_unmatched_pos(
                cancelled=cancelled,
                platform=platform,
                order_date=order_date,
                coverage=settlement_metadata,
                as_of=self._as_of,
                is_duplicate_settlement=False,
            )
        else:
            status = self._classifier.classify_unmatched_settlement(
                is_duplicate=row.order_id in matched_ids,
            )

        return BusinessRuleResult(
            order_id=row.order_id,
            platform=platform,
            status=status,
            remarks=remarks_for(status, unmatched_settlement=unmatched_settlement),
            recommendation=recommendation_for(
                status, unmatched_settlement=unmatched_settlement
            ),
            matched=row.matched,
            source_pos_document=row.source_pos_document,
            source_settlement_document=row.source_settlement_document,
        )

    @staticmethod
    def _index_facts(
        order_facts: Mapping[str, OrderFacts] | Sequence[OrderFacts] | None,
    ) -> dict[str, OrderFacts]:
        if order_facts is None:
            return {}
        if isinstance(order_facts, Mapping):
            return dict(order_facts)
        return {f.order_id: f for f in order_facts}


def order_facts_from_pos_orders(pos_orders: Sequence[object]) -> list[OrderFacts]:
    """
    Helper: build :class:`OrderFacts` from POS CanonicalOrder-like objects.

    Does not modify ingestion — read-only adapter for runners/tests.
    """
    facts: list[OrderFacts] = []
    for order in pos_orders:
        oid = str(getattr(order, "aggregator_order_id", "")).strip()
        if not oid:
            continue
        status = str(getattr(order, "status", "") or "").lower()
        cancelled = any(tok in status for tok in ("cancel", "cancelled", "canceled", "void"))
        raw_date = getattr(order, "date", None)
        order_date: date | None
        if isinstance(raw_date, datetime):
            order_date = raw_date.date()
        elif isinstance(raw_date, date):
            order_date = raw_date
        else:
            order_date = None
        platform = getattr(order, "platform", None)
        facts.append(
            OrderFacts(
                order_id=oid,
                platform=str(platform) if platform else None,
                order_date=order_date,
                cancelled=cancelled,
            )
        )
    return facts
