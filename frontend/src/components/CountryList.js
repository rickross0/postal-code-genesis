import React, { useEffect, useState } from 'react';
import { listCountries } from '../services/api';

const styles = {
  container: { padding: '30px', maxWidth: '800px', margin: '0 auto' },
  title: { fontSize: '28px', fontWeight: 700, marginBottom: '8px', color: '#1a1a2e' },
  subtitle: { fontSize: '14px', color: '#666', marginBottom: '30px' },
  card: {
    background: '#fff', borderRadius: '12px', padding: '20px', marginBottom: '12px',
    border: '1px solid #e8e8f0', cursor: 'pointer', transition: 'box-shadow 0.2s',
  },
  name: { fontSize: '18px', fontWeight: 600, color: '#1a1a2e' },
  iso: { fontSize: '12px', color: '#999', marginLeft: '8px' },
  tier: {
    display: 'inline-block', padding: '2px 10px', borderRadius: '12px',
    fontSize: '11px', fontWeight: 600, marginTop: '6px',
  },
  details: { fontSize: '13px', color: '#666', marginTop: '8px' },
};

const TIER_COLORS = {
  urban_developing: { bg: '#e6f7ee', color: '#155724' },
  mixed_rural_urban: { bg: '#fff8e1', color: '#856404' },
  primarily_rural: { bg: '#fff3e0', color: '#bf360c' },
  conflict_post_conflict: { bg: '#fce4ec', color: '#880e4f' },
};

const TIER_LABELS = {
  urban_developing: 'Tier 1 — Urban',
  mixed_rural_urban: 'Tier 2 — Mixed',
  primarily_rural: 'Tier 3 — Rural',
  conflict_post_conflict: 'Tier 4 — Post-Conflict',
};

export default function CountryList({ onSelect }) {
  const [countries, setCountries] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listCountries()
      .then((res) => setCountries(res.data))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>🌍 Countries</h1>
      <p style={styles.subtitle}>Manage countries with postal code systems</p>

      {loading ? (
        <p style={{ color: '#999' }}>Loading...</p>
      ) : countries.length === 0 ? (
        <p style={{ color: '#999' }}>No countries yet. Use the Country Setup Wizard to add one.</p>
      ) : (
        countries.map((c) => {
          const tierStyle = TIER_COLORS[c.tier] || TIER_COLORS.mixed_rural_urban;
          return (
            <div key={c.id} style={styles.card} onClick={() => onSelect(c)}>
              <span style={styles.name}>{c.name}</span>
              <span style={styles.iso}>({c.iso_code})</span>
              <div>
                <span style={{ ...styles.tier, background: tierStyle.bg, color: tierStyle.color }}>
                  {TIER_LABELS[c.tier] || c.tier}
                </span>
              </div>
              <div style={styles.details}>
                Population: {c.estimated_population.toLocaleString()} · Area: {c.area_sq_km.toLocaleString()} km² ·
                Regions: {c.num_regions} · Districts: {c.num_districts}
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
