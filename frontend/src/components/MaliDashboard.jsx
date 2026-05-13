import React, { useState, useEffect, useRef } from 'react';
import NeighborhoodGrid from './NeighborhoodGrid';
import InfoWidget, { WidgetTypes } from './InfoWidget';
import TrendChart from './TrendChart';
import MapView from './MapView';
import AlertPanel from './AlertPanel';
import CommuneStats from './CommuneStats';
import ToastNotification from './ToastNotification';
import { floodAPI } from '../services/api';
import './MaliDashboard.css';

const MALI_CITIES = [
  { code: 'bamako', name: 'Bamako' },
  { code: 'kayes', name: 'Kayes' },
  { code: 'sikasso', name: 'Sikasso' },
  { code: 'mopti', name: 'Mopti' },
  { code: 'segou', name: 'Ségou' }
];

const MaliDashboard = () => {
  const [selectedCity, setSelectedCity] = useState('bamako');
  const [neighborhoods, setNeighborhoods] = useState([]);
  const [predictions, setPredictions] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedNeighborhoods, setSelectedNeighborhoods] = useState([]);
  const [predictionsLoading, setPredictionsLoading] = useState(false);
  const [predictionError, setPredictionError] = useState(null);
  const [toasts, setToasts] = useState([]);
  const previousAlertsRef = useRef([]);

  useEffect(() => {
    loadNeighborhoods();
  }, [selectedCity]);

  useEffect(() => {
    if (neighborhoods.length > 0) {
      loadPredictions();
    }
  }, [neighborhoods]);

  useEffect(() => {
    loadAlerts();
    const interval = setInterval(loadAlerts, 60000); // Update every minute
    return () => clearInterval(interval);
  }, [selectedCity]);

  // Detect new critical alerts and show toast
  useEffect(() => {
    const currentCritical = alerts.filter(a => a.alert_level === 'critical');
    const previousCritical = previousAlertsRef.current.filter(a => a.alert_level === 'critical');
    
    // Find new critical alerts
    const newCritical = currentCritical.filter(current => 
      !previousCritical.some(prev => prev.id === current.id)
    );

    if (newCritical.length > 0) {
      newCritical.forEach(alert => {
        addToast({
          message: `🚨 Alerte Critique: ${alert.location} - ${(alert.flood_probability * 100).toFixed(1)}% de risque`,
          type: 'critical',
          duration: 8000
        });
      });
    }

    previousAlertsRef.current = alerts;
  }, [alerts]);

  const addToast = (toast) => {
    const id = Date.now();
    setToasts(prev => [...prev, { ...toast, id }]);
  };

  const removeToast = (id) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  };

  const loadNeighborhoods = async () => {
    try {
      setLoading(true);
      const data = await floodAPI.getMaliNeighborhoods(selectedCity);
      setNeighborhoods(data.neighborhoods || []);
    } catch (error) {
      console.error('Error loading neighborhoods:', error);
      setNeighborhoods([]);
    } finally {
      setLoading(false);
    }
  };

  const loadPredictions = async () => {
    try {
      setPredictionsLoading(true);
      setPredictionError(null);
      const predictionPromises = neighborhoods.map(async (neighborhood) => {
        try {
          if (selectedCity === 'bamako') {
            const data = await floodAPI.predictBamako({
              neighborhood: neighborhood.name,
              commune: neighborhood.commune,
            });
            const prediction = {
              ...(data.prediction || {}),
              commune: data.commune,
              neighborhood: neighborhood.name,
              context: data.context,
              metadata: data.metadata,
            };
            return { name: neighborhood.name, prediction };
          }

          const data = await floodAPI.getNeighborhoodForecast(
            neighborhood.name,
            selectedCity
          );
          return { name: neighborhood.name, prediction: data.prediction || data };
        } catch (error) {
          console.error(`Error predicting for ${neighborhood.name}:`, error);
          return null;
        }
      });

      const results = await Promise.all(predictionPromises);
      const predictionsMap = {};
      results.forEach(result => {
        if (result) {
          predictionsMap[result.name] = result.prediction;
        }
      });
      setPredictions(predictionsMap);
      setPredictionsLoading(false);
    } catch (error) {
      console.error('Error loading predictions:', error);
      setPredictionError("Impossible de calculer les probabilités d'inondation actuellement.");
      setPredictionsLoading(false);
    }
  };

  const loadAlerts = async () => {
    try {
      const data = await floodAPI.getAlerts('mali');
      setAlerts(data.alerts || []);
    } catch (error) {
      console.error('Error loading alerts:', error);
    }
  };

  const handleNeighborhoodClick = (neighborhood, prediction) => {
    // Toggle selection for trend chart
    const index = selectedNeighborhoods.indexOf(neighborhood.name);
    if (index > -1) {
      setSelectedNeighborhoods(selectedNeighborhoods.filter(n => n !== neighborhood.name));
    } else {
      setSelectedNeighborhoods([...selectedNeighborhoods, neighborhood.name]);
    }
  };

  const getStats = () => {
    const totalNeighborhoods = neighborhoods.length;
    const activeAlerts = alerts.filter(a => 
      a.location?.toLowerCase().includes(selectedCity)
    ).length;
    
    // Find highest risk neighborhood
    let highestRisk = null;
    let maxProbability = 0;
    Object.entries(predictions).forEach(([name, pred]) => {
      const prob = pred?.flood_probability || 0;
      if (prob > maxProbability) {
        maxProbability = prob;
        highestRisk = name;
      }
    });

    // Count by risk level
    const riskCounts = { critical: 0, high: 0, medium: 0, low: 0, none: 0 };
    Object.values(predictions).forEach(pred => {
      const risk = pred?.risk_level || pred?.alert_level || 'none';
      if (riskCounts.hasOwnProperty(risk)) {
        riskCounts[risk]++;
      }
    });

    return {
      totalNeighborhoods,
      activeAlerts,
      highestRisk,
      riskCounts
    };
  };

  const stats = getStats();

  const getWeatherWidgetData = () => {
    const totalPredictions = Object.values(predictions || {}).length;
    if (loading) {
      return {
        value: 'Chargement...',
        subtitle: 'Récupération des quartiers'
      };
    }
    if (!totalPredictions) {
      return {
        value: 'En attente',
        subtitle: 'Analyse LSTM en cours'
      };
    }
    const probabilities = Object.values(predictions).map(
      (pred) => pred?.flood_probability ?? 0
    );
    const avgProbability = probabilities.reduce((sum, p) => sum + p, 0) / probabilities.length;
    const maxProbability = Math.max(...probabilities);

    let text = 'Conditions calmes';
    if (avgProbability >= 0.6 || maxProbability >= 0.8) {
      text = '🌧️ Fortes pluies probables';
    } else if (avgProbability >= 0.4 || maxProbability >= 0.6) {
      text = '🌦️ Risque modéré';
    } else if (avgProbability >= 0.2) {
      text = '☁️ Faible risque';
    } else if (stats.riskCounts?.critical || stats.riskCounts?.high) {
      text = '⚠️ Vigilance requise';
    }

    return {
      value: text,
      subtitle: `Probabilité moyenne ${(avgProbability * 100).toFixed(0)}%`
    };
  };

  const weatherWidget = getWeatherWidgetData();

  // Prepare trend data
  const trendData = selectedNeighborhoods.map(name => {
    const pred = predictions[name];
    if (!pred || !pred.forecast) return null;
    
    return pred.forecast.forecasts?.map(day => ({
      date: day.date,
      neighborhood: name,
      probability: day.precipitation?.total || 0
    })) || [];
  }).flat().filter(Boolean);

  return (
    <div className="mali-dashboard">
      {/* Toast Notifications */}
      {toasts.length > 0 && (
        <div className="toast-container">
          {toasts.map(toast => (
            <ToastNotification
              key={toast.id}
              message={toast.message}
              type={toast.type}
              duration={toast.duration}
              onClose={() => removeToast(toast.id)}
            />
          ))}
        </div>
      )}

      <div className="dashboard-header">
        <h1>Dashboard Mali - Prédictions par Quartier</h1>
        <p>Surveillance des risques d'inondation par quartier</p>
      </div>

      {/* City Selector */}
      <div className="city-selector">
        <label>Sélectionner une ville:</label>
        <div className="city-buttons">
          {MALI_CITIES.map(city => (
            <button
              key={city.code}
              className={`city-button ${selectedCity === city.code ? 'active' : ''}`}
              onClick={() => setSelectedCity(city.code)}
            >
              {city.name}
            </button>
          ))}
        </div>
      </div>

      {/* Stats Widgets */}
      <div className="stats-grid">
        <InfoWidget
          {...WidgetTypes.TOTAL_NEIGHBORHOODS}
          value={stats.totalNeighborhoods}
          color={WidgetTypes.TOTAL_NEIGHBORHOODS.color}
        />
        <InfoWidget
          {...WidgetTypes.ACTIVE_ALERTS}
          value={stats.activeAlerts}
          color={WidgetTypes.ACTIVE_ALERTS.color}
        />
        <InfoWidget
          {...WidgetTypes.HIGH_RISK}
          value={stats.highestRisk || 'Aucun'}
          subtitle={stats.highestRisk ? `${(predictions[stats.highestRisk]?.flood_probability || 0) * 100}% de risque` : ''}
          color={WidgetTypes.HIGH_RISK.color}
        />
        <InfoWidget
          {...WidgetTypes.WEATHER}
          value={weatherWidget.value}
          subtitle={weatherWidget.subtitle}
          color={WidgetTypes.WEATHER.color}
        />
      </div>

      {/* Map and Alerts Row */}
      <div className="map-alerts-row">
        <div className="map-section">
          <MapView
            predictions={predictions}
            alerts={alerts}
            neighborhoods={neighborhoods}
            city={MALI_CITIES.find(c => c.code === selectedCity)?.name}
          />
        </div>
        <div className="alerts-section">
          <AlertPanel alerts={alerts} showNeighborhoodBadge={true} />
        </div>
      </div>

      {/* Commune Statistics */}
      {selectedCity === 'bamako' && Object.keys(predictions).length > 0 && (
        <CommuneStats 
          predictions={predictions}
          neighborhoods={neighborhoods}
        />
      )}

      {/* Trend Chart */}
      {selectedNeighborhoods.length > 0 && (
        <TrendChart 
          data={trendData}
          neighborhoods={selectedNeighborhoods}
        />
      )}

      {/* Neighborhood Grid */}
      {predictionsLoading && (
        <div className="status-banner loading">
          Analyse LSTM en cours pour Bamako...
        </div>
      )}
      {predictionError && (
        <div className="status-banner error">
          ⚠️ {predictionError}
        </div>
      )}
      {loading ? (
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Chargement des quartiers...</p>
        </div>
      ) : (
        <NeighborhoodGrid
          neighborhoods={neighborhoods}
          predictions={predictions}
          onNeighborhoodClick={handleNeighborhoodClick}
          city={MALI_CITIES.find(c => c.code === selectedCity)?.name}
        />
      )}
    </div>
  );
};

export default MaliDashboard;

