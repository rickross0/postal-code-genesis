import React, { useState } from 'react';
import { generatePolicy } from '../services/api';

const styles = {
  container: { padding: '30px', maxWidth: '800px', margin: '0 auto' },
  title: { fontSize: '28px', fontWeight: 700, marginBottom: '8px', color: '#1a1a2e' },
  subtitle: { fontSize: '14px', color: '#666', marginBottom: '30px' },
  button: {
    padding: '10px 24px', background: '#6c63ff', color: 'white', border: 'none',
    borderRadius: '8px', fontSize: '14px', fontWeight: 600, cursor: 'pointer', marginBottom: '20px',
  },
  doc: {
    background: '#1a1a2e', color: '#d4d4d4', padding: '24px', borderRadius: '12px',
    fontFamily: 'monospace', fontSize: '12px', whiteSpace: 'pre-wrap', lineHeight: '1.6',
    maxHeight: '70vh', overflow: 'auto',
  },
  tabs: { display: 'flex', gap: '8px', marginBottom: '16px' },
  tab: {
    padding: '8px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: 600,
    cursor: 'pointer', border: '1px solid #ddd', background: '#fff',
  },
  activeTab: { background: '#6c63ff', color: 'white', border: '1px solid #6c63ff' },
};

export default function PolicyPanel({ selectedCountry }) {
  const [policy, setPolicy] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('policy');

  const handleGenerate = async () => {
    if (!selectedCountry) return;
    setLoading(true);
    try {
      const res = await generatePolicy(selectedCountry.id);
      setPolicy(res.data);
    } catch (err) {
      alert('Error: ' + err.message);
    }
    setLoading(false);
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>📄 Policy Documents</h1>
      <p style={styles.subtitle}>Generate official government policy documents for the postal code system</p>

      {selectedCountry ? (
        <>
          <button style={styles.button} onClick={handleGenerate} disabled={loading}>
            {loading ? 'Generating...' : `Generate Policy for ${selectedCountry.name}`}
          </button>

          {policy && (
            <>
              <div style={styles.tabs}>
                <div
                  style={{ ...styles.tab, ...(activeTab === 'policy' ? styles.activeTab : {}) }}
                  onClick={() => setActiveTab('policy')}
                >
                  Policy Document
                </div>
                <div
                  style={{ ...styles.tab, ...(activeTab === 'guide' ? styles.activeTab : {}) }}
                  onClick={() => setActiveTab('guide')}
                >
                  Implementation Guide
                </div>
              </div>
              <div style={styles.doc}>
                {activeTab === 'policy' ? policy.policy_document : policy.implementation_guide}
              </div>
            </>
          )}
        </>
      ) : (
        <p style={{ color: '#999' }}>Select a country first to generate policy documents</p>
      )}
    </div>
  );
}
