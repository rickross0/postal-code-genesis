import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Polygon, Marker, useMap } from 'react-leaflet';
import L from 'leaflet';
import { listZones, updateZone, autoCreateZones, listDistricts } from '../services/api';
import 'leaflet/dist/leaflet.css';

const styles = {
  container: { flex: 1, display: 'flex', flexDirection: 'column', height: '100vh' },
  toolbar: {
    padding: '10px 16px', background: '#fff', borderBottom: '1px solid #e8e8f0',
    display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap',
  },
  mapContainer: { flex: 1, position: 'relative', background: '#f0f0f5', overflow: 'hidden' },
  infoPanel: {
    position: 'absolute', bottom: '20px', right: '20px', background: 'white',
    borderRadius: '12px', padding: '16px', boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
    maxWidth: '300px', zIndex: 1000, fontSize: '13px',
  },
  legendPanel: {
    position: 'absolute', top: '20px', left: '20px', background: 'white',
    borderRadius: '10px', padding: '12px', boxShadow: '0 2px 12px rgba(0,0,0,0.12)',
    maxWidth: '220px', zIndex: 1000, fontSize: '12px', maxHeight: '50vh', overflowY: 'auto',
  },
  btn: {
    padding: '6px 14px', background: '#6c63ff', color: 'white', border: 'none',
    borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer',
  },
  btnSecondary: {
    padding: '6px 14px', background: '#f0f0f5', color: '#333', border: '1px solid #ddd',
    borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer',
  },
  btnDanger: {
    padding: '6px 14px', background: '#ff6b6b', color: 'white', border: 'none',
    borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer',
  },
  emptyState: {
    flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: '#999', fontSize: '16px', textAlign: 'center', padding: '40px',
  },
};

// 10 distinct district colors (each district gets one hue; zones get variations)
const DISTRICT_COLORS = [
  '#6c63ff', '#ff6b6b', '#51cf66', '#ffd43b', '#339af0',
  '#f06595', '#845ef7', '#20c997', '#ff922b', '#748ffc',
];

function getDistrictColor(districtIndex, zoneIndex) {
  const base = DISTRICT_COLORS[districtIndex % DISTRICT_COLORS.length];
  // For zones within same district, we can vary opacity via fillOpacity in GeoJSON
  return base;
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
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [60, 60] });
  }, [zones, map, countryId]);
  return null;
}

