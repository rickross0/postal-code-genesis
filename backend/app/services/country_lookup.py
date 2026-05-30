"""Country auto-fill service — fetches real-world data from free APIs."""

import httpx
from typing import Optional, Dict, Any


class CountryLookupService:
    """Look up country metadata from REST Countries API and other free sources."""

    async def lookup_country(self, name: str) -> Optional[Dict[str, Any]]:
        """Fetch country data from restcountries.com (free, no API key)."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                url = f"https://restcountries.com/v3.1/name/{name}?fields=name,cca2,cca3,capital,population,area,latlng,languages,currencies,region"
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        c = data[0]
                        return self._normalize(c)
                # Try alternative: common name search
                url2 = f"https://restcountries.com/v3.1/name/{name}?fullText=true&fields=name,cca2,cca3,capital,population,area,latlng,languages,currencies,region"
                resp2 = await client.get(url2)
                if resp2.status_code == 200:
                    data2 = resp2.json()
                    if isinstance(data2, list) and len(data2) > 0:
                        return self._normalize(data2[0])
        except Exception as e:
            print(f"Country lookup error: {e}")
        return None

    async def lookup_city(self, city_name: str, country_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch city coordinates from OpenStreetMap Nominatim (free, no API key)."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                q = f"{city_name}, {country_code}" if country_code else city_name
                url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1"
                resp = await client.get(url, headers={"User-Agent": "PostalCodeGenesis/1.0"})
                if resp.status_code == 200:
                    data = resp.json()
                    if data and len(data) > 0:
                        return {
                            "name": data[0].get("display_name", city_name),
                            "lat": float(data[0]["lat"]),
                            "lng": float(data[0]["lon"]),
                            "boundingbox": data[0].get("boundingbox"),
                        }
        except Exception as e:
            print(f"City lookup error: {e}")
        return None

    def _normalize(self, c: Dict[str, Any]) -> Dict[str, Any]:
        """Convert REST Countries response to our schema."""
        name_obj = c.get("name", {})
        common = name_obj.get("common", "")
        official = name_obj.get("official", "")

        capitals = c.get("capital", [])
        capital_city = capitals[0] if capitals else None

        latlng = c.get("latlng", [])
        lat = latlng[0] if len(latlng) > 0 else None
        lng = latlng[1] if len(latlng) > 1 else None

        langs_obj = c.get("languages", {})
        languages = list(langs_obj.values()) if langs_obj else []

        return {
            "name": common or official,
            "official_name": official,
            "iso_code": c.get("cca3", ""),
            "iso_code_2": c.get("cca2", ""),
            "capital_city": capital_city,
            "capital_lat": lat,
            "capital_lng": lng,
            "population": c.get("population"),
            "area_sq_km": c.get("area"),
            "region": c.get("region"),
            "languages": languages,
        }
