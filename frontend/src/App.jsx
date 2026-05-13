import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import AlertPanel from './components/AlertPanel';
import MapView from './components/MapView';
import SatelliteView from './components/SatelliteView';
import MaliPage from './pages/MaliPage';
import './App.css';

function AppContent() {
  const location = useLocation();
  const [alerts, setAlerts] = useState([]);
  const [predictions, setPredictions] = useState({});
  const [countries, setCountries] = useState({});
  const [selectedCountry, setSelectedCountry] = useState(null);

  useEffect(() => {
    fetchAlerts();
    fetchCountries();
    
    // Update alerts every minute
    const interval = setInterval(fetchAlerts, 60000);
    return () => clearInterval(interval);
  }, []);

  const fetchAlerts = async () => {
    try {
      const { floodAPI } = await import('./services/api');
      const data = await floodAPI.getAlerts();
      setAlerts(data.alerts || []);
    } catch (error) {
      console.error('Error fetching alerts:', error);
    }
  };

  const fetchCountries = async () => {
    try {
      const { floodAPI } = await import('./services/api');
      const data = await floodAPI.getCountries();
      setCountries(data.countries || {});
    } catch (error) {
      console.error('Error fetching countries:', error);
    }
  };

  const handlePredict = async (location, lat, lon, country) => {
    try {
      const { floodAPI } = await import('./services/api');
      const data = await floodAPI.predict(location, lat, lon, country);
      setPredictions(prev => ({ ...prev, [location]: data }));
      fetchAlerts();
    } catch (error) {
      console.error('Error predicting:', error);
      alert(`Erreur de prédiction: ${error.message || error}`);
    }
  };

  const handleCountrySelect = (countryCode) => {
    setSelectedCountry(countryCode);
    if (countries[countryCode]) {
      const country = countries[countryCode];
      handlePredict(
        country.name,
        country.coordinates.lat,
        country.coordinates.lon,
        countryCode
      );
    }
  };

  const isMaliPage = location.pathname === '/mali';

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <div>
        <h1>🌊 Système d'Alerte de Prédiction d'Inondations</h1>
        <p>Prédiction d'inondations pour les pays d'Afrique</p>
          </div>
          <nav className="main-nav">
            <Link 
              to="/" 
              className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
            >
              Vue Globale
            </Link>
            <Link 
              to="/mali" 
              className={`nav-link ${location.pathname === '/mali' ? 'active' : ''}`}
            >
              Dashboard Mali
            </Link>
          </nav>
        </div>
      </header>
      
      <Routes>
        <Route path="/mali" element={<MaliPage />} />
        <Route path="/" element={
      <div className="main-container">
        <div className="left-panel">
          <Dashboard 
            onPredict={handlePredict} 
            predictions={predictions}
            countries={countries}
            onCountrySelect={handleCountrySelect}
            selectedCountry={selectedCountry}
          />
          <AlertPanel alerts={alerts} />
        </div>
        
        <div className="right-panel">
          <MapView 
            predictions={predictions} 
            alerts={alerts}
            countries={countries}
          />
          <SatelliteView 
            predictions={predictions}
            onPredict={handlePredict}
          />
        </div>
      </div>
        } />
      </Routes>
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;

