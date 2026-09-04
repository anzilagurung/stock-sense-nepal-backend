from app.analysis.rules.base import (
    SectorRules,
    MetricRule,
    CategoryDefinition,
    Direction,
    Band,
)
from app.analysis.rules.commercial_bank import COMMERCIAL_BANK_RULES

SECTOR_RULES: dict[str, SectorRules] = {
    "Commercial Banks": COMMERCIAL_BANK_RULES,
}


def get_rules_for_sector(sector: str) -> SectorRules | None:
    return SECTOR_RULES.get(sector)


__all__ = [
    "SectorRules",
    "MetricRule",
    "CategoryDefinition",
    "Direction",
    "Band",
    "SECTOR_RULES",
    "get_rules_for_sector",
]
