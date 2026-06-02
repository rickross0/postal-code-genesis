import logging
import json
"""FastAPI route definitions for the Postal Code Genesis Platform."""

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
    ManualZoneCreate,
    BoundaryUpdate,
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


# ── Helpers ──────────────────────────────────────────────

async def _generate_next_postal_code(db, district_id: int, region_name: str, district_name: str) -> str:
    """Generate the next unique postal code for a district.
    Format: first 2 letters of region + first 2 letters of district + 3-digit sequential number."""
    from sqlalchemy import text
    region_prefix = (region_name[:2] if region_name else "ZZ").upper()
    district_prefix = (district_name[:2] if district_name else "ZZ").upper()
    prefix = f"{region_prefix}{district_prefix}"

    existing = await db.execute(text(
        "SELECT postal_code FROM postal_zones WHERE district_id = :did AND postal_code LIKE :pat ORDER BY postal_code DESC LIMIT 1"
    ), {"did": district_id, "pat": f"{prefix}%"})
    last_code = existing.scalar_one_or_none()
    if last_code and len(last_code) > len(prefix):
        try:
            next_num = int(last_code[len(prefix):]) + 1
        except ValueError:
            next_num = 1
    else:
        next_num = 1

    postal_code = f"{prefix}{next_num:03d}"
    while True:
        dup_check = await db.execute(text(
            "SELECT id FROM postal_zones WHERE postal_code = :code"
        ), {"code": postal_code})
        if not dup_check.scalar_one_or_none():
            break
        next_num += 1
        postal_code = f"{prefix}{next_num:03d}"
    return postal_code



# ── Countries ──────────────────────────────────────────────

