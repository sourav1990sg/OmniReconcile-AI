"""Generic column-name → semantic-role mapping utilities."""

from __future__ import annotations

from typing import Mapping, Sequence

import pandas as pd


def normalize_header(name: str) -> str:
    """Normalize a spreadsheet header for alias comparison."""
    return " ".join(name.strip().lower().replace("_", " ").split())


def matches_aliases(normalized: str, aliases: Sequence[str]) -> bool:
    """Return True when ``normalized`` equals or contains an alias."""
    for alias in aliases:
        alias_n = normalize_header(alias)
        if normalized == alias_n:
            return True
        if alias_n in normalized and len(alias_n) >= 4:
            return True
    return False


def map_columns(
    columns: pd.Index | list[str],
    *,
    aliases: Mapping[str, Sequence[str]],
    preferred_exact: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, str]:
    """
    Build ``{source_column: role}`` using alias matching on column **names**.

    Never uses positional indexes.
    """
    preferred_exact = preferred_exact or {}
    normalized = {str(col): normalize_header(str(col)) for col in columns}
    role_to_source: dict[str, str] = {}

    for role, role_aliases in aliases.items():
        preferred = tuple(preferred_exact.get(role, ()))
        chosen: str | None = None

        for source, norm in normalized.items():
            if role in role_to_source:
                break
            if norm in preferred:
                chosen = source
                break

        if chosen is None:
            for source, norm in normalized.items():
                if role in role_to_source:
                    break
                if source in role_to_source.values():
                    continue
                if not matches_aliases(norm, role_aliases):
                    continue
                if norm in {normalize_header(a) for a in role_aliases}:
                    chosen = source
                    break
                if chosen is None:
                    chosen = source

        if chosen is not None and role not in role_to_source:
            if chosen not in role_to_source.values():
                role_to_source[role] = chosen

    return {source: role for role, source in role_to_source.items()}
