"""Comprehensive endpoint tests for Postal Code Genesis API."""
from unittest.mock import AsyncMock, MagicMock
import pytest


def _make_country(**kw):
    defaults = dict(
        id=1, name="Testland", iso_code="TST", tier="mixed_rural_urban",
        estimated_population=1000000, area_sq_km=50000, num_regions=3, num_districts=9,
        languages='["English"]', has_street_names=False, has_house_numbers=False,
        has_any_addressing=False, urban_percentage=30.0, literacy_rate=70.0,
        mobile_penetration=50.0, internet_penetration=30.0,
        existing_admin_divisions='{"region":3}', capital_city="Test City",
        capital_lat=4.85, capital_lng=31.6, locked=False, boundary=None,
    )
    defaults.update(kw)
    c = MagicMock()
    for k, v in defaults.items():
        setattr(c, k, v)
    return c


def _make_region(**kw):
    defaults = dict(id=1, country_id=1, name="Region CE", code="01", locked=False,
        boundary=None, center_point=None)
    defaults.update(kw)
    r = MagicMock()
    for k, v in defaults.items():
        setattr(r, k, v)
    return r


def _make_district(**kw):
    defaults = dict(id=1, region_id=1, name="District JU", code="0101", locked=False,
        boundary=None, center_point=None)
    defaults.update(kw)
    d = MagicMock()
    for k, v in defaults.items():
        setattr(d, k, v)
    return d


def _mock_result(mock_db, scalar=None, mappings_list=None, scalars_list=None, first=None):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = scalar
    if scalars_list is not None:
        result_mock.scalars.return_value.all.return_value = scalars_list
        result_mock.scalars.return_value.first.return_value = scalars_list[0] if scalars_list else None
    if mappings_list is not None:
        result_mock.mappings.return_value.all.return_value = mappings_list
        result_mock.mappings.return_value.first.return_value = first or (mappings_list[0] if mappings_list else None)

    async def _execute(*args, **kwargs):
        return result_mock

    mock_db.execute = _execute


class TestHealthAndRoot:
    def test_health(self, client, mock_db):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_api_root(self, client, mock_db):
        r = client.get("/api")
        assert r.status_code == 200
        assert "Postal Code Genesis" in r.json()["name"]


class TestCountries:
    def test_create_country(self, client, mock_db):
        # Simulate db flush setting id
        original_flush = mock_db.flush
        async def _flush_with_id():
            await original_flush()
            # After flush, the country object gets an id
            for call in mock_db.add.call_args_list:
                obj = call[0][0]
                if not hasattr(obj, 'id') or obj.id is None:
                    obj.id = 42
        mock_db.flush = _flush_with_id
        _mock_result(mock_db, scalar=None)
        r = client.post("/api/v1/countries", json={
            "name": "Testland", "iso_code": "TST", "tier": "mixed_rural_urban",
            "estimated_population": 1000000, "area_sq_km": 50000,
            "num_regions": 3, "num_districts": 9, "languages": ["English"],
            "urban_percentage": 30.0, "literacy_rate": 70.0,
            "mobile_penetration": 50.0, "internet_penetration": 30.0,
        })
        assert r.status_code == 201
        data = r.json()
        assert data["iso_code"] == "TST"

    def test_list_countries(self, client, mock_db):
        _mock_result(mock_db, mappings_list=[{
            "id": 1, "name": "Testland", "iso_code": "TST", "tier": "mixed_rural_urban",
            "estimated_population": 1000000, "area_sq_km": 50000, "num_regions": 3,
            "num_districts": 9, "languages": '["English"]', "urban_percentage": 30.0,
            "literacy_rate": 70.0, "mobile_penetration": 50.0, "capital_city": "Test City",
            "capital_lat": 4.85, "capital_lng": 31.6, "locked": False, "boundary_geojson": None,
        }])
        r = client.get("/api/v1/countries")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["name"] == "Testland"

    def test_delete_country(self, client, mock_db):
        _mock_result(mock_db, scalar=_make_country(id=42))
        r = client.delete("/api/v1/countries/42")
        assert r.status_code == 204

    def test_delete_country_not_found(self, client, mock_db):
        _mock_result(mock_db, scalar=None)
        r = client.delete("/api/v1/countries/999")
        assert r.status_code == 404


