"""
Thin integration pipeline — wires existing Sprint modules without redesign.

POS Ingestion → Settlement Ingestion → Reconciliation → Business Rules
"""

from __future__ import annotations

import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Sequence
from uuid import uuid4

# Allow imports when launched from omni-backend/
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.agreement_engine import (  # noqa: E402
    AgreementService,
    AgreementStore,
    AgreementVerifier,
)
from backend.agreement_engine.report import build_coverage  # noqa: E402
from backend.analytics import AnalyticsEngine  # noqa: E402
from backend.intelligence import BusinessIntelligenceEngine  # noqa: E402
from backend.data_quality import resolve_outlet  # noqa: E402
from backend.business_rules import (  # noqa: E402
    BusinessRulesConfig,
    BusinessRulesEngine,
    order_facts_from_pos_orders,
)
from backend.ingestion import PosUploadService  # noqa: E402
from backend.ingestion.logging_utils import log_with_context  # noqa: E402
from backend.ingestion.models import CanonicalOrder as PosOrder  # noqa: E402
from backend.platform_engines import SettlementFinancialIndex  # noqa: E402
from backend.reconciliation import ReconciliationEngine  # noqa: E402
from backend.settlement import SettlementUploadService  # noqa: E402

logger = logging.getLogger(__name__)


@dataclass
class PipelineSession:
    """In-memory staged upload session (POS then settlement then run)."""

    session_id: str
    pos_files: list[tuple[str, bytes]] = field(default_factory=list)
    settlement_files: list[tuple[str, bytes]] = field(default_factory=list)
    pos_summary: dict[str, Any] | None = None
    settlement_summary: dict[str, Any] | None = None
    # Sprint 5A — upload intelligence / session protection
    pos_locked: bool = False
    upload_history: list[dict[str, Any]] = field(default_factory=list)
    pos_previews: list[dict[str, Any]] = field(default_factory=list)
    settlement_previews: list[dict[str, Any]] = field(default_factory=list)
    coverage: dict[str, Any] | None = None
    uploaded_by: str = "operator"
    # Sprint 6B — optional commercial agreement (independent of financial engines)
    agreement_store: AgreementStore = field(default_factory=AgreementStore)
    agreement_summary: dict[str, Any] | None = None


_SESSIONS: dict[str, PipelineSession] = {}


def get_or_create_session(session_id: str | None = None) -> PipelineSession:
    sid = session_id or str(uuid4())
    if sid not in _SESSIONS:
        _SESSIONS[sid] = PipelineSession(session_id=sid)
    return _SESSIONS[sid]


def get_agreement_service(session: PipelineSession) -> AgreementService:
    return AgreementService(store=session.agreement_store)


