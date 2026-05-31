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
            tier=existing_country.tier,
            estimated_population=existing_country.estimated_population,
            area_sq_km=existing_country.area_sq_km,
            num_regions=existing_country.num_regions,
            num_districts=existing_country.num_districts,
            languages=profile.languages,
            urban_percentage=existing_country.urban_percentage,
            literacy_rate=existing_country.literacy_rate,
            mobile_penetration=existing_country.mobile_penetration,
            capital_city=existing_country.capital_city,
            capital_lat=existing_country.capital_lat,
            capital_lng=existing_country.capital_lng,
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
    from sqlalchemy import select
    try:
        result = await db.execute(select(Country).order_by(Country.name))
        countries = result.scalars().all()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to query countries: {e}")
        raise HTTPException(503, f"Database not ready: {e}")
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
    zones = engine.assign_codes(zones, district.name, dc)

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

    # Delete existing zones for this country
    await db.execute(text("""
        DELETE FROM postal_zones WHERE district_id IN (
            SELECT d.id FROM districts d JOIN regions r ON d.region_id = r.id WHERE r.country_id = :cid
        )
    """), {"cid": country_id})

    engine = ZoneCreationEngine()
    all_zones = []

    for region in regions:
        # Load districts for this region
        dist_res = await db.execute(select(District).where(District.region_id == region.id))
        districts = dist_res.scalars().all()

        for district in districts:
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
            zones = engine.assign_codes(zones, district.name, dc)

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
                    region_name=region.name,
                    district_name=district.name,
                    boundary_geojson=z.get("boundary_geojson"),
                ))

    return all_zones


@router.get("/countries/{country_id}/zones", response_model=List[ZoneResponse])
async def list_zones(
    country_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List all postal zones for a country, including district boundaries."""
    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT
            pz.id, pz.postal_code, pz.name, pz.status,
            ST_Y(pz.center_point) AS center_lat,
            ST_X(pz.center_point) AS center_lng,
            pz.area_sq_km, pz.population,
            d.id AS district_id, d.name AS district_name, d.code AS district_code,
            r.name AS region_name, r.code AS region_code,
            ST_AsGeoJSON(pz.boundary) AS boundary_geojson,
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
        rows.append(row)
    return rows


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

    if zone_update.name is not None:
        zone.name = zone_update.name
    if zone_update.population is not None:
        zone.population = zone_update.population
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
        SELECT pz.id, pz.postal_code, pz.name, pz.status,
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
        boundary_geojson=json.loads(row["boundary_geojson"]) if row["boundary_geojson"] else None,
    )


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

    if level == 0:
        return USSDResponse(
            response="CON Welcome to Postal Code Lookup\n1. Search by area name\n2. Verify a postal code",
            type="CON",
        )
    elif level == 1 and parts[0] == "1":
        return USSDResponse(response="CON Enter area/village name:", type="CON")
    elif level == 1 and parts[0] == "2":
        return USSDResponse(response="CON Enter postal code to verify:", type="CON")
    elif level == 2 and parts[0] == "1":
        results = await service.lookup_by_name(parts[1], "SSD")
        if results["zone_results"]:
            text = "END Results:\n"
            for i, r in enumerate(results["zone_results"][:3]):
                text += f"{i+1}. {r['zone_name']}: {r['postal_code']}\n"
            return USSDResponse(response=text, type="END")
        return USSDResponse(response=f"END No postal code found for '{parts[1]}'.", type="END")
    elif level == 2 and parts[0] == "2":
        result = await service.verify_code(parts[1])
        if result and result.get("valid"):
            return USSDResponse(
                response=f"END Valid: {result['postal_code']}\nArea: {result['name']}\nDistrict: {result['district']}",
                type="END",
            )
        return USSDResponse(response=f"END Invalid code: {parts[1]}", type="END")
    else:
        return USSDResponse(response="END Invalid option. Try again.", type="END")


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
        languages=json.loads(country.languages) if country.languages else [],
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