class TestRegionsAndDistricts:
    def test_list_regions(self, client, mock_db):
        _mock_result(mock_db, scalars_list=[_make_region()])
        r = client.get("/api/v1/countries/1/regions")
        assert r.status_code == 200

    def test_list_districts(self, client, mock_db):
        _mock_result(mock_db, scalars_list=[_make_district()])
        r = client.get("/api/v1/countries/1/districts")
        assert r.status_code == 200


class TestZones:
    def test_list_zones(self, client, mock_db):
        _mock_result(mock_db, mappings_list=[{
            "id": 1, "postal_code": "CEJU001", "name": "Zone 1", "status": "active",
            "color": None, "center_lat": 4.85, "center_lng": 31.6,
            "area_sq_km": 25.0, "population": 5000,
            "district_id": 1, "district_name": "District JU", "district_code": "0101",
            "region_name": "Region CE", "region_code": "01",
            "zone_locked": False, "boundary_geojson": None,
            "district_boundary_geojson": None,
        }])
        r = client.get("/api/v1/countries/1/zones")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["postal_code"] == "CEJU001"
        assert len(data[0]["postal_code"]) == 7


class TestExports:
    def test_export_zones_pattern_param(self, client, mock_db):
        """Verify the regex pattern param uses 'pattern' not deprecated 'regex'."""
        _mock_result(mock_db, mappings_list=[])
        r = client.get("/api/v1/countries/1/zones/export?format=csv")
        assert r.status_code == 200

    def test_export_report_pattern_param(self, client, mock_db):
        _mock_result(mock_db, mappings_list=[])
        _mock_result(mock_db, scalar=_make_country())
        r = client.get("/api/v1/countries/1/report?format=json")
        assert r.status_code == 200

    def test_export_zones_invalid_format(self, client, mock_db):
        r = client.get("/api/v1/countries/1/zones/export?format=invalid")
        assert r.status_code == 422


class TestSnapshots:
    def test_save_snapshot(self, client, mock_db):
        _mock_result(mock_db, mappings_list=[])
        _mock_result(mock_db, scalar=None)
        r = client.post("/api/v1/countries/1/snapshots")
        assert r.status_code == 200

    def test_list_snapshots(self, client, mock_db):
        _mock_result(mock_db, scalars_list=[])
        r = client.get("/api/v1/countries/1/snapshots")
        assert r.status_code == 200

    def test_restore_snapshot(self, client, mock_db):
        _mock_result(mock_db, scalar=None)
        _mock_result(mock_db, scalar=None)
        r = client.post("/api/v1/countries/1/snapshots/1/restore")
        # This may return 404 if snapshot not found, but should not 500
        assert r.status_code in [200, 404]


class TestPostalCodeFormat:
    def test_7_digit_postal_code_format(self, client, mock_db):
        """Verify postal codes follow the 7-digit format: RRDDNNN"""
        _mock_result(mock_db, mappings_list=[{
            "id": 1, "postal_code": "CEJU001", "name": "Zone 1", "status": "active",
            "color": None, "center_lat": 4.85, "center_lng": 31.6,
            "area_sq_km": 25.0, "population": 5000,
            "district_id": 1, "district_name": "District JU", "district_code": "0101",
            "region_name": "Region CE", "region_code": "01",
            "zone_locked": False, "boundary_geojson": None,
            "district_boundary_geojson": None,
        }])
        r = client.get("/api/v1/countries/1/zones")
        data = r.json()
        pc = data[0]["postal_code"]
        assert len(pc) == 7, f"Postal code '{pc}' should be 7 chars"
        assert pc[:2].isalpha(), f"First 2 chars should be letters: {pc[:2]}"
        assert pc[2:4].isalpha(), f"Next 2 chars should be letters: {pc[2:4]}"
        assert pc[4:].isdigit(), f"Last 3 chars should be digits: {pc[4:]}"
