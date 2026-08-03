"""Confidence scoring for column-based platform detection."""

from __future__ import annotations

from backend.parsers.column_mapper import normalize_header
from backend.upload_intelligence.models import DatasetRole, DetectionCandidate, PlatformKind
from backend.upload_intelligence.profiles import DetectionProfile


class ConfidenceEngine:
    """
    Score how well a column set matches a detection profile.

    Purely schema / column driven — never uses filenames.
    """

    def __init__(self, *, match_threshold: float = 0.95) -> None:
        if not 0.0 < match_threshold <= 1.0:
            raise ValueError("match_threshold must be in (0, 1]")
        self._threshold = match_threshold

    @property
    def match_threshold(self) -> float:
        return self._threshold

    def score(
        self,
        profile: DetectionProfile,
        column_map: dict[str, str],
        columns: list[str],
    ) -> DetectionCandidate:
        roles = set(column_map.values())
        missing = tuple(r for r in profile.required_roles if r not in roles)
        mapped_required = len(profile.required_roles) - len(missing)
        required_score = (
            mapped_required / len(profile.required_roles) if profile.required_roles else 0.0
        )

        optional_mapped = sum(1 for r in profile.optional_roles if r in roles)
        optional_score = 0.0
        if profile.optional_roles:
            optional_score = 0.08 * (optional_mapped / len(profile.optional_roles))

        distinctive = self._distinctive_hits(profile, columns)
        distinctive_bonus = min(0.12, 0.06 * distinctive)

        preferred_hits = self._preferred_exact_hits(profile, columns, column_map)
        preferred_bonus = min(0.05, 0.025 * preferred_hits)

        confidence = min(1.0, required_score + optional_score + distinctive_bonus + preferred_bonus)
        # Cap confidence when required columns are missing
        if missing:
            confidence = min(confidence, required_score * 0.9)

        reasons: list[str] = []
        if not missing:
            reasons.append(f"All required {profile.platform.value} columns present")
        else:
            reasons.append(
                f"Missing required columns for {profile.platform.value}: {', '.join(missing)}"
            )
        if distinctive:
            reasons.append(f"Distinctive headers matched ({distinctive})")
        if preferred_hits:
            reasons.append(f"Preferred exact headers matched ({preferred_hits})")
        if confidence < self._threshold:
            reasons.append(
                f"Confidence {round(confidence * 100)}% below threshold "
                f"{round(self._threshold * 100)}%"
            )

        matched = len(missing) == 0 and confidence >= self._threshold
        pct = int(round(confidence * 100))
        return DetectionCandidate(
            platform=profile.platform,
            confidence=confidence,
            confidence_pct=pct,
            matched=matched,
            column_map=dict(column_map),
            missing_required=missing,
            reasons=tuple(reasons),
            source=profile.source,
            currency=profile.currency,
            dataset_role=profile.dataset_role,
        )

    def unknown_candidate(self, *, reasons: tuple[str, ...], confidence: float = 0.12) -> DetectionCandidate:
        pct = int(round(max(0.0, min(1.0, confidence)) * 100))
        return DetectionCandidate(
            platform=PlatformKind.UNKNOWN,
            confidence=confidence,
            confidence_pct=pct,
            matched=False,
            column_map={},
            missing_required=(),
            reasons=reasons,
            source="Unknown",
            currency="INR",
            dataset_role=DatasetRole.UNKNOWN,
        )

    @staticmethod
    def _distinctive_hits(profile: DetectionProfile, columns: list[str]) -> int:
        norms = {normalize_header(c) for c in columns}
        hits = 0
        for alias in profile.distinctive_aliases:
            a = normalize_header(alias)
            if a in norms or any(a in n and len(a) >= 4 for n in norms):
                hits += 1
        return hits

    @staticmethod
    def _preferred_exact_hits(
        profile: DetectionProfile,
        columns: list[str],
        column_map: dict[str, str],
    ) -> int:
        norms = {normalize_header(c) for c in columns}
        hits = 0
        role_to_source = {role: src for src, role in column_map.items()}
        for role, preferred in profile.preferred_exact.items():
            if role not in role_to_source:
                continue
            src_norm = normalize_header(role_to_source[role])
            if src_norm in {normalize_header(p) for p in preferred}:
                hits += 1
            elif src_norm in norms and src_norm in {normalize_header(p) for p in preferred}:
                hits += 1
        return hits
