import axios from 'axios';

// When served from the same origin (production), use relative URLs.
// In development with CRA dev server, proxy in package.json handles it.
const API_BASE = '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

// Countries
export const createCountry = (data) => api.post('/countries', data);
export const listCountries = () => api.get('/countries');
export const analyzeCountry = (id) => api.post(`/countries/${id}/analyze`);
export const getCountryStats = (id) => api.get(`/countries/${id}/stats`);
export const generatePolicy = (id) => api.post(`/countries/${id}/policy`);

// Zones
export const listZones = (countryId) => api.get(`/countries/${countryId}/zones`);
export const autoCreateZones = (countryId, regionCode, districtCode, targetPop = 5000) =>
  api.post(`/countries/${countryId}/zones/auto-create?region_code=${regionCode}&district_code=${districtCode}&target_population=${targetPop}`);

// Lookup
export const lookupByCoordinates = (lat, lng) => api.get(`/lookup/coordinates?lat=${lat}&lng=${lng}`);
export const lookupByName = (query, country) => api.get(`/lookup/search?query=${encodeURIComponent(query)}&country=${country}`);

// USSD
export const ussdLookup = (data) => api.post('/lookup/ussd', data);

export const listDistricts = (countryId) => api.get(`/countries/${countryId}/districts`);
export const updateZone = (zoneId, data) => api.put(`/zones/${zoneId}`, data);

export default api;