@router.post("/countries", response_model=CountryProfileResponse, status_code=201)
async def create_country(
    profile: CountryProfileCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new country profile or return existing one if iso_code matches."""
    from sqlalchemy import select
    logger = logging.getLogger(__name__)
    logger.info(f"CREATE COUNTRY payload: {profile.model_dump()}")
    # Check if country with this iso_code already exists
    existing = await db.execute(
        select(Country).where(Country.iso_code == profile.iso_code.upper())
    )
    existing_country = existing.scalar_one_or_none()
    if existing_country:
        # Update existing country with new data
        existing_country.name = profile.name
        existing_country.tier = profile.tier.value if hasattr(profile.tier, "value") else str(profile.tier)
        existing_country.estimated_population = profile.estimated_population
        existing_country.area_sq_km = profile.area_sq_km
        existing_country.num_regions = profile.num_regions
        existing_country.num_districts = profile.num_districts
        existing_country.languages = json.dumps(profile.languages)
        existing_country.has_street_names = profile.has_street_names
        existing_country.has_house_numbers = profile.has_house_numbers
        existing_country.has_any_addressing = profile.has_any_addressing
        existing_country.urban_percentage = profile.urban_percentage
        existing_country.literacy_rate = profile.literacy_rate
        existing_country.mobile_penetration = profile.mobile_penetration
        existing_country.internet_penetration = profile.internet_penetration
        existing_country.existing_admin_divisions = json.dumps(profile.existing_admin_divisions)
        if profile.capital_city:
            existing_country.capital_city = profile.capital_city
        if profile.capital_lat is not None:
            existing_country.capital_lat = profile.capital_lat
        if profile.capital_lng is not None:
            existing_country.capital_lng = profile.capital_lng
        await db.flush()
        return CountryProfileResponse(
            id=existing_country.id,
            name=existing_country.name,
            iso_code=existing_country.iso_code,
            tier=existing_country.tier or "mixed_rural_urban",
            estimated_population=existing_country.estimated_population or 0,
            area_sq_km=existing_country.area_sq_km or 0,
            num_regions=existing_country.num_regions or 1,
            num_districts=existing_country.num_districts or 1,
            languages=profile.languages,
            urban_percentage=float(existing_country.urban_percentage or 0),
            literacy_rate=float(existing_country.literacy_rate or 0),
            mobile_penetration=float(existing_country.mobile_penetration or 0),
            capital_city=existing_country.capital_city,
            capital_lat=float(existing_country.capital_lat) if existing_country.capital_lat else None,
            capital_lng=float(existing_country.capital_lng) if existing_country.capital_lng else None,
        )
    country = Country(
        name=profile.name,
        iso_code=profile.iso_code.upper(),
        tier=profile.tier.value if hasattr(profile.tier, "value") else str(profile.tier),
        estimated_population=profile.estimated_population,
        area_sq_km=profile.area_sq_km,
        num_regions=profile.num_regions,
        num_districts=profile.num_districts,
        languages=json.dumps(profile.languages),
        has_street_names=profile.has_street_names,
        has_house_numbers=profile.has_house_numbers,
        has_any_addressing=profile.has_any_addressing,
        urban_percentage=profile.urban_percentage,
        literacy_rate=profile.literacy_rate,
        mobile_penetration=profile.mobile_penetration,
        internet_penetration=profile.internet_penetration,
        existing_admin_divisions=json.dumps(profile.existing_admin_divisions),
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
        languages=profile.languages,
        urban_percentage=country.urban_percentage,
        literacy_rate=country.literacy_rate,
        mobile_penetration=country.mobile_penetration,
    )


@router.get("/countries", response_model=List[CountryProfileResponse])
async def list_countries(db: AsyncSession = Depends(get_db)):
    """List all countries in the platform."""
    from sqlalchemy import select, text
    try:
        result = await db.execute(text("""
            SELECT
                c.id, c.name, c.iso_code, c.tier, c.estimated_population, c.area_sq_km,
                c.num_regions, c.num_districts, c.languages,
                c.urban_percentage, c.literacy_rate, c.mobile_penetration,
                c.capital_city, c.capital_lat, c.capital_lng, c.locked,
                ST_AsGeoJSON(c.boundary) AS boundary_geojson
            FROM countries c
            ORDER BY c.name
        """))
        rows = result.mappings().all()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to query countries: {e}")
        raise HTTPException(503, f"Database not ready: {e}")
    return [
        CountryProfileResponse(
            id=r["id"], name=r["name"], iso_code=r["iso_code"], tier=r["tier"] or "mixed_rural_urban",
            estimated_population=r["estimated_population"] or 0, area_sq_km=r["area_sq_km"] or 0,
            num_regions=r["num_regions"] or 1, num_districts=r["num_districts"] or 1,
            languages=json.loads(r["languages"]) if r["languages"] else [],
            urban_percentage=float(r["urban_percentage"] or 0), literacy_rate=float(r["literacy_rate"] or 0),
            mobile_penetration=float(r["mobile_penetration"] or 0),
            capital_city=r["capital_city"], capital_lat=float(r["capital_lat"]) if r["capital_lat"] else None,
            capital_lng=float(r["capital_lng"]) if r["capital_lng"] else None,
            locked=bool(r["locked"]) if r["locked"] is not None else False,
            boundary_geojson=json.loads(r["boundary_geojson"]) if r["boundary_geojson"] else None,
        )
        for r in rows
    ]


@router.delete("/countries/{country_id}", status_code=204)
async def delete_country(country_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a country and all associated data (cascades to regions, districts, zones, landmarks)."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Country)
        .where(Country.id == country_id)
        .options(
            selectinload(Country.regions)
            .selectinload(Region.districts)
            .selectinload(District.postal_zones)
            .selectinload(PostalZone.landmarks_rel)
        )
    )
    country = result.scalar_one_or_none()
    if not country:
        raise HTTPException(404, "Country not found")
    await db.delete(country)
    await db.flush()
    return None


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
    region_code: str = Query("01", description="2-digit region code"),
    district_code: str = Query("01", description="2-digit district code"),
    target_population: int = Query(5000, description="Target population per zone"),
    db: AsyncSession = Depends(get_db),
):
    """Auto-generate postal zones for a district, starting from the capital city outward."""
    from sqlalchemy import select, text
    from geoalchemy2.shape import from_shape, to_shape
    from shapely.geometry import Point, shape, box, mapping as shapely_mapping

    # Get country
    country_res = await db.execute(select(Country).where(Country.id == country_id))
    country = country_res.scalar_one_or_none()
    if not country:
        raise HTTPException(404, "Country not found")

    # Get or create region
    region_result = await db.execute(
        select(Region).where(Region.country_id == country_id, Region.code == region_code)
    )
    region = region_result.scalar_one_or_none()
    if not region:
        region = Region(
            country_id=country_id, name=f"Region {region_code}", code=region_code,
            center_point=from_shape(Point(country.capital_lng or 31.6, country.capital_lat or 4.85), srid=4326) if country.capital_lat else None,
        )
        db.add(region)
        await db.flush()

    # Get or create district
    result = await db.execute(
        select(District)
        .where(District.region_id == region.id)
        .where(District.code == district_code)
    )
    district = result.scalar_one_or_none()

    if not district:
        district = District(
            region_id=region.id,
            name=f"District {district_code}",
            code=district_code,
            center_point=from_shape(Point(country.capital_lng or 31.6, country.capital_lat or 4.85), srid=4326) if country.capital_lat else None,
        )
        db.add(district)
        await db.flush()

    # Build district boundary: prefer existing geometry, else derive from capital + area
    district_boundary = None
    if district.boundary is not None:
        try:
            district_boundary = to_shape(district.boundary)
        except Exception:
            pass

    if district_boundary is None:
        # Derive a rough district shape from capital location and country area
        cap_lng = country.capital_lng or 31.6
        cap_lat = country.capital_lat or 4.85
        # Approx side length: sqrt(country_area / num_districts) in km, then degrees
        side_km = max(5, (country.area_sq_km / max(country.num_districts, 1)) ** 0.5)
        delta_deg = side_km / 111.0
        district_boundary = box(cap_lng - delta_deg, cap_lat - delta_deg, cap_lng + delta_deg, cap_lat + delta_deg)

    # Delete existing zones for this district to avoid duplicate postal_code errors
    await db.execute(text("DELETE FROM postal_zones WHERE district_id = :did"), {"did": district.id})

    # Generate zones inside this district boundary, starting from capital
    cap_point = Point(country.capital_lng or district_boundary.centroid.x, country.capital_lat or district_boundary.centroid.y)

    engine = ZoneCreationEngine()
    zones = engine.create_zones_in_district(
        district_boundary=district_boundary,
        capital_point=cap_point,
        target_population_per_zone=target_population,
        estimated_population=target_population * 4,
    )
    dc = {"lat": country.capital_lat, "lng": country.capital_lng}
    zones = engine.assign_codes(zones, region.name, district.name, dc)

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
            color=zone_db.color,
            region_name=region.name,
            district_name=district.name,
        ))

    return created_zones


@router.post("/countries/{country_id}/zones/auto-create-all", response_model=List[ZoneResponse])
async def auto_create_all_zones(
    country_id: int,
    target_population: int = Query(5000, description="Target population per zone"),
    db: AsyncSession = Depends(get_db),
):
    """Auto-generate postal zones for ALL districts in a country, using their admin boundaries."""
    from sqlalchemy import select, text
    from geoalchemy2.shape import from_shape, to_shape
    from shapely.geometry import Point, shape, box, mapping as shapely_mapping
    import math

    # Get country
    country_res = await db.execute(select(Country).where(Country.id == country_id))
    country = country_res.scalar_one_or_none()
    if not country:
        raise HTTPException(404, "Country not found")

    # Get all regions and districts
    region_res = await db.execute(select(Region).where(Region.country_id == country_id))
    regions = region_res.scalars().all()

    if not regions:
        # Create default regions and districts from country data
        for ri in range(1, max(country.num_regions, 1) + 1):
            rcode = f"{ri:02d}"
            region = Region(
                country_id=country_id,
                name=f"Region {rcode}",
                code=rcode,
                center_point=from_shape(
                    Point(country.capital_lng or 31.6, country.capital_lat or 4.85), srid=4326
                ) if country.capital_lat else None,
            )
            db.add(region)
            await db.flush()

            for di in range(1, max(country.num_districts // max(country.num_regions, 1), 1) + 1):
                dcode = f"{di:02d}"
                district = District(
                    region_id=region.id,
                    name=f"District {rcode}{dcode}",
                    code=f"{rcode}{dcode}",
                    center_point=from_shape(
                        Point(country.capital_lng or 31.6, country.capital_lat or 4.85), srid=4326
                    ) if country.capital_lat else None,
                )
                db.add(district)
        await db.flush()

        # Reload regions and districts
        region_res = await db.execute(select(Region).where(Region.country_id == country_id))
        regions = region_res.scalars().all()

    engine = ZoneCreationEngine()
    all_zones = []

    for region in regions:
        # Load districts for this region
        dist_res = await db.execute(select(District).where(District.region_id == region.id))
        districts = dist_res.scalars().all()

        for district in districts:
            # Skip locked districts
            if district.locked:
                continue
            # Skip districts that already have zones
            zone_count_res = await db.execute(text("SELECT COUNT(*) FROM postal_zones WHERE district_id = :did"), {"did": district.id})
            zone_count = zone_count_res.scalar()
            if zone_count > 0:
                continue
            # Get or derive district boundary
            district_boundary = None
            if district.boundary is not None:
                try:
                    district_boundary = to_shape(district.boundary)
                except Exception:
                    pass

            if district_boundary is None:
                # Derive from capital + area
                cap_lng = country.capital_lng or 31.6
                cap_lat = country.capital_lat or 4.85
                side_km = max(5, (country.area_sq_km / max(country.num_districts, 1)) ** 0.5)
                delta_deg = side_km / 111.0
                district_boundary = box(
                    cap_lng - delta_deg, cap_lat - delta_deg,
                    cap_lng + delta_deg, cap_lat + delta_deg
                )

            cap_point = Point(
                country.capital_lng or district_boundary.centroid.x,
                country.capital_lat or district_boundary.centroid.y,
            )

            try:
                zones = engine.create_zones_in_district(
                    district_boundary=district_boundary,
                    capital_point=cap_point,
                    target_population_per_zone=target_population,
                    estimated_population=target_population * 4,
                )
            except Exception:
                continue

            dc = {"lat": cap_point.y, "lng": cap_point.x}
            zones = engine.assign_codes(zones, region.name, district.name, dc)

            for z in zones:
                boundary_shape = shape(z.get("boundary_geojson", {})) if z.get("boundary_geojson") else None
                zone_db = PostalZone(
                    district_id=district.id,
                    postal_code=z["postal_code"],
                    code_numeric=z.get("code_numeric"),
                    name=z.get("name") or f"Zone {z['id']}",
                    population=z.get("population"),
                    center_point=from_shape(Point(z["center"]["lng"], z["center"]["lat"]), srid=4326) if z.get("center") else None,
                    boundary=from_shape(boundary_shape, srid=4326) if boundary_shape else None,
                    area_sq_km=z.get("area_sq_km"),
                )
                db.add(zone_db)
                await db.flush()
                await db.refresh(zone_db)
                all_zones.append(ZoneResponse(
                    id=zone_db.id,
                    postal_code=zone_db.postal_code,
                    name=zone_db.name,
                    center_lat=z["center"]["lat"],
                    center_lng=z["center"]["lng"],
                    area_sq_km=z.get("area_sq_km"),
                    population=z.get("population"),
                    status=zone_db.status,
                    color=zone_db.color,
                    region_name=region.name,
                    district_name=district.name,
                    boundary_geojson=z.get("boundary_geojson"),
                ))

    return all_zones


@router.post("/countries/{country_id}/zones/create", response_model=ZoneResponse)
async def create_zone_manual(
    country_id: int,
    zone_data: ManualZoneCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a single zone by drawing a polygon on the map. Auto-assigns postal code."""
    from sqlalchemy import select, text
    from geoalchemy2.shape import from_shape
    from shapely.geometry import shape, Point

    # Validate country
    country_res = await db.execute(select(Country).where(Country.id == country_id))
    country = country_res.scalar_one_or_none()
    if not country:
        raise HTTPException(404, "Country not found")

    # Parse boundary polygon
    try:
        boundary_geom = shape(zone_data.boundary_geojson)
        if not boundary_geom.is_valid:
            boundary_geom = boundary_geom.buffer(0)
    except Exception as e:
        raise HTTPException(400, f"Invalid boundary GeoJSON: {e}")

    # Get or create district
    district = None
    if zone_data.district_id:
        dist_res = await db.execute(select(District).where(District.id == zone_data.district_id))
        district = dist_res.scalar_one_or_none()
    elif zone_data.region_code and zone_data.district_code:
        region_res = await db.execute(
            select(Region).where(Region.country_id == country_id, Region.code == zone_data.region_code)
        )
        region = region_res.scalar_one_or_none()
        if not region:
            region = Region(
                country_id=country_id, name=f"Region {zone_data.region_code}",
                code=zone_data.region_code,
            )
            db.add(region)
            await db.flush()
        dist_res = await db.execute(
            select(District).where(District.region_id == region.id, District.code == zone_data.district_code)
        )
        district = dist_res.scalar_one_or_none()
        if not district:
            district = District(
                region_id=region.id, name=f"District {zone_data.district_code}",
                code=zone_data.district_code,
            )
            db.add(district)
            await db.flush()

    if not district:
        # Get or create default region/district
        region_res = await db.execute(
            select(Region).where(Region.country_id == country_id).order_by(Region.id)
        )
        region = region_res.scalars().first()
        if not region:
            region = Region(country_id=country_id, name="Default Region", code="01")
            db.add(region)
            await db.flush()
        district = District(region_id=region.id, name="Default District", code="0101")
        db.add(district)
        await db.flush()

    # Get region for postal code prefix
    region_res = await db.execute(select(Region).where(Region.id == district.region_id))
    region = region_res.scalar_one_or_none()
    # Calculate the next postal code for this district
    postal_code = await _generate_next_postal_code(db, district.id, region.name if region else "", district.name)

    # Compute area
    area_sq_km = 0.0
    try:
        from pyproj import Geod
        geod = Geod(ellps="WGS84")
        area, _ = geod.geometry_area_perimeter(boundary_geom)
        area_sq_km = abs(area) / 1_000_000
    except Exception:
        pass

    # Create the zone
    zone_name = zone_data.name or f"Zone {postal_code}"
    zone = PostalZone(
        district_id=district.id,
        postal_code=postal_code,
        name=zone_name,
        population=zone_data.population or 0,
        boundary=from_shape(boundary_geom, srid=4326),
        center_point=from_shape(boundary_geom.centroid, srid=4326),
        area_sq_km=area_sq_km,
        color=zone_data.color,
    )
    db.add(zone)
    await db.flush()
    await db.refresh(zone)

    # Fetch full zone data for response
    fresh = await db.execute(text("""
        SELECT pz.id, pz.postal_code, pz.name, pz.status, pz.color,
               ST_Y(pz.center_point) AS center_lat,
               ST_X(pz.center_point) AS center_lng,
               pz.area_sq_km, pz.population,
               d.name AS district_name, r.name AS region_name,
               ST_AsGeoJSON(pz.boundary) AS boundary_geojson
        FROM postal_zones pz
        JOIN districts d ON pz.district_id = d.id
        JOIN regions r ON d.region_id = r.id
        WHERE pz.id = :zid
    """), {"zid": zone.id})
    row = fresh.mappings().first()
    if not row:
        raise HTTPException(500, "Zone created but could not be fetched")

    return ZoneResponse(
        id=row["id"], postal_code=row["postal_code"], name=row["name"],
        center_lat=row["center_lat"] or 0, center_lng=row["center_lng"] or 0,
        area_sq_km=row["area_sq_km"], population=row["population"],
        region_name=row["region_name"], district_name=row["district_name"],
        status=row["status"],
        color=row["color"],
        boundary_geojson=json.loads(row["boundary_geojson"]) if row["boundary_geojson"] else None,
    )


@router.get("/countries/{country_id}/zones", response_model=List[ZoneResponse])
async def list_zones(
    country_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List all postal zones for a country, including district boundaries."""
    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT
            pz.id, pz.postal_code, pz.name, pz.status, pz.color,
            ST_Y(pz.center_point) AS center_lat,
            ST_X(pz.center_point) AS center_lng,
            pz.area_sq_km, pz.population,
            d.id AS district_id, d.name AS district_name, d.code AS district_code,
            r.name AS region_name, r.code AS region_code,
            ST_AsGeoJSON(pz.boundary) AS boundary_geojson,
            pz.locked AS zone_locked,
            ST_AsGeoJSON(d.boundary) AS district_boundary_geojson
        FROM postal_zones pz
        JOIN districts d ON pz.district_id = d.id
        JOIN regions r ON d.region_id = r.id
        JOIN countries c ON r.country_id = c.id
        WHERE c.id = :country_id
        ORDER BY d.code, pz.postal_code
    """), {"country_id": country_id})
    return [
        ZoneResponse(
            id=r["id"], postal_code=r["postal_code"], name=r["name"],
            center_lat=r["center_lat"] or 0, center_lng=r["center_lng"] or 0,
            area_sq_km=r["area_sq_km"], population=r["population"],
            region_name=r["region_name"], district_name=r["district_name"],
            status=r["status"],
            color=r["color"],
            locked=bool(r.get("zone_locked", False)),
            boundary_geojson=json.loads(r["boundary_geojson"]) if r["boundary_geojson"] else None,
        )
        for r in result.mappings().all()
    ]


