"""Intelligent Zone Creation Engine - creates postal zones algorithmically."""

from typing import List, Dict, Any, Optional, Tuple
from shapely.geometry import Polygon, Point, MultiPolygon, mapping
from shapely.ops import unary_union
import json
import math


class ZoneCreationEngine:
    """Creates postal zones using map data + intelligent algorithms."""

    def create_zones_intelligent(
        self,
        region_boundary_geojson: Dict[str, Any],
        settlements: List[Dict[str, Any]],
        target_population_per_zone: int = 5000,
        estimated_population: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Intelligently create postal zones considering settlements, roads, etc."""
        region = self._geojson_to_polygon(region_boundary_geojson)
        if region is None or region.is_empty:
            raise ValueError("Invalid region boundary")

        if estimated_population:
            n_zones = max(4, estimated_population // target_population_per_zone)
        else:
            n_zones = max(4, len(settlements) // 2)

        if settlements:
            zones = self._create_zones_around_settlements(region, settlements, n_zones)
        else:
            zones = self._create_grid_zones(region, n_zones)

        zones = self._name_zones(zones)
        return zones

    def _create_zones_around_settlements(
        self,
        region: Polygon,
        settlements: List[Dict[str, Any]],
        n_zones: int,
    ) -> List[Dict[str, Any]]:
        """Voronoi-based zones centered on settlements."""
        try:
            import numpy as np
            from scipy.spatial import Voronoi
        except ImportError:
            # Fallback to grid if scipy not available
            return self._create_grid_zones(region, n_zones)

        points = []
        for s in settlements[:n_zones]:
            lng = s.get("location", {}).get("lng", s.get("lng", 0))
            lat = s.get("location", {}).get("lat", s.get("lat", 0))
            p = Point(lng, lat)
            if region.contains(p):
                points.append([lng, lat])

        while len(points) < n_zones:
            minx, miny, maxx, maxy = region.bounds
            rng = np.random.default_rng()
            rp = Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy))
            if region.contains(rp):
                points.append([rp.x, rp.y])

        points_arr = np.array(points[:n_zones])

        if len(points_arr) < 4:
            return self._create_grid_zones(region, n_zones)

        vor = Voronoi(points_arr)
        zones = []
        for i in range(len(points_arr)):
            region_idx = vor.point_region[i]
            vertices = vor.regions[region_idx]
            if -1 in vertices or len(vertices) == 0:
                continue
            poly_points = [vor.vertices[v] for v in vertices]
            try:
                zone_polygon = Polygon(poly_points)
                zone_polygon = zone_polygon.intersection(region)
                if zone_polygon.is_empty:
                    continue
                zones.append({
                    "id": i + 1,
                    "center": {"lng": float(points_arr[i][0]), "lat": float(points_arr[i][1])},
                    "boundary_geojson": mapping(zone_polygon) if hasattr(zone_polygon, "__geo_interface__") else None,
                    "area_sq_km": self._calc_area_sq_km(zone_polygon),
                    "landmarks": [],
                    "name": None,
                    "postal_code": None,
                })
            except Exception:
                continue
        return zones

    def _create_grid_zones(
        self, region: Polygon, n_zones: int
    ) -> List[Dict[str, Any]]:
        """Fallback: create a regular grid of zones."""
        import math
        minx, miny, maxx, maxy = region.bounds
        cols = max(2, int(math.ceil(math.sqrt(n_zones))))
        rows = max(2, int(math.ceil(n_zones / cols)))
        dx = (maxx - minx) / cols
        dy = (maxy - miny) / rows

        zones = []
        zone_id = 1
        for r in range(rows):
            for c in range(cols):
                cell = Polygon([
                    (minx + c * dx, miny + r * dy),
                    (minx + (c + 1) * dx, miny + r * dy),
                    (minx + (c + 1) * dx, miny + (r + 1) * dy),
                    (minx + c * dx, miny + (r + 1) * dy),
                ])
                clipped = cell.intersection(region)
                if clipped.is_empty:
                    continue
                centroid = clipped.centroid
                zones.append({
                    "id": zone_id,
                    "center": {"lng": centroid.x, "lat": centroid.y},
                    "boundary_geojson": mapping(clipped) if hasattr(clipped, "__geo_interface__") else None,
                    "area_sq_km": self._calc_area_sq_km(clipped),
                    "landmarks": [],
                    "name": None,
                    "postal_code": None,
                })
                zone_id += 1
        return zones

    def assign_codes(
        self,
        zones: List[Dict[str, Any]],
        region_code: str,
        district_code: str,
        start_from: int = 1,
        reserve_percentage: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """Assign postal codes with room for future growth."""
        zones_sorted = sorted(
            zones,
            key=lambda z: (-z["center"]["lat"], z["center"]["lng"]),
        )
        max_code = 99
        available = max_code - start_from + 1
        usable = int(available * (1 - reserve_percentage))
        spacing = max(1, usable // max(len(zones_sorted), 1))

        current_code = start_from
        for zone in zones_sorted:
            zone_code = f"{current_code:02d}"
            zone["postal_code"] = f"{region_code}-{district_code}-{zone_code}"
            zone["code_numeric"] = f"{region_code}{district_code}{zone_code}"
            current_code += spacing
        return zones_sorted

    def _name_zones(self, zones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Name zones based on their primary landmark."""
        for zone in zones:
            landmarks = zone.get("landmarks", [])
            if landmarks:
                priority = [
                    "local_government_office", "school", "hospital",
                    "church", "mosque", "market", "bus_station",
                ]
                best = None
                for ptype in priority:
                    for lm in landmarks:
                        if lm.get("type") == ptype:
                            best = lm
                            break
                    if best:
                        break
                zone["name"] = f"{(best or landmarks[0]).get('name', 'Unknown')} Area"
            else:
                zone["name"] = f"Zone {zone['id']}"
        return zones

    def create_zones_in_district(
        self,
        district_boundary: Polygon,
        capital_point: Point,
        target_population_per_zone: int = 5000,
        estimated_population: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Create zones inside a district boundary, starting from the capital city."""
        if district_boundary is None or district_boundary.is_empty:
            raise ValueError("Invalid district boundary")

        n_zones = max(1, estimated_population // target_population_per_zone) if estimated_population else 4

        # Generate seed points inside the district
        # Capital is always zone 1 center
        seed_points = [[capital_point.x, capital_point.y]]

        # Additional points: spread outward from capital within district
        import math
        bounds = district_boundary.bounds
        for i in range(1, n_zones):
            angle = (2 * math.pi * i) / n_zones
            # Spiral outward
            radius_deg = 0.02 * (1 + i * 0.3)
            px = capital_point.x + radius_deg * math.cos(angle)
            py = capital_point.y + radius_deg * math.sin(angle)
            pt = Point(px, py)
            if district_boundary.contains(pt):
                seed_points.append([px, py])
            else:
                # Fallback: random point inside district
                for _ in range(50):
                    rx = bounds[0] + (bounds[2] - bounds[0]) * (i / n_zones)
                    ry = bounds[1] + (bounds[3] - bounds[1]) * ((i * 0.618) % 1)
                    rpt = Point(rx, ry)
                    if district_boundary.contains(rpt):
                        seed_points.append([rx, ry])
                        break

        if len(seed_points) < 2:
            return self._create_grid_zones(district_boundary, n_zones)

        try:
            import numpy as np
            from scipy.spatial import Voronoi
        except ImportError:
            return self._create_grid_zones(district_boundary, n_zones)

        points_arr = np.array(seed_points)
        if len(points_arr) < 4:
            return self._create_grid_zones(district_boundary, n_zones)

        vor = Voronoi(points_arr)
        zones = []
        for i in range(len(points_arr)):
            region_idx = vor.point_region[i]
            vertices = vor.regions[region_idx]
            if -1 in vertices or len(vertices) == 0:
                continue
            poly_points = [vor.vertices[v] for v in vertices]
            try:
                zone_polygon = Polygon(poly_points)
                zone_polygon = zone_polygon.intersection(district_boundary)
                if zone_polygon.is_empty or zone_polygon.area < 1e-12:
                    continue
                zones.append({
                    "id": i + 1,
                    "center": {"lng": float(points_arr[i][0]), "lat": float(points_arr[i][1])},
                    "boundary_geojson": shapely_mapping(zone_polygon) if hasattr(zone_polygon, "__geo_interface__") else None,
                    "area_sq_km": self._calc_area_sq_km(zone_polygon),
                    "landmarks": [],
                    "name": None,
                    "postal_code": None,
                })
            except Exception:
                continue

        if not zones:
            return self._create_grid_zones(district_boundary, n_zones)

        # Ensure capital city is zone 1
        zones_sorted = sorted(zones, key=lambda z: (z["center"]["lat"] - capital_point.y) ** 2 + (z["center"]["lng"] - capital_point.x) ** 2)
        capital_zone = zones_sorted[0]
        capital_zone["name"] = f"{country.name} Capital Central" if 'country' in dir() else "Capital Central"
        capital_zone["id"] = 1
        other_zones = [z for z in zones if z is not capital_zone]
        for idx, z in enumerate(other_zones, start=2):
            z["id"] = idx
        zones = [capital_zone] + other_zones

        zones = self._name_zones(zones)
        return zones

    @staticmethod
    def _geojson_to_polygon(geojson: Dict[str, Any]) -> Optional[Polygon]:
        """Convert GeoJSON to Shapely Polygon."""
        try:
            if geojson.get("type") == "Polygon":
                return Polygon(geojson["coordinates"][0])
            elif geojson.get("type") == "MultiPolygon":
                polys = [Polygon(c[0]) for c in geojson["coordinates"]]
                return MultiPolygon(polys)
            elif geojson.get("type") == "Feature":
                return ZoneCreationEngine._geojson_to_polygon(geojson["geometry"])
        except Exception:
            return None
        return None

    @staticmethod
    def _calc_area_sq_km(polygon) -> float:
        """Calculate area in square kilometers."""
        try:
            from pyproj import Geod
            geod = Geod(ellps="WGS84")
            area, _ = geod.geometry_area_perimeter(polygon)
            return abs(area) / 1_000_000
        except Exception:
            minx, miny, maxx, maxy = polygon.bounds
            dx_km = (maxx - minx) * 111.32 * math.cos(math.radians((miny + maxy) / 2))
            dy_km = (maxy - miny) * 111.32
            return dx_km * dy_km
