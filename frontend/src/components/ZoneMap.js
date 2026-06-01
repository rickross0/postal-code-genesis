import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Marker, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { listZones, updateZone, autoCreateAllZones, createZoneManual, listDistricts, deleteZone } from '../services/api';

const ZONE_COLORS = [
  '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
  '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4',
  '#469990', '#dcbeff', '#9A6324', '#fffac8', '#800000',
  '#aaffc3', '#808000', '#ffd8b1', '#000075', '#a9a9a9',
];

const styles = {
  container: { flex: 1, display: 'flex', flexDirection: 'column', height: '100vh' },
  toolbar: { padding: '10px 16px', background: '#fff', borderBottom: '1px solid #e8e8f0', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' },
  mapContainer: { flex: 1, position: 'relative', background: '#f0f0f5', overflow: 'hidden' },
  btn: { padding: '6px 14px', background: '#6c63ff', color: 'white', border: 'none', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer' },
  btnSec: { padding: '6px 14px', background: '#f0f0f5', color: '#333', border: '1px solid #ddd', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer' },
  btnDanger: { padding: '6px 14px', background: '#ff6b6b', color: 'white', border: 'none', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer' },
  btnSuccess: { padding: '6px 14px', background: '#51cf66', color: 'white', border: 'none', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer' },
  btnWarning: { padding: '6px 14px', background: '#ff922b', color: 'white', border: 'none', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer' },
  drawBar: { position: 'absolute', top: '10px', left: '50%', transform: 'translateX(-50%)', zIndex: 2000, background: 'white', padding: '10px 18px', borderRadius: '10px', boxShadow: '0 2px 16px rgba(0,0,0,0.18)', display: 'flex', gap: '10px', alignItems: 'center' },
  infoPanel: { position: 'absolute', bottom: '20px', right: '20px', background: 'white', borderRadius: '12px', padding: '16px', boxShadow: '0 4px 20px rgba(0,0,0,0.15)', maxWidth: '320px', zIndex: 1000, fontSize: '13px' },
  legend: { position: 'absolute', top: '20px', left: '20px', background: 'white', borderRadius: '10px', padding: '12px', boxShadow: '0 2px 12px rgba(0,0,0,0.12)', maxWidth: '240px', zIndex: 1000, fontSize: '12px', maxHeight: '50vh', overflowY: 'auto' },
  empty: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999', fontSize: '16px', textAlign: 'center', padding: '40px' },
};

function FitBounds({ zones, countryId }) {
  const map = useMap();
  const last = useRef(null);
  useEffect(() => {
    if (!zones.length) return;
    if (last.current === countryId) return;
    last.current = countryId;
    const valid = zones.filter(z => z.center_lat && z.center_lng);
    if (!valid.length) return;
    const bounds = L.latLngBounds(valid.map(z => [z.center_lat, z.center_lng]));
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [60, 60] });
  }, [zones, map, countryId]);
  return null;
}

function ClickHandler({ onClick }) {
  useMapEvents({ click: onClick });
  return null;
}

export default function ZoneMap({ selectedCountry }) {
  const [zones, setZones] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [selectedZone, setSelectedZone] = useState(null);
  const [selectedDistrict, setSelectedDistrict] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [drawing, setDrawing] = useState(false);
  const [drawPoints, setDrawPoints] = useState([]);
  const [editingZone, setEditingZone] = useState(null);
  const [saving, setSaving] = useState(false);
  const [showDistricts, setShowDistricts] = useState(true);

  const loadData = useCallback(async () => {
    if (!selectedCountry) return;
    setLoading(true);
    try {
      const [zRes, dRes] = await Promise.all([listZones(selectedCountry.id), listDistricts(selectedCountry.id)]);
      setZones(zRes.data);
      setDistricts(dRes.data);
    } catch (err) { console.error('Load error', err); }
    setLoading(false);
  }, [selectedCountry]);

  useEffect(() => { loadData(); }, [loadData]);

  const startDrawing = useCallback((districtId) => {
    setDrawing(true);
    setDrawPoints([]);
    setEditingZone(null);
    setSelectedZone(null);
    if (districtId) setSelectedDistrict(districtId);
  }, []);

  const startEditing = useCallback((zone) => {
    setEditingZone(zone);
    setDrawing(true);
    setDrawPoints([]);
    if (zone.boundary_geojson && zone.boundary_geojson.coordinates) {
      const coords = zone.boundary_geojson.coordinates[0];
      setDrawPoints(coords.slice(0, -1).map(c => [c[1], c[0]]));
    }
  }, []);

  const cancelDraw = useCallback(() => { setDrawing(false); setDrawPoints([]); setEditingZone(null); }, []);

  const saveDraw = useCallback(async () => {
    if (drawPoints.length < 3) { alert('Need at least 3 points to form a zone boundary.'); return; }
    setSaving(true);
    try {
      const closed = [...drawPoints, drawPoints[0]];
      const coordinates = [closed.map(p => [p[1], p[0]])];
      const geojson = { type: 'Polygon', coordinates };

      if (editingZone) {
        await updateZone(editingZone.id, { boundary_geojson: geojson });
      } else {
        const districtId = selectedDistrict || (districts.length > 0 ? districts[0].id : undefined);
        await createZoneManual(selectedCountry.id, {
          country_id: selectedCountry.id,
          boundary_geojson: geojson,
          district_id: districtId,
        });
      }
      setDrawing(false); setDrawPoints([]); setEditingZone(null);
      await loadData();
    } catch (err) {
      alert('Save failed: ' + (err.response?.data?.detail || err.message));
    }
    setSaving(false);
  }, [drawPoints, editingZone, selectedCountry, selectedDistrict, districts, loadData]);

  const handleDeleteZone = useCallback(async (zoneId) => {
    if (!window.confirm('Delete this zone permanently?')) return;
    try {
      await deleteZone(zoneId);
      setSelectedZone(null);
      await loadData();
    } catch (err) {
      alert('Delete failed: ' + (err.response?.data?.detail || err.message));
    }
  }, [loadData]);

  const handleGenerateAll = useCallback(async () => {
    if (!selectedCountry) return;
    if (!window.confirm('Auto-generate zones for ALL districts? This replaces existing zones.')) return;
    setGenerating(true);
    try { await autoCreateAllZones(selectedCountry.id, 5000); await loadData(); }
    catch (err) { alert('Failed: ' + (err.response?.data?.detail || err.message)); }
    setGenerating(false);
  }, [selectedCountry, loadData]);

  const handleMapClick = useCallback((e) => {
    if (!drawing) return;
    setDrawPoints(prev => [...prev, [e.latlng.lat, e.latlng.lng]]);
  }, [drawing]);

  const undoPoint = useCallback(() => setDrawPoints(prev => prev.slice(0, -1)), []);

  if (!selectedCountry) return <div style={styles.empty}>Select a country to view zones</div>;

  // Filter zones by selected district if one is highlighted
  const filteredZones = selectedDistrict
    ? zones.filter(z => z.district_name === (districts.find(d => d.id === selectedDistrict)?.name))
    : zones;

  return (
    <div style={styles.container}>
      <div style={styles.toolbar}>
        <span style={{ fontWeight: 700, fontSize: '14px', color: '#1a1a2e' }}>{selectedCountry.name} Zones</span>
        <span style={{ fontSize: '12px', color: '#666' }}>({zones.length} total)</span>
        <div style={{ flex: 1 }} />
        <button style={styles.btn} onClick={() => startDrawing(null)}>✏️ Draw Zone</button>
        <button style={styles.btnSuccess} onClick={handleGenerateAll} disabled={generating}>
          {generating ? 'Generating...' : '⚡ Auto-Generate'}
        </button>
        <button style={styles.btnSec} onClick={() => setShowDistricts(!showDistricts)}>
          {showDistricts ? 'Hide' : 'Show'} Districts
        </button>
        <button style={styles.btnSec} onClick={loadData} disabled={loading}>Refresh</button>
      </div>

      <div style={styles.mapContainer}>
        <MapContainer center={[4.85, 31.6]} zoom={6} style={{ height: '100%', width: '100%' }}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <FitBounds zones={zones} countryId={selectedCountry.id} />
          <ClickHandler onClick={handleMapClick} />

          {showDistricts && districts.map((d, i) => (
            d.boundary_geojson ? (
              <GeoJSON key={`d-${d.id}`} data={d.boundary_geojson} style={{
                color: '#555', weight: 2, fillColor: selectedDistrict === d.id ? '#6c63ff' : '#aaa',
                fillOpacity: selectedDistrict === d.id ? 0.1 : 0.03, dashArray: '6,4',
              }} eventHandlers={{
                click: () => { if (!drawing) setSelectedDistrict(selectedDistrict === d.id ? null : d.id); }
              }} />
            ) : null
          ))}

          {filteredZones.map((zone) => {
            const color = ZONE_COLORS[zone.id % ZONE_COLORS.length];
            const isSelected = selectedZone?.id === zone.id;
            const isEditing = editingZone?.id === zone.id;
            if (isEditing) return null;
            if (zone.boundary_geojson) {
              return (
                <GeoJSON key={zone.id} data={zone.boundary_geojson} style={{
                  color: isSelected ? '#fff' : color, weight: isSelected ? 3 : 1.5,
                  fillColor: color, fillOpacity: isSelected ? 0.5 : 0.25,
                }} eventHandlers={{ click: () => { if (!drawing) setSelectedZone(zone); } }} />
              );
            }
            return (
              <CircleMarker key={zone.id} center={[zone.center_lat || 0, zone.center_lng || 0]}
                radius={10} pathOptions={{ color: isSelected ? '#ff6b6b' : color, fillColor: color, fillOpacity: 0.3, weight: isSelected ? 3 : 2 }}
                eventHandlers={{ click: () => { if (!drawing) setSelectedZone(zone); } }} />
            );
          })}

          {filteredZones.map((zone) => {
            const color = ZONE_COLORS[zone.id % ZONE_COLORS.length];
            return (
              <Marker key={`l-${zone.id}`} position={[zone.center_lat || 0, zone.center_lng || 0]}
                icon={L.divIcon({ className: '', html: `<div style="background:rgba(255,255,255,0.95);padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700;color:${color};border:1px solid ${color};white-space:nowrap;pointer-events:none;">${zone.postal_code}</div>`, iconSize: [80, 20], iconAnchor: [40, 10] })}
                interactive={false} />
            );
          })}

          {drawing && drawPoints.length > 0 && (
            <>
              <Polygon positions={drawPoints} pathOptions={{ color: '#ff6b6b', dashArray: '5,8', fillColor: '#ff6b6b', fillOpacity: 0.15, weight: 2 }} />
              {drawPoints.map((p, i) => <CircleMarker key={`p-${i}`} center={p} radius={5} pathOptions={{ color: '#ff6b6b', fillColor: '#ff6b6b', fillOpacity: 1, weight: 1 }} />)}
            </>
          )}
        </MapContainer>

        {drawing && (
          <div style={styles.drawBar}>
            <span style={{ fontWeight: 700, fontSize: '13px', color: '#6c63ff' }}>
              {editingZone ? `Editing: ${editingZone.postal_code}` : 'Draw new zone'}
              {selectedDistrict && !editingZone ? ` (District: ${districts.find(d => d.id === selectedDistrict)?.name || ''})` : ''}
            </span>
            <span style={{ fontSize: '12px', color: '#666' }}>{drawPoints.length} points</span>
            {drawPoints.length >= 3 && (
              <button style={styles.btnSuccess} onClick={saveDraw} disabled={saving}>
                {saving ? 'Saving...' : '✓ Save Zone'}
              </button>
            )}
            {drawPoints.length > 0 && <button style={styles.btnSec} onClick={undoPoint}>Undo</button>}
            <button style={styles.btnDanger} onClick={cancelDraw}>Cancel</button>
          </div>
        )}

        {zones.length > 0 && !drawing && (
          <div style={styles.legend}>
            <div style={{ fontWeight: 600, marginBottom: '8px', fontSize: '13px', color: '#1a1a2e' }}>
              {selectedDistrict ? `${districts.find(d => d.id === selectedDistrict)?.name || 'District'}` : 'All Zones'}
              <span style={{ fontWeight: 400, fontSize: '11px', color: '#999', marginLeft: '6px' }}>({filteredZones.length})</span>
            </div>
            <div style={{ maxHeight: '40vh', overflowY: 'auto' }}>
              {filteredZones.slice(0, 50).map((zone) => {
                const color = ZONE_COLORS[zone.id % ZONE_COLORS.length];
                return (
                  <div key={zone.id} style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '3px', cursor: 'pointer' }}
                    onClick={() => setSelectedZone(zone)}>
                    <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: color, border: '1px solid rgba(0,0,0,0.1)' }} />
                    <span style={{ color: '#333', fontSize: '11px' }}>{zone.postal_code}</span>
                    <span style={{ color: '#888', fontSize: '10px' }}>- {zone.name}</span>
                  </div>
                );
              })}
              {filteredZones.length > 50 && <div style={{ color: '#999', fontSize: '11px', marginTop: '4px' }}>+{filteredZones.length - 50} more</div>}
            </div>
          </div>
        )}

        {selectedZone && !drawing && (
          <div style={styles.infoPanel}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontSize: '22px', fontWeight: 700, color: ZONE_COLORS[selectedZone.id % ZONE_COLORS.length] }}>{selectedZone.postal_code}</div>
                <div style={{ fontWeight: 600, fontSize: '14px' }}>{selectedZone.name}</div>
              </div>
              <button style={{ background: 'none', border: 'none', fontSize: '18px', cursor: 'pointer', color: '#999' }} onClick={() => setSelectedZone(null)}>✕</button>
            </div>
            <div style={{ fontSize: '12px', color: '#666', marginTop: '6px' }}>
              {selectedZone.region_name && <div>Region: <strong>{selectedZone.region_name}</strong></div>}
              {selectedZone.district_name && <div>District: <strong>{selectedZone.district_name}</strong></div>}
              {selectedZone.population && <div>Population: <strong>{selectedZone.population.toLocaleString()}</strong></div>}
              {selectedZone.area_sq_km && <div>Area: <strong>{selectedZone.area_sq_km.toFixed(1)} km²</strong></div>}
              <div>Status: <strong>{selectedZone.status || 'active'}</strong></div>
            </div>
            <div style={{ marginTop: '10px', display: 'flex', gap: '6px' }}>
              <button style={styles.btn} onClick={() => startEditing(selectedZone)}>✏️ Edit Boundary</button>
              <button style={styles.btnDanger} onClick={() => handleDeleteZone(selectedZone.id)}>🗑 Delete</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
