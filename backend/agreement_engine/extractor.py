"""Rule extraction from agreement text — never guesses; low confidence → UNKNOWN."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from backend.agreement_engine.models import AgreementRules
from backend.agreement_engine.parser import ParsedDocument

# Confidence threshold below which fields stay UNKNOWN (no guessing).
LOW_CONFIDENCE = 0.55


def _money_or_pct(raw: str) -> Decimal | None:
    text = raw.strip().replace(",", "").replace("%", "")
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _parse_date(raw: str) -> date | None:
    text = raw.strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


class AgreementExtractor:
    """
    Regex / keyword extractor for commercial terms.

    If a match is weak or ambiguous, leave field UNKNOWN (unknown=True).
    """

    def extract(self, document: ParsedDocument) -> AgreementRules:
        rules = AgreementRules()
        text = document.text or ""
        if not text.strip():
            return rules

        self._extract_platform(text, rules)
        self._extract_restaurant(text, rules)
        self._extract_dates(text, rules)
        self._extract_commission(text, rules)
        self._extract_fee_line(
            text,
            rules,
            key="payment_mechanism_fee",
            patterns=(
                r"payment\s+mechanism\s+fee[^\d%]{0,40}(\d+(?:\.\d+)?)\s*%?",
                r"payment\s+fee[^\d%]{0,40}(\d+(?:\.\d+)?)\s*%?",
            ),
        )
        self._extract_clause(
            text,
            rules,
            key="advertisement_terms",
            patterns=(r"(advertisement[^\n.]{0,120})", r"(ads?\s+fee[^\n.]{0,80})"),
        )
        self._extract_clause(
            text,
            rules,
            key="promo_cost_sharing",
            patterns=(r"(promo(?:tion)?\s+cost\s+sharing[^\n.]{0,120})", r"(discount\s+sharing[^\n.]{0,80})"),
        )
        self._extract_clause(
            text,
            rules,
            key="brand_pack",
            patterns=(r"(brand\s+pack[^\n.]{0,100})",),
        )
        self._extract_fee_line(
            text,
            rules,
            key="packaging_charges",
            patterns=(r"packaging\s+charges?[^\d]{0,40}(?:₹|rs\.?\s*)?(\d+(?:\.\d+)?)",),
        )
        self._extract_fee_line(
            text,
            rules,
            key="delivery_charges",
            patterns=(r"delivery\s+charges?[^\d]{0,40}(?:₹|rs\.?\s*)?(\d+(?:\.\d+)?)",),
        )
        self._extract_clause(
            text,
            rules,
            key="cancellation_policy",
            patterns=(r"(cancellation\s+policy[^\n.]{0,160})",),
        )
        self._extract_clause(
            text,
            rules,
            key="settlement_cycle",
            patterns=(
                r"(settlement\s+cycle[^\n.]{0,80})",
                r"(payout\s+within\s+\d+\s+days?[^\n.]{0,40})",
            ),
        )
        self._extract_clause(
            text,
            rules,
            key="gst_rules",
            patterns=(r"(gst[^\n.]{0,100})", r"(section\s*9\(5\)[^\n.]{0,80})"),
        )
        self._extract_fee_line(
            text,
            rules,
            key="tds",
            patterns=(r"\btds\b[^\d%]{0,30}(\d+(?:\.\d+)?)\s*%",),
        )
        self._extract_fee_line(
            text,
            rules,
            key="tcs",
            patterns=(r"\btcs\b[^\d%]{0,30}(\d+(?:\.\d+)?)\s*%",),
        )
        self._extract_clause(
            text,
            rules,
            key="other_clauses",
            patterns=(r"(other\s+commercial\s+terms?[^\n.]{0,160})",),
            min_conf=0.45,
        )
        return rules

    def _set(
        self,
        rules: AgreementRules,
        key: str,
        value: Any,
        *,
        confidence: float,
        snippet: str,
    ) -> None:
        if value is None or confidence < LOW_CONFIDENCE:
            # Explicit UNKNOWN — do not guess
            rules.set_field(key, None, confidence=confidence, source_snippet=snippet[:200])
            return
        rules.set_field(
            key,
            value,
            confidence=confidence,
            source_snippet=snippet[:200],
            unknown_threshold=LOW_CONFIDENCE,
        )

    def _extract_platform(self, text: str, rules: AgreementRules) -> None:
        lower = text.lower()
        if re.search(r"\bzomato\b", lower):
            conf = 0.9 if lower.count("zomato") >= 1 else 0.6
            self._set(rules, "platform", "zomato", confidence=conf, snippet="zomato")
        elif re.search(r"\bswiggy\b", lower):
            conf = 0.9
            self._set(rules, "platform", "swiggy", confidence=conf, snippet="swiggy")
        else:
            self._set(rules, "platform", None, confidence=0.0, snippet="")

    def _extract_restaurant(self, text: str, rules: AgreementRules) -> None:
        patterns = (
            r"(?:restaurant|merchant|partner)\s*name\s*[:\-]\s*([A-Za-z0-9 &.'-]{3,80})",
            r"(?:this agreement is (?:made|executed) (?:by|between).{0,40}?and\s+)([A-Za-z0-9 &.'-]{3,60})",
        )
        for pat in patterns:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if m:
                name = m.group(1).strip(" .,;")
                if len(name) >= 3:
                    self._set(rules, "restaurant_name", name, confidence=0.75, snippet=m.group(0))
                    return
        self._set(rules, "restaurant_name", None, confidence=0.0, snippet="")

    def _extract_dates(self, text: str, rules: AgreementRules) -> None:
        date_specs = (
            ("agreement_date", (r"agreement\s+date\s*[:\-]\s*([0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4})",)),
            ("effective_date", (r"effective\s+(?:date|from)\s*[:\-]\s*([0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4})",)),
            ("expiry_date", (r"(?:expir(?:y|es)|valid\s+till|end\s+date)\s*[:\-]\s*([0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4})",)),
        )
        for key, pats in date_specs:
            found = False
            for pat in pats:
                m = re.search(pat, text, flags=re.IGNORECASE)
                if m:
                    d = _parse_date(m.group(1))
                    if d:
                        self._set(rules, key, d, confidence=0.8, snippet=m.group(0))
                        found = True
                        break
            if not found:
                self._set(rules, key, None, confidence=0.0, snippet="")

    def _extract_commission(self, text: str, rules: AgreementRules) -> None:
        patterns = (
            r"commission(?:\s+rate|\s+percentage|\s+%)?\s*(?:of\s+)?[:\-]?\s*(\d+(?:\.\d+)?)\s*%",
            r"(\d+(?:\.\d+)?)\s*%\s+commission",
            r"service\s+fee\s*(?:of\s+)?[:\-]?\s*(\d+(?:\.\d+)?)\s*%",
        )
        for pat in patterns:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if m:
                val = _money_or_pct(m.group(1))
                if val is not None:
                    self._set(rules, "commission_pct", val, confidence=0.85, snippet=m.group(0))
                    return
        self._set(rules, "commission_pct", None, confidence=0.0, snippet="")

    def _extract_fee_line(
        self,
        text: str,
        rules: AgreementRules,
        *,
        key: str,
        patterns: tuple[str, ...],
    ) -> None:
        for pat in patterns:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if m:
                val = _money_or_pct(m.group(1))
                if val is not None:
                    self._set(rules, key, val, confidence=0.7, snippet=m.group(0))
                    return
        self._set(rules, key, None, confidence=0.0, snippet="")

    def _extract_clause(
        self,
        text: str,
        rules: AgreementRules,
        *,
        key: str,
        patterns: tuple[str, ...],
        min_conf: float = 0.65,
    ) -> None:
        for pat in patterns:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if m:
                snippet = m.group(1).strip()
                if len(snippet) >= 8:
                    self._set(rules, key, snippet, confidence=min_conf, snippet=snippet)
                    return
        self._set(rules, key, None, confidence=0.0, snippet="")
