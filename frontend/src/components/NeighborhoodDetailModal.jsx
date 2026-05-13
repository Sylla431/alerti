import React from 'react';
import { createPortal } from 'react-dom';
import RiskIndicator from './RiskIndicator';
import './NeighborhoodDetailModal.css';

const NeighborhoodDetailModal = ({ neighborhood, prediction, onClose }) => {
  if (!neighborhood && !prediction) return null;

  const riskLevel = prediction?.risk_level || prediction?.alert_level || 'none';
  const probability = prediction?.flood_probability || 0;
  const context = prediction?.context || {};
  const staticFeatures = context?.static_features || {};
  const riskFactors = context?.risk_factors || {};
  const zonesRisque = context?.zones_risque || [];

  const getRiskColor = (level) => {
    const colors = {
      critical: '#F44336',
      high: '#FF9800',
      medium: '#FFC107',
      low: '#4CAF50',
      none: '#9E9E9E'
    };
    return colors[level] || '#757575';
  };

  const formatValue = (value, unit = '') => {
    if (value === null || value === undefined) return 'N/A';
    if (typeof value === 'number') {
      if (isNaN(value)) return 'N/A';
      return `${value.toFixed(2)}${unit ? ` ${unit}` : ''}`;
    }
    return String(value) || 'N/A';
  };

  // Safe coordinate access
  const getCoordinates = () => {
    if (neighborhood?.coordinates?.lat && neighborhood?.coordinates?.lon) {
      return neighborhood.coordinates;
    }
    if (prediction?.coordinates?.lat && prediction?.coordinates?.lon) {
      return prediction.coordinates;
    }
    return null;
  };

  const coordinates = getCoordinates();

  const modalContent = (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>📍 {neighborhood?.name || 'Quartier'}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          {/* Risk Summary */}
          <div className="modal-section risk-summary">
            <h3>Niveau de Risque</h3>
            <div className="risk-summary-content">
              <RiskIndicator 
                probability={probability}
                riskLevel={riskLevel}
                size="large"
                showLabel={true}
                animated={true}
              />
              <div className="risk-info">
                <div className="risk-badge-large" style={{ backgroundColor: getRiskColor(riskLevel) }}>
                  {riskLevel.toUpperCase()}
                </div>
                <p className="risk-probability">
                  Probabilité: <strong>{(probability * 100).toFixed(1)}%</strong>
                </p>
                {prediction?.sequence_end_date && (
                  <p className="risk-date">
                    Dernière mise à jour: {new Date(prediction.sequence_end_date).toLocaleDateString('fr-FR')}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Topography Factors */}
          {staticFeatures.elevation !== undefined && (
            <div className="modal-section">
              <h3>🏔️ Topographie</h3>
              <div className="factors-grid">
                <div className="factor-item">
                  <span className="factor-label">Élévation:</span>
                  <span className="factor-value">{formatValue(staticFeatures.elevation, 'm')}</span>
                </div>
                <div className="factor-item">
                  <span className="factor-label">Pente:</span>
                  <span className="factor-value">{formatValue(staticFeatures.slope, '°')}</span>
                </div>
                <div className="factor-item">
                  <span className="factor-label">Distance au fleuve:</span>
                  <span className="factor-value">{formatValue(staticFeatures.distance_to_river, 'm')}</span>
                </div>
                <div className="factor-item">
                  <span className="factor-label">Plaine inondable:</span>
                  <span className="factor-value">
                    {staticFeatures.in_flood_plain ? '⚠️ Oui' : '✅ Non'}
                  </span>
                </div>
                {riskFactors.topography_risk !== undefined && (
                  <div className="factor-item risk-score">
                    <span className="factor-label">Score risque topographique:</span>
                    <span className="factor-value">{(riskFactors.topography_risk * 100).toFixed(0)}%</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Drainage Infrastructure */}
          {staticFeatures.drainage_density !== undefined && (
            <div className="modal-section">
              <h3>🏗️ Infrastructure de Drainage</h3>
              <div className="factors-grid">
                <div className="factor-item">
                  <span className="factor-label">Densité drainage:</span>
                  <span className="factor-value">{formatValue(staticFeatures.drainage_density, 'km/km²')}</span>
                </div>
                <div className="factor-item">
                  <span className="factor-label">État drainage:</span>
                  <span className="factor-value">
                    {staticFeatures.drainage_state ? `${staticFeatures.drainage_state}/5` : 'N/A'}
                  </span>
                </div>
                <div className="factor-item">
                  <span className="factor-label">Couverture:</span>
                  <span className="factor-value">{formatValue(staticFeatures.drainage_coverage, '%')}</span>
                </div>
                <div className="factor-item">
                  <span className="factor-label">Canaux bouchés:</span>
                  <span className="factor-value">{formatValue(staticFeatures.blocked_drainage_pct, '%')}</span>
                </div>
                {riskFactors.drainage_risk !== undefined && (
                  <div className="factor-item risk-score">
                    <span className="factor-label">Score risque drainage:</span>
                    <span className="factor-value">{(riskFactors.drainage_risk * 100).toFixed(0)}%</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Urbanization */}
          {staticFeatures.impermeable_surface !== undefined && (
            <div className="modal-section">
              <h3>Urbanisation</h3>
              <div className="factors-grid">
                <div className="factor-item">
                  <span className="factor-label">Surface imperméable:</span>
                  <span className="factor-value">{formatValue(staticFeatures.impermeable_surface, '%')}</span>
                </div>
                <div className="factor-item">
                  <span className="factor-label">Densité bâtiments:</span>
                  <span className="factor-value">{formatValue(staticFeatures.building_density, '%')}</span>
                </div>
                <div className="factor-item">
                  <span className="factor-label">Densité population:</span>
                  <span className="factor-value">{formatValue(staticFeatures.population_density, 'hab/km²')}</span>
                </div>
                {riskFactors.urbanization_risk !== undefined && (
                  <div className="factor-item risk-score">
                    <span className="factor-label">Score risque urbanisation:</span>
                    <span className="factor-value">{(riskFactors.urbanization_risk * 100).toFixed(0)}%</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Vulnerability */}
          {staticFeatures.informal_settlement_pct !== undefined && (
            <div className="modal-section">
              <h3>Vulnérabilité</h3>
              <div className="factors-grid">
                <div className="factor-item">
                  <span className="factor-label">Habitat précaire:</span>
                  <span className="factor-value">{formatValue(staticFeatures.informal_settlement_pct, '%')}</span>
                </div>
                <div className="factor-item">
                  <span className="factor-label">Indice pauvreté:</span>
                  <span className="factor-value">{formatValue(staticFeatures.poverty_index, '/100')}</span>
                </div>
                <div className="factor-item">
                  <span className="factor-label">Préparation inondation:</span>
                  <span className="factor-value">
                    {staticFeatures.flood_preparedness ? `${staticFeatures.flood_preparedness}/5` : 'N/A'}
                  </span>
                </div>
                {riskFactors.vulnerability_risk !== undefined && (
                  <div className="factor-item risk-score">
                    <span className="factor-label">Score vulnérabilité:</span>
                    <span className="factor-value">{(riskFactors.vulnerability_risk * 100).toFixed(0)}%</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Risk Zones */}
          {zonesRisque.length > 0 && (
            <div className="modal-section">
              <h3>Zones à Risque Identifiées</h3>
              <ul className="zones-list">
                {zonesRisque.map((zone, index) => (
                  <li key={index}>⚠️ {zone}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Recommendations */}
          {prediction?.recommendations && prediction.recommendations.length > 0 && (
            <div className="modal-section recommendations">
              <h3>Recommandations</h3>
              <ul className="recommendations-list">
                {prediction.recommendations.map((rec, index) => (
                  <li key={index}>{rec}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Coordinates */}
          {coordinates && (
            <div className="modal-section">
              <h3>Coordonnées</h3>
              <p className="coordinates-text">
                {coordinates.lat.toFixed(6)}, {coordinates.lon.toFixed(6)}
              </p>
            </div>
          )}

          {/* Fallback if no detailed data */}
          {Object.keys(staticFeatures).length === 0 && (
            <div className="modal-section">
              <p style={{ color: '#666', fontStyle: 'italic', textAlign: 'center', padding: '20px' }}>
                Les données détaillées ne sont pas encore disponibles pour ce quartier.
                <br />
                <small>Probabilité d'inondation: {(probability * 100).toFixed(1)}%</small>
              </p>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>Fermer</button>
          {coordinates && (
            <button 
              className="btn-primary"
              onClick={() => {
                const url = `https://www.google.com/maps?q=${coordinates.lat},${coordinates.lon}`;
                window.open(url, '_blank');
              }}
            >
              Voir sur Google Maps
            </button>
          )}
        </div>
      </div>
    </div>
  );

  // Render modal using portal to body (outside card hierarchy)
  return createPortal(modalContent, document.body);
};

export default NeighborhoodDetailModal;

