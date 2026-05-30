import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Polygon, Marker, useMap, useMapEvent } from 'react-leaflet';
import L from 'leaflet';
import { listZones, updateZone, autoCreateZones } from '../services/api';
import 'leaflet/dist/leaflet.css';

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
    maxWidth: '320px', zIndex: 1000,
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

function getZoneColor(idx) {
  return REGION_COLORS[idx % REGION_COLORS.length];
}

function FitBounds({ zones, countryId }) {
  const map = useMap();
  const lastId = useRef(null);
  useEffect(() => {
    if (zones.length === 0) return;
    if (lastId.current === countryId) return;
    lastId.current = countryId;
    const valid = zones.filter(z => z.center_lat && z.center_lng);
    if (valid.length === 0) return;
    const bounds = L.latLngBounds(valid.map(z => [z.center_lat, z.center_lng]));
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [50, 50] });
  }, [zones, map, countryId]);
  return null;
}

function MapClickHandler({ drawMode, onClick }) {
  useMapEvent('click', (e) => {
    if (drawMode) onClick(e);
  });
  return null;
}

export default function ZoneMap({ selectedCountry }) {
  const [zones, setZones] = useState([]);
  const [selectedZone, setSelectedZone] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [drawMode, setDrawMode] = useState(false);
  const [drawPoints, setDrawPoints] = useState([]);
  const [editZoneId, setEditZoneId] = useState(null);
  const drawModeRef = useRef(false);
  drawModeRef.current = drawMode;

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

  const handleMapClick = useCallback((e) => {
    const { lat, lng } = e.latlng;
    setDrawPoints(prev => [...prev, [lat, lng]]);
  }, []);

  const startEdit = useCallback((zone) => {
    setSelectedZone(zone);
    setEditZoneId(zone.id);
    setDrawMode(true);
    setDrawPoints([]);
    if (zone.boundary_geojson && zone.boundary_geojson.coordinates) {
      const coords = zone.boundary_geojson.coordinates[0];
      const open = coords.slice(0, -1);
      setDrawPoints(open.map(c => [c[1], c[0]]));
    }
  }, []);

  const handleSaveEdit = useCallback(async () => {
    if (!editZoneId || drawPoints.length < 3) {
      alert('Need at least 3 points to form a zone boundary.');
      return;
    }
    const closed = [...drawPoints, drawPoints[0]];
    const geojson = {
      type: 'Polygon',
      coordinates: [closed.map(p => [p[1], p[0]])]
    };
    try {
      await updateZone(editZoneId, { boundary_geojson: geojson });
      await loadZones();
      setDrawMode(false);
      setDrawPoints([]);
      setEditZoneId(null);
    } catch (err) {
      alert('Failed to save boundary: ' + (err.response?.data?.detail || err.message));
    }
  }, [editZoneId, drawPoints, loadZones]);

  const handleCancelEdit = useCallback(() => {
    setDrawMode(false);
    setDrawPoints([]);
    setEditZoneId(null);
  }, []);

  const handleUndoPoint = useCallback(() => {
    setDrawPoints(prev => prev.slice(0, -1));
  }, []);

  const handleGenerateZones = useCallback(async () => {
    if (!selectedCountry) return;
    setGenerating(true);
    try {
      await autoCreateZones(selectedCountry.id, '01', '01', 5000);
      await loadZones();
    } catch (err) {
      alert('Failed to generate zones: ' + (err.response?.data?.detail || err.message));
    }
    setGenerating(false);
  }, [selectedCountry, loadZones]);

  const mapCenter = useMemo(() => {
    if (zones.length === 0) return [4.85, 31.6];
    const avgLat = zones.reduce((s, z) => s + (z.center_lat || 0), 0) / zones.length;
    const avgLng = zones.reduce((s, z) => s + (z.center_lng || 0), 0) / zones.length;
    return [avgLat, avgLng];
  }, [zones]);

  if (!selectedCountry) {
    return <div style={styles.emptyState}>Select a country from the sidebar to view zones</div>;
  }

  return (
    <div style={styles.container}>
      <div style={styles.toolbar}>
        <span style={{ fontWeight: 600, fontSize: '14px' }}>{selectedCountry.name} Zones</span>
        <span style={{ fontSize: '13px', color: '#666' }}>{zones.length} zones</span>
        {!drawMode && (
          <button style={styles.btn} onClick={loadZones} disabled={loading}>
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        )}
        {drawMode && (
          <>
            <span style={{ fontSize: '13px', color: '#666' }}>{drawPoints.length} points — click map to add</span>
            <button style={{...styles.btn, background: '#ff6b6b'}} onClick={handleUndoPoint} disabled={drawPoints.length === 0}>Undo</button>
            <button style={styles.btn} onClick={handleSaveEdit} disabled={drawPoints.length < 3}>Save Boundary</button>
            <button style={{...styles.btn, background: '#999'}} onClick={handleCancelEdit}>Cancel</button>
          </>
        )}
      </div>

      <div style={styles.mapContainer}>
        {zones.length === 0 && !drawMode ? (
          <div style={{ textAlign: 'center', padding: '40px 20px' }}>
            <div style={{ fontSize: '16px', fontWeight: 600, color: '#1a1a2e', marginBottom: '12px' }}>
              No postal zones yet
            </div>
            <div style={{ fontSize: '14px', color: '#666', marginBottom: '20px', maxWidth: '400px', margin: '0 auto 20px' }}>
              {selectedCountry.name} has a profile but no zones have been generated.
            </div>
            <button style={{ padding: '12px 28px', background: '#6c63ff', color: 'white', border: 'none', borderRadius: '8px', fontSize: '14px', fontWeight: 600, cursor: 'pointer' }} onClick={handleGenerateZones} disabled={generating}>
              {generating ? 'Generating zones…' : 'Generate Postal Zones'}
            </button>
          </div>
        ) : (
          <MapContainer center={mapCenter} zoom={6} style={{ height: '100%', width: '100%' }}>
            <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <FitBounds zones={zones} countryId={selectedCountry.id} />
            <MapClickHandler drawMode={drawMode} onClick={handleMapClick} />

            {zones.map((zone, idx) => {
              const color = getZoneColor(idx);
              const isSelected = selectedZone?.id === zone.id;
              if (zone.boundary_geojson) {
                return (
                  <GeoJSON
                    key={zone.id}
                    data={zone.boundary_geojson}
                    style={{
                      color: isSelected ? '#ff6b6b' : color,
                      weight: isSelected ? 3 : 2,
                      fillColor: color,
                      fillOpacity: isSelected ? 0.35 : 0.15,
                    }}
                    eventHandlers={{
                      click: () => { if (!drawModeRef.current) setSelectedZone(zone); }
                    }}
                  />
                );
              } else {
                return (
                  <CircleMarker
                    key={zone.id}
                    center={[zone.center_lat || 0, zone.center_lng || 0]}
                    radius={12}
                    pathOptions={{
                      color: isSelected ? '#ff6b6b' : color,
                      fillColor: color,
                      fillOpacity: 0.3,
                      weight: isSelected ? 3 : 2,
                    }}
                    eventHandlers={{
                      click: () => { if (!drawModeRef.current) setSelectedZone(zone); }
                    }}
                  />
                );
              }
            })}

            {zones.map((zone, idx) => {
              const color = getZoneColor(idx);
              return (
                <Marker
                  key={`label-${zone.id}`}
                  position={[zone.center_lat || 0, zone.center_lng || 0]}
                  icon={L.divIcon({
                    className: '',
                    html: `<div style="background:rgba(255,255,255,0.9);padding:2px 5px;border-radius:4px;font-size:10px;font-weight:700;color:${color};border:1px solid ${color};white-space:nowrap;pointer-events:none;">${zone.postal_code}</div>`,
                    iconSize: [80, 20],
                    iconAnchor: [40, 10],
                  })}
                  interactive={false}
                />
              );
            })}

            {drawMode && drawPoints.length > 0 && (
              <>
                <Polygon
                  positions={drawPoints}
                  pathOptions={{ color: '#ff6b6b', dashArray: '5, 10', fillColor: '#ff6b6b', fillOpacity: 0.1, weight: 2 }}
                />
                {drawPoints.map((p, i) => (
                  <CircleMarker key={`draw-${i}`} center={p} radius={5} pathOptions={{ color: '#ff6b6b', fillColor: '#ff6b6b', fillOpacity: 1, weight: 1 }} />
                ))}
              </>
            )}
          </MapContainer>
        )}
      </div>

      {selectedZone && !drawMode && (
        <div style={styles.infoPanel}>
          <div style={styles.infoCode}>{selectedZone.postal_code}</div>
          <div style={styles.infoTitle}>{selectedZone.name}</div>
          <div style={styles.infoRow}>Region: {selectedZone.region_name || '-'}</div>
          <div style={styles.infoRow}>District: {selectedZone.district_name || '-'}</div>
          {selectedZone.population && <div style={styles.infoRow}>Population: {selectedZone.population.toLocaleString()}</div>}
          {selectedZone.area_sq_km && <div style={styles.infoRow}>Area: {selectedZone.area_sq_km.toFixed(1)} km2</div>}
          <div style={styles.infoRow}>Status: {selectedZone.status}</div>
          <div style={{ marginTop: '10px', display: 'flex', gap: '8px' }}>
            <button style={{ ...styles.btn, fontSize: '12px', padding: '6px 12px' }} onClick={() => startEdit(selectedZone)}>Edit Boundary</button>
            <button style={{ ...styles.btn, fontSize: '12px', padding: '6px 12px', background: '#999' }} onClick={() => setSelectedZone(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
