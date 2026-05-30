import React, { useState } from 'react';
import { createCountry, analyzeCountry, autoCreateZones, lookupCountry, lookupCity } from '../services/api';

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
    languages: 'English', has_street_names: false, has_house_numbers: false, has_any_addressing: false,
    urban_percentage: '0', literacy_rate: '0', mobile_penetration: '0', internet_penetration: '0',
    capital_city: '', capital_lat: '', capital_lng: '',
  });

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  const handleLookup = async () => {
    if (!form.name.trim()) {
      alert("Enter a country name first");
      return;
    }
    setLoading(true);
    try {
      const res = await lookupCountry(form.name);
      const data = res.data;
      if (data.population) {
        setForm((prev) => ({
          ...prev,
          iso_code: data.iso_code || prev.iso_code,
          estimated_population: String(data.population || prev.estimated_population),
          area_sq_km: data.area_sq_km ? String(Math.round(data.area_sq_km)) : prev.area_sq_km,
          capital_city: data.capital_city || prev.capital_city,
          capital_lat: data.capital_lat != null ? String(data.capital_lat) : prev.capital_lat,
          capital_lng: data.capital_lng != null ? String(data.capital_lng) : prev.capital_lng,
          languages: data.languages?.join(', ') || prev.languages,
        }));
        // If capital city exists, try to refine its coordinates
        if (data.capital_city) {
          try {
            const cityRes = await lookupCity(data.capital_city, data.iso_code_2);
            const c = cityRes.data;
            if (c.lat != null && c.lng != null) {
              setForm((prev) => ({
                ...prev,
                capital_lat: String(c.lat),
                capital_lng: String(c.lng),
              }));
            }
          } catch (_) { /* ignore city lookup failure */ }
        }
      } else {
        alert("No data found for "" + form.name + """);
      }
    } catch (err) {
      alert("Lookup failed: " + (err.response?.data?.detail || err.message));
    }
    setLoading(false);
  };

  const handleCreate = async () => {
    setLoading(true);
    try {
      const payload = {
        name: form.name,
        iso_code: form.iso_code,
        tier: form.tier,
        estimated_population: parseInt(form.estimated_population) || 1,
        area_sq_km: parseFloat(form.area_sq_km) || 1,
        num_regions: parseInt(form.num_regions) || 1,
        num_districts: parseInt(form.num_districts) || 1,
        languages: form.languages.split(',').map((l) => l.trim()).filter(Boolean),
        has_street_names: !!form.has_street_names,
        has_house_numbers: !!form.has_house_numbers,
        has_any_addressing: !!form.has_any_addressing,
        urban_percentage: parseFloat(form.urban_percentage) || 0,
        literacy_rate: (parseFloat(form.literacy_rate) || 0) / 100,
        mobile_penetration: (parseFloat(form.mobile_penetration) || 0) / 100,
        internet_penetration: (parseFloat(form.internet_penetration) || 0) / 100,
        capital_city: form.capital_city || null,
        capital_lat: form.capital_lat ? parseFloat(form.capital_lat) : null,
        capital_lng: form.capital_lng ? parseFloat(form.capital_lng) : null,
        existing_admin_divisions: {},
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
              <div style={{ display: 'flex', gap: '8px' }}>
                <input style={{ ...styles.input, flex: 1 }} name="name" value={form.name} onChange={handleChange} placeholder="e.g. South Sudan" />
                <button style={{ ...styles.btnSecondary, whiteSpace: 'nowrap' }} onClick={handleLookup} disabled={loading}>
                  {loading ? 'Looking up…' : '🔍 Look Up'}
                </button>
              </div>
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
              <label style={styles.label}>Capital City</label>
              <input style={styles.input} name="capital_city" value={form.capital_city} onChange={handleChange} placeholder="e.g. Juba" />
            </div>
          </div>
          <div style={styles.half}>
            <div style={styles.formGroup}>
              <label style={styles.label}>Capital Coordinates (lat, lng)</label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input style={{ ...styles.input, flex: 1 }} name="capital_lat" value={form.capital_lat} onChange={handleChange} placeholder="4.85" />
                <input style={{ ...styles.input, flex: 1 }} name="capital_lng" value={form.capital_lng} onChange={handleChange} placeholder="31.6" />
              </div>
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