@router.get("/countries/{country_id}/districts")
async def list_districts_with_boundaries(
    country_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List all districts for a country with their boundary GeoJSON."""
    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT
            d.id, d.name, d.code, d.local_name,
            ST_Y(d.center_point) AS center_lat,
            ST_X(d.center_point) AS center_lng,
            d.locked AS district_locked,
            ST_AsGeoJSON(d.boundary) AS boundary_geojson,
            r.name AS region_name, r.code AS region_code
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.country_id = :country_id
        ORDER BY r.code, d.code
    """), {"country_id": country_id})
    rows = []
    for r in result.mappings().all():
        row = dict(r)
        row["boundary_geojson"] = json.loads(r["boundary_geojson"]) if r["boundary_geojson"] else None
        row["locked"] = bool(r.get("district_locked", False))
        rows.append(row)
    return rows


@router.get("/countries/{country_id}/regions")
async def list_regions_with_boundaries(
    country_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List all regions for a country with their boundary GeoJSON."""
    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT
            r.id, r.name, r.code, r.local_name,
            ST_Y(r.center_point) AS center_lat,
            ST_X(r.center_point) AS center_lng,
            r.locked,
            ST_AsGeoJSON(r.boundary) AS boundary_geojson
        FROM regions r
        WHERE r.country_id = :country_id
        ORDER BY r.code
    """), {"country_id": country_id})
    rows = []
    for r in result.mappings().all():
        row = dict(r)
        row["boundary_geojson"] = json.loads(r["boundary_geojson"]) if r["boundary_geojson"] else None
        row["locked"] = bool(r.get("locked", False))
        rows.append(row)
    return rows


# ── Region CRUD ───────────────────────────────────────────

@router.post("/countries/{country_id}/regions", status_code=201)
async def create_region(
    country_id: int,
    db: AsyncSession = Depends(get_db),
    name: str = Query("New Region"),
    code: str = Query("01"),
):
    """Create a new region in a country."""
    from sqlalchemy import select
    country_res = await db.execute(select(Country).where(Country.id == country_id))
    country = country_res.scalar_one_or_none()
    if not country:
        raise HTTPException(404, "Country not found")
    region = Region(country_id=country_id, name=name, code=code)
    db.add(region)
    await db.flush()
    await db.refresh(region)
    return {"id": region.id, "name": region.name, "code": region.code, "locked": False}


