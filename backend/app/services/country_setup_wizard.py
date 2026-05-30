"""Country Setup Wizard — designs postal code systems from scratch."""

from dataclasses import dataclass, field as dfield
from typing import List, Optional, Dict, Any
from enum import Enum
import json

from app.models.schemas import (
    CountryTier,
    CountryProfileCreate,
    CodeFormatResponse,
    AnalysisRecommendation,
    SpecialConsideration,
    CountryAnalysisResponse,
)


class PostalSystemDesigner:
    """Designs an entire postal code system for a country from scratch."""

    def __init__(self, profile: CountryProfileCreate):
        self.profile = profile

    def analyze_country(self) -> CountryAnalysisResponse:
        pop = self.profile.estimated_population
        area = self.profile.area_sq_km
        tier = CountryTier(self.profile.tier)

        if pop < 500_000:
            code_length, levels = 4, 3
        elif pop < 5_000_000:
            code_length, levels = 5, 4
        elif pop < 50_000_000:
            code_length, levels = 6, 4
        else:
            code_length, levels = 7, 5

        if tier == CountryTier.TIER_3:
            people_per_zone = 2000
        elif tier == CountryTier.TIER_1:
            people_per_zone = 8000
        else:
            people_per_zone = 5000

        estimated_zones = pop // people_per_zone
        code_format = self._design_code_format(code_length)

        return CountryAnalysisResponse(
            country=self.profile.name,
            population=pop,
            area_sq_km=area,
            population_density=pop / area,
            tier=tier.value,
            recommendation=AnalysisRecommendation(
                code_length=code_length,
                code_format=code_format,
                hierarchy_levels=levels,
                estimated_total_zones=estimated_zones,
                people_per_zone_target=people_per_zone,
                implementation_timeline_months=self._estimate_timeline(),
                estimated_cost_usd=self._estimate_cost(),
            ),
            hierarchy=self._design_hierarchy(levels),
            special_considerations=self._get_considerations(),
        )

    def _design_code_format(self, length: int) -> CodeFormatResponse:
        formats = {
            4: CodeFormatResponse(
                pattern="CC##D", display="CC##D",
                breakdown={"CC": "City prefix (first 2 letters)", "##": "Zone number (01-99)", "D": "Direction from city center (N, NE, E, SE, S, SW, W, NW)"},
                max_regions=99, max_districts_per_region=0,
                max_zones_per_district=99, total_capacity=9801, example="JU01N",
            ),
            5: CodeFormatResponse(
                pattern="CC##D", display="CC##D",
                breakdown={"CC": "City prefix (first 2 letters)", "##": "Zone number (01-99)", "D": "Direction from city center (N, NE, E, SE, S, SW, W, NW)"},
                max_regions=99, max_districts_per_region=9,
                max_zones_per_district=99, total_capacity=88209, example="JU01N",
            ),
            6: CodeFormatResponse(
                pattern="CC##D", display="CC##D",
                breakdown={"CC": "City prefix (first 2 letters)", "##": "Zone number (01-99)", "D": "Direction from city center (N, NE, E, SE, S, SW, W, NW)"},
                max_regions=99, max_districts_per_region=99,
                max_zones_per_district=99, total_capacity=970299, example="JU01N",
            ),
            7: CodeFormatResponse(
                pattern="CC##D", display="CC##D",
                breakdown={"CC": "City prefix (first 2 letters)", "##": "Zone number (01-99)", "D": "Direction from city center (N, NE, E, SE, S, SW, W, NW)"},
                max_regions=99, max_districts_per_region=99,
                max_zones_per_district=999, total_capacity=9702099, example="JU01N",
            ),
        }
        return formats.get(length, formats[6])

    def _design_hierarchy(self, levels: int) -> list:
        base = [
            {"level": 0, "name": "Country", "local_name": self.profile.name,
             "code_digits": 0, "description": "Top level — entire country", "source": "Country boundary"},
            {"level": 1, "name": "Region", "local_name": self._get_local_term("region"),
             "code_digits": 2, "description": "Major administrative divisions",
             "source": "Existing regional/state boundaries or create new ones",
             "estimated_count": self.profile.num_regions,
             "how_to_define": ["Use existing administrative boundaries", "Import from government records",
                               "Draw on map following natural boundaries", "Consider ethnic/linguistic regions"]},
            {"level": 2, "name": "District", "local_name": self._get_local_term("district"),
             "code_digits": 2, "description": "Sub-regional divisions",
             "source": "Existing district boundaries or subdivide regions",
             "estimated_count": self.profile.num_districts,
             "how_to_define": ["Use existing district/county boundaries", "Auto-subdivide regions by population",
                               "Follow major road networks", "Consider market/trading areas"]},
            {"level": 3, "name": "Postal Zone", "local_name": "Postal Zone", "code_digits": 2,
             "description": "Delivery zones — the actual postal code",
             "source": "Algorithm-generated + manual adjustment",
             "how_to_define": ["Auto-generate based on population density", "Snap to roads and rivers",
                               "Group nearby villages together", "Keep urban neighborhoods separate"]},
        ]
        if levels >= 5:
            base.append({"level": 4, "name": "Sub-Zone", "local_name": "Delivery Area",
                         "code_digits": 1, "description": "Fine-grained areas within postal zones",
                         "source": "For dense urban areas only"})
        return base[: levels + 1]

    def _get_local_term(self, term: str) -> str:
        local_terms = {
            "region": {"default": "Region", "french_africa": "Région", "arabic": "منطقة", "portuguese_africa": "Região"},
            "district": {"default": "District", "french_africa": "Département", "arabic": "مقاطعة", "portuguese_africa": "Distrito"},
        }
        return local_terms.get(term, {}).get("default", term.title())

    def _get_considerations(self) -> list:
        considerations = []
        if not self.profile.has_street_names:
            considerations.append(SpecialConsideration(
                issue="No street names exist",
                solution="Postal codes become the PRIMARY way to identify locations. Make zones small enough to be useful without street addresses.",
                action="Consider adding landmark-based sub-addressing (e.g., 01-05-12 near Central Market)",
            ))
        if self.profile.literacy_rate < 0.5:
            considerations.append(SpecialConsideration(
                issue="Low literacy rate",
                solution="Use simple numeric codes (no letters). Consider color-coding for regions. Use visual/icon-based signage.",
                action="Design visual postal code signs with colors and symbols",
            ))
        if self.profile.mobile_penetration > 0.3:
            considerations.append(SpecialConsideration(
                issue="Mobile phones available",
                solution="Build USSD/SMS lookup service so people can find their postal code via basic phone.",
                action="Integrate USSD gateway for code lookup by SMS",
            ))
        if self.profile.tier == CountryTier.TIER_4.value:
            considerations.append(SpecialConsideration(
                issue="Post-conflict / unstable areas",
                solution="Design flexible zones that can be updated as displaced populations return. Leave code gaps for future zones.",
                action="Use only 50% of available codes initially, reserve rest for future growth",
            ))
        if self.profile.urban_percentage < 30:
            considerations.append(SpecialConsideration(
                issue="Primarily rural population",
                solution="Rural zones can be larger in area but should contain similar population counts. Use landmarks as reference points.",
                action="Map landmarks during zone creation, name zones after prominent landmarks",
            ))
        considerations.append(SpecialConsideration(
            issue="Future growth",
            solution="Reserve code ranges for new zones. Urban areas will need splitting as they grow.",
            action="Only assign codes 01-70 initially per district, reserve 71-99 for future expansion",
        ))
        return considerations

    def _estimate_timeline(self) -> int:
        pop = self.profile.estimated_population
        if pop < 1_000_000:
            return 6
        elif pop < 10_000_000:
            return 12
        elif pop < 50_000_000:
            return 18
        return 24

    def _estimate_cost(self) -> dict:
        pop = self.profile.estimated_population
        zones = pop // 5000
        return {
            "software_platform": 50000,
            "zone_mapping": zones * 50,
            "field_verification": zones * 100,
            "training": 20000,
            "signage_printing": zones * 200,
            "total_estimated": 50000 + zones * 50 + zones * 100 + 20000 + zones * 200,
            "annual_maintenance": 30000,
        }
