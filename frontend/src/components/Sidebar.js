import React from 'react';

const sidebarStyles = {
  sidebar: {
    width: '260px',
    background: '#1a1a2e',
    color: '#e0e0e0',
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    overflowY: 'auto',
    flexShrink: 0,
  },
  logo: {
    padding: '20px',
    borderBottom: '1px solid #2a2a4e',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    fontSize: '18px',
    fontWeight: 700,
  },
  section: {
    padding: '16px 20px 8px',
    fontSize: '11px',
    textTransform: 'uppercase',
    letterSpacing: '1.5px',
    color: '#8888aa',
    fontWeight: 600,
  },
  item: {
    padding: '10px 20px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    fontSize: '14px',
    transition: 'background 0.2s',
    borderLeft: '3px solid transparent',
  },
  activeItem: {
    background: '#2a2a4e',
    borderLeftColor: '#6c63ff',
  },
  stats: {
    padding: '20px',
    borderTop: '1px solid #2a2a4e',
    fontSize: '12px',
  },
  statRow: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '6px',
  },
  statLabel: { color: '#8888aa' },
  statValue: { color: '#6c63ff', fontWeight: 600 },
};

export default function Sidebar({ countries, selectedCountry, onSelectCountry, currentView, onNavigate, stats }) {
  return (
    <div style={sidebarStyles.sidebar}>
      <div style={sidebarStyles.logo}>
        <span>📍</span>
        <span>PostalCode Genesis</span>
      </div>

      <div style={sidebarStyles.section}>Setup</div>
      <div
        style={{ ...sidebarStyles.item, ...(currentView === 'wizard' ? sidebarStyles.activeItem : {}) }}
        onClick={() => onNavigate('wizard')}
      >
        <span>🌍</span> Country Setup
      </div>
      <div
        style={{ ...sidebarStyles.item, ...(currentView === 'countries' ? sidebarStyles.activeItem : {}) }}
        onClick={() => onNavigate('countries')}
      >
        <span>📋</span> Countries
      </div>

      {countries.length > 0 && (
        <>
          <div style={sidebarStyles.section}>Zones</div>
          {countries.map((c) => (
            <div
              key={c.id}
              style={{
                ...sidebarStyles.item,
                ...(selectedCountry?.id === c.id ? sidebarStyles.activeItem : {}),
                paddingLeft: '32px',
                fontSize: '13px',
              }}
              onClick={() => onSelectCountry(c)}
            >
              📍 {c.name}
            </div>
          ))}
        </>
      )}

      <div style={sidebarStyles.section}>Tools</div>
      <div
        style={{ ...sidebarStyles.item, ...(currentView === 'map' ? sidebarStyles.activeItem : {}) }}
        onClick={() => onNavigate('map')}
      >
        <span>🗺️</span> Zone Map
      </div>
      <div
        style={{ ...sidebarStyles.item, ...(currentView === 'lookup' ? sidebarStyles.activeItem : {}) }}
        onClick={() => onNavigate('lookup')}
      >
        <span>🔍</span> Lookup
      </div>
      <div
        style={{ ...sidebarStyles.item, ...(currentView === 'policy' ? sidebarStyles.activeItem : {}) }}
        onClick={() => onNavigate('policy')}
      >
        <span>📄</span> Policy Docs
      </div>

      {stats && (
        <div style={sidebarStyles.stats}>
          <div style={sidebarStyles.statRow}>
            <span style={sidebarStyles.statLabel}>Zones</span>
            <span style={sidebarStyles.statValue}>{stats.total_zones || 0}</span>
          </div>
          <div style={sidebarStyles.statRow}>
            <span style={sidebarStyles.statLabel}>Regions</span>
            <span style={sidebarStyles.statValue}>{stats.total_regions || 0}</span>
          </div>
          <div style={sidebarStyles.statRow}>
            <span style={sidebarStyles.statLabel}>Districts</span>
            <span style={sidebarStyles.statValue}>{stats.total_districts || 0}</span>
          </div>
          <div style={sidebarStyles.statRow}>
            <span style={sidebarStyles.statLabel}>Landmarks</span>
            <span style={sidebarStyles.statValue}>{stats.total_landmarks || 0}</span>
          </div>
        </div>
      )}
    </div>
  );
}
