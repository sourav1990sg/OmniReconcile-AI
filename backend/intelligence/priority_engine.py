"""Priority action ranking — answers 'what should I do next?'"""

from __future__ import annotations

from backend.intelligence.models import IntelligenceCard, PriorityAction
from backend.intelligence.rules import SEVERITY_RANK

OWNER_BY_DOMAIN = {
    "finance": "CFO",
    "recovery": "Finance",
    "commercial": "Commercial",
    "operations": "Operations",
    "outlet": "Operations",
    "platform": "CEO",
    "general": "CEO",
}


def _impact_score(card: IntelligenceCard) -> float:
    """Deterministic score from severity + numeric metrics when present."""
    base = float(SEVERITY_RANK[card.severity]) * 100
    metrics = card.supporting_metrics or {}
    for key in (
        "recoverable",
        "outlet_recoverable",
        "total_recoverable",
        "commission_gap_pp",
        "deduction_ratio_pct",
        "cancelled_pct",
        "pending_pct",
        "share_pct",
    ):
        val = metrics.get(key)
        if isinstance(val, (int, float)):
            base += float(val)
            break
    return base + card.confidence


def build_priority_actions(
    *,
    risks: list[IntelligenceCard],
    opportunities: list[IntelligenceCard],
    recommendations: list[IntelligenceCard],
    limit: int = 8,
) -> list[PriorityAction]:
    """
    Rank next actions. Risks outrank opportunities at equal severity.
    """
    pool: list[tuple[float, IntelligenceCard]] = []
    for card in risks:
        pool.append((_impact_score(card) + 50, card))  # risk bias
    for card in opportunities:
        pool.append((_impact_score(card), card))
    # Fill from recommendations if thin
    if len(pool) < 3:
        for card in recommendations:
            pool.append((_impact_score(card) * 0.9, card))

    pool.sort(key=lambda t: (-t[0], t[1].id))
    seen_actions: set[str] = set()
    actions: list[PriorityAction] = []

    for score, card in pool:
        action_key = card.recommended_action.strip().lower()
        if action_key in seen_actions:
            continue
        seen_actions.add(action_key)
        actions.append(
            PriorityAction(
                rank=len(actions) + 1,
                title=card.title,
                description=card.description,
                severity=card.severity,
                recommended_action=card.recommended_action,
                business_impact=card.business_impact,
                owner=OWNER_BY_DOMAIN.get(card.domain, "CEO"),
                confidence=card.confidence,
                source_card_ids=[card.id],
                supporting_metrics=dict(card.supporting_metrics),
            )
        )
        if len(actions) >= limit:
            break

    return actions