class OmniPipeline:
    """
    Integration façade over existing engines.

    Does not reimplement reconciliation or business rules — only orchestrates.
    """

    def __init__(self, *, as_of: date | None = None) -> None:
        self._as_of = as_of or date.today()
        self._pos = PosUploadService()
        self._settlement = SettlementUploadService(reference_date=self._as_of)
        self._recon = ReconciliationEngine()
        self._rules = BusinessRulesEngine(
            config=BusinessRulesConfig.load(),
            as_of=self._as_of,
        )

    def ingest_pos(self, files: Sequence[tuple[str, bytes]]) -> dict[str, Any]:
        result = self._pos.ingest(list(files))
        meta = result.metadata
        return {
            "total_files": meta.total_files,
            "total_orders": meta.total_orders,
            "cancelled_orders": meta.cancelled_orders,
            "eligible_orders": meta.eligible_orders,
            "duplicate_orders": meta.duplicate_orders,
            "date_range": {"from": meta.start_date, "to": meta.end_date},
            "outlets": list(meta.outlets),
            "currency": meta.currency,
            "platform": meta.platform,
            "source": meta.source,
        }

    def ingest_settlement(self, files: Sequence[tuple[str, bytes]]) -> dict[str, Any]:
        result = self._settlement.ingest(list(files))
        meta = result.metadata
        return {
            "total_files": meta.total_files,
            "total_orders": meta.total_orders,
            "platforms": list(meta.platforms),
            "date_range": {"from": meta.start_date, "to": meta.end_date},
            "null_order_ids": meta.null_order_ids,
            "negative_amounts": meta.negative_amounts,
            "currency": meta.currency,
            "platform": meta.platform,
            "source": meta.source,
        }

    def run(
        self,
        pos_files: Sequence[tuple[str, bytes]],
        settlement_files: Sequence[tuple[str, bytes]],
        *,
        agreement_store: AgreementStore | None = None,
    ) -> dict[str, Any]:
        """Full pipeline → dashboard summary + FE-compatible row data."""
        pos_result = self._pos.ingest(list(pos_files))
        settle_result = self._settlement.ingest(list(settlement_files))
        # Sprint 6A — always build financial index when settlement uploads exist so
        # live /api/reconcile enters PlatformEngineFactory (not legacy AmountCalculator).
        financial_index: SettlementFinancialIndex | None = None
        if settlement_files:
            financial_index = SettlementFinancialIndex().load_files(list(settlement_files))
        recon = self._recon.reconcile(
            pos_result.dataset,
            settle_result.dataset,
            financial_index=financial_index,
        )
        facts = order_facts_from_pos_orders(pos_result.dataset.orders())
        classified = self._rules.classify(
            recon,
            settlement_metadata=settle_result.metadata,
            order_facts=facts,
        )

        pos_by_id = {o.aggregator_order_id: o for o in pos_result.dataset.orders()}
        # Classify order matches recon.all_results order — zip to avoid order_id collisions
        # (duplicate POS IDs can appear as matched + unmatched_pos).
        classified_by_index = list(classified.results)
        all_recon = list(recon.all_results)
        if len(classified_by_index) != len(all_recon):
            status_by_id = {}
            for rule in classified_by_index:
                prev = status_by_id.get(rule.order_id)
                if prev is None or (rule.matched and not prev.matched):
                    status_by_id[rule.order_id] = rule
            rows = [
                self._to_api_row(r, pos_by_id.get(r.order_id), status_by_id.get(r.order_id))
                for r in all_recon
            ]
        else:
            rows = [
                self._to_api_row(r, pos_by_id.get(r.order_id), rule)
                for r, rule in zip(all_recon, classified_by_index)
            ]

        # Sprint 6B — optional commercial verification (post-pass; does not alter 6A math)
        store = agreement_store
        active = store.active() if store else None
        AgreementVerifier(store).enrich_rows(rows)
        coverage = build_coverage(
            rows,
            unknown_terms=active.rules.unknown_count() if active else 0,
            agreement_available=active is not None,
        )

        status_counts = dict(classified.status_counts)

        # Sprint 7A — Analytics Engine is the single source of truth for KPIs
        analytics_report = AnalyticsEngine().build(
            rows,
            pos_metadata={
                "total_orders": pos_result.metadata.total_orders,
                "cancelled_orders": pos_result.metadata.cancelled_orders,
                "eligible_orders": pos_result.metadata.eligible_orders,
            },
            settlement_metadata={
                "total_orders": settle_result.metadata.total_orders,
            },
            status_counts=status_counts,
            recon_totals={
                "unmatched_settlement": len(recon.unmatched_settlement),
                "unmatched_pos": len(recon.unmatched_pos),
                "total_expected": float(recon.summary.total_expected) if recon.summary else 0.0,
                "total_settled": float(recon.summary.total_settled) if recon.summary else 0.0,
                "total_difference": float(recon.summary.total_difference) if recon.summary else 0.0,
                "duplicate_settlement": status_counts.get("DUPLICATE_SETTLEMENT", 0),
                "manual_review": status_counts.get("MANUAL_REVIEW", 0),
                "unknown_agreement_terms": coverage.unknown_agreement_terms,
                "agreement_available": coverage.agreement_available,
            },
        )
        # Sprint 8 — Business Intelligence Decision Engine (deterministic, no AI)
        bi_report = BusinessIntelligenceEngine().build(analytics_report)
        dashboard = dict(analytics_report.dashboard)
        dashboard["unmatched_orders"] = len(recon.unmatched_pos)

        cross_checks = self._cross_check(dashboard, rows, status_counts)

        log_with_context(
            logger,
            logging.INFO,
            "Pipeline complete",
            matched=dashboard["matched_orders"],
            unmatched_pos=dashboard["unmatched_orders"],
            financial_discrepancy=dashboard["financial_discrepancy"],
            recoverable=dashboard["recoverable_amount"],
            agreement_available=coverage.agreement_available,
        )

        return {
            "message": "Success",
            "pos_summary": {
                "total_files": pos_result.metadata.total_files,
                "total_orders": pos_result.metadata.total_orders,
                "cancelled_orders": pos_result.metadata.cancelled_orders,
                "eligible_orders": pos_result.metadata.eligible_orders,
                "date_range": {
                    "from": pos_result.metadata.start_date,
                    "to": pos_result.metadata.end_date,
                },
                "outlets": list(pos_result.metadata.outlets),
            },
            "settlement_summary": {
                "total_files": settle_result.metadata.total_files,
                "total_orders": settle_result.metadata.total_orders,
                "platforms": list(settle_result.metadata.platforms),
                "date_range": {
                    "from": settle_result.metadata.start_date,
                    "to": settle_result.metadata.end_date,
                },
            },
            "agreement_summary": store.to_dict() if store else {"count": 0, "active": None},
            "business_rules_summary": status_counts,
            "analytics": analytics_report.to_dict(),
            "business_intelligence": bi_report.to_dict(),
            "dashboard": dashboard,
            "cross_checks": cross_checks,
            "data": rows,
        }

    def _to_api_row(
        self,
        recon_row: Any,
        pos: PosOrder | None,
        rule: Any,
    ) -> dict[str, Any]:
        status = rule.status.value if rule else ("Matched" if recon_row.matched else "Flagged")
        legacy = {
            "RECONCILED": "Matched",
            "FINANCIALLY_RECONCILED": "Matched",
            "AMOUNT_MISMATCH": "Flagged",
            "FINANCIAL_DISCREPANCY": "Flagged",
            "PENDING": "Under Review",
            "NOT_RECONCILED": "Flagged",
            "CANCELLED": "Under Review",
            "DUPLICATE_SETTLEMENT": "Flagged",
            "MANUAL_REVIEW": "Under Review",
        }.get(status, "Flagged")

        date_str = "—"
        outlet_raw = "—"
        if pos is not None:
            if pos.date is not None:
                date_str = (
                    pos.date.strftime("%Y-%m-%d %H:%M:%S")
                    if isinstance(pos.date, datetime)
                    else str(pos.date)
                )
            if pos.outlet:
                outlet_raw = pos.outlet

        # Sprint 9 — never emit Unknown; map RID / labels to canonical outlets
        outlet_resolution = resolve_outlet(outlet_raw)
        outlet = outlet_resolution.display_name

        calculated = float(
            recon_row.calculated_payout
            if getattr(recon_row, "calculated_payout", None) is not None
            else (recon_row.expected_amount or 0)
        )
        actual = float(
            recon_row.actual_payout
            if getattr(recon_row, "actual_payout", None) is not None
            else (recon_row.settled_amount or 0)
        )
        financial_diff = (
            float(recon_row.financial_difference)
            if getattr(recon_row, "financial_difference", None) is not None
            else (
                float(recon_row.difference)
                if recon_row.difference is not None
                else actual - calculated
            )
        )
        pos_sale = float(
            recon_row.pos_sale
            if getattr(recon_row, "pos_sale", None) is not None
            else ((pos.expected_amount if pos else 0) or 0)
        )
        gov = float(getattr(recon_row, "gross_order_value", None) or 0)
        deductions = float(getattr(recon_row, "total_deductions", None) or 0)

        remarks = getattr(recon_row, "explanation", None) or recon_row.remarks
        if rule and rule.remarks and status in {
            "PENDING",
            "NOT_RECONCILED",
            "CANCELLED",
            "MANUAL_REVIEW",
            "DUPLICATE_SETTLEMENT",
        }:
            remarks = rule.remarks

        return {
            "Date": date_str,
            "Order ID": recon_row.order_id,
            "Platform": recon_row.platform or (pos.platform if pos else "Unknown"),
            "Outlet": outlet,
            "Outlet Original": outlet_resolution.original,
            "Outlet Mapped": outlet_resolution.mapped,
            "Expected Amount": round(calculated, 2),
            "Settled Amount": round(actual, 2),
            "Discrepancy": round(financial_diff, 2),
            "POS Sale": round(pos_sale, 2),
            "Gross Order Value": round(gov, 2),
            "Total Deductions": round(deductions, 2),
            "Calculated Payout": round(calculated, 2),
            "Actual Payout": round(actual, 2),
            "Financial Difference": round(financial_diff, 2),
            "Financial Status": getattr(recon_row, "financial_status", None) or status,
            "Platform Formula": getattr(recon_row, "formula_used", None) or "",
            "Explanation": getattr(recon_row, "explanation", None) or "",
            "Deduction Summary": getattr(recon_row, "deduction_summary", None) or {},
            "Financial Breakdown": getattr(recon_row, "financial_breakdown", None) or {},
            "Status": status,
            "LegacyStatus": legacy,
            "Remarks": remarks,
            "Recommendation": rule.recommendation if rule else "",
            "Matched": recon_row.matched,
            "Source POS": recon_row.source_pos_document,
            "Source Settlement": recon_row.source_settlement_document,
        }

    @staticmethod
    def _cross_check(
        dashboard: dict[str, Any],
        rows: list[dict[str, Any]],
        status_counts: dict[str, int],
    ) -> dict[str, Any]:
        row_status_counts: dict[str, int] = {}
        for row in rows:
            st = str(row.get("Status", ""))
            row_status_counts[st] = row_status_counts.get(st, 0) + 1

        matched_rows = sum(1 for r in rows if r.get("Matched"))
        recoverable_from_rows = sum(
            max(
                float(r.get("Calculated Payout") or r.get("Expected Amount") or 0)
                - float(r.get("Actual Payout") or r.get("Settled Amount") or 0),
                0,
            )
            for r in rows
            if r.get("Status") == "FINANCIAL_DISCREPANCY"
        )
        recoverable_from_rows = round(recoverable_from_rows, 2)

        checks = {
            "status_counts_match_rows": status_counts == row_status_counts,
            "status_counts": status_counts,
            "row_status_counts": row_status_counts,
            "matched_dashboard_vs_rows": dashboard["matched_orders"] == matched_rows,
            "recoverable_dashboard_vs_rows": abs(
                float(dashboard["recoverable_amount"]) - recoverable_from_rows
            )
            <= 0.02,
            "recoverable_from_rows": recoverable_from_rows,
            "row_count": len(rows),
        }
        checks["passed"] = (
            checks["status_counts_match_rows"]
            and checks["matched_dashboard_vs_rows"]
            and checks["recoverable_dashboard_vs_rows"]
        )
        return checks
