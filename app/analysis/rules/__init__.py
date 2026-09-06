from app.analysis.rules.base import (
    SectorRules,
    MetricRule,
    CategoryDefinition,
    Direction,
    Band,
)
from app.analysis.rules.commercial_bank import COMMERCIAL_BANK_RULES
from app.analysis.rules.development_bank import DEVELOPMENT_BANK_RULES
from app.analysis.rules.finance import FINANCE_RULES
from app.analysis.rules.hydro_power import HYDRO_POWER_RULES

SECTOR_RULES: dict[str, SectorRules] = {
    "Commercial Banks": COMMERCIAL_BANK_RULES,
    "Development Banks": DEVELOPMENT_BANK_RULES,
    "Finance": FINANCE_RULES,
    "Hydro Power": HYDRO_POWER_RULES,
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