export default function ZoneMap({ selectedCountry }) {
  const [zones, setZones] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [selectedZone, setSelectedZone] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [drawMode, setDrawMode] = useState(false);
  const [drawPoints, setDrawPoints] = useState([]);
  const [editZoneId, setEditZoneId] = useState(null);
  const [showDistricts, setShowDistricts] = useState(true);

  const loadData = useCallback(async () => {
    if (!selectedCountry) return;
    setLoading(true);
    try {
      // Load zones
      const zRes = await listZones(selectedCountry.id);
      setZones(zRes.data);
      // Load districts with boundaries
      const dRes = await listDistricts(selectedCountry.id);
      setDistricts(dRes.data);
    } catch (err) {
      console.error('Error loading map data', err);
    }
    setLoading(false);
  }, [selectedCountry]);

  useEffect(() => { loadData(); }, [loadData]);

  // Group zones by district for coloring
  const districtMap = useMemo(() => {
    const map = new Map();
    zones.forEach(z => {
      const dName = z.district_name || 'Unknown';
      if (!map.has(dName)) map.set(dName, []);
      map.get(dName).push(z);
    });
    return map;
  }, [zones]);

  const districtNames = useMemo(() => Array.from(districtMap.keys()), [districtMap]);

  const handleExport = useCallback(async (format) => {
    if (!selectedCountry) return;
    const url = `/api/v1/countries/${selectedCountry.id}/zones/export?format=${format}`;
    window.open(url, '_blank');
  }, [selectedCountry]);

  const handleReport = useCallback(async () => {
    if (!selectedCountry) return;
    const url = `/api/v1/countries/${selectedCountry.id}/report?format=pdf`;
    window.open(url, '_blank');
  }, [selectedCountry]);

  const handleGenerateZones = useCallback(async () => {
    if (!selectedCountry) return;
    setGenerating(true);
    try {
      await autoCreateZones(selectedCountry.id, '01', '01', 5000);
      await loadData();
    } catch (err) {
      alert('Failed to generate zones: ' + (err.response?.data?.detail || err.message));
    }
    setGenerating(false);
  }, [selectedCountry, loadData]);

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
      await loadData();
      setDrawMode(false);
      setDrawPoints([]);
      setEditZoneId(null);
    } catch (err) {
      alert('Failed to save boundary: ' + (err.response?.data?.detail || err.message));
    }
  }, [editZoneId, drawPoints, loadData]);

  const handleCancelEdit = useCallback(() => {
    setDrawMode(false);
    setDrawPoints([]);
    setEditZoneId(null);
  }, []);

  const handleUndoPoint = useCallback(() => {
    setDrawPoints(prev => prev.slice(0, -1));
  }, []);

  const mapCenter = useMemo(() => {
    if (selectedCountry?.capital_lat && selectedCountry?.capital_lng) {
      return [selectedCountry.capital_lat, selectedCountry.capital_lng];
    }
    if (zones.length === 0) return [4.85, 31.6];
    const valid = zones.filter(z => z.center_lat && z.center_lng);
    if (valid.length === 0) return [4.85, 31.6];
    const avgLat = valid.reduce((s, z) => s + z.center_lat, 0) / valid.length;
    const avgLng = valid.reduce((s, z) => s + z.center_lng, 0) / valid.length;
    return [avgLat, avgLng];
  }, [zones, selectedCountry]);

  if (!selectedCountry) {
    return <div style={styles.emptyState}>Select a country from the sidebar to view zones</div>;
  }

  return (
    <div style={styles.container}>
      <div style={styles.toolbar}>
        <span style={{ fontWeight: 600, fontSize: '14px' }}>{selectedCountry.name}</span>
        <span style={{ fontSize: '12px', color: '#666' }}>{zones.length} zones · {districtNames.length} districts</span>
        {!drawMode && (
          <>
            <button style={styles.btnSecondary} onClick={loadData} disabled={loading}>
              {loading ? 'Loading…' : 'Refresh'}
            </button>
            <button style={styles.btnSecondary} onClick={() => setShowDistricts(v => !v)}>
              {showDistricts ? 'Hide Districts' : 'Show Districts'}
            </button>
          </>
        )}
        {drawMode && (
          <>
            <span style={{ fontSize: '12px', color: '#666' }}>{drawPoints.length} pts</span>
            <button style={styles.btnSecondary} onClick={handleUndoPoint} disabled={drawPoints.length === 0}>Undo</button>
            <button style={styles.btn} onClick={handleSaveEdit} disabled={drawPoints.length < 3}>Save</button>
            <button style={styles.btnDanger} onClick={handleCancelEdit}>Cancel</button>
          </>
        )}
        <div style={{ flex: 1 }} />
        <button style={styles.btnSecondary} onClick={() => handleExport('csv')}>Export CSV</button>
        <button style={styles.btnSecondary} onClick={() => handleExport('xlsx')}>Export Excel</button>
        <button style={styles.btnSecondary} onClick={handleReport}>Export PDF</button>
      </div>

      <div style={styles.mapContainer}>
        {zones.length === 0 && !drawMode ? (
          <div style={{ textAlign: 'center', padding: '40px 20px' }}>
            <div style={{ fontSize: '16px', fontWeight: 600, color: '#1a1a2e', marginBottom: '12px' }}>
              No postal zones yet
            </div>
            <div style={{ fontSize: '14px', color: '#666', marginBottom: '20px' }}>
              {selectedCountry.name} has a profile but no zones have been generated.
            </div>
            <button style={{ padding: '12px 28px', background: '#6c63ff', color: 'white', border: 'none', borderRadius: '8px', fontSize: '14px', fontWeight: 600, cursor: 'pointer' }} onClick={handleGenerateZones} disabled={generating}>
              {generating ? 'Generating zones…' : 'Generate Postal Zones'}
            </button>
          </div>
        ) : (
          <MapContainer center={mapCenter} zoom={7} style={{ height: '100%', width: '100%' }}>
            <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <FitBounds zones={zones} countryId={selectedCountry.id} />

            {/* District Boundaries */}
            {showDistricts && districts.map((d, idx) => (
              d.boundary_geojson ? (
                <GeoJSON
                  key={`district-${d.id}`}
                  data={d.boundary_geojson}
                  style={{
                    color: DISTRICT_COLORS[idx % DISTRICT_COLORS.length],
                    weight: 3,
                    fillOpacity: 0.05,
                    dashArray: '6, 6',
                  }}
                />
              ) : null
            ))}

            {/* Zone Polygons — colored by district */}
            {zones.map((zone) => {
              const dIdx = districtNames.indexOf(zone.district_name || 'Unknown');
              const color = getDistrictColor(dIdx, 0);
              const isSelected = selectedZone?.id === zone.id;
              if (zone.boundary_geojson) {
                return (
                  <GeoJSON
                    key={zone.id}
                    data={zone.boundary_geojson}
                    style={{
                      color: color,
                      weight: isSelected ? 3 : 1.5,
                      fillColor: color,
                      fillOpacity: isSelected ? 0.5 : 0.25,
                    }}
                    eventHandlers={{
                      click: () => { if (!drawMode) setSelectedZone(zone); }
                    }}
                  />
                );
              } else {
                return (
                  <CircleMarker
                    key={zone.id}
                    center={[zone.center_lat || 0, zone.center_lng || 0]}
                    radius={10}
                    pathOptions={{
                      color: isSelected ? '#ff6b6b' : color,
                      fillColor: color,
                      fillOpacity: isSelected ? 0.6 : 0.3,
                      weight: isSelected ? 3 : 2,
                    }}
                    eventHandlers={{
                      click: () => { if (!drawMode) setSelectedZone(zone); }
                    }}
                  />
                );
              }
            })}

            {/* Zone Labels */}
            {zones.map((zone) => {
              const dIdx = districtNames.indexOf(zone.district_name || 'Unknown');
              const color = getDistrictColor(dIdx, 0);
              return (
                <Marker
                  key={`label-${zone.id}`}
                  position={[zone.center_lat || 0, zone.center_lng || 0]}
                  icon={L.divIcon({
                    className: '',
                    html: `<div style="background:rgba(255,255,255,0.95);padding:2px 5px;border-radius:4px;font-size:10px;font-weight:700;color:${color};border:1px solid ${color};white-space:nowrap;pointer-events:none;box-shadow:0 1px 3px rgba(0,0,0,0.15);"">${zone.postal_code}</div>`,
                    iconSize: [80, 20],
                    iconAnchor: [40, 10],
                  })}
                  interactive={false}
                />
              );
            })}

            {/* Draw mode overlay */}
            {drawMode && (
              <MapEventHandler onClick={handleMapClick} />
            )}
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

        {/* Legend */}
        {zones.length > 0 && (
          <div style={styles.legendPanel}>
            <div style={{ fontWeight: 600, marginBottom: '8px', fontSize: '13px', color: '#1a1a2e' }}>Districts</div>
            {districtNames.map((name, idx) => (
              <div key={name} style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: DISTRICT_COLORS[idx % DISTRICT_COLORS.length], border: '1px solid rgba(0,0,0,0.1)' }} />
                <span style={{ color: '#444' }}>{name}</span>
              </div>
            ))}
          </div>
        )}

        {/* Zone Info Panel */}
        {selectedZone && !drawMode && (
          <div style={styles.infoPanel}>
            <div style={{ fontSize: '20px', fontWeight: 700, color: '#6c63ff', marginBottom: '4px' }}>{selectedZone.postal_code}</div>
            <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '6px' }}>{selectedZone.name}</div>
            <div style={styles.infoRow}>Region: {selectedZone.region_name || '-'}</div>
            <div style={styles.infoRow}>District: {selectedZone.district_name || '-'}</div>
            {selectedZone.population && <div style={styles.infoRow}>Population: {selectedZone.population.toLocaleString()}</div>}
            {selectedZone.area_sq_km && <div style={styles.infoRow}>Area: {selectedZone.area_sq_km.toFixed(1)} km²</div>}
            <div style={styles.infoRow}>Status: {selectedZone.status}</div>
            <div style={{ marginTop: '10px', display: 'flex', gap: '6px' }}>
              <button style={styles.btn} onClick={() => startEdit(selectedZone)}>Edit Boundary</button>
              <button style={styles.btnSecondary} onClick={() => setSelectedZone(null)}>Close</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function MapEventHandler({ onClick }) {
  const map = useMap();
  useEffect(() => {
    map.on('click', onClick);
    return () => { map.off('click', onClick); };
  }, [map, onClick]);
  return null;
}
