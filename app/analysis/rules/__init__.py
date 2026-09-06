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
from app.analysis.rules.hotels_tourism import HOTELS_TOURISM_RULES
from app.analysis.rules.hydro_power import HYDRO_POWER_RULES
from app.analysis.rules.investment import INVESTMENT_RULES
from app.analysis.rules.life_insurance import LIFE_INSURANCE_RULES
from app.analysis.rules.manufacturing import MANUFACTURING_RULES
from app.analysis.rules.microfinance import MICROFINANCE_RULES
from app.analysis.rules.mutual_fund import MUTUAL_FUND_RULES
from app.analysis.rules.non_life_insurance import NON_LIFE_INSURANCE_RULES
from app.analysis.rules.others import OTHERS_RULES
from app.analysis.rules.tradings import TRADINGS_RULES

SECTOR_RULES: dict[str, SectorRules] = {
    "Commercial Banks": COMMERCIAL_BANK_RULES,
    "Development Banks": DEVELOPMENT_BANK_RULES,
    "Finance": FINANCE_RULES,
    "Hotels And Tourism": HOTELS_TOURISM_RULES,
    "Hydro Power": HYDRO_POWER_RULES,
    "Investment": INVESTMENT_RULES,
    "Life Insurance": LIFE_INSURANCE_RULES,
    "Manufacturing And Processing": MANUFACTURING_RULES,
    "Microfinance": MICROFINANCE_RULES,
    "Mutual Fund": MUTUAL_FUND_RULES,
    "Non Life Insurance": NON_LIFE_INSURANCE_RULES,
    "Others": OTHERS_RULES,
    "Tradings": TRADINGS_RULES,
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
