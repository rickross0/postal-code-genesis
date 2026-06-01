import axios from 'axios';
const API_BASE = '/api/v1';
const api = axios.create({ baseURL: API_BASE, timeout: 30000 });

// Countries
export const createCountry = (data) => api.post('/countries', data);
export const listCountries = () => api.get('/countries');
export const analyzeCountry = (id) => api.post(`/countries/${id}/analyze`);
export const getCountryStats = (id) => api.get(`/countries/${id}/stats`);
export const generatePolicy = (id) => api.post(`/countries/${id}/policy`);
export const updateCountryBoundary = (countryId, data) => api.put(`/countries/${countryId}/boundary`, data);

// Zones
export const listZones = (countryId) => api.get(`/countries/${countryId}/zones`);
export const autoCreateZones = (countryId, regionCode, districtCode, targetPop = 5000) =>
  api.post(`/countries/${countryId}/zones/auto-create?region_code=${regionCode}&district_code=${districtCode}&target_population=${targetPop}`);
export const autoCreateAllZones = (countryId, targetPop = 5000) =>
  api.post(`/countries/${countryId}/zones/auto-create-all?target_population=${targetPop}`);
export const createZoneManual = (countryId, data) =>
  api.post(`/countries/${countryId}/zones/create`, data);
export const updateZone = (zoneId, data) => api.put(`/zones/${zoneId}`, data);
export const deleteZone = (zoneId) => api.delete(`/zones/${zoneId}`);

// Districts
export const listDistricts = (countryId) => api.get(`/countries/${countryId}/districts`);
export const createDistrict = (regionId, name, code) =>
  api.post(`/regions/${regionId}/districts?name=${encodeURIComponent(name)}&code=${code}`);
export const updateDistrict = (districtId, data) => api.put(`/districts/${districtId}`, data);
export const deleteDistrict = (districtId) => api.delete(`/districts/${districtId}`);

// Regions
export const listRegions = (countryId) => api.get(`/countries/${countryId}/regions`);
export const createRegion = (countryId, name, code) =>
  api.post(`/countries/${countryId}/regions?name=${encodeURIComponent(name)}&code=${code}`);
export const updateRegion = (regionId, data) => api.put(`/regions/${regionId}`, data);
export const deleteRegion = (regionId) => api.delete(`/regions/${regionId}`);

// Lookup
export const lookupByCoordinates = (lat, lng) => api.get(`/lookup/coordinates?lat=${lat}&lng=${lng}`);
export const lookupByName = (query, country) => api.get(`/lookup/search?query=${encodeURIComponent(query)}&country=${country}`);
export const lookupCountry = (name) => api.get(`/countries/lookup/${encodeURIComponent(name)}`);
export const lookupCity = (query, countryCode) => api.get(`/cities/lookup?query=${encodeURIComponent(query)}${countryCode ? '&country_code=' + countryCode : ''}`);

// USSD
export const ussdLookup = (data) => api.post('/lookup/ussd', data);

export default api;
