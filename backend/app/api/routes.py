"""FastAPI route definitions for the Postal Code Genesis Platform."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from app.core.database import get_db
from app.models.schemas import (
    CountryProfileCreate,
    CountryProfileResponse,
    CountryAnalysisResponse,
    ZoneCreate,
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
from app.models.database import Country, Region, District, PostalZone, Landmark

router = APIRouter()


# ── Countries ──────────────────────────────────────────────

@router.post("/countries", response_model=CountryProfileResponse, status_code=201)
async def create_country(
    profile: CountryProfileCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new country profile and begin postal code system design."""
    country = Country(
        name=profile.name,
        iso_code=profile.iso_code.upper(),
        tier=profile.tier.value,
        estimated_population=profile.estimated_population,
        area_sq_km=profile.area_sq_km,
        num_regions=profile.num_regions,
        num_districts=profile.num_districts,
        languages=str(profile.languages),
        has_street_names=profile.has_street_names,
        has_house_numbers=profile.has_house_numbers,
        has_any_addressing=profile.has_any_addressing,
        urban_percentage=profile.urban_percentage,
        literacy_rate=profile.literacy_rate,
        mobile_penetration=profile.mobile_penetration,
        internet_penetration=profile.internet_penetration,
        existing_admin_divisions=str(profile.existing_admin_divisions),
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
        languages=profile.languages,
        urban_percentage=country.urban_percentage,
        literacy_rate=country.literacy_rate,
        mobile_penetration=country.mobile_penetration,
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
            languages=eval(c.languages) if c.languages else [],
            urban_percentage=c.urban_percentage, literacy_rate=c.literacy_rate,
            mobile_penetration=c.mobile_penetration,
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
        languages=eval(country.languages) if country.languages else [],
        has_street_names=country.has_street_names,
        has_house_numbers=country.has_house_numbers,
        urban_percentage=country.urban_percentage,
        literacy_rate=country.literacy_rate,
        mobile_penetration=country.mobile_penetration,
    )
    designer = PostalSystemDesigner(profile)
    return designer.analyze_country()


# ── Zones ─────────────────────────────────────────────────

