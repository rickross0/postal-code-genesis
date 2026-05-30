"""Public Lookup System — web, USSD, and SMS lookup."""

from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json


class LookupService:
    """Service for looking up postal codes by coordinates, name, or USSD."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def lookup_by_coordinates(self, lat: float, lng: float) -> Dict[str, Any]:
        """Find postal code for any GPS coordinate."""
        result = await self.db.execute(text("""
            SELECT
                pz.postal_code, pz.name AS zone_name,
                pz.population,
                d.name AS district_name,
                r.name AS region_name,
                ST_AsGeoJSON(pz.boundary) AS boundary,
                ST_Y(pz.center_point) AS center_lat,
                ST_X(pz.center_point) AS center_lng
            FROM postal_zones pz
            JOIN districts d ON pz.district_id = d.id
            JOIN regions r ON d.region_id = r.id
            WHERE ST_Contains(
                pz.boundary,
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)
            ) AND pz.status = 'active'
            LIMIT 1
        """), {"lat": lat, "lng": lng})
        zone = result.mappings().first()

        if not zone:
            nearest = await self.db.execute(text("""
                SELECT pz.postal_code, pz.name AS zone_name,
                       ST_Distance(
                           pz.boundary::geography,
                           ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
                       ) AS distance
                FROM postal_zones pz
                WHERE pz.status = 'active'
                ORDER BY pz.boundary <->
                    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)
                LIMIT 1
            """), {"lat": lat, "lng": lng})
            near = nearest.mappings().first()
            return {
                "found": False,
                "nearest_code": near["postal_code"] if near else None,
                "message": "Location is outside defined postal zones. Nearest zone shown.",
            }

        # Get nearby landmarks
        landmarks_result = await self.db.execute(text("""
            SELECT name, category,
                   ST_Distance(
                       location::geography,
                       ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
                   ) AS distance
            FROM landmarks
            WHERE postal_zone_id = (SELECT id FROM postal_zones WHERE postal_code = :code)
            ORDER BY location <->
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)
            LIMIT 5
        """), {"lat": lat, "lng": lng, "code": zone["postal_code"]})
        landmarks = [
            {"name": lm["name"], "type": lm["category"], "distance_meters": round(lm["distance"] or 0)}
            for lm in landmarks_result.mappings().all()
        ]

        return {
            "found": True,
            "postal_code": zone["postal_code"],
            "zone_name": zone["zone_name"],
            "district": zone["district_name"],
            "region": zone["region_name"],
            "nearby_landmarks": landmarks,
            "full_address_suggestion": (
                f"{zone['zone_name']}, {zone['district_name']}, "
                f"{zone['region_name']} [{zone['postal_code']}]"
            ),
        }

    async def lookup_by_name(self, query: str, country: str) -> Dict[str, Any]:
        """Search by place name or landmark."""
        zone_results = await self.db.execute(text("""
            SELECT
                pz.postal_code, pz.name AS zone_name,
                d.name AS district, r.name AS region,
                ST_Y(pz.center_point) AS lat,
                ST_X(pz.center_point) AS lng,
                similarity(pz.name, :query) AS name_match
            FROM postal_zones pz
            JOIN districts d ON pz.district_id = d.id
            JOIN regions r ON d.region_id = r.id
            JOIN countries c ON r.country_id = c.id
            WHERE c.iso_code = :country
            AND (pz.name ILIKE '%' || :query || '%'
                 OR d.name ILIKE '%' || :query || '%'
                 OR similarity(pz.name, :query) > 0.3)
            AND pz.status = 'active'
            ORDER BY similarity(pz.name, :query) DESC
            LIMIT 10
        """), {"query": query, "country": country})

        landmark_results = await self.db.execute(text("""
            SELECT l.name AS landmark_name, l.category,
                   pz.postal_code, pz.name AS zone_name
            FROM landmarks l
            JOIN postal_zones pz ON l.postal_zone_id = pz.id
            JOIN districts d ON pz.district_id = d.id
            JOIN regions r ON d.region_id = r.id
            JOIN countries c ON r.country_id = c.id
            WHERE c.iso_code = :country
            AND l.name ILIKE '%' || :query || '%'
            LIMIT 5
        """), {"query": query, "country": country})

        return {
            "zone_results": [dict(r) for r in zone_results.mappings().all()],
            "landmark_results": [dict(r) for r in landmark_results.mappings().all()],
        }

    async def verify_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Verify if a postal code exists."""
        result = await self.db.execute(text("""
            SELECT pz.name, pz.postal_code, d.name AS district, r.name AS region
            FROM postal_zones pz
            JOIN districts d ON pz.district_id = d.id
            JOIN regions r ON d.region_id = r.id
            WHERE pz.postal_code = :code
        """), {"code": code})
        row = result.mappings().first()
        if row:
            return {"valid": True, **dict(row)}
        return {"valid": False, "postal_code": code}
