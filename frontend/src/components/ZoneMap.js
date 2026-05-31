import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Polygon, Marker, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet-draw/dist/leaflet.draw.css';
import { listZones, updateZone, autoCreateZones, autoCreateAllZones, listDistricts } from '../services/api';

// Leaflet Draw integration
let leafletDrawInitialized = false;
function initLeafletDraw() {
  if (leafletDrawInitialized) return;
  try {
    require('leaflet-draw');
    leafletDrawInitialized = true;
  } catch (e) {
    console.warn('leaflet-draw not available');
  }
}

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
    maxWidth: '320px', zIndex: 1000, fontSize: '13px',
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
  btnSuccess: {
    padding: '6px 14px', background: '#51cf66', color: 'white', border: 'none',
    borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer',
  },
  emptyState: {
    flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: '#999', fontSize: '16px', textAlign: 'center', padding: '40px',
  },
  infoRow: { display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #f0f0f5' },
};

const DISTRICT_COLORS = [
  '#6c63ff', '#ff6b6b', '#51cf66', '#ffd43b', '#339af0',
  '#f06595', '#845ef7', '#20c997', '#ff922b', '#748ffc',
];

function getDistrictColor(idx) {
  return DISTRICT_COLORS[idx % DISTRICT_COLORS.length];
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

// Component that adds Leaflet Draw controls to the map
function DrawControl({ onCreated, onEdited, editLayer }) {
  const map = useMap();
  const drawRef = useRef(null);

  useEffect(() => {
    initLeafletDraw();
    if (!window.L || !window.L.Control || !window.L.Control.Draw) return;

    // Remove existing draw control if any
    if (drawRef.current) {
      map.removeControl(drawRef.current);
    }

    const drawnItems = new L.FeatureGroup();
    map.addLayer(drawnItems);

    const drawControl = new L.Control.Draw({
      position: 'topright',
      draw: {
        polygon: { shapeOptions: { color: '#ff6b6b', weight: 3, fillOpacity: 0.15 } },
        polyline: false,
        circle: false,
        circlemarker: false,
        rectangle: false,
        marker: false,
      },
      edit: {
        featureGroup: drawnItems,
      },
    });

    map.addControl(drawControl);
    drawRef.current = drawControl;

    map.on(L.Draw.Event.CREATED, (e) => {
      const layer = e.layer;
      drawnItems.addLayer(layer);
      const geojson = layer.toGeoJSON();
      if (onCreated) onCreated(geojson.geometry);
    });

    map.on(L.Draw.Event.EDITED, (e) => {
      e.layers.eachLayer((layer) => {
        const geojson = layer.toGeoJSON();
        if (onEdited) onEdited(geojson.geometry);
      });
    });

    return () => {
      try { map.removeControl(drawControl); } catch (_) {}
      map.off(L.Draw.Event.CREATED);
      map.off(L.Draw.Event.EDITED);
    };
  }, [map]);

  // When editing a zone, add its existing boundary to the drawn items
  useEffect(() => {
    // This would need drawnItems ref to be accessible
    // For simplicity we handle boundary editing via the click-draw approach
  }, [editLayer]);

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
  const [editingZoneId, setEditingZoneId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [showDistricts, setShowDistricts] = useState(true);

  const loadData = useCallback(async () => {
    if (!selectedCountry) return;
    setLoading(true);
    try {
      const [zRes, dRes] = await Promise.all([
        listZones(selectedCountry.id),
        listDistricts(selectedCountry.id),
      ]);
      setZones(zRes.data);
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

  const handleGenerateAll = useCallback(async () => {
    if (!selectedCountry) return;
    if (!window.confirm('Generate zones for ALL districts? This will replace existing zones.')) return;
    setGenerating(true);
    try {
      await autoCreateAllZones(selectedCountry.id, 5000);
      await loadData();
    } catch (err) {
      alert('Failed to generate zones: ' + (err.response?.data?.detail || err.message));
    }
    setGenerating(false);
  }, [selectedCountry, loadData]);

  const handleGenerateSingle = useCallback(async () => {
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

  const startEdit = useCallback((zone) => {
    setSelectedZone(zone);
    setEditingZoneId(zone.id);
    setDrawMode(true);
    setDrawPoints([]);
    if (zone.boundary_geojson && zone.boundary_geojson.coordinates) {
      const coords = zone.boundary_geojson.coordinates[0];
      const open = coords.slice(0, -1);
      setDrawPoints(open.map(c => [c[1], c[0]]));
    }
  }, []);

  const cancelEdit = useCallback(() => {
    setDrawMode(false);
    setDrawPoints([]);
    setEditingZoneId(null);
  }, []);

  const handleMapClick = useCallback((e) => {
    if (!drawMode) return;
    const { lat, lng } = e.latlng;
    setDrawPoints(prev => [...prev, [lat, lng]]);
  }, [drawMode]);

  const saveBoundary = useCallback(async () => {
    if (!editingZoneId || drawPoints.length < 3) {
      alert('Need at least 3 points to form a zone boundary.');
      return;
    }
    setSaving(true);
    try {
      // Close the polygon
      const closedPoints = [...drawPoints, drawPoints[0]];
      const coordinates = [closedPoints.map(p => [p[1], p[0]])];
      const geojson = { type: 'Polygon', coordinates };
      await updateZone(editingZoneId, { boundary_geojson: geojson });
      setDrawMode(false);
      setDrawPoints([]);
      setEditingZoneId(null);
      await loadData();
    } catch (err) {
      alert('Failed to save boundary: ' + (err.response?.data?.detail || err.message));
    }
    setSaving(false);
  }, [editingZoneId, drawPoints, loadData]);

  const undoLastPoint = useCallback(() => {
    setDrawPoints(prev => prev.slice(0, -1));
  }, []);

  if (!selectedCountry) {
    return <div style={styles.emptyState}>Select a country to view zones</div>;
  }

  return (
    <div style={styles.container}>
      <div style={styles.toolbar}>
        <span style={{ fontWeight: 700, fontSize: '14px', color: '#1a1a2e' }}>
          {selectedCountry.name} Zones
        </span>
        <span style={{ fontSize: '12px', color: '#666' }}>
          ({zones.length} zones in {districtNames.length} districts)
        </span>
        <div style={{ flex: 1 }} />
        <button style={styles.btnSuccess} onClick={handleGenerateAll} disabled={generating}>
          {generating ? 'Generating...' : 'Generate All Zones'}
        </button>
        <button style={styles.btnSecondary} onClick={handleGenerateSingle} disabled={generating}>
          Generate District 01
        </button>
        <button style={styles.btnSecondary} onClick={() => setShowDistricts(!showDistricts)}>
          {showDistricts ? 'Hide' : 'Show'} Districts
        </button>
        <button style={styles.btnSecondary} onClick={loadData} disabled={loading}>
          Refresh
        </button>
      </div>

      <div style={styles.mapContainer}>
        <MapContainer center={[4.85, 31.6]} zoom={6} style={{ height: '100%', width: '100%' }}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <FitBounds zones={zones} countryId={selectedCountry.id} />
          <MapEventHandler onClick={handleMapClick} />

          {/* District Boundaries */}
          {showDistricts && districts.map((d, idx) => (
            d.boundary_geojson ? (
              <GeoJSON
                key={`district-${d.id}`}
                data={d.boundary_geojson}
                style={{
                  color: getDistrictColor(idx),
                  weight: 3,
                  fillOpacity: 0.04,
                  dashArray: '8, 6',
                }}
              />
            ) : null
          ))}

          {/* Zone Polygons — colored by district */}
          {zones.map((zone) => {
            const dIdx = districtNames.indexOf(zone.district_name || 'Unknown');
            const color = getDistrictColor(dIdx);
            const isSelected = selectedZone?.id === zone.id;
            const isEditing = editingZoneId === zone.id;
            if (isEditing) return null; // Don't show the original boundary while editing
            if (zone.boundary_geojson) {
              return (
                <GeoJSON
                  key={zone.id}
                  data={zone.boundary_geojson}
                  style={{
                    color: color,
                    weight: isSelected ? 3 : 1.5,
                    fillColor: color,
                    fillOpacity: isSelected ? 0.4 : 0.2,
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
                    fillOpacity: 0.3,
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
            const color = getDistrictColor(dIdx);
            return (
              <Marker
                key={`label-${zone.id}`}
                position={[zone.center_lat || 0, zone.center_lng || 0]}
                icon={L.divIcon({
                  className: '',
                  html: `<div style="background:rgba(255,255,255,0.95);padding:2px 5px;border-radius:4px;font-size:10px;font-weight:700;color:${color};border:1px solid ${color};white-space:nowrap;pointer-events:none;box-shadow:0 1px 3px rgba(0,0,0,0.15);">${zone.postal_code}</div>`,
                  iconSize: [80, 20],
                  iconAnchor: [40, 10],
                })}
                interactive={false}
              />
            );
          })}

          {/* Draw mode polygon overlay */}
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

        {/* Draw mode controls overlay */}
        {drawMode && (
          <div style={{
            position: 'absolute', top: '10px', left: '50%', transform: 'translateX(-50%)',
            background: 'white', padding: '10px 16px', borderRadius: '8px',
            boxShadow: '0 2px 12px rgba(0,0,0,0.2)', zIndex: 2000,
            display: 'flex', gap: '8px', alignItems: 'center',
          }}>
            <span style={{ fontSize: '13px', fontWeight: 600, color: '#ff6b6b' }}>
              Drawing boundary for: {selectedZone?.postal_code}
            </span>
            <span style={{ fontSize: '12px', color: '#666' }}>
              {drawPoints.length} points
            </span>
            {drawPoints.length >= 3 && (
              <button style={styles.btnSuccess} onClick={saveBoundary} disabled={saving}>
                {saving ? 'Saving...' : 'Save Boundary'}
              </button>
            )}
            {drawPoints.length > 0 && (
              <button style={styles.btnSecondary} onClick={undoLastPoint}>Undo</button>
            )}
            <button style={styles.btnDanger} onClick={cancelEdit}>Cancel</button>
          </div>
        )}

        {/* Legend */}
        {zones.length > 0 && !drawMode && (
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
            <div style={styles.infoRow}>Region: <strong>{selectedZone.region_name || '-'}</strong></div>
            <div style={styles.infoRow}>District: <strong>{selectedZone.district_name || '-'}</strong></div>
            {selectedZone.population && <div style={styles.infoRow}>Population: <strong>{selectedZone.population.toLocaleString()}</strong></div>}
            {selectedZone.area_sq_km && <div style={styles.infoRow}>Area: <strong>{selectedZone.area_sq_km.toFixed(1)} km²</strong></div>}
            <div style={styles.infoRow}>Status: <strong>{selectedZone.status}</strong></div>
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
  useMapEvents({ click: onClick });
  return null;
}