@router.post("/countries/{country_id}/regions/auto-create")
async def auto_create_regions(
    country_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Auto-generate regions for a country, preserving existing regions and filling open areas."""
    from sqlalchemy import select, text
    from geoalchemy2.shape import from_shape, to_shape
    from shapely.geometry import Point, shape, box, mapping as shapely_mapping, MultiPolygon
    from shapely.ops import unary_union
    import math

    country_res = await db.execute(select(Country).where(Country.id == country_id))
    country = country_res.scalar_one_or_none()
    if not country:
        raise HTTPException(404, "Country not found")

    # Load existing regions (preserve them)
    existing_res = await db.execute(select(Region).where(Region.country_id == country_id))
    existing_regions = existing_res.scalars().all()
    existing_count = len(existing_regions)

    cap_lat = country.capital_lat or 4.85
    cap_lng = country.capital_lng or 31.6
    num_regions = max(country.num_regions, 1)

    # Try to derive regions from country boundary
    country_boundary = None
    if country.boundary is not None:
        try:
            country_boundary = to_shape(country.boundary)
        except Exception:
            pass

    # Calculate uncovered area (country minus existing region boundaries)
    uncovered = None
    if country_boundary:
        existing_polys = []
        for reg in existing_regions:
            if reg.boundary is not None:
                try:
                    reg_geom = to_shape(reg.boundary)
                    if reg_geom and not reg_geom.is_empty:
                        existing_polys.append(reg_geom)
                except Exception:
                    pass
        if existing_polys:
            try:
                covered = unary_union(existing_polys)
                if not covered.is_valid:
                    covered = covered.buffer(0)
                uncovered = country_boundary.difference(covered)
            except Exception:
                uncovered = country_boundary
        else:
            uncovered = country_boundary

    # If nothing to fill, return early
    if uncovered is None or uncovered.is_empty:
        return {"detail": "No open areas to fill", "created": 0, "regions": []}

    # Filter out tiny slivers
    if uncovered.geom_type == "Polygon":
        if uncovered.area < 1e-8:
            return {"detail": "No open areas to fill", "created": 0, "regions": []}
        uncovered_polys = [uncovered]
    elif uncovered.geom_type == "MultiPolygon":
        uncovered_polys = [p for p in uncovered.geoms if p.area >= 1e-8]
        if not uncovered_polys:
            return {"detail": "No open areas to fill", "created": 0, "regions": []}
    else:
        try:
            uncovered_polys = [p for p in uncovered.geoms if p.geom_type == "Polygon" and p.area >= 1e-8]
        except Exception:
            uncovered_polys = []
        if not uncovered_polys:
            return {"detail": "No open areas to fill", "created": 0, "regions": []}

    # Determine how many new regions to create
    num_new = max(1, num_regions - existing_count)

    created = []
    # Grid subdivision of uncovered area bounding box
    all_bounds = [p.bounds for p in uncovered_polys]
    minx = min(b[0] for b in all_bounds)
    miny = min(b[1] for b in all_bounds)
    maxx = max(b[2] for b in all_bounds)
    maxy = max(b[3] for b in all_bounds)

    cols = max(1, int(math.sqrt(num_new)))
    rows = max(1, int(math.ceil(num_new / cols)))
    dx = (maxx - minx) / cols if cols > 0 else (maxx - minx)
    dy = (maxy - miny) / rows if rows > 0 else (maxy - miny)

    cell_index = 0
    for ri in range(rows):
        for ci in range(cols):
            if cell_index >= num_new:
                break
            reg_box = box(minx + ci * dx, miny + ri * dy, minx + (ci + 1) * dx, miny + (ri + 1) * dy)

            # Intersect with uncovered polygons
            pieces = []
            for poly in uncovered_polys:
                try:
                    inter = reg_box.intersection(poly)
                    if not inter.is_empty and inter.area >= 1e-8:
                        pieces.append(inter)
                except Exception:
                    pass

            if not pieces:
                continue

            if len(pieces) == 1:
                reg_poly = pieces[0]
            else:
                try:
                    reg_poly = unary_union(pieces)
                except Exception:
                    reg_poly = pieces[0]

            if reg_poly.is_empty or reg_poly.area < 1e-8:
                continue

            cell_index += 1
            rcode = f"{existing_count + cell_index:02d}"

            center_point = from_shape(reg_poly.centroid, srid=4326)
            region = Region(
                country_id=country_id,
                name=f"Region {rcode}",
                code=rcode,
                center_point=center_point,
            )
            if reg_poly.geom_type in ("Polygon", "MultiPolygon"):
                region.boundary = from_shape(reg_poly, srid=4326)

            db.add(region)
            await db.flush()
            await db.refresh(region)
            created.append({"id": region.id, "name": region.name, "code": region.code, "locked": False})

    return {"detail": f"Created {len(created)} regions in open areas", "created": len(created), "regions": created}


@router.delete("/countries/{country_id}/regions")
async def delete_all_regions(
    country_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete all regions for a country (cascades to districts and zones). Use as undo for auto-regions."""
    from sqlalchemy import select
    result = await db.execute(select(Region).where(Region.country_id == country_id))
    regions = result.scalars().all()
    for region in regions:
        if region.locked:
            raise HTTPException(423, f"Region {region.name} is locked. Unlock it first.")
        await db.delete(region)
    await db.flush()
    return {"detail": f"Deleted {len(regions)} regions", "count": len(regions)}


@router.put("/regions/{region_id}")
async def update_region(
    region_id: int,
    update: BoundaryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a region boundary, name, or lock status."""
    from sqlalchemy import select, text
    from geoalchemy2.shape import from_shape
    from shapely.geometry import shape

    result = await db.execute(select(Region).where(Region.id == region_id))
    region = result.scalar_one_or_none()
    if not region:
        raise HTTPException(404, "Region not found")
    if region.locked and (update.boundary_geojson is not None or update.name is not None):
        raise HTTPException(423, "Region is locked. Unlock it first to edit.")
    if update.name is not None:
        region.name = update.name
    if update.locked is not None:
        region.locked = update.locked
    if update.boundary_geojson is not None:
        try:
            geom = shape(update.boundary_geojson)
            if not geom.is_valid:
                geom = geom.buffer(0)
            region.boundary = from_shape(geom, srid=4326)
            region.center_point = from_shape(geom.centroid, srid=4326)
        except Exception as e:
            raise HTTPException(400, f"Invalid boundary: {e}")
    await db.flush()
    return {"id": region.id, "name": region.name, "code": region.code, "locked": region.locked}


@router.delete("/regions/{region_id}")
async def delete_region(region_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a region and all its districts/zones."""
    from sqlalchemy import select
    result = await db.execute(select(Region).where(Region.id == region_id))
    region = result.scalar_one_or_none()
    if not region:
        raise HTTPException(404, "Region not found")
    if region.locked:
        raise HTTPException(423, "Region is locked. Unlock it first.")
    await db.delete(region)
    await db.flush()
    return {"detail": "Region deleted", "id": region_id}


# ── District CRUD ──────────────────────────────────────────

@router.post("/regions/{region_id}/districts", status_code=201)
async def create_district(
    region_id: int,
    db: AsyncSession = Depends(get_db),
    name: str = Query("New District"),
    code: str = Query("01"),
):
    """Create a new district in a region."""
    from sqlalchemy import select
    region_res = await db.execute(select(Region).where(Region.id == region_id))
    region = region_res.scalar_one_or_none()
    if not region:
        raise HTTPException(404, "Region not found")
    district = District(region_id=region_id, name=name, code=code)
    db.add(district)
    await db.flush()
    await db.refresh(district)
    return {"id": district.id, "name": district.name, "code": district.code, "locked": False}


@router.post("/regions/{region_id}/districts/auto-create")
async def auto_create_districts(
    region_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Auto-generate districts for a region, preserving existing districts and filling open areas."""
    from sqlalchemy import select, text
    from geoalchemy2.shape import from_shape, to_shape
    from shapely.geometry import Point, shape, box, mapping as shapely_mapping
    from shapely.ops import unary_union
    import math
    import json
    from app.models.database import DrawingSnapshot

    region_res = await db.execute(select(Region).where(Region.id == region_id))
    region = region_res.scalar_one_or_none()
    if not region:
        raise HTTPException(404, "Region not found")

    country_res = await db.execute(select(Country).where(Country.id == region.country_id))
    country = country_res.scalar_one_or_none()
    if not country:
        raise HTTPException(404, "Country not found")

    # Save snapshot before changes (for undo)
    # Re-use save_snapshot logic inline for this country
    snap_reg_res = await db.execute(text("""
        SELECT id, name, code, locked,
               ST_AsGeoJSON(boundary) AS boundary_geojson,
               ST_AsGeoJSON(center_point) AS center_geojson
        FROM regions WHERE country_id = :cid
    """), {"cid": region.country_id})
    snap_regions = []
    for r in snap_reg_res.mappings().all():
        snap_regions.append({
            "id": r["id"], "name": r["name"], "code": r["code"], "locked": bool(r["locked"]),
            "boundary_geojson": json.loads(r["boundary_geojson"]) if r["boundary_geojson"] else None,
            "center_geojson": json.loads(r["center_geojson"]) if r["center_geojson"] else None,
        })

    snap_dist_res = await db.execute(text("""
        SELECT d.id, d.name, d.code, d.region_id, d.locked,
               ST_AsGeoJSON(d.boundary) AS boundary_geojson,
               ST_AsGeoJSON(d.center_point) AS center_geojson
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.country_id = :cid
    """), {"cid": region.country_id})
    snap_districts = []
    for d in snap_dist_res.mappings().all():
        snap_districts.append({
            "id": d["id"], "name": d["name"], "code": d["code"],
            "region_id": d["region_id"], "locked": bool(d["locked"]),
            "boundary_geojson": json.loads(d["boundary_geojson"]) if d["boundary_geojson"] else None,
            "center_geojson": json.loads(d["center_geojson"]) if d["center_geojson"] else None,
        })

    snap_zone_res = await db.execute(text("""
        SELECT pz.id, pz.postal_code, pz.name, pz.status, pz.population, pz.area_sq_km, pz.color, pz.locked,
               d.id AS district_id,
               ST_AsGeoJSON(pz.boundary) AS boundary_geojson,
               ST_AsGeoJSON(pz.center_point) AS center_geojson
        FROM postal_zones pz
        JOIN districts d ON pz.district_id = d.id
        JOIN regions r ON d.region_id = r.id
        WHERE r.country_id = :cid
    """), {"cid": region.country_id})
    snap_zones = []
    for z in snap_zone_res.mappings().all():
        snap_zones.append({
            "id": z["id"], "postal_code": z["postal_code"], "name": z["name"],
            "status": z["status"], "population": z["population"], "area_sq_km": z["area_sq_km"],
            "color": z["color"], "locked": bool(z["locked"]), "district_id": z["district_id"],
            "boundary_geojson": json.loads(z["boundary_geojson"]) if z["boundary_geojson"] else None,
            "center_geojson": json.loads(z["center_geojson"]) if z["center_geojson"] else None,
        })

    snap_payload = json.dumps({"regions": snap_regions, "districts": snap_districts, "zones": snap_zones})
    snap_record = DrawingSnapshot(country_id=region.country_id, snapshot=snap_payload)
    db.add(snap_record)
    await db.flush()
    await db.refresh(snap_record)
    snapshot_id = snap_record.id

    # Preserve existing districts
    existing_res = await db.execute(select(District).where(District.region_id == region_id))
    existing_districts = existing_res.scalars().all()
    existing_count = len(existing_districts)

    cap_lat = country.capital_lat or 4.85
    cap_lng = country.capital_lng or 31.6
    num_regions = max(country.num_regions, 1)
    num_districts_total = max(country.num_districts, 1)
    districts_per_region = max(num_districts_total // num_regions, 1)

    # Derive region boundary or center
    region_boundary = None
    if region.boundary is not None:
        try:
            region_boundary = to_shape(region.boundary)
        except Exception:
            pass

    # Calculate uncovered area (region minus existing districts)
    uncovered = None
    if region_boundary:
        existing_polys = []
        for dist in existing_districts:
            if dist.boundary is not None:
                try:
                    dg = to_shape(dist.boundary)
                    if dg and not dg.is_empty:
                        existing_polys.append(dg)
                except Exception:
                    pass
        if existing_polys:
            try:
                covered = unary_union(existing_polys)
                if not covered.is_valid:
                    covered = covered.buffer(0)
                uncovered = region_boundary.difference(covered)
            except Exception:
                uncovered = region_boundary
        else:
            uncovered = region_boundary

    if uncovered is None or uncovered.is_empty:
        return {"detail": "No open areas to fill", "created": 0, "districts": [], "snapshot_id": snapshot_id}

    # Filter slivers
    if uncovered.geom_type == "Polygon":
        if uncovered.area < 1e-8:
            return {"detail": "No open areas to fill", "created": 0, "districts": [], "snapshot_id": snapshot_id}
        uncovered_polys = [uncovered]
    elif uncovered.geom_type == "MultiPolygon":
        uncovered_polys = [p for p in uncovered.geoms if p.area >= 1e-8]
        if not uncovered_polys:
            return {"detail": "No open areas to fill", "created": 0, "districts": [], "snapshot_id": snapshot_id}
    else:
        try:
            uncovered_polys = [p for p in uncovered.geoms if p.geom_type == "Polygon" and p.area >= 1e-8]
        except Exception:
            uncovered_polys = []
        if not uncovered_polys:
            return {"detail": "No open areas to fill", "created": 0, "districts": [], "snapshot_id": snapshot_id}

    # Determine how many new districts to create
    num_new = max(1, districts_per_region - existing_count)

    # Combine uncovered polygons into one area for grid subdivision
    try:
        union_uncovered = unary_union(uncovered_polys)
    except Exception:
        union_uncovered = uncovered_polys[0] if uncovered_polys else None

    if union_uncovered is None or union_uncovered.is_empty:
        return {"detail": "No open areas to fill", "created": 0, "districts": [], "snapshot_id": snapshot_id}

    all_bounds = [p.bounds for p in uncovered_polys]
    minx = min(b[0] for b in all_bounds)
    miny = min(b[1] for b in all_bounds)
    maxx = max(b[2] for b in all_bounds)
    maxy = max(b[3] for b in all_bounds)

    cols = max(1, int(math.sqrt(num_new)))
    rows = max(1, int(math.ceil(num_new / cols)))
    dx = (maxx - minx) / cols if cols > 0 else (maxx - minx)
    dy = (maxy - miny) / rows if rows > 0 else (maxy - miny)

    created = []
    cell_index = 0
    for ri in range(rows):
        for ci in range(cols):
            if cell_index >= num_new:
                break
            dist_box = box(minx + ci * dx, miny + ri * dy, minx + (ci + 1) * dx, miny + (ri + 1) * dy)

            # Intersect with uncovered
            pieces = []
            for poly in uncovered_polys:
                try:
                    inter = dist_box.intersection(poly)
                    if not inter.is_empty and inter.area >= 1e-8:
                        pieces.append(inter)
                except Exception:
                    pass

            if not pieces:
                continue

            if len(pieces) == 1:
                dist_poly = pieces[0]
            else:
                try:
                    dist_poly = unary_union(pieces)
                except Exception:
                    dist_poly = pieces[0]

            if dist_poly.is_empty or dist_poly.area < 1e-8:
                continue

            cell_index += 1
            dcode = f"{region.code}{existing_count + cell_index:02d}"

            center_point = from_shape(dist_poly.centroid, srid=4326)
            district = District(
                region_id=region_id,
                name=f"District {dcode}",
                code=dcode,
                center_point=center_point,
            )
            if dist_poly.geom_type in ("Polygon", "MultiPolygon"):
                district.boundary = from_shape(dist_poly, srid=4326)

            db.add(district)
            await db.flush()
            await db.refresh(district)
            created.append({"id": district.id, "name": district.name, "code": district.code, "locked": False})

    return {"detail": f"Created {len(created)} districts in open areas", "created": len(created), "districts": created, "snapshot_id": snapshot_id}


@router.put("/districts/{district_id}")
async def update_district(
    district_id: int,
    update: BoundaryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a district boundary, name, or lock status."""
    from sqlalchemy import select, text
    from geoalchemy2.shape import from_shape
    from shapely.geometry import shape

    result = await db.execute(select(District).where(District.id == district_id))
    district = result.scalar_one_or_none()
    if not district:
        raise HTTPException(404, "District not found")
    if district.locked and (update.boundary_geojson is not None or update.name is not None):
        raise HTTPException(423, "District is locked. Unlock it first to edit.")
    if update.name is not None:
        district.name = update.name
    if update.locked is not None:
        district.locked = update.locked
    if update.boundary_geojson is not None:
        try:
            geom = shape(update.boundary_geojson)
            if not geom.is_valid:
                geom = geom.buffer(0)
            district.boundary = from_shape(geom, srid=4326)
            district.center_point = from_shape(geom.centroid, srid=4326)
        except Exception as e:
            raise HTTPException(400, f"Invalid boundary: {e}")
    await db.flush()
    return {"id": district.id, "name": district.name, "code": district.code, "locked": district.locked}


@router.delete("/districts/{district_id}")
async def delete_district(district_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a district and all its zones."""
    from sqlalchemy import select
    result = await db.execute(select(District).where(District.id == district_id))
    district = result.scalar_one_or_none()
    if not district:
        raise HTTPException(404, "District not found")
    if district.locked:
        raise HTTPException(423, "District is locked. Unlock it first.")
    await db.delete(district)
    await db.flush()
    return {"detail": "District deleted", "id": district_id}


# ── Country boundary update ──────────────────────────────

@router.put("/countries/{country_id}/boundary")
async def update_country_boundary(
    country_id: int,
    update: BoundaryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update country boundary, or lock/unlock it."""
    from sqlalchemy import select
    from geoalchemy2.shape import from_shape
    from shapely.geometry import shape

    result = await db.execute(select(Country).where(Country.id == country_id))
    country = result.scalar_one_or_none()
    if not country:
        raise HTTPException(404, "Country not found")
    if country.locked and update.boundary_geojson is not None:
        raise HTTPException(423, "Country is locked. Unlock it first to edit.")
    if update.name is not None:
        country.name = update.name
    if update.locked is not None:
        country.locked = update.locked
    if update.boundary_geojson is not None:
        try:
            geom = shape(update.boundary_geojson)
            if not geom.is_valid:
                geom = geom.buffer(0)
            country.boundary = from_shape(geom, srid=4326)
        except Exception as e:
            raise HTTPException(400, f"Invalid boundary: {e}")
    await db.flush()
    # Fetch fresh boundary for response
    from sqlalchemy import text
    bres = await db.execute(text("SELECT ST_AsGeoJSON(boundary) AS bg FROM countries WHERE id = :cid"), {"cid": country_id})
    brow = bres.mappings().first()
    return {
        "id": country.id,
        "name": country.name,
        "locked": country.locked,
        "boundary_geojson": json.loads(brow["bg"]) if brow and brow["bg"] else None,
    }


# ── Zone Update ───────────────────────────────────────────

@router.put("/zones/{zone_id}", response_model=ZoneResponse)
async def update_zone(
    zone_id: int,
    zone_update: ZoneUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a zone's name, population, or redraw its boundary."""
    from sqlalchemy import select, text
    from geoalchemy2.shape import from_shape
    from shapely.geometry import shape

    result = await db.execute(select(PostalZone).where(PostalZone.id == zone_id))
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(404, "Zone not found")

    if zone.locked and (zone_update.boundary_geojson is not None or zone_update.name is not None):
        raise HTTPException(423, "Zone is locked. Unlock it first to edit.")
    if zone_update.name is not None:
        zone.name = zone_update.name
    if zone_update.population is not None:
        zone.population = zone_update.population
    if zone_update.locked is not None:
        zone.locked = zone_update.locked
    if zone_update.color is not None:
        zone.color = zone_update.color
    if zone_update.lat is not None and zone_update.lng is not None:
        from geoalchemy2.shape import from_shape
        from shapely.geometry import Point
        zone.center_point = from_shape(Point(zone_update.lng, zone_update.lat), srid=4326)
    if zone_update.boundary_geojson is not None:
        try:
            geom = shape(zone_update.boundary_geojson)
            if not geom.is_valid:
                raise ValueError("Invalid or self-intersecting polygon")
            zone.boundary = from_shape(geom, srid=4326)
            zone.center_point = from_shape(geom.centroid, srid=4326)
            try:
                from pyproj import Geod
                geod = Geod(ellps="WGS84")
                area, _ = geod.geometry_area_perimeter(geom)
                zone.area_sq_km = abs(area) / 1_000_000
            except Exception:
                pass
        except Exception as e:
            raise HTTPException(400, f"Invalid boundary geometry: {e}")

    await db.flush()

    fresh = await db.execute(text("""
        SELECT pz.id, pz.postal_code, pz.name, pz.status, pz.color,
               ST_Y(pz.center_point) AS center_lat,
               ST_X(pz.center_point) AS center_lng,
               pz.area_sq_km, pz.population,
               d.name AS district_name, r.name AS region_name,
               ST_AsGeoJSON(pz.boundary) AS boundary_geojson
        FROM postal_zones pz
        JOIN districts d ON pz.district_id = d.id
        JOIN regions r ON d.region_id = r.id
        WHERE pz.id = :zone_id
    """), {"zone_id": zone_id})
    row = fresh.mappings().first()
    if not row:
        raise HTTPException(404, "Zone not found after update")

    return ZoneResponse(
        id=row["id"], postal_code=row["postal_code"], name=row["name"],
        center_lat=row["center_lat"] or 0, center_lng=row["center_lng"] or 0,
        area_sq_km=row["area_sq_km"], population=row["population"],
        region_name=row["region_name"], district_name=row["district_name"],
        status=row["status"],
        color=row["color"],
        boundary_geojson=json.loads(row["boundary_geojson"]) if row["boundary_geojson"] else None,
    )


@router.delete("/zones/{zone_id}")
async def delete_zone(
    zone_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a zone by ID."""
    from sqlalchemy import select
    result = await db.execute(select(PostalZone).where(PostalZone.id == zone_id))
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(404, "Zone not found")
    if zone.locked:
        raise HTTPException(423, "Zone is locked. Unlock it first.")
    await db.delete(zone)
    await db.flush()
    return {"detail": "Zone deleted", "id": zone_id}


# ── Exports ───────────────────────────────────────────────

@router.get("/countries/{country_id}/zones/export")
async def export_zones(
    country_id: int,
    format: str = Query("csv", regex="^(csv|xlsx|json)$"),
    db: AsyncSession = Depends(get_db),
):
    """Export zones for a country as CSV, Excel, or JSON."""
    from sqlalchemy import text
    from fastapi.responses import StreamingResponse, JSONResponse
    import csv
    import io
    import pandas as pd

    result = await db.execute(text("""
        SELECT
            pz.postal_code, pz.name AS zone_name, pz.status,
            ST_Y(pz.center_point) AS center_lat, ST_X(pz.center_point) AS center_lng,
            pz.area_sq_km, pz.population,
            d.name AS district_name, r.name AS region_name
        FROM postal_zones pz
        JOIN districts d ON pz.district_id = d.id
        JOIN regions r ON d.region_id = r.id
        WHERE r.country_id = :country_id
        ORDER BY pz.postal_code
    """), {"country_id": country_id})
    rows = [dict(r) for r in result.mappings().all()]

    if format == "json":
        return JSONResponse(content=rows)

    df = pd.DataFrame(rows)
    if format == "csv":
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        stream.seek(0)
        return StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=zones.csv"}
        )

    # xlsx
    stream = io.BytesIO()
    df.to_excel(stream, index=False, sheet_name="Postal Zones")
    stream.seek(0)
    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=zones.xlsx"}
    )


@router.get("/countries/{country_id}/report")
async def export_report(
    country_id: int,
    format: str = Query("pdf", regex="^(pdf|json)$"),
    db: AsyncSession = Depends(get_db),
):
    """Generate a country postal code report as PDF or JSON summary."""
    from sqlalchemy import text, select
    from fastapi.responses import StreamingResponse, JSONResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    import io

    country_res = await db.execute(select(Country).where(Country.id == country_id))
    country = country_res.scalar_one_or_none()
    if not country:
        raise HTTPException(404, "Country not found")

    result = await db.execute(text("""
        SELECT
            pz.postal_code, pz.name AS zone_name, pz.status,
            pz.area_sq_km, pz.population,
            d.name AS district_name, r.name AS region_name
        FROM postal_zones pz
        JOIN districts d ON pz.district_id = d.id
        JOIN regions r ON d.region_id = r.id
        WHERE r.country_id = :country_id
        ORDER BY pz.postal_code
    """), {"country_id": country_id})
    zones = [dict(r) for r in result.mappings().all()]

    stats = await db.execute(text("""
        SELECT
            COUNT(DISTINCT pz.id) AS total_zones,
            COUNT(DISTINCT d.id) AS total_districts,
            COUNT(DISTINCT r.id) AS total_regions,
            COALESCE(SUM(pz.population), 0) AS total_population_covered
        FROM postal_zones pz
        JOIN districts d ON pz.district_id = d.id
        JOIN regions r ON d.region_id = r.id
        WHERE r.country_id = :country_id
    """), {"country_id": country_id})
    stats_row = stats.mappings().first()

    if format == "json":
        return JSONResponse(content={
            "country": country.name,
            "iso_code": country.iso_code,
            "stats": dict(stats_row) if stats_row else {},
            "zones": zones,
        })

    # PDF generation
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"<b>National Postal Code Report</b>", styles["Title"]))
    story.append(Paragraph(f"Country: {country.name} ({country.iso_code})", styles["Heading2"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"<b>Overview</b>", styles["Heading3"]))
    story.append(Paragraph(f"Total Zones: {stats_row['total_zones'] if stats_row else 0}", styles["Normal"]))
    story.append(Paragraph(f"Total Districts: {stats_row['total_districts'] if stats_row else 0}", styles["Normal"]))
    story.append(Paragraph(f"Total Regions: {stats_row['total_regions'] if stats_row else 0}", styles["Normal"]))
    story.append(Paragraph(f"Population Covered: {(stats_row['total_population_covered'] or 0):,}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"<b>Postal Zones</b>", styles["Heading3"]))
    if zones:
        table_data = [["Postal Code", "Zone Name", "District", "Region", "Population", "Area km²", "Status"]]
        for z in zones:
            table_data.append([
                z["postal_code"], z["zone_name"], z["district_name"],
                z["region_name"], str(z["population"] or "-"),
                f"{z['area_sq_km']:.1f}" if z["area_sq_km"] else "-",
                z["status"],
            ])
        t = Table(table_data, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6c63ff')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No zones generated yet.", styles["Normal"]))

    doc.build(story)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={country.iso_code}_postal_zones.pdf"}
    )


# ── Country Lookup ─────────────────────────────────────────

@router.get("/countries/lookup/{name}")
async def lookup_country_by_name(name: str):
    """Look up a country by name and return real-world metadata."""
    service = CountryLookupService()
    result = await service.lookup_country(name)
    if not result:
        raise HTTPException(404, f"Country '{name}' not found in global databases")
    return result


@router.get("/cities/lookup")
async def lookup_city(query: str, country_code: Optional[str] = None):
    """Look up a city by name and return coordinates."""
    service = CountryLookupService()
    result = await service.lookup_city(query, country_code)
    if not result:
        raise HTTPException(404, f"City '{query}' not found")
    return result


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
    """USSD handler for basic phone lookup."""
    parts = request.text.split("*") if request.text else []
    level = len(parts)
    service = LookupService(db)
    sid = request.session_id or "ussd-session"

    if level == 0:
        return USSDResponse(
            session_id=sid,
            text="CON Welcome to Postal Code Lookup\n1. Search by area name\n2. Verify a postal code",
            response_type="CON",
        )
    elif level == 1 and parts[0] == "1":
        return USSDResponse(session_id=sid, text="CON Enter area/village name:", response_type="CON")
    elif level == 1 and parts[0] == "2":
        return USSDResponse(session_id=sid, text="CON Enter postal code to verify:", response_type="CON")
    elif level == 2 and parts[0] == "1":
        results = await service.lookup_by_name(parts[1], "SSD")
        if results["zone_results"]:
            text = "END Results:\n"
            for i, r in enumerate(results["zone_results"][:3]):
                text += f"{i+1}. {r['zone_name']}: {r['postal_code']}\n"
            return USSDResponse(session_id=sid, text=text, response_type="END")
        return USSDResponse(session_id=sid, text=f"END No postal code found for '{parts[1]}'.", response_type="END")
    elif level == 2 and parts[0] == "2":
        result = await service.verify_code(parts[1])
        if result and result.get("valid"):
            return USSDResponse(
                session_id=sid,
                text=f"END Valid: {result['postal_code']}\nArea: {result['name']}\nDistrict: {result['district']}",
                response_type="END",
            )
        return USSDResponse(session_id=sid, text=f"END Invalid code: {parts[1]}", response_type="END")
    else:
        return USSDResponse(session_id=sid, text="END Invalid option. Try again.", response_type="END")


# ── Policy ────────────────────────────────────────────────

@router.post("/countries/{country_id}/policy", response_model=PolicyDocumentResponse)
async def generate_policy(country_id: int, db: AsyncSession = Depends(get_db)):
    """Generate policy documents for a country's postal code system."""
    from sqlalchemy import select
    try:
        result = await db.execute(select(Country).where(Country.id == country_id))
        country = result.scalar_one_or_none()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Policy: DB error loading country {country_id}: {e}")
        raise HTTPException(503, f"Database not ready: {e}")

    if not country:
        raise HTTPException(404, "Country not found")

    try:
        profile = CountryProfileCreate(
            name=country.name,
            iso_code=country.iso_code,
            tier=country.tier if country.tier else "mixed_rural_urban",
            estimated_population=country.estimated_population or 0,
            area_sq_km=country.area_sq_km or 1,
            num_regions=country.num_regions or 1,
            num_districts=country.num_districts or 1,
            languages=json.loads(country.languages) if country.languages else [],
            has_street_names=bool(country.has_street_names),
            has_house_numbers=bool(country.has_house_numbers),
            has_any_addressing=bool(country.has_any_addressing),
            urban_percentage=float(country.urban_percentage or 0),
            literacy_rate=float(country.literacy_rate or 0),
            mobile_penetration=float(country.mobile_penetration or 0),
            internet_penetration=float(country.internet_penetration or 0),
            existing_admin_divisions=json.loads(country.existing_admin_divisions) if country.existing_admin_divisions else {},
            capital_city=country.capital_city,
            capital_lat=float(country.capital_lat) if country.capital_lat else None,
            capital_lng=float(country.capital_lng) if country.capital_lng else None,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Policy: validation error for country {country_id}: {e}")
        raise HTTPException(422, f"Invalid country data: {e}")

    try:
        designer = PostalSystemDesigner(profile)
        analysis = designer.analyze_country()
        generator = PolicyDocumentGenerator()
        doc_result = generator.generate_postal_code_policy(profile, analysis)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Policy: generation error for country {country_id}: {e}")
        raise HTTPException(500, f"Failed to generate policy: {e}")

    return PolicyDocumentResponse(
        country_id=country_id,
        title=f"National Postal Code Policy - {country.name}",
        policy_document=doc_result["policy_document"],
        implementation_guide=doc_result["implementation_guide"],
        sections=[],
    )


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


# ── Drawing Snapshots ────────────────────────────────────

@router.post("/countries/{country_id}/snapshots")
async def save_snapshot(
    country_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Save a snapshot of current regions, districts, and zones for a country."""
    from sqlalchemy import select, text
    from geoalchemy2.shape import to_shape
    import json

    # Get regions with boundaries
    reg_res = await db.execute(text("""
        SELECT id, name, code, locked,
               ST_AsGeoJSON(boundary) AS boundary_geojson,
               ST_AsGeoJSON(center_point) AS center_geojson
        FROM regions WHERE country_id = :cid
    """), {"cid": country_id})
    regions = []
    for r in reg_res.mappings().all():
        regions.append({
            "id": r["id"], "name": r["name"], "code": r["code"], "locked": bool(r["locked"]),
            "boundary_geojson": json.loads(r["boundary_geojson"]) if r["boundary_geojson"] else None,
            "center_geojson": json.loads(r["center_geojson"]) if r["center_geojson"] else None,
        })

    # Get districts with boundaries
    dist_res = await db.execute(text("""
        SELECT d.id, d.name, d.code, d.region_id, d.locked,
               ST_AsGeoJSON(d.boundary) AS boundary_geojson,
               ST_AsGeoJSON(d.center_point) AS center_geojson
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.country_id = :cid
    """), {"cid": country_id})
    districts = []
    for d in dist_res.mappings().all():
        districts.append({
            "id": d["id"], "name": d["name"], "code": d["code"],
            "region_id": d["region_id"], "locked": bool(d["locked"]),
            "boundary_geojson": json.loads(d["boundary_geojson"]) if d["boundary_geojson"] else None,
            "center_geojson": json.loads(d["center_geojson"]) if d["center_geojson"] else None,
        })

    # Get zones with boundaries
    zone_res = await db.execute(text("""
        SELECT pz.id, pz.postal_code, pz.name, pz.status, pz.population, pz.area_sq_km, pz.color, pz.locked,
               d.id AS district_id,
               ST_AsGeoJSON(pz.boundary) AS boundary_geojson,
               ST_AsGeoJSON(pz.center_point) AS center_geojson
        FROM postal_zones pz
        JOIN districts d ON pz.district_id = d.id
        JOIN regions r ON d.region_id = r.id
        WHERE r.country_id = :cid
    """), {"cid": country_id})
    zones = []
    for z in zone_res.mappings().all():
        zones.append({
            "id": z["id"], "postal_code": z["postal_code"], "name": z["name"],
            "status": z["status"], "population": z["population"], "area_sq_km": z["area_sq_km"],
            "color": z["color"], "locked": bool(z["locked"]), "district_id": z["district_id"],
            "boundary_geojson": json.loads(z["boundary_geojson"]) if z["boundary_geojson"] else None,
            "center_geojson": json.loads(z["center_geojson"]) if z["center_geojson"] else None,
        })

    snapshot = json.dumps({"regions": regions, "districts": districts, "zones": zones})

    from app.models.database import DrawingSnapshot
    snap = DrawingSnapshot(country_id=country_id, snapshot=snapshot)
    db.add(snap)
    await db.flush()
    await db.refresh(snap)
    return {"id": snap.id, "country_id": country_id, "created_at": str(snap.created_at), "regions": len(regions), "districts": len(districts), "zones": len(zones)}


@router.get("/countries/{country_id}/snapshots")
async def list_snapshots(
    country_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List all saved snapshots for a country."""
    from sqlalchemy import select, text
    from app.models.database import DrawingSnapshot
    result = await db.execute(
        select(DrawingSnapshot).where(DrawingSnapshot.country_id == country_id).order_by(DrawingSnapshot.created_at.desc())
    )
    snaps = result.scalars().all()
    return [{"id": s.id, "country_id": s.country_id, "created_at": str(s.created_at)} for s in snaps]


@router.post("/countries/{country_id}/snapshots/{snapshot_id}/restore")
async def restore_snapshot(
    country_id: int,
    snapshot_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Restore a snapshot: replace all regions, districts, and zones with the saved state."""
    from sqlalchemy import select, text
    from geoalchemy2.shape import from_shape
    from shapely.geometry import shape
    import json
    from app.models.database import DrawingSnapshot, Region, District, PostalZone

    snap_res = await db.execute(select(DrawingSnapshot).where(DrawingSnapshot.id == snapshot_id, DrawingSnapshot.country_id == country_id))
    snap = snap_res.scalar_one_or_none()
    if not snap:
        raise HTTPException(404, "Snapshot not found")

    data = json.loads(snap.snapshot)

    # Delete current regions using ORM so SQLAlchemy cascades work properly
    # Raw SQL DELETE would orphan districts and zones, causing unique constraint errors on restore
    reg_res = await db.execute(select(Region).where(Region.country_id == country_id))
    for reg in reg_res.scalars().all():
        await db.delete(reg)
    await db.flush()

    # Restore regions
    region_id_map = {}  # old_id -> new_id
    for r in data.get("regions", []):
        reg = Region(
            country_id=country_id,
            name=r["name"],
            code=r["code"],
            locked=r.get("locked", False),
        )
        if r.get("boundary_geojson"):
            try:
                geom = shape(r["boundary_geojson"])
                if not geom.is_valid:
                    geom = geom.buffer(0)
                reg.boundary = from_shape(geom, srid=4326)
            except Exception:
                pass
        if r.get("center_geojson"):
            try:
                geom = shape(r["center_geojson"])
                reg.center_point = from_shape(geom, srid=4326)
            except Exception:
                pass
        db.add(reg)
        await db.flush()
        await db.refresh(reg)
        region_id_map[r["id"]] = reg.id

    # Restore districts
    district_id_map = {}  # old_id -> new_id
    for d in data.get("districts", []):
        new_region_id = region_id_map.get(d["region_id"])
        if not new_region_id:
            continue
        dist = District(
            region_id=new_region_id,
            name=d["name"],
            code=d["code"],
            locked=d.get("locked", False),
        )
        if d.get("boundary_geojson"):
            try:
                geom = shape(d["boundary_geojson"])
                if not geom.is_valid:
                    geom = geom.buffer(0)
                dist.boundary = from_shape(geom, srid=4326)
            except Exception:
                pass
        if d.get("center_geojson"):
            try:
                geom = shape(d["center_geojson"])
                dist.center_point = from_shape(geom, srid=4326)
            except Exception:
                pass
        db.add(dist)
        await db.flush()
        await db.refresh(dist)
        district_id_map[d["id"]] = dist.id

    # Restore zones
    for z in data.get("zones", []):
        new_district_id = district_id_map.get(z["district_id"])
        if not new_district_id:
            continue
        zone = PostalZone(
            district_id=new_district_id,
            postal_code=z["postal_code"],
            name=z["name"],
            status=z.get("status", "active"),
            population=z.get("population"),
            area_sq_km=z.get("area_sq_km"),
            color=z.get("color"),
            locked=z.get("locked", False),
        )
        if z.get("boundary_geojson"):
            try:
                geom = shape(z["boundary_geojson"])
                if not geom.is_valid:
                    geom = geom.buffer(0)
                zone.boundary = from_shape(geom, srid=4326)
            except Exception:
                pass
        if z.get("center_geojson"):
            try:
                geom = shape(z["center_geojson"])
                zone.center_point = from_shape(geom, srid=4326)
            except Exception:
                pass
        db.add(zone)
        await db.flush()

    await db.flush()
    return {"detail": "Snapshot restored", "regions": len(data.get("regions", [])), "districts": len(data.get("districts", [])), "zones": len(data.get("zones", []))}


# ── Zone Split ───────────────────────────────────────────

@router.post("/zones/{zone_id}/split")
async def split_zone(
    zone_id: int,
    line_geojson: dict,
    db: AsyncSession = Depends(get_db),
):
    """Split a zone into two zones using a line."""
    from sqlalchemy import select, text
    from geoalchemy2.shape import from_shape, to_shape
    from shapely.geometry import shape, LineString, MultiPolygon, Polygon
    from shapely.ops import split
    import json

    result = await db.execute(select(PostalZone).where(PostalZone.id == zone_id))
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(404, "Zone not found")
    if zone.locked:
        raise HTTPException(423, "Zone is locked. Unlock it first.")

    # Parse zone boundary
    if zone.boundary is None:
        raise HTTPException(400, "Zone has no boundary to split")

    try:
        zone_poly = to_shape(zone.boundary)
    except Exception as e:
        raise HTTPException(400, f"Invalid zone boundary: {e}")

    # Parse split line
    try:
        line_geom = shape(line_geojson)
        if not line_geom.is_valid:
            line_geom = line_geom.buffer(0)
    except Exception as e:
        raise HTTPException(400, f"Invalid line geometry: {e}")

    # Ensure line extends beyond the polygon
    minx, miny, maxx, maxy = zone_poly.bounds
    dx = maxx - minx
    dy = maxy - miny
    
    # Extend the line
    coords = list(line_geom.coords)
    if len(coords) < 2:
        raise HTTPException(400, "Line must have at least 2 points")
    
    # Calculate direction vector
    x1, y1 = coords[0]
    x2, y2 = coords[-1]
    length = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5
    if length == 0:
        raise HTTPException(400, "Line has zero length")
    
    dx_line = (x2 - x1) / length
    dy_line = (y2 - y1) / length
    
    # Extend by 2x the polygon size in each direction
    extend = max(dx, dy) * 2
    extended_coords = [
        (x1 - dx_line * extend, y1 - dy_line * extend),
        *coords[1:-1],
        (x2 + dx_line * extend, y2 + dy_line * extend),
    ]
    extended_line = LineString(extended_coords)

    # Split the polygon
    try:
        split_result = split(zone_poly, extended_line)
    except Exception as e:
        raise HTTPException(400, f"Failed to split zone: {e}")

    # Filter valid polygons
    pieces = []
    for geom in split_result.geoms:
        if isinstance(geom, Polygon) and not geom.is_empty and geom.area > 1e-12:
            pieces.append(geom)
        elif isinstance(geom, MultiPolygon):
            for poly in geom.geoms:
                if not poly.is_empty and poly.area > 1e-12:
                    pieces.append(poly)

    if len(pieces) < 2:
        raise HTTPException(400, "Split line did not divide the zone into separate pieces")

    # Use the two largest pieces
    pieces.sort(key=lambda p: p.area, reverse=True)
    piece_a, piece_b = pieces[0], pieces[1]

    # Update original zone with first piece
    zone.boundary = from_shape(piece_a, srid=4326)
    zone.center_point = from_shape(piece_a.centroid, srid=4326)
    try:
        from pyproj import Geod
        geod = Geod(ellps="WGS84")
        area, _ = geod.geometry_area_perimeter(piece_a)
        zone.area_sq_km = abs(area) / 1_000_000
    except Exception:
        pass

    # Create second zone
    # Get next postal code
    dist_res = await db.execute(select(District).where(District.id == zone.district_id))
    district = dist_res.scalar_one_or_none()
    region_res = await db.execute(select(Region).where(Region.id == district.region_id)) if district else None
    region = region_res.scalar_one_or_none() if region_res else None
    new_postal_code = await _generate_next_postal_code(
        db, zone.district_id,
        region.name if region else "",
        district.name if district else ""
    )

    new_zone = PostalZone(
        district_id=zone.district_id,
        postal_code=new_postal_code,
        name=f"{zone.name} B",
        status="active",
        population=zone.population // 2 if zone.population else None,
        boundary=from_shape(piece_b, srid=4326),
        center_point=from_shape(piece_b.centroid, srid=4326),
    )
    try:
        from pyproj import Geod
        geod = Geod(ellps="WGS84")
        area, _ = geod.geometry_area_perimeter(piece_b)
        new_zone.area_sq_km = abs(area) / 1_000_000
    except Exception:
        pass

    db.add(new_zone)
    await db.flush()
    await db.refresh(new_zone)

    # Update original zone name
    zone.name = f"{zone.name} A"
    await db.flush()

    return {
        "detail": "Zone split successfully",
        "original_zone": {"id": zone.id, "postal_code": zone.postal_code, "name": zone.name},
        "new_zone": {"id": new_zone.id, "postal_code": new_zone.postal_code, "name": new_zone.name},
    }
