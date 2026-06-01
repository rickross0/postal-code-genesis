import React, { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import CountryWizard from './components/CountryWizard';
import CountryList from './components/CountryList';
import ZoneMap from './components/ZoneMap';
import LookupPanel from './components/LookupPanel';
import PolicyPanel from './components/PolicyPanel';
import { listCountries, getCountryStats } from './services/api';

const styles = {
  app: { display: 'flex', fontFamily: "'Inter', sans-serif", height: '100vh', background: '#f5f5fa' },
  main: { flex: 1, overflow: 'auto' },
};


export default function App() {
  const [currentView, setCurrentView] = useState('wizard');
  const [countries, setCountries] = useState([]);
  const [selectedCountry, setSelectedCountry] = useState(null);
  const [stats, setStats] = useState(null);

  const refreshCountries = useCallback(async () => {
    try {
      const res = await listCountries();
      setCountries(res.data);
    } catch (err) {
      console.error('Error loading countries', err);
    }
  }, []);

  useEffect(() => { refreshCountries(); }, [refreshCountries]);

  useEffect(() => {
    if (selectedCountry) {
      getCountryStats(selectedCountry.id)
        .then((res) => setStats(res.data))
        .catch(() => setStats(null));
    } else {
      setStats(null);
    }
  }, [selectedCountry]);

  const handleSelectCountry = (country) => {
    setSelectedCountry(country);
    setCurrentView('map');
  };

  const renderView = () => {
    switch (currentView) {
      case 'wizard':
        return <CountryWizard onCountryCreated={refreshCountries} />;
      case 'countries':
        return <CountryList onSelect={handleSelectCountry} onCountryDeleted={refreshCountries} />;
      case 'map':
        return <ZoneMap selectedCountry={selectedCountry} />;
      case 'lookup':
        return <LookupPanel />;
      case 'policy':
        return <PolicyPanel selectedCountry={selectedCountry} />;
      default:
        return <CountryWizard onCountryCreated={refreshCountries} />;
    }
  };

  return (
    <div style={styles.app}>
      <Sidebar
        countries={countries}
        selectedCountry={selectedCountry}
        onSelectCountry={handleSelectCountry}
        currentView={currentView}
        onNavigate={setCurrentView}
        stats={stats}
      />
      <div style={styles.main}>
        {renderView()}
      </div>
    </div>
  );
}
