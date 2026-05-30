"""Pydantic schemas for API request/response models."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class CountryTier(str, Enum):
    TIER_1 = "urban_developing"
    TIER_2 = "mixed_rural_urban"
    TIER_3 = "primarily_rural"
    TIER_4 = "conflict_post_conflict"


class CountryProfileCreate(BaseModel):
    name: str = Field(..., example="South Sudan")
    iso_code: str = Field(..., min_length=2, max_length=3, example="SSD")
    tier: CountryTier
    estimated_population: int = Field(..., gt=0)
    area_sq_km: float = Field(..., gt=0)
    num_regions: int = Field(..., gt=0)
    num_districts: int = Field(..., gt=0)
    languages: List[str] = []
    existing_admin_divisions: Dict[str, int] = {}
    has_street_names: bool = False
    has_house_numbers: bool = False
    has_any_addressing: bool = False
    urban_percentage: float = 0.0
    literacy_rate: float = 0.0
    mobile_penetration: float = 0.0
    internet_penetration: float = 0.0


class CountryProfileResponse(BaseModel):
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

    class Config:
        from_attributes = True


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
    action: Optional[str] = None


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
    name: str
    region_code: str
    district_code: str
    center_lat: float
    center_lng: float
    boundary_geojson: Optional[Dict[str, Any]] = None
    population: Optional[int] = None
    landmarks: Optional[List[Dict[str, Any]]] = None


class ZoneResponse(BaseModel):
    id: int
    postal_code: str
    name: str
    region_name: Optional[str] = None
    district_name: Optional[str] = None
    center_lat: float
    center_lng: float
    area_sq_km: Optional[float] = None
    population: Optional[int] = None
    landmarks: Optional[List[Dict[str, Any]]] = None
    boundary_geojson: Optional[Dict[str, Any]] = None
    status: str = "active"


class LookupByCoordinates(BaseModel):
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")


class LookupResult(BaseModel):
    found: bool
    postal_code: Optional[str] = None
    zone_name: Optional[str] = None
    district: Optional[str] = None
    region: Optional[str] = None
    nearby_landmarks: Optional[List[Dict[str, Any]]] = None
    full_address_suggestion: Optional[str] = None
    nearest_code: Optional[str] = None
    message: Optional[str] = None


class SearchQuery(BaseModel):
    query: str
    country: str


class SearchResult(BaseModel):
    zone_results: List[Dict[str, Any]] = []
    landmark_results: List[Dict[str, Any]] = []


class USSDRequest(BaseModel):
    session_id: str
    phone_number: str
    text: str = ""
    service_code: str


class USSDResponse(BaseModel):
    response: str
    type: str  # "CON" or "END"


class PolicyDocumentResponse(BaseModel):
    policy_document: str
    implementation_guide: str
