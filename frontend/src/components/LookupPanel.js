import React, { useState } from 'react';
import { lookupByCoordinates, lookupByName } from '../services/api';

const styles = {
  container: { padding: '30px', maxWidth: '700px', margin: '0 auto' },
  title: { fontSize: '28px', fontWeight: 700, marginBottom: '8px', color: '#1a1a2e' },
  subtitle: { fontSize: '14px', color: '#666', marginBottom: '30px' },
  card: { background: '#f8f9ff', borderRadius: '12px', padding: '24px', marginBottom: '20px', border: '1px solid #e8e8f0' },
  input: {
    width: '100%', padding: '10px 14px', border: '1px solid #ddd', borderRadius: '8px',
    fontSize: '14px', boxSizing: 'border-box', outline: 'none',
  },
  button: {
    padding: '10px 24px', background: '#6c63ff', color: 'white', border: 'none',
    borderRadius: '8px', fontSize: '14px', fontWeight: 600, cursor: 'pointer', marginTop: '12px',
  },
  result: { marginTop: '16px', padding: '16px', background: '#fff', borderRadius: '8px', border: '1px solid #e0e0f0' },
  code: { fontSize: '28px', fontWeight: 700, color: '#6c63ff' },
  row: { fontSize: '13px', color: '#666', marginTop: '4px' },
  label: { fontSize: '13px', fontWeight: 600, marginBottom: '6px', display: 'block', color: '#333' },
  row2: { display: 'flex', gap: '12px' },
  half: { flex: 1 },
};

export default function LookupPanel() {
  const [lat, setLat] = useState('');
  const [lng, setLng] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchCountry, setSearchCountry] = useState('SSD');
  const [coordResult, setCoordResult] = useState(null);
  const [nameResult, setNameResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleCoordLookup = async () => {
    if (!lat || !lng) return;
    setLoading(true);
    try {
      const res = await lookupByCoordinates(parseFloat(lat), parseFloat(lng));
      setCoordResult(res.data);
    } catch (err) {
      setCoordResult({ found: false, message: 'Error: ' + err.message });
    }
    setLoading(false);
  };

  const handleNameLookup = async () => {
    if (!searchQuery) return;
    setLoading(true);
    try {
      const res = await lookupByName(searchQuery, searchCountry);
      setNameResult(res.data);
    } catch (err) {
      setNameResult({ zone_results: [], landmark_results: [], error: err.message });
    }
    setLoading(false);
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>🔍 Postal Code Lookup</h1>
      <p style={styles.subtitle}>Find postal codes by GPS coordinates or place name</p>

      <div style={styles.card}>
        <h3 style={{ marginBottom: '12px' }}>Lookup by GPS Coordinates</h3>
        <div style={styles.row2}>
          <div style={styles.half}>
            <label style={styles.label}>Latitude</label>
            <input style={styles.input} value={lat} onChange={(e) => setLat(e.target.value)} placeholder="6.877" />
          </div>
          <div style={styles.half}>
            <label style={styles.label}>Longitude</label>
            <input style={styles.input} value={lng} onChange={(e) => setLng(e.target.value)} placeholder="31.307" />
          </div>
        </div>
        <button style={styles.button} onClick={handleCoordLookup} disabled={loading}>
          {loading ? 'Looking up...' : 'Find Code'}
        </button>

        {coordResult && (
          <div style={styles.result}>
            {coordResult.found ? (
              <>
                <div style={styles.code}>{coordResult.postal_code}</div>
                <div style={styles.row}>Zone: {coordResult.zone_name}</div>
                <div style={styles.row}>District: {coordResult.district}</div>
                <div style={styles.row}>Region: {coordResult.region}</div>
                {coordResult.full_address_suggestion && (
                  <div style={{ ...styles.row, marginTop: '8px', fontStyle: 'italic', color: '#333' }}>
                    {coordResult.full_address_suggestion}
                  </div>
                )}
              </>
            ) : (
              <div style={{ color: '#999' }}>{coordResult.message || 'No zone found at this location'}</div>
            )}
          </div>
        )}
      </div>

      <div style={styles.card}>
        <h3 style={{ marginBottom: '12px' }}>Search by Name</h3>
        <div style={styles.row2}>
          <div style={{ flex: 2 }}>
            <label style={styles.label}>Place Name / Landmark</label>
            <input style={styles.input} value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Juba Market" />
          </div>
          <div style={{ flex: 1 }}>
            <label style={styles.label}>Country</label>
            <input style={styles.input} value={searchCountry} onChange={(e) => setSearchCountry(e.target.value)} placeholder="SSD" />
          </div>
        </div>
        <button style={styles.button} onClick={handleNameLookup} disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>

        {nameResult && (
          <div style={styles.result}>
            {nameResult.zone_results?.length > 0 ? (
              nameResult.zone_results.map((r, i) => (
                <div key={i} style={{ padding: '8px 0', borderBottom: i < nameResult.zone_results.length - 1 ? '1px solid #eee' : 'none' }}>
                  <strong style={{ color: '#6c63ff' }}>{r.postal_code}</strong> — {r.zone_name}
                  <span style={{ color: '#999', fontSize: '12px' }}> ({r.district}, {r.region})</span>
                </div>
              ))
            ) : (
              <div style={{ color: '#999' }}>No zones found matching "{searchQuery}"</div>
            )}
            {nameResult.landmark_results?.length > 0 && (
              <div style={{ marginTop: '12px' }}>
                <strong style={{ fontSize: '13px' }}>Landmarks:</strong>
                {nameResult.landmark_results.map((r, i) => (
                  <div key={i} style={{ fontSize: '13px', color: '#666', padding: '4px 0' }}>
                    {r.landmark_name} ({r.category}) → <strong>{r.postal_code}</strong>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
