"""Seed database with demo data (South Sudan example)."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.core.database import engine, async_session, Base
from app.models.database import Country, Region, District, PostalZone, Landmark
from geoalchemy2.shape import from_shape
from shapely.geometry import Point, Polygon, MultiPolygon
from sqlalchemy import text


async def seed():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # South Sudan
        country = Country(
            name="South Sudan",
            iso_code="SSD",
            tier="conflict_post_conflict",
            estimated_population=11_000_000,
            area_sq_km=619_745,
            num_regions=10,
            num_districts=79,
            languages='["English", "Arabic", "Dinka", "Nuer"]',
            has_street_names=False,
            has_house_numbers=False,
            urban_percentage=19.6,
            literacy_rate=0.34,
            mobile_penetration=0.33,
            internet_penetration=0.08,
        )
        session.add(country)
        await session.flush()

        # Regions (states)
        regions_data = [
            ("Central Equatoria", "01", 4.85, 31.60),
            ("Eastern Equatoria", "02", 4.30, 33.50),
            ("Jonglei", "03", 7.10, 32.50),
            ("Lakes", "04", 6.80, 30.50),
            ("Northern Bahr el Ghazal", "05", 8.50, 27.50),
            ("Unity", "06", 7.60, 29.50),
            ("Upper Nile", "07", 9.50, 32.50),
            ("Western Bahr el Ghazal", "08", 7.50, 28.00),
            ("Western Equatoria", "09", 4.50, 28.50),
            ("Warrap", "10", 7.80, 28.80),
        ]

        regions = []
        for name, code, lat, lng in regions_data:
            r = Region(
                country_id=country.id, name=name, code=code,
                center_point=from_shape(Point(lng, lat), srid=4326),
            )
            session.add(r)
            await session.flush()
            regions.append(r)

        # Districts for Central Equatoria
        districts_data = [
            ("Juba County", "01", 4.85, 31.60),
            ("Kajo Keji County", "02", 3.90, 31.60),
            ("Lainya County", "03", 4.50, 31.20),
            ("Morobo County", "04", 3.70, 30.90),
            ("Yei County", "05", 4.10, 30.60),
            ("Terekeka County", "06", 4.90, 31.90),
        ]

        districts = []
        for name, code, lat, lng in districts_data:
            d = District(
                region_id=regions[0].id, name=name, code=code,
                center_point=from_shape(Point(lng, lat), srid=4326),
            )
            session.add(d)
            await session.flush()
            districts.append(d)

        # Postal Zones for Juba County
        zones_data = [
            ("Juba Central Market Area", "01-01-01", 4.850, 31.580, 12000, 5.2),
            ("Juba University Area", "01-01-02", 4.840, 31.600, 8000, 4.1),
            ("Juba Airport Area", "01-01-03", 4.870, 31.610, 6000, 3.8),
            ("Juba Hai Malakal Area", "01-01-04", 4.860, 31.570, 9000, 4.5),
            ("Juba Gudele Area", "01-01-05", 4.830, 31.550, 11000, 6.2),
            ("Juba Munuki Area", "01-01-06", 4.820, 31.620, 7500, 5.0),
            ("Juba Lologo Area", "01-01-07", 4.810, 31.560, 5000, 3.5),
            ("Juba Custom Market Area", "01-01-08", 4.855, 31.590, 7000, 2.8),
            ("Juba Kator Area", "01-01-09", 4.845, 31.565, 8500, 3.2),
            ("Juba Atlabara Area", "01-01-10", 4.865, 31.595, 6500, 4.0),
            ("Juba Jebel Area", "01-01-11", 4.835, 31.545, 4500, 5.5),
            ("Juba News Area", "01-01-12", 4.825, 31.610, 5500, 3.8),
        ]

        zones = []
        for name, postal_code, lat, lng, pop, area in zones_data:
            # Create a simple polygon around the center point
            delta = 0.01
            boundary = Polygon([
                (lng - delta, lat - delta),
                (lng + delta, lat - delta),
                (lng + delta, lat + delta),
                (lng - delta, lat + delta),
                (lng - delta, lat - delta),
            ])
            z = PostalZone(
                district_id=districts[0].id,
                postal_code=postal_code,
                code_numeric=postal_code.replace("-", ""),
                name=name,
                population=pop,
                area_sq_km=area,
                center_point=from_shape(Point(lng, lat), srid=4326),
                boundary=from_shape(boundary, srid=4326),
                status="active",
            )
            session.add(z)
            await session.flush()
            zones.append(z)

        # Landmarks
        landmarks_data = [
            ("Juba Central Market", "market", 4.850, 31.580, zones[0].id, True),
            ("Juba Teaching Hospital", "hospital", 4.845, 31.575, zones[0].id, True),
            ("University of Juba", "school", 4.840, 31.600, zones[1].id, True),
            ("Juba International Airport", "bus_station", 4.870, 31.610, zones[2].id, True),
            ("St. Mary's Cathedral", "church", 4.860, 31.570, zones[3].id, True),
            ("Juba Police Station", "police", 4.855, 31.585, zones[0].id, True),
            ("Gudele Primary School", "school", 4.830, 31.550, zones[4].id, False),
            ("Juba City Council", "local_government_office", 4.852, 31.582, zones[0].id, True),
            ("Kator Catholic Church", "church", 4.845, 31.565, zones[8].id, True),
            ("Atlabara Health Center", "hospital", 4.865, 31.595, zones[9].id, False),
        ]

        for name, category, lat, lng, zone_id, is_known in landmarks_data:
            lm = Landmark(
                postal_zone_id=zone_id,
                name=name,
                category=category,
                location=from_shape(Point(lng, lat), srid=4326),
                is_well_known=is_known,
            )
            session.add(lm)

        await session.commit()

    print("✅ Seed data created successfully!")
    print(f"   Country: South Sudan (SSD)")
    print(f"   Regions: {len(regions)}")
    print(f"   Districts: {len(districts)} (Central Equatoria)")
    print(f"   Zones: {len(zones)} (Juba County)")
    print(f"   Landmarks: {len(landmarks_data)}")


if __name__ == "__main__":
    asyncio.run(seed())