@router.post("/countries/{country_id}/zones/auto-create", response_model=List[ZoneResponse])
async def auto_create_zones(
    country_id: int,
    region_code: str = Query(..., description="2-digit region code"),
    district_code: str = Query(..., description="2-digit district code"),
    target_population: int = Query(5000, description="Target population per zone"),
    db: AsyncSession = Depends(get_db),
):
    """Auto-generate postal zones for a district using Voronoi tessellation."""
    from sqlalchemy import select, text

    # Get the district
    result = await db.execute(
        select(District)
        .join(Region)
        .where(Region.country_id == country_id)
        .where(District.code == district_code)
        .where(Region.code == region_code)
    )
    district = result.scalar_one_or_none()
    if not district:
        raise HTTPException(404, "District not found for given region/district codes")

    # Get the region boundary (use district boundary if available, else region)
    boundary_result = await db.execute(
        select(Region.boundary).where(Region.id == district.region_id)
    )
    boundary_wkb = boundary_result.scalar_one_or_none()

    # Get settlements/landmarks as seed points
    settlements_result = await db.execute(text("""
        SELECT ST_Y(location) AS lat, ST_X(location) AS lng, name
        FROM landmarks l
        JOIN postal_zones pz ON l.postal_zone_id = pz.id
        JOIN districts d ON pz.district_id = d.id
        WHERE d.id = :district_id
    """), {"district_id": district.id})
    settlements = [
        {"location": {"lat": r[0], "lng": r[1]}, "name": r[2]}
        for r in settlements_result.all()
    ]

    # If no settlements, use district center as single seed
    if not settlements and district.center_point:
        center_result = await db.execute(text("""
            SELECT ST_Y(:cp) AS lat, ST_X(:cp) AS lng
        """), {"cp": district.center_point})
        center = center_result.one()
        settlements = [{"location": {"lat": center[0], "lng": center[1]}, "name": district.name}]

    # Create a simple bounding box if no boundary
    if not boundary_wkb:
        # Use country boundary
        country_boundary = await db.execute(
            select(Country.boundary).where(Country.id == country_id)
        )
        boundary_wkb = country_boundary.scalar_one_or_none()

    # Use GeoJSON for the engine
    boundary_geojson = None
    if boundary_wkb:
        geojson_result = await db.execute(text("""
            SELECT ST_AsGeoJSON(:boundary) AS geojson
        """), {"boundary": boundary_wkb})
        geojson_str = geojson_result.scalar_one_or_none()
        if geojson_str:
            import json
            boundary_geojson = json.loads(geojson_str)

    # Default bounding box: create a rough polygon around district center
    if not boundary_geojson:
        center_lat, center_lng = 0.0, 0.0
        if district.center_point:
            cr = await db.execute(text("SELECT ST_Y(:cp), ST_X(:cp)"), {"cp": district.center_point})
            row = cr.one()
            center_lat, center_lng = row[0], row[1]
        boundary_geojson = {
            "type": "Polygon",
            "coordinates": [[
                [center_lng - 0.5, center_lat - 0.5],
                [center_lng + 0.5, center_lat - 0.5],
                [center_lng + 0.5, center_lat + 0.5],
                [center_lng - 0.5, center_lat + 0.5],
                [center_lng - 0.5, center_lat - 0.5],
            ]],
        }

    engine = ZoneCreationEngine()
    zones = engine.create_zones_intelligent(
        region_boundary_geojson=boundary_geojson,
        settlements=settlements,
        target_population_per_zone=target_population,
        estimated_population=district.population if hasattr(district, 'population') and district.population else target_population * 4,
    )
    zones = engine.assign_codes(zones, region_code, district_code)

    # Persist zones
    from geoalchemy2.shape import from_shape
    from shapely.geometry import shape

    created_zones = []
    for z in zones:
        boundary_shape = shape(z["boundary_geojson"]) if z.get("boundary_geojson") else None
        zone_db = PostalZone(
            district_id=district.id,
            postal_code=z["postal_code"],
            code_numeric=z.get("code_numeric"),
            name=z["name"] or f"Zone {z['id']}",
            population=z.get("population"),
            center_point=from_shape(Point(z["center"]["lng"], z["center"]["lat"]), srid=4326) if z.get("center") else None,
            boundary=from_shape(boundary_shape, srid=4326) if boundary_shape else None,
            area_sq_km=z.get("area_sq_km"),
        )
        db.add(zone_db)
        await db.flush()
        await db.refresh(zone_db)
        created_zones.append(ZoneResponse(
            id=zone_db.id,
            postal_code=zone_db.postal_code,
            name=zone_db.name,
            center_lat=z["center"]["lat"],
            center_lng=z["center"]["lng"],
            area_sq_km=z.get("area_sq_km"),
            population=z.get("population"),
            status=zone_db.status,
        ))

    return created_zones


