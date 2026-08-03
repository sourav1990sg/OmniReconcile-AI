"""Recommendation cards derived from insights, risks, and opportunities."""

from __future__ import annotations

from backend.intelligence.models import IntelligenceCard
from backend.intelligence.rules import SEVERITY_RANK


def _dedupe_key(card: IntelligenceCard) -> str:
    return f"{card.recommended_action.strip().lower()}::{card.domain}"


def build_recommendation_cards(
    *,
    insights: list[IntelligenceCard],
    risks: list[IntelligenceCard],
    opportunities: list[IntelligenceCard],
) -> list[IntelligenceCard]:
    """
    Collapse overlapping actions into recommendation cards.
    Deterministic: highest severity wins; confidence = max of sources.
    """
    best: dict[str, IntelligenceCard] = {}

    for src in [*risks, *opportunities, *insights]:
        key = _dedupe_key(src)
        rec = IntelligenceCard(
            id=f"rec-{src.id}",
            title=src.recommended_action.rstrip("."),
            description=src.description,
            severity=src.severity,
            business_impact=src.business_impact,
            recommended_action=src.recommended_action,
            supporting_metrics=dict(src.supporting_metrics),
            confidence=src.confidence,
            category="recommendation",
            domain=src.domain,
        )
        existing = best.get(key)
        if existing is None:
            best[key] = rec
            continue
        if SEVERITY_RANK[rec.severity] > SEVERITY_RANK[existing.severity]:
            best[key] = rec
        elif (
            SEVERITY_RANK[rec.severity] == SEVERITY_RANK[existing.severity]
            and rec.confidence > existing.confidence
        ):
            best[key] = rec

    ranked = sorted(
        best.values(),
        key=lambda c: (-SEVERITY_RANK[c.severity], -c.confidence, c.title),
    )
    # Stable ids by rank
    out: list[IntelligenceCard] = []
    for i, card in enumerate(ranked, start=1):
        out.append(
            IntelligenceCard(
                id=f"recommendation-{i}",
                title=card.title,
                description=card.description,
                severity=card.severity,
                business_impact=card.business_impact,
                recommended_action=card.recommended_action,
                supporting_metrics=card.supporting_metrics,
                confidence=card.confidence,
                category="recommendation",
                domain=card.domain,
            )
        )
    return out
