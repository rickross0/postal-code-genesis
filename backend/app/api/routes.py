"""FastAPI route definitions for the Postal Code Genesis Platform."""

import logging
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional

from app.core.database import get_db
from app.models.schemas import (
    CountryProfileCreate,
    CountryProfileResponse,
    CountryAnalysisResponse,
    ZoneCreate,
    ZoneUpdate,
    ZoneResponse,
    LookupResult,
    SearchResult,
    USSDRequest,
    USSDResponse,
    PolicyDocumentResponse,
)
from app.services.country_setup_wizard import PostalSystemDesigner
from app.services.zone_creation_engine import ZoneCreationEngine
from app.services.policy_generator import PolicyDocumentGenerator
from app.services.public_lookup import LookupService
from app.services.country_lookup import CountryLookupService
from app.models.database import Country, Region, District, PostalZone, Landmark

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Countries ──────────────────────────────────────────────

@router.post("/countries", response_model=CountryProfileResponse, status_code=201)
async def create_country(
    profile: CountryProfileCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new country profile and begin postal code system design."""
    logger.info(f"CREATE COUNTRY payload: {profile.model_dump()}")
    
    # Handle tier - convert to string if it's an enum
    tier_value = profile.tier.value if hasattr(profile.tier, 'value') else str(profile.tier)
    
    # Handle languages - ensure it's a list
    languages = profile.languages
    if isinstance(languages, str):
        languages = [l.strip() for l in languages.split(',') if l.strip()]
    elif not languages:
        languages = []
    
    # Handle existing_admin_divisions
    admin_divisions = profile.existing_admin_divisions
    if not admin_divisions:
        admin_divisions = {}
    
    country = Country(
        name=profile.name,
        iso_code=profile.iso_code.upper(),
        tier=tier_value,
        estimated_population=profile.estimated_population,
        area_sq_km=profile.area_sq_km,
        num_regions=profile.num_regions,
        num_districts=profile.num_districts,
        languages=json.dumps(languages),
        has_street_names=profile.has_street_names,
        has_house_numbers=profile.has_house_numbers,
        has_any_addressing=profile.has_any_addressing,
        urban_percentage=profile.urban_percentage or 0.0,
        literacy_rate=profile.literacy_rate or 0.0,
        mobile_penetration=profile.mobile_penetration or 0.0,
        internet_penetration=profile.internet_penetration or 0.0,
        existing_admin_divisions=json.dumps(admin_divisions),
        capital_city=profile.capital_city,
        capital_lat=profile.capital_lat,
        capital_lng=profile.capital_lng,
    )
    db.add(country)
    await db.flush()
    await db.refresh(country)
    return CountryProfileResponse(
        id=country.id,
        name=country.name,
        iso_code=country.iso_code,
        tier=country.tier,
        estimated_population=country.estimated_population,
        area_sq_km=country.area_sq_km,
        num_regions=country.num_regions,
        num_districts=country.num_districts,
        languages=languages,
        urban_percentage=country.urban_percentage,
        literacy_rate=country.literacy_rate,
        mobile_penetration=country.mobile_penetration,
        capital_city=country.capital_city,
        capital_lat=country.capital_lat,
        capital_lng=country.capital_lng,
    )


@router.get("/countries", response_model=List[CountryProfileResponse])
async def list_countries(db: AsyncSession = Depends(get_db)):
    """List all countries in the platform."""
    from sqlalchemy import select
    result = await db.execute(select(Country).order_by(Country.name))
    countries = result.scalars().all()
    return [
        CountryProfileResponse(
            id=c.id, name=c.name, iso_code=c.iso_code, tier=c.tier,
            estimated_population=c.estimated_population, area_sq_km=c.area_sq_km,
            num_regions=c.num_regions, num_districts=c.num_districts,
            languages=json.loads(c.languages) if c.languages else [],
            urban_percentage=c.urban_percentage, literacy_rate=c.literacy_rate,
            mobile_penetration=c.mobile_penetration,
            capital_city=c.capital_city, capital_lat=c.capital_lat, capital_lng=c.capital_lng,
        )
        for c in countries
    ]


# ── Analysis ─────────────────────────────────────────────

@router.post("/countries/{country_id}/analyze", response_model=CountryAnalysisResponse)
async def analyze_country(country_id: int, db: AsyncSession = Depends(get_db)):
    """Analyze a country and get postal code system recommendations."""
    from sqlalchemy import select
    result = await db.execute(select(Country).where(Country.id == country_id))
    country = result.scalar_one_or_none()
    if not country:
        raise HTTPException(404, "Country not found")

    profile = CountryProfileCreate(
        name=country.name,
        iso_code=country.iso_code,
        tier=country.tier,
        estimated_population=country.estimated_population,
        area_sq_km=country.area_sq_km,
        num_regions=country.num_regions,
        num_districts=country.num_districts,
        languages=json.loads(country.languages) if country.languages else [],
        has_street_names=country.has_street_names,
        has_house_numbers=country.has_house_numbers,
        has_any_addressing=country.has_any_addressing,
        urban_percentage=country.urban_percentage,
        literacy_rate=country.literacy_rate,
        mobile_penetration=country.mobile_penetration,
        internet_penetration=country.internet_penetration,
        existing_admin_divisions=json.loads(country.existing_admin_divisions) if country.existing_admin_divisions else {},
        capital_city=country.capital_city,
        capital_lat=country.capital_lat,
        capital_lng=country.capital_lng,
    )

    designer = PostalSystemDesigner(profile)
    analysis = await designer.analyze()

    return CountryAnalysisResponse(
        country_id=country.id,
        recommendation=analysis["recommendation"],
        special_considerations=analysis["special_considerations"],
        estimated_cost_usd=analysis["estimated_cost_usd"],
    )


# ── Zones ───────────────────────────────────────────────

@router.get("/countries/{country_id}/zones", response_model=List[ZoneResponse])
async def list_zones(country_id: int, db: AsyncSession = Depends(get_db)):
    """List all zones for a country."""
    from sqlalchemy import select
    result = await db.execute(
        select(PostalZone).where(PostalZone.country_id == country_id).order_by(PostalZone.code)
    )
    zones = result.scalars().all()
    return [
        ZoneResponse(
            id=z.id, code=z.code, name=z.name,
            region_code=z.region_code, district_code=z.district_code,
            population=z.population, area_sq_km=z.area_sq_km,
            lat=z.lat, lng=z.lng,
        )
        for z in zones
    ]


@router.post("/countries/{country_id}/zones/auto-create", response_model=List[ZoneResponse])
async def auto_create_zones(
    country_id: int,
    region_code: str = Query(...),
    district_code: str = Query(...),
    target_population: int = Query(5000),
    db: AsyncSession = Depends(get_db),
):
    """Auto-create zones for a region/district based on target population."""
    from sqlalchemy import select
    
    result = await db.execute(select(Country).where(Country.id == country_id))
    country = result.scalar_one_or_none()
    if not country:
        raise HTTPException(404, "Country not found")

    engine = ZoneCreationEngine(country)
    zones = await engine.create_zones_for_district(
        region_code=region_code,
        district_code=district_code,
        target_population=target_population,
    )

    return [
        ZoneResponse(
            id=z.id, code=z.code, name=z.name,
            region_code=z.region_code, district_code=z.district_code,
            population=z.population, area_sq_km=z.area_sq_km,
            lat=z.lat, lng=z.lng,
        )
        for z in zones
    ]


# ── Districts ────────────────────────────────────────────

@router.get("/countries/{country_id}/districts")
async def list_districts(country_id: int, db: AsyncSession = Depends(get_db)):
    """List all districts for a country."""
    from sqlalchemy import select, text
    result = await db.execute(
        select(District).where(District.country_id == country_id).order_by(District.name)
    )
    districts = result.scalars().all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "code": d.code,
            "region_code": d.region_code,
            "population": d.population,
        }
        for d in districts
    ]


# ── Stats ────────────────────────────────────────────────

@router.get("/countries/{country_id}/stats")
async def get_country_stats(country_id: int, db: AsyncSession = Depends(get_db)):
    """Get statistics for a country."""
    from sqlalchemy import select, func
    
    result = await db.execute(select(Country).where(Country.id == country_id))
    country = result.scalar_one_or_none()
    if not country:
        raise HTTPException(404, "Country not found")

    # Count zones
    zones_result = await db.execute(
        select(func.count(PostalZone.id)).where(PostalZone.country_id == country_id)
    )
    num_zones = zones_result.scalar() or 0

    # Count districts
    districts_result = await db.execute(
        select(func.count(District.id)).where(District.country_id == country_id)
    )
    num_districts = districts_result.scalar() or 0

    return {
        "country_id": country_id,
        "name": country.name,
        "population": country.estimated_population,
        "num_zones": num_zones,
        "num_districts": num_districts,
    }


# ── Lookup ───────────────────────────────────────────────

@router.get("/lookup/coordinates")
async def lookup_coordinates(lat: float, lng: float, db: AsyncSession = Depends(get_db)):
    """Look up postal code by coordinates."""
    service = LookupService(db)
    result = await service.lookup_by_coordinates(lat, lng)
    if not result:
        raise HTTPException(404, "No postal zone found at these coordinates")
    return result


@router.get("/lookup/search")
async def lookup_search(query: str, country: str = None, db: AsyncSession = Depends(get_db)):
    """Search for postal codes by location name."""
    service = LookupService(db)
    results = await service.search_by_name(query, country)
    return results


@router.post("/lookup/ussd", response_model=USSDResponse)
async def ussd_lookup(request: USSDRequest, db: AsyncSession = Depends(get_db)):
    """USSD-compatible postal code lookup."""
    service = LookupService(db)
    result = await service.ussd_lookup(request.phone, request.session_id, request.text)
    return USSDResponse(
        session_id=result["session_id"],
        text=result["text"],
        response_type=result["response_type"],
    )


# ── Policy ───────────────────────────────────────────────

@router.post("/countries/{country_id}/policy", response_model=PolicyDocumentResponse)
async def generate_policy(country_id: int, db: AsyncSession = Depends(get_db)):
    """Generate policy document for a country."""
    from sqlalchemy import select
    
    result = await db.execute(select(Country).where(Country.id == country_id))
    country = result.scalar_one_or_none()
    if not country:
        raise HTTPException(404, "Country not found")

    generator = PolicyDocumentGenerator(country)
    policy = await generator.generate()

    return PolicyDocumentResponse(
        country_id=country.id,
        title=policy["title"],
        content=policy["content"],
        sections=policy["sections"],
    )


# ── Country Lookup Service ───────────────────────────────

@router.get("/countries/lookup/{name}")
async def lookup_country_by_name(name: str, db: AsyncSession = Depends(get_db)):
    """Lookup country information by name."""
    from sqlalchemy import select
    
    # Try exact match first
    result = await db.execute(
        select(Country).where(Country.name.ilike(f"%{name}%"))
    )
    country = result.scalar_one_or_none()
    
    if country:
        return {
            "name": country.name,
            "iso_code": country.iso_code,
            "population": country.estimated_population,
            "area_sq_km": country.area_sq_km,
            "capital_city": country.capital_city,
            "capital_lat": country.capital_lat,
            "capital_lng": country.capital_lng,
            "languages": json.loads(country.languages) if country.languages else [],
        }
    
    # Use external API if not found
    service = CountryLookupService()
    data = await service.lookup_country(name)
    if not data:
        raise HTTPException(404, f"Country '{name}' not found")
    
    return data


# ── City Lookup ──────────────────────────────────────────

@router.get("/cities/lookup")
async def lookup_city(query: str, country_code: str = None, db: AsyncSession = Depends(get_db)):
    """Lookup city information."""
    service = CountryLookupService()
    result = await service.lookup_city(query, country_code)
    if not result:
        raise HTTPException(404, f"City '{query}' not found")
    return result
