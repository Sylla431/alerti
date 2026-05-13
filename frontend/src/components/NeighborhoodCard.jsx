import React, { useState } from 'react';
import RiskIndicator from './RiskIndicator';
import NeighborhoodDetailModal from './NeighborhoodDetailModal';
import './NeighborhoodCard.css';

const NeighborhoodCard = ({ 
  neighborhood, 
  prediction, 
  onClick,
  city 
}) => {
  const [showModal, setShowModal] = useState(false);
  const riskLevel = prediction?.risk_level || prediction?.alert_level || 'none';
  const probability = prediction?.flood_probability || 0;
  const commune = prediction?.commune;
  const sequenceDate = prediction?.sequence_end_date;
  const coordinates = neighborhood?.coordinates || prediction?.coordinates;

  const getRiskBadgeClass = (risk) => {
    return `risk-badge risk-badge-${risk}`;
  };

  const handleCardClick = () => {
    if (onClick) {
      onClick(neighborhood, prediction);
    }
  };

  const handleDetailsClick = (e) => {
    e.stopPropagation();
    setShowModal(true);
  };

  return (
    <div 
      className="neighborhood-card"
      onClick={handleCardClick}
    >
      <div className="card-header">
        <div className="card-title-section">
          <h3 className="neighborhood-name">{neighborhood?.name || 'Quartier'}</h3>
          {city && (
            <span className="neighborhood-city">{city}</span>
          )}
        </div>
        <div className={getRiskBadgeClass(riskLevel)}>
          {riskLevel.toUpperCase()}
        </div>
      </div>

      <div className="card-body">
        <div className="risk-indicator-wrapper">
          <RiskIndicator 
            probability={probability}
            riskLevel={riskLevel}
            size="small"
            showLabel={false}
            animated={true}
          />
        </div>

        {coordinates && (
          <div className="mini-map-container">
            <div className="mini-map">
              <div className="map-marker" style={{ 
                left: '50%', 
                top: '50%',
                transform: 'translate(-50%, -50%)'
              }}>
                📍
              </div>
            </div>
            <div className="coordinates">
              {coordinates.lat.toFixed(4)}, {coordinates.lon.toFixed(4)}
            </div>
          </div>
        )}

        {prediction && (
          <div className="prediction-details">
            {commune && (
              <div className="detail-item">
                <span className="detail-label">Commune:</span>
                <span className="detail-value">{commune}</span>
              </div>
            )}
            <div className="detail-item">
              <span className="detail-label">Probabilité:</span>
              <span className="detail-value">{(probability * 100).toFixed(1)}%</span>
            </div>
            {prediction.confidence && (
              <div className="detail-item">
                <span className="detail-label">Confiance:</span>
                <span className="detail-value">{(prediction.confidence * 100).toFixed(1)}%</span>
              </div>
            )}
            {prediction.timestamp && (
              <div className="detail-item">
                <span className="detail-label">Mise à jour:</span>
                <span className="detail-value">
                  {new Date(prediction.timestamp).toLocaleTimeString('fr-FR', { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                </span>
              </div>
            )}
            {sequenceDate && (
              <div className="detail-item">
                <span className="detail-label">Séquence:</span>
                <span className="detail-value">
                  {new Date(sequenceDate).toLocaleDateString('fr-FR')}
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="card-footer">
        <button className="details-button" onClick={handleDetailsClick}>
          Voir les détails →
        </button>
      </div>

      {/* Hover effect overlay */}
      <div className="card-overlay"></div>

      {/* Detail Modal */}
      {showModal && (
        <NeighborhoodDetailModal
          neighborhood={neighborhood}
          prediction={prediction}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  );
};

export default NeighborhoodCard;

