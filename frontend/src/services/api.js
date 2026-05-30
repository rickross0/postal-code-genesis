import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || '/api/v1';

const api = axios.create({ baseURL: API_BASE });

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

export default api;
