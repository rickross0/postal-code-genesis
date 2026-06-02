"""Pydantic schemas for API request/response models."""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any, Union
from enum import Enum


class CountryTier(str, Enum):
    TIER_1 = "urban_developing"
    TIER_2 = "mixed_rural_urban"
    TIER_3 = "primarily_rural"
    TIER_4 = "conflict_post_conflict"


class CountryProfileCreate(BaseModel):
    name: str
    iso_code: str = Field(min_length=2, max_length=3)
    tier: Union[CountryTier, str]
    estimated_population: int = Field(ge=0)
    area_sq_km: float = Field(ge=0)
    num_regions: int = Field(ge=0)
    num_districts: int = Field(ge=0)
    languages: Union[List[str], str] = []
    existing_admin_divisions: Union[Dict[str, int], str] = {}
    has_street_names: bool = False
    has_house_numbers: bool = False
    has_any_addressing: bool = False
    urban_percentage: float = 0.0
    literacy_rate: float = 0.0
    mobile_penetration: float = 0.0
    internet_penetration: float = 0.0
    capital_city: Optional[str] = None
    capital_lat: Optional[float] = None
    capital_lng: Optional[float] = None

    @field_validator('tier', mode='before')
    @classmethod
    def parse_tier(cls, v):
        if isinstance(v, str):
            # Try to find matching enum value
            for tier in CountryTier:
                if tier.value == v or tier.name == v:
                    return tier
            # If no match, assume it's a valid string value
            return v
        return v
    
    @field_validator('languages', mode='before')
    @classmethod
    def parse_languages(cls, v):
        if isinstance(v, str):
            return [l.strip() for l in v.split(',') if l.strip()]
        return v or []
    
    @field_validator('existing_admin_divisions', mode='before')
    @classmethod
    def parse_admin_divisions(cls, v):
        if isinstance(v, str):
            return {}
        return v or {}


class CountryProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    iso_code: str
    tier: str
    estimated_population: int
    area_sq_km: float
    num_regions: int
    num_districts: int
    languages: List[str]
    urban_percentage: float
    literacy_rate: float
    mobile_penetration: float
    capital_city: Optional[str] = None
    capital_lat: Optional[float] = None
    capital_lng: Optional[float] = None
    locked: bool = False
    boundary_geojson: Optional[Any] = None


class CodeFormatResponse(BaseModel):
    pattern: str
    display: str
    breakdown: Dict[str, str]
    max_regions: int
    max_districts_per_region: int
    max_zones_per_district: int
    total_capacity: int
    example: str



class AnalysisRecommendation(BaseModel):
    code_length: int
    code_format: CodeFormatResponse
    hierarchy_levels: int
    estimated_total_zones: int
    people_per_zone_target: int
    implementation_timeline_months: int
    estimated_cost_usd: Dict[str, Any]


class SpecialConsideration(BaseModel):
    issue: str
    solution: str
    action: str


class CountryAnalysisResponse(BaseModel):
    country: str
    population: int
    area_sq_km: float
    population_density: float
    tier: str
    recommendation: AnalysisRecommendation
    hierarchy: List[Dict[str, Any]]
    special_considerations: List[SpecialConsideration]


class ZoneCreate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    region_code: Optional[str] = None
    district_code: Optional[str] = None
    district_id: Optional[int] = None
    population: Optional[int] = 0
    area_sq_km: Optional[float] = 0.0
    lat: Optional[float] = None
    lng: Optional[float] = None
    color: Optional[str] = None
    boundary_geojson: Optional[Any] = None


class BoundaryUpdate(BaseModel):
    """Update a boundary polygon and optionally lock/unlock."""
    boundary_geojson: Optional[Any] = None
    name: Optional[str] = None
    locked: Optional[bool] = None


class ManualZoneCreate(BaseModel):
    """Create a zone by drawing a polygon on the map."""
    country_id: int
    district_id: Optional[int] = None
    region_code: Optional[str] = None
    district_code: Optional[str] = None
    boundary_geojson: Any  # Required: the drawn polygon
    name: Optional[str] = None
    population: Optional[int] = 0
    color: Optional[str] = None


class ZoneUpdate(BaseModel):
    name: Optional[str] = None
    population: Optional[int] = None
    area_sq_km: Optional[float] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    color: Optional[str] = None
    boundary_geojson: Optional[Any] = None
    status: Optional[str] = None
    locked: Optional[bool] = None


class ZoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    postal_code: str
    name: str
    center_lat: Optional[float] = None
    center_lng: Optional[float] = None
    area_sq_km: Optional[float] = None
    population: Optional[int] = None
    status: Optional[str] = None
    region_name: Optional[str] = None
    district_name: Optional[str] = None
    district_id: Optional[int] = None
    color: Optional[str] = None
    boundary_geojson: Optional[Any] = None
    locked: bool = False


class LookupResult(BaseModel):
    postal_code: str
    location_name: str
    lat: float
    lng: float
    country: str
    zone_id: int


class SearchResult(BaseModel):
    query: str
    results: List[LookupResult]


class USSDRequest(BaseModel):
    phone: str
    session_id: Optional[str] = None
    text: Optional[str] = ""


class USSDResponse(BaseModel):
    session_id: Optional[str] = None
    text: str
    response_type: str


class PolicyDocumentResponse(BaseModel):
    country_id: int
    title: str
    policy_document: str
    implementation_guide: str
    sections: List[Dict[str, Any]]
