"""Tests for country deletion endpoint."""
from unittest.mock import AsyncMock, MagicMock


def _make_mock_country(**kwargs):
    """Create a mock Country ORM object."""
    defaults = dict(
        id=1,
        name="Testland",
        iso_code="TST",
        tier="mixed_rural_urban",
        estimated_population=1000000,
        area_sq_km=50000,
        num_regions=5,
        num_districts=20,
        languages='["English"]',
        has_street_names=True,
        has_house_numbers=True,
        has_any_addressing=True,
        urban_percentage=45.0,
        literacy_rate=85.0,
        mobile_penetration=70.0,
        internet_penetration=60.0,
        existing_admin_divisions='{"region": 5}',
        capital_city="Test City",
        capital_lat=12.34,
        capital_lng=56.78,
        locked=False,
        boundary=None,
    )
    defaults.update(kwargs)
    country = MagicMock()
    for k, v in defaults.items():
        setattr(country, k, v)
    return country


def _mock_result(mock_db, scalar=None, mappings_list=None, scalars_list=None):
    """Helper to wire up mock_db.execute to return a configurable result."""
    result_mock = MagicMock()
    # Always set scalar_one_or_none so None is returned when requested
    result_mock.scalar_one_or_none.return_value = scalar
    if scalars_list is not None:
        result_mock.scalars.return_value.all.return_value = scalars_list
    if mappings_list is not None:
        result_mock.mappings.return_value.all.return_value = mappings_list
        result_mock.mappings.return_value.first.return_value = mappings_list[0] if mappings_list else None

    async def _execute(*args, **kwargs):
        return result_mock

    mock_db.execute = _execute


class TestDeleteCountry:
    def test_delete_country_success(self, client, mock_db):
        country = _make_mock_country(id=42)
        _mock_result(mock_db, scalar=country)

        response = client.delete("/api/v1/countries/42")
        assert response.status_code == 204
        mock_db.delete.assert_awaited_once_with(country)
        mock_db.flush.assert_awaited_once()

    def test_delete_country_not_found(self, client, mock_db):
        _mock_result(mock_db, scalar=None)

        response = client.delete("/api/v1/countries/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Country not found"


class TestListCountries:
    def test_list_countries_empty(self, client, mock_db):
        _mock_result(mock_db, mappings_list=[])

        response = client.get("/api/v1/countries")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_countries_returns_data(self, client, mock_db):
        row = {
            "id": 1,
            "name": "Testland",
            "iso_code": "TST",
            "tier": "mixed_rural_urban",
            "estimated_population": 1000000,
            "area_sq_km": 50000,
            "num_regions": 5,
            "num_districts": 20,
            "languages": '["English"]',
            "urban_percentage": 45.0,
            "literacy_rate": 85.0,
            "mobile_penetration": 70.0,
            "capital_city": "Test City",
            "capital_lat": 12.34,
            "capital_lng": 56.78,
            "locked": False,
            "boundary_geojson": None,
        }
        _mock_result(mock_db, mappings_list=[row])

        response = client.get("/api/v1/countries")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Testland"
        assert data[0]["iso_code"] == "TST"
