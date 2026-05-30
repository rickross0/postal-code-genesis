import React, { useState } from 'react';
import { createCountry, analyzeCountry, autoCreateZones } from '../services/api';

const styles = {
  container: { padding: '30px', maxWidth: '800px', margin: '0 auto' },
  title: { fontSize: '28px', fontWeight: 700, marginBottom: '8px', color: '#1a1a2e' },
  subtitle: { fontSize: '14px', color: '#666', marginBottom: '30px' },
  formGroup: { marginBottom: '20px' },
  label: { display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '6px', color: '#333' },
  input: {
    width: '100%', padding: '10px 14px', border: '1px solid #ddd', borderRadius: '8px',
    fontSize: '14px', boxSizing: 'border-box', outline: 'none',
  },
  select: {
    width: '100%', padding: '10px 14px', border: '1px solid #ddd', borderRadius: '8px',
    fontSize: '14px', background: 'white', boxSizing: 'border-box',
  },
  row: { display: 'flex', gap: '16px' },
  half: { flex: 1 },
  button: {
    padding: '12px 28px', background: '#6c63ff', color: 'white', border: 'none',
    borderRadius: '8px', fontSize: '14px', fontWeight: 600, cursor: 'pointer',
    marginTop: '10px',
  },
  buttonSecondary: {
    padding: '12px 28px', background: '#2a2a4e', color: 'white', border: 'none',
    borderRadius: '8px', fontSize: '14px', fontWeight: 600, cursor: 'pointer',
    marginTop: '10px', marginLeft: '12px',
  },
  card: {
    background: '#f8f9ff', borderRadius: '12px', padding: '24px',
    marginBottom: '20px', border: '1px solid #e8e8f0',
  },
  cardTitle: { fontSize: '16px', fontWeight: 600, marginBottom: '12px', color: '#1a1a2e' },
  metric: { display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #eee' },
  metricLabel: { color: '#666', fontSize: '13px' },
  metricValue: { fontWeight: 600, fontSize: '13px', color: '#1a1a2e' },
  consideration: { padding: '12px', background: '#fff', borderRadius: '8px', marginBottom: '8px', border: '1px solid #e0e0f0' },
  badge: { display: 'inline-block', padding: '2px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 600, marginBottom: '6px' },
  loading: { textAlign: 'center', padding: '40px', color: '#6c63ff', fontSize: '16px' },
};

const TIERS = [
  { value: 'urban_developing', label: 'Tier 1 — Urban Developing' },
  { value: 'mixed_rural_urban', label: 'Tier 2 — Mixed Rural/Urban' },
  { value: 'primarily_rural', label: 'Tier 3 — Primarily Rural' },
  { value: 'conflict_post_conflict', label: 'Tier 4 — Post-Conflict' },
];

export default function CountryWizard({ onCountryCreated }) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [createdCountry, setCreatedCountry] = useState(null);
  const [form, setForm] = useState({
    name: '', iso_code: '', tier: 'mixed_rural_urban',
    estimated_population: '', area_sq_km: '', num_regions: '', num_districts: '',
    languages: 'English', has_street_names: false, has_house_numbers: false,
    urban_percentage: '0', literacy_rate: '0', mobile_penetration: '0',
  });

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  const handleCreate = async () => {
    setLoading(true);
    try {
      const payload = {
        ...form,
        estimated_population: parseInt(form.estimated_population),
        area_sq_km: parseFloat(form.area_sq_km),
        num_regions: parseInt(form.num_regions),
        num_districts: parseInt(form.num_districts),
        languages: form.languages.split(',').map((l) => l.trim()),
        urban_percentage: parseFloat(form.urban_percentage),
        literacy_rate: parseFloat(form.literacy_rate) / 100,
        mobile_penetration: parseFloat(form.mobile_penetration) / 100,
      };
      const res = await createCountry(payload);
      setCreatedCountry(res.data);
      setStep(2);
    } catch (err) {
      alert('Error creating country: ' + (err.response?.data?.detail || err.message));
    }
    setLoading(false);
  };

  const handleAnalyze = async () => {
    setLoading(true);
    try {
      const res = await analyzeCountry(createdCountry.id);
      setAnalysis(res.data);
      setStep(3);
    } catch (err) {
      alert('Error analyzing: ' + err.message);
    }
    setLoading(false);
  };

  const handleGenerateZones = async () => {
    if (!analysis) return;
    setLoading(true);
    try {
      await autoCreateZones(createdCountry.id, '01', '01', analysis.recommendation.people_per_zone_target);
      if (onCountryCreated) onCountryCreated();
      setStep(4);
    } catch (err) {
      alert('Error creating zones: ' + err.message);
    }
    setLoading(false);
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>📍 Country Setup Wizard</h1>
      <p style={styles.subtitle}>Build a postal code system for a country that has none</p>

      {/* Step 1: Country Info */}
      <div style={styles.card}>
        <div style={{ ...styles.badge, background: step >= 1 ? '#e0ddd8' : '#eee', color: step >= 1 ? '#6c63ff' : '#999' }}>
          Step 1
        </div>
        <h3 style={styles.cardTitle}>Country Profile</h3>
        <div style={styles.row}>
          <div style={styles.half}>
            <div style={styles.formGroup}>
              <label style={styles.label}>Country Name</label>
              <input style={styles.input} name="name" value={form.name} onChange={handleChange} placeholder="e.g. South Sudan" />
            </div>
          </div>
          <div style={styles.half}>
            <div style={styles.formGroup}>
              <label style={styles.label}>ISO Code</label>
              <input style={styles.input} name="iso_code" value={form.iso_code} onChange={handleChange} placeholder="e.g. SSD" maxLength={3} />
            </div>
          </div>
        </div>
        <div style={styles.formGroup}>
          <label style={styles.label}>Infrastructure Tier</label>
          <select style={styles.select} name="tier" value={form.tier} onChange={handleChange}>
            {TIERS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>
        <div style={styles.row}>
          <div style={styles.half}>
            <div style={styles.formGroup}>
              <label style={styles.label}>Estimated Population</label>
              <input style={styles.input} name="estimated_population" value={form.estimated_population} onChange={handleChange} placeholder="11000000" />
            </div>
          </div>
          <div style={styles.half}>
            <div style={styles.formGroup}>
              <label style={styles.label}>Area (km²)</label>
              <input style={styles.input} name="area_sq_km" value={form.area_sq_km} onChange={handleChange} placeholder="619745" />
            </div>
          </div>
        </div>
        <div style={styles.row}>
          <div style={styles.half}>
            <div style={styles.formGroup}>
              <label style={styles.label}>Number of Regions</label>
              <input style={styles.input} name="num_regions" value={form.num_regions} onChange={handleChange} placeholder="10" />
            </div>
          </div>
          <div style={styles.half}>
            <div style={styles.formGroup}>
              <label style={styles.label}>Number of Districts</label>
              <input style={styles.input} name="num_districts" value={form.num_districts} onChange={handleChange} placeholder="79" />
            </div>
          </div>
        </div>
        <div style={styles.row}>
          <div style={styles.half}>
            <div style={styles.formGroup}>
              <label style={styles.label}>Languages (comma separated)</label>
              <input style={styles.input} name="languages" value={form.languages} onChange={handleChange} placeholder="English, Arabic" />
            </div>
          </div>
          <div style={styles.half}>
            <div style={styles.formGroup}>
              <label style={styles.label}>Urban %</label>
              <input style={styles.input} name="urban_percentage" value={form.urban_percentage} onChange={handleChange} placeholder="19.6" />
            </div>
          </div>
        </div>
        <div style={styles.row}>
          <div style={styles.half}>
            <div style={styles.formGroup}>
              <label style={styles.label}>Literacy Rate %</label>
              <input style={styles.input} name="literacy_rate" value={form.literacy_rate} onChange={handleChange} placeholder="34" />
            </div>
          </div>
          <div style={styles.half}>
            <div style={styles.formGroup}>
              <label style={styles.label}>Mobile Penetration %</label>
              <input style={styles.input} name="mobile_penetration" value={form.mobile_penetration} onChange={handleChange} placeholder="33" />
            </div>
          </div>
        </div>
        <div style={styles.formGroup}>
          <label>
            <input type="checkbox" name="has_street_names" checked={form.has_street_names} onChange={handleChange} /> Has street names
          </label>
        </div>
        {step === 1 && <button style={styles.button} onClick={handleCreate} disabled={loading}>
          {loading ? 'Creating...' : 'Create Country Profile →'}
        </button>}
      </div>

      {/* Step 2: Analyze */}
      {step >= 2 && (
        <div style={styles.card}>
          <div style={{ ...styles.badge, background: '#e0ddd8', color: '#6c63ff' }}>Step 2</div>
          <h3 style={styles.cardTitle}>System Analysis</h3>
          {createdCountry && <p style={{ color: '#666', fontSize: '13px' }}>Created: {createdCountry.name} ({createdCountry.iso_code})</p>}
          {step === 2 && <button style={styles.button} onClick={handleAnalyze} disabled={loading}>
            {loading ? 'Analyzing...' : 'Analyze Country →'}
          </button>}
        </div>
      )}

      {/* Step 3: Recommendations */}
      {analysis && step >= 3 && (
        <div style={styles.card}>
          <div style={{ ...styles.badge, background: '#e0ddd8', color: '#6c63ff' }}>Step 3</div>
          <h3 style={styles.cardTitle}>Recommendations</h3>

          <div style={styles.metric}>
            <span style={styles.metricLabel}>Code Format</span>
            <span style={styles.metricValue}>{analysis.recommendation.code_format.display}</span>
          </div>
          <div style={styles.metric}>
            <span style={styles.metricLabel}>Total Capacity</span>
            <span style={styles.metricValue}>{analysis.recommendation.code_format.total_capacity.toLocaleString()} zones</span>
          </div>
          <div style={styles.metric}>
            <span style={styles.metricLabel}>Estimated Zones Needed</span>
            <span style={styles.metricValue}>{analysis.recommendation.estimated_total_zones.toLocaleString()}</span>
          </div>
          <div style={styles.metric}>
            <span style={styles.metricLabel}>People per Zone</span>
            <span style={styles.metricValue}>{analysis.recommendation.people_per_zone_target.toLocaleString()}</span>
          </div>
          <div style={styles.metric}>
            <span style={styles.metricLabel}>Timeline</span>
            <span style={styles.metricValue}>{analysis.recommendation.implementation_timeline_months} months</span>
          </div>
          <div style={styles.metric}>
            <span style={styles.metricLabel}>Est. Total Cost</span>
            <span style={styles.metricValue}>
              ${analysis.recommendation.estimated_cost_usd.total_estimated.toLocaleString()}
            </span>
          </div>

          <h4 style={{ marginTop: '16px', marginBottom: '8px', fontSize: '14px' }}>Special Considerations</h4>
          {analysis.special_considerations.map((c, i) => (
            <div key={i} style={styles.consideration}>
              <strong style={{ fontSize: '13px' }}>{c.issue}</strong>
              <p style={{ fontSize: '12px', color: '#666', margin: '4px 0 0' }}>{c.solution}</p>
              {c.action && <p style={{ fontSize: '12px', color: '#6c63ff', margin: '4px 0 0' }}>→ {c.action}</p>}
            </div>
          ))}

          {step === 3 && <button style={styles.button} onClick={handleGenerateZones} disabled={loading}>
            {loading ? 'Generating...' : 'Auto-Create Zones →'}
          </button>}
        </div>
      )}

      {/* Step 4: Done */}
      {step === 4 && (
        <div style={styles.card}>
          <div style={{ ...styles.badge, background: '#d4edda', color: '#155724' }}>✓ Complete</div>
          <h3 style={styles.cardTitle}>Postal Code System Created!</h3>
          <p style={{ color: '#666', fontSize: '14px' }}>
            Zones have been generated. Use the sidebar to explore the map, look up codes, or generate policy documents.
          </p>
        </div>
      )}
    </div>
  );
}
