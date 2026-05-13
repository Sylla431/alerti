import React, { useState } from 'react';
import { floodAPI } from '../services/api';

const Dashboard = ({ onPredict, predictions, countries, onCountrySelect, selectedCountry }) => {
  const [location, setLocation] = useState('');
  const [lat, setLat] = useState('');
  const [lon, setLon] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!location.trim() && (!lat || !lon)) {
      alert('Veuillez entrer une localisation ou des coordonnées');
      return;
    }

    setLoading(true);
    try {
      const latitude = lat ? parseFloat(lat) : null;
      const longitude = lon ? parseFloat(lon) : null;
      
      await onPredict(location || 'Location', latitude, longitude, null);
      setLocation('');
      setLat('');
      setLon('');
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCountryClick = (countryCode) => {
    onCountrySelect(countryCode);
  };

  const getRiskColor = (risk) => {
    const colors = {
      critical: '#F44336',
      high: '#FF9800',
      medium: '#FFC107',
      low: '#4CAF50',
      none: '#9E9E9E'
    };
    return colors[risk] || '#757575';
  };

  return (
    <div className="dashboard">
      <h2>🌍 Prédiction d'Inondations</h2>
      
      {/* Country Selection */}
      {Object.keys(countries).length > 0 && (
        <div className="country-selector">
          <h3>Sélectionner un pays:</h3>
          <div className="country-buttons">
            {Object.entries(countries).slice(0, 12).map(([code, country]) => (
              <button
                key={code}
                className={`country-btn ${selectedCountry === code ? 'active' : ''}`}
                onClick={() => handleCountryClick(code)}
              >
                {country.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Manual Input Form */}
      <form onSubmit={handleSubmit} className="prediction-form">
        <div className="form-group">
          <label>Localisation:</label>
          <input
            type="text"
            placeholder="Nom de la ville/région (optionnel)"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            className="location-input"
          />
        </div>
        
        <div className="form-row">
          <div className="form-group">
            <label>Latitude:</label>
            <input
              type="number"
              step="any"
              placeholder="Ex: 9.0820"
              value={lat}
              onChange={(e) => setLat(e.target.value)}
              className="coord-input"
            />
          </div>
          
          <div className="form-group">
            <label>Longitude:</label>
            <input
              type="number"
              step="any"
              placeholder="Ex: 8.6753"
              value={lon}
              onChange={(e) => setLon(e.target.value)}
              className="coord-input"
            />
          </div>
        </div>

        <button 
          type="submit" 
          disabled={loading}
          className="predict-button"
        >
          {loading ? 'Prédiction en cours...' : '🔮 Prédire le Risque'}
        </button>
      </form>

      {/* Predictions List */}
      <div className="predictions-list">
        <h3>Prédictions Récentes</h3>
        {Object.entries(predictions).length === 0 ? (
          <p className="no-predictions">Aucune prédiction effectuée</p>
        ) : (
          Object.entries(predictions).map(([loc, pred]) => {
            const prediction = pred.prediction || pred;
            const riskLevel = prediction.risk_level || prediction.alert_level || 'none';
            const probability = prediction.flood_probability || 0;

            return (
              <div key={loc} className="prediction-card">
                <div className="prediction-header">
                  <h3>{pred.location || loc}</h3>
                  <span className="prediction-time">
                    {new Date(pred.timestamp).toLocaleString('fr-FR')}
                  </span>
                </div>
                
                <div 
                  className="risk-indicator" 
                  style={{ backgroundColor: getRiskColor(riskLevel) }}
                >
                  <div className="risk-content">
                    <span className="risk-label">Niveau de Risque: {riskLevel.toUpperCase()}</span>
                    <span className="risk-probability">
                      Probabilité: {(probability * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>

                {prediction.confidence && (
                  <div className="confidence-indicator">
                    Confiance: {(prediction.confidence * 100).toFixed(1)}%
                  </div>
                )}

                {pred.recommendations && pred.recommendations.length > 0 && (
                  <div className="recommendations">
                    <strong>Recommandations:</strong>
                    <ul>
                      {pred.recommendations.map((rec, i) => (
                        <li key={i}>{rec}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {prediction.predictions && (
                  <div className="model-breakdown">
                    <strong>Détails des Modèles:</strong>
                    <div className="model-details">
                      <div className="model-item">
                        <span>LSTM (Météo):</span>
                        <span>{(prediction.predictions.lstm?.probability * 100 || 0).toFixed(1)}%</span>
                      </div>
                      <div className="model-item">
                        <span>CNN (Image):</span>
                        <span>{(prediction.predictions.cnn?.probability * 100 || 0).toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default Dashboard;

