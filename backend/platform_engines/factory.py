"""Factory for platform financial engines."""

from __future__ import annotations

from backend.platform_engines.base_engine import PlatformFinancialEngine
from backend.platform_engines.swiggy_engine import SwiggyFinancialEngine
from backend.platform_engines.zomato_engine import ZomatoFinancialEngine


class PlatformEngineFactory:
    """Resolve a platform key to its financial engine (Open/Closed)."""

    def __init__(self) -> None:
        self._engines: dict[str, PlatformFinancialEngine] = {
            "zomato": ZomatoFinancialEngine(),
            "swiggy": SwiggyFinancialEngine(),
        }

    def register(self, platform: str, engine: PlatformFinancialEngine) -> None:
        self._engines[platform.strip().lower()] = engine

    def get(self, platform: str | None) -> PlatformFinancialEngine | None:
        if not platform:
            return None
        key = str(platform).strip().lower()
        if key in self._engines:
            return self._engines[key]
        # Soft aliases
        if "zomato" in key:
            return self._engines.get("zomato")
        if "swiggy" in key:
            return self._engines.get("swiggy")
        return None

    def supported_platforms(self) -> tuple[str, ...]:
        return tuple(sorted(self._engines.keys()))
