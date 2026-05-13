import React, { useState } from 'react';
import { floodAPI } from '../services/api';

const SatelliteView = ({ predictions, onPredict }) => {
  const [loading, setLoading] = useState(false);
  const [satelliteData, setSatelliteData] = useState(null);
  const [location, setLocation] = useState('');

  const handleAnalyzeImage = async (predictionData) => {
    if (!predictionData) return;

    setLoading(true);
    setLocation(predictionData.location || 'Unknown');

    try {
      const coords = predictionData.coordinates || 
                    predictionData.prediction?.coordinates ||
                    {};
      
      if (!coords.lat || !coords.lon) {
        throw new Error('Coordonnées manquantes');
      }

      const bbox = [
        coords.lon - 0.1,
        coords.lat - 0.1,
        coords.lon + 0.1,
        coords.lat + 0.1
      ];

      const data = await floodAPI.predictImage(
        predictionData.location || 'Unknown',
        coords.lat,
        coords.lon,
        bbox
      );

      setSatelliteData(data);
    } catch (error) {
      console.error('Error analyzing satellite image:', error);
      alert(`Erreur lors de l'analyse de l'image: ${error.message || error}`);
    } finally {
      setLoading(false);
    }
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

  // Get first prediction for demonstration
  const firstPrediction = Object.values(predictions)[0];

  return (
    <div className="satellite-view">
      <h2>🛰️ Analyse d'Image Satellite</h2>
      
      {firstPrediction && (
        <div className="satellite-actions">
          <button
            onClick={() => handleAnalyzeImage(firstPrediction)}
            disabled={loading}
            className="analyze-button"
          >
            {loading ? 'Analyse en cours...' : '📡 Analyser Image Satellite'}
          </button>
        </div>
      )}

      {satelliteData && (
        <div className="satellite-results">
          {satelliteData.prediction?.flood_mask && (
            <div className="satellite-image-container">
              <img
                src={`data:image/png;base64,${satelliteData.prediction.flood_mask}`}
                alt="Masque de détection d'inondation"
                className="flood-mask"
              />
              <div className="mask-overlay">
                <p>Masque de détection d'inondation</p>
                <p className="mask-note">
                  Zones en blanc = zones inondées détectées
                </p>
              </div>
            </div>
          )}

          {satelliteData.prediction && (
            <div className="satellite-prediction">
              <h3>Résultats de l'Analyse</h3>
              <div className="prediction-stats">
                <div className="stat-item">
                  <strong>Statut:</strong>
                  <span className={satelliteData.prediction.flood_detected ? 'detected' : 'not-detected'}>
                    {satelliteData.prediction.flood_detected ? 'Inondation Détectée' : 'Aucune Inondation'}
                  </span>
                </div>
                
                <div className="stat-item">
                  <strong>Zone Inondée:</strong>
                  <span>{satelliteData.prediction.flood_percentage?.toFixed(2) || 0}%</span>
                </div>
                
                <div className="stat-item">
                  <strong>Niveau de Risque:</strong>
                  <span 
                    style={{ 
                      color: getRiskColor(satelliteData.prediction.risk_level),
                      fontWeight: 'bold'
                    }}
                  >
                    {satelliteData.prediction.risk_level?.toUpperCase() || 'N/A'}
                  </span>
                </div>

                <div className="stat-item">
                  <strong>Modèle:</strong>
                  <span>{satelliteData.prediction.model_type || 'CNN/U-Net'}</span>
                </div>

                {satelliteData.prediction.satellite_source && (
                  <div className="stat-item">
                    <strong>Source:</strong>
                    <span>{satelliteData.prediction.satellite_source}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {!satelliteData.prediction?.flood_mask && satelliteData.prediction && (
            <div className="satellite-info">
              <p>
                <strong>Note:</strong> L'analyse d'image a été effectuée mais aucune image n'est disponible pour l'affichage.
              </p>
              <p>
                Zone analysée: {satelliteData.prediction.flood_percentage?.toFixed(1) || 0}%
              </p>
            </div>
          )}
        </div>
      )}

      {!firstPrediction && !satelliteData && (
        <div className="satellite-placeholder">
          <p>Effectuez d'abord une prédiction pour analyser les images satellite</p>
        </div>
      )}
    </div>
  );
};

export default SatelliteView;

