"""Configurable platform rules (settlement delay, tolerances)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from backend.ingestion.logging_utils import log_with_context

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "platform_rules.json"


@dataclass(frozen=True)
class PlatformRuleConfig:
    """Per-platform business-rule configuration."""

    platform: str
    delay_days: int
    zero_difference_tolerance: Decimal = Decimal("0.00")

    def __post_init__(self) -> None:
        if self.delay_days < 0:
            raise ValueError(f"delay_days must be >= 0 for platform {self.platform!r}")


@dataclass(frozen=True)
class BusinessRulesConfig:
    """Full configurable rule set loaded from JSON (not hardcoded delays)."""

    platforms: Mapping[str, PlatformRuleConfig]
    default: PlatformRuleConfig

    def for_platform(self, platform: str | None) -> PlatformRuleConfig:
        if not platform:
            return self.default
        key = platform.strip().lower()
        if key in self.platforms:
            return self.platforms[key]
        # Accept "Swiggy" / "Zomato" etc.
        for name, cfg in self.platforms.items():
            if name.lower() == key:
                return cfg
        return self.default

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> BusinessRulesConfig:
        platforms_raw = raw.get("platforms") or {}
        default_raw = raw.get("default") or {"delay_days": 7}
        platforms = {
            str(name).lower(): PlatformRuleConfig(
                platform=str(name).lower(),
                delay_days=int(cfg.get("delay_days", 7)),
                zero_difference_tolerance=Decimal(
                    str(cfg.get("zero_difference_tolerance", "0.00"))
                ),
            )
            for name, cfg in platforms_raw.items()
        }
        default = PlatformRuleConfig(
            platform="default",
            delay_days=int(default_raw.get("delay_days", 7)),
            zero_difference_tolerance=Decimal(
                str(default_raw.get("zero_difference_tolerance", "0.00"))
            ),
        )
        return cls(platforms=platforms, default=default)

    @classmethod
    def load(cls, path: str | Path | None = None) -> BusinessRulesConfig:
        config_path = Path(path) if path else _DEFAULT_CONFIG_PATH
        with config_path.open(encoding="utf-8") as fh:
            raw = json.load(fh)
        cfg = cls.from_dict(raw)
        log_with_context(
            logger,
            logging.INFO,
            "Loaded business rules config",
            path=str(config_path),
            platforms=sorted(cfg.platforms.keys()),
            default_delay_days=cfg.default.delay_days,
        )
        return cfg

    @classmethod
    def default_config(cls) -> BusinessRulesConfig:
        """In-memory defaults (still not hardcoded inside classifiers — via config object)."""
        return cls.from_dict(
            {
                "platforms": {
                    "swiggy": {"delay_days": 7, "zero_difference_tolerance": "0.00"},
                    "zomato": {"delay_days": 7, "zero_difference_tolerance": "0.00"},
                },
                "default": {"delay_days": 7, "zero_difference_tolerance": "0.00"},
            }
        )
