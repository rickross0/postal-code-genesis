import React, { useState, useEffect, useRef, useCallback } from 'react';
import { listZones } from '../services/api';

const styles = {
  container: { flex: 1, display: 'flex', flexDirection: 'column', height: '100vh' },
  toolbar: {
    padding: '12px 20px', background: '#fff', borderBottom: '1px solid #e8e8f0',
    display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap',
  },
  mapContainer: { flex: 1, position: 'relative', background: '#f0f0f5', overflow: 'auto' },
  infoPanel: {
    position: 'absolute', bottom: '20px', left: '20px', background: 'white',
    borderRadius: '12px', padding: '16px', boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
    maxWidth: '320px', zIndex: 10,
  },
  infoTitle: { fontSize: '16px', fontWeight: 600, marginBottom: '8px' },
  infoRow: { fontSize: '13px', color: '#666', marginBottom: '4px' },
  infoCode: { fontSize: '22px', fontWeight: 700, color: '#6c63ff', marginBottom: '4px' },
  btn: {
    padding: '8px 16px', background: '#6c63ff', color: 'white', border: 'none',
    borderRadius: '8px', fontSize: '13px', fontWeight: 600, cursor: 'pointer',
  },
  emptyState: {
    flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: '#999', fontSize: '16px', textAlign: 'center', padding: '40px',
  },
};

const REGION_COLORS = [
  '#6c63ff', '#ff6b6b', '#51cf66', '#ffd43b', '#339af0',
  '#f06595', '#845ef7', '#20c997', '#ff922b', '#748ffc',
];

export default function ZoneMap({ selectedCountry, googleMapsApiKey }) {
  const [zones, setZones] = useState([]);
  const [selectedZone, setSelectedZone] = useState(null);
  const [loading, setLoading] = useState(false);
  const mapRef = useRef(null);
  const googleMapRef = useRef(null);
  const markersRef = useRef([]);

  const loadZones = useCallback(async () => {
    if (!selectedCountry) return;
    setLoading(true);
    try {
      const res = await listZones(selectedCountry.id);
      setZones(res.data);
    } catch (err) {
      console.error('Error loading zones', err);
    }
    setLoading(false);
  }, [selectedCountry]);

  useEffect(() => { loadZones(); }, [loadZones]);

  // Initialize Google Map if API key provided
  useEffect(() => {
    if (!googleMapsApiKey || !window.google || !mapRef.current || !selectedCountry) return;
    if (googleMapRef.current) return;
    const lat = selectedCountry.name === 'South Sudan' ? 6.877 : 0;
    const lng = selectedCountry.name === 'South Sudan' ? 31.307 : 30;
    googleMapRef.current = new window.google.maps.Map(mapRef.current, {
      center: { lat, lng }, zoom: 6, mapTypeId: 'roadmap',
    });
  }, [selectedCountry, googleMapsApiKey]);

  // Draw zones on Google Map
  useEffect(() => {
    if (!googleMapsApiKey || !googleMapRef.current || !zones.length) return;
    const map = googleMapRef.current;
    markersRef.current.forEach((m) => m.setMap(null));
    markersRef.current = [];
    const bounds = new window.google.maps.LatLngBounds();
    zones.forEach((zone, idx) => {
      const color = REGION_COLORS[idx % REGION_COLORS.length];
      const pos = { lat: zone.center_lat, lng: zone.center_lng };
      bounds.extend(pos);
      const circle = new window.google.maps.Circle({
        strokeColor: color, strokeOpacity: 0.8, strokeWeight: 2,
        fillColor: color, fillOpacity: 0.25, map, center: pos,
        radius: Math.max(2000, (zone.area_sq_km || 10) * 500),
      });
      const marker = new window.google.maps.Marker({
        position: pos, map, title: `${zone.postal_code} — ${zone.name}`,
        icon: { path: window.google.maps.SymbolPath.CIRCLE, scale: 6, fillColor: color, fillOpacity: 1, strokeWeight: 2, strokeColor: '#fff' },
      });
      marker.addListener('click', () => setSelectedZone(zone));
      markersRef.current.push(marker, circle);
    });
    if (!bounds.isEmpty()) map.fitBounds(bounds);
  }, [zones, googleMapsApiKey]);

  if (!selectedCountry) {
    return <div style={styles.emptyState}>📍 Select a country from the sidebar to view zones</div>;
  }

  return (
    <div style={styles.container}>
      <div style={styles.toolbar}>
        <span style={{ fontWeight: 600, fontSize: '14px' }}>📍 {selectedCountry.name} Zones</span>
        <span style={{ fontSize: '13px', color: '#666' }}>{zones.length} zones</span>
        <button style={styles.btn} onClick={loadZones} disabled={loading}>
          {loading ? 'Loading...' : '↻ Refresh'}
        </button>
      </div>
      <div style={styles.mapContainer}>
        {googleMapsApiKey ? (
          <div ref={mapRef} style={{ width: '100%', height: '100%' }} />
        ) : (
          <div style={{ padding: '30px' }}>
            <h3 style={{ marginBottom: '16px' }}>Postal Zones</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
              {zones.map((zone, idx) => {
                const color = REGION_COLORS[idx % REGION_COLORS.length];
                return (
                  <div
                    key={zone.id}
                    onClick={() => setSelectedZone(zone)}
                    style={{
                      padding: '16px', borderRadius: '10px', cursor: 'pointer',
                      background: '#fff',
                      borderLeft: `4px solid ${color}`,
                      boxShadow: selectedZone?.id === zone.id ? '0 2px 12px rgba(108,99,255,0.3)' : '0 1px 4px rgba(0,0,0,0.08)',
                    }}
                  >
                    <div style={{ fontSize: '18px', fontWeight: 700, color }}>{zone.postal_code}</div>
                    <div style={{ fontSize: '13px', color: '#333', marginTop: '4px' }}>{zone.name}</div>
                    {zone.population && <div style={{ fontSize: '12px', color: '#999', marginTop: '2px' }}>Pop: {zone.population.toLocaleString()}</div>}
                  </div>
                );
              })}
            </div>
          </div>
        )}
        {selectedZone && (
          <div style={styles.infoPanel}>
            <div style={styles.infoCode}>{selectedZone.postal_code}</div>
            <div style={styles.infoTitle}>{selectedZone.name}</div>
            <div style={styles.infoRow}>Region: {selectedZone.region_name || '—'}</div>
            <div style={styles.infoRow}>District: {selectedZone.district_name || '—'}</div>
            {selectedZone.population && <div style={styles.infoRow}>Population: {selectedZone.population.toLocaleString()}</div>}
            {selectedZone.area_sq_km && <div style={styles.infoRow}>Area: {selectedZone.area_sq_km.toFixed(1)} km²</div>}
            <div style={styles.infoRow}>Status: {selectedZone.status}</div>
            <button style={{ ...styles.btn, marginTop: '8px', fontSize: '12px', padding: '6px 12px' }} onClick={() => setSelectedZone(null)}>Close</button>
          </div>
        )}
      </div>
    </div>
  );
}
