"""
Order-ID matcher for Reconciliation Engine V2.

Matches solely on Aggregator Order ID. Never touches files or DataFrames.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable


@runtime_checkable
class PosOrderLike(Protocol):
    """Minimal POS order surface required by the matcher."""

    aggregator_order_id: str
    expected_amount: object
    platform: str | None
    source_file: str | None


@runtime_checkable
class SettlementOrderLike(Protocol):
    """Minimal settlement order surface required by the matcher."""

    aggregator_order_id: str
    settled_amount: object
    platform: str | None
    source_file: str | None


@dataclass(frozen=True)
class MatchedPair:
    """One POS order paired with one settlement order on the same ID."""

    pos: PosOrderLike
    settlement: SettlementOrderLike


@dataclass
class MatchResult:
    """Buckets produced by :class:`OrderMatcher`."""

    matched: list[MatchedPair]
    unmatched_pos: list[PosOrderLike]
    unmatched_settlement: list[SettlementOrderLike]


class OrderMatcher:
    """
    Match POS and settlement orders on Aggregator Order ID only.

    Pairing strategy (no duplicate business rules beyond mechanical pairing):
    for each shared ID, pair orders FIFO one-to-one; leftovers stay unmatched.
    """

    def match(
        self,
        pos_orders: Sequence[PosOrderLike],
        settlement_orders: Sequence[SettlementOrderLike],
    ) -> MatchResult:
        pos_index: dict[str, list[PosOrderLike]] = defaultdict(list)
        for order in pos_orders:
            oid = str(order.aggregator_order_id).strip()
            if oid:
                pos_index[oid].append(order)

        settle_index: dict[str, list[SettlementOrderLike]] = defaultdict(list)
        for order in settlement_orders:
            oid = str(order.aggregator_order_id).strip()
            if oid:
                settle_index[oid].append(order)

        matched: list[MatchedPair] = []
        unmatched_pos: list[PosOrderLike] = []
        unmatched_settlement: list[SettlementOrderLike] = []

        all_ids = set(pos_index) | set(settle_index)
        for oid in sorted(all_ids):
            pos_list = list(pos_index.get(oid, []))
            settle_list = list(settle_index.get(oid, []))
            while pos_list and settle_list:
                matched.append(MatchedPair(pos=pos_list.pop(0), settlement=settle_list.pop(0)))
            unmatched_pos.extend(pos_list)
            unmatched_settlement.extend(settle_list)

        return MatchResult(
            matched=matched,
            unmatched_pos=unmatched_pos,
            unmatched_settlement=unmatched_settlement,
        )