@router.get("/countries/{country_id}/zones", response_model=List[ZoneResponse])
async def list_zones(
    country_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List all postal zones for a country."""
    from sqlalchemy import select, text
    result = await db.execute(text("""
        SELECT pz.id, pz.postal_code, pz.name, pz.status,
               ST_Y(pz.center_point) AS center_lat,
               ST_X(pz.center_point) AS center_lng,
               pz.area_sq_km, pz.population,
               d.name AS district_name, r.name AS region_name
        FROM postal_zones pz
        JOIN districts d ON pz.district_id = d.id
        JOIN regions r ON d.region_id = r.id
        JOIN countries c ON r.country_id = c.id
        WHERE c.id = :country_id
        ORDER BY pz.postal_code
    """), {"country_id": country_id})
    return [
        ZoneResponse(
            id=r["id"], postal_code=r["postal_code"], name=r["name"],
            center_lat=r["center_lat"] or 0, center_lng=r["center_lng"] or 0,
            area_sq_km=r["area_sq_km"], population=r["population"],
            region_name=r["region_name"], district_name=r["district_name"],
            status=r["status"],
        )
        for r in result.mappings().all()
    ]


# ── Lookup ────────────────────────────────────────────────

@router.get("/lookup/coordinates", response_model=LookupResult)
async def lookup_by_coordinates(
    lat: float = Query(...),
    lng: float = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Find postal code for any GPS coordinate."""
    service = LookupService(db)
    return await service.lookup_by_coordinates(lat, lng)


@router.get("/lookup/search", response_model=SearchResult)
async def lookup_by_name(
    query: str = Query(...),
    country: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Search by place name or landmark."""
    service = LookupService(db)
    return await service.lookup_by_name(query, country)


@router.post("/lookup/ussd", response_model=USSDResponse)
async def ussd_handler(request: USSDRequest, db: AsyncSession = Depends(get_db)):
    """USSD handler for basic phone lookup (works without internet)."""
    parts = request.text.split("*") if request.text else []
    level = len(parts)
    service = LookupService(db)

    if level == 0:
        return USSDResponse(
            response="CON Welcome to Postal Code Lookup\n1. Find my postal code (GPS)\n2. Search by area name\n3. Verify a postal code",
            type="CON",
        )
    elif level == 1 and parts[0] == "2":
        return USSDResponse(response="CON Enter area/village name:", type="CON")
    elif level == 1 and parts[0] == "3":
        return USSDResponse(response="CON Enter postal code to verify:", type="CON")
    elif level == 2 and parts[0] == "2":
        results = await service.lookup_by_name(parts[1], "SSD")
        if results["zone_results"]:
            text = "END Results:\n"
            for i, r in enumerate(results["zone_results"][:3]):
                text += f"{i+1}. {r['zone_name']}: {r['postal_code']}\n"
            return USSDResponse(response=text, type="END")
        return USSDResponse(response=f"END No postal code found for '{parts[1]}'.", type="END")
    elif level == 2 and parts[0] == "3":
        result = await service.verify_code(parts[1])
        if result and result.get("valid"):
            return USSDResponse(
                response=f"END ✓ Valid: {result['postal_code']}\nArea: {result['name']}\nDistrict: {result['district']}",
                type="END",
            )
        return USSDResponse(response=f"END ✗ Invalid code: {parts[1]}", type="END")
    else:
        return USSDResponse(response="END Invalid option. Please try again.", type="END")


# ── Policy ────────────────────────────────────────────────

@router.post("/countries/{country_id}/policy", response_model=PolicyDocumentResponse)
async def generate_policy(country_id: int, db: AsyncSession = Depends(get_db)):
    """Generate policy documents for a country's postal code system."""
    from sqlalchemy import select
    result = await db.execute(select(Country).where(Country.id == country_id))
    country = result.scalar_one_or_none()
    if not country:
        raise HTTPException(404, "Country not found")

    profile = CountryProfileCreate(
        name=country.name, iso_code=country.iso_code, tier=country.tier,
        estimated_population=country.estimated_population, area_sq_km=country.area_sq_km,
        num_regions=country.num_regions, num_districts=country.num_districts,
        languages=eval(country.languages) if country.languages else [],
        has_street_names=country.has_street_names, urban_percentage=country.urban_percentage,
        literacy_rate=country.literacy_rate, mobile_penetration=country.mobile_penetration,
    )
    designer = PostalSystemDesigner(profile)
    analysis = designer.analyze_country()
    generator = PolicyDocumentGenerator()
    return generator.generate_postal_code_policy(profile, analysis)


# ── Statistics ────────────────────────────────────────────

@router.get("/countries/{country_id}/stats")
async def country_stats(country_id: int, db: AsyncSession = Depends(get_db)):
    """Get statistics for a country's postal code system."""
    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT
            (SELECT COUNT(*) FROM postal_zones pz
             JOIN districts d ON pz.district_id = d.id
             JOIN regions r ON d.region_id = r.id
             WHERE r.country_id = :cid) AS total_zones,
            (SELECT COUNT(*) FROM regions WHERE country_id = :cid) AS total_regions,
            (SELECT COUNT(*) FROM districts d
             JOIN regions r ON d.region_id = r.id
             WHERE r.country_id = :cid) AS total_districts,
            (SELECT COUNT(*) FROM landmarks l
             JOIN postal_zones pz ON l.postal_zone_id = pz.id
             JOIN districts d ON pz.district_id = d.id
             JOIN regions r ON d.region_id = r.id
             WHERE r.country_id = :cid) AS total_landmarks
    """), {"cid": country_id})
    row = result.mappings().first()
    return dict(row) if row else {"total_zones": 0, "total_regions": 0, "total_districts": 0, "total_landmarks": 0}
