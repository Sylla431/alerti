import React from 'react';
import './CommuneStats.css';

const CommuneStats = ({ predictions, neighborhoods }) => {
  // Group by commune
  const communeData = React.useMemo(() => {
    const communeMap = {};
    
    neighborhoods?.forEach(n => {
      const pred = predictions[n.name];
      const commune = pred?.commune || n.commune;
      if (!commune) return;

      if (!communeMap[commune]) {
        communeMap[commune] = {
          name: commune,
          neighborhoods: [],
          totalRisk: 0,
          maxRisk: 0,
          riskCounts: { critical: 0, high: 0, medium: 0, low: 0, none: 0 }
        };
      }

      const risk = pred?.risk_level || pred?.alert_level || 'none';
      const probability = pred?.flood_probability || 0;

      communeMap[commune].neighborhoods.push({
        name: n.name,
        risk,
        probability
      });

      communeMap[commune].totalRisk += probability;
      communeMap[commune].maxRisk = Math.max(communeMap[commune].maxRisk, probability);
      if (communeMap[commune].riskCounts.hasOwnProperty(risk)) {
        communeMap[commune].riskCounts[risk]++;
      }
    });

    // Calculate averages
    Object.values(communeMap).forEach(commune => {
      commune.avgRisk = commune.neighborhoods.length > 0 
        ? commune.totalRisk / commune.neighborhoods.length 
        : 0;
    });

    return Object.values(communeMap).sort((a, b) => b.maxRisk - a.maxRisk);
  }, [predictions, neighborhoods]);

  if (communeData.length === 0) {
    return (
      <div className="commune-stats-empty">
        <p>📊 Aucune statistique par commune disponible</p>
      </div>
    );
  }

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
    <div className="commune-stats-container">
      <h3>Statistiques par Commune</h3>
      <div className="commune-stats-grid">
        {communeData.map(commune => (
          <div key={commune.name} className="commune-stat-card">
            <div className="commune-header">
              <h4>{commune.name}</h4>
              <div className="commune-risk-badge" style={{
                backgroundColor: commune.maxRisk >= 0.8 ? '#F44336' :
                                 commune.maxRisk >= 0.6 ? '#FF9800' :
                                 commune.maxRisk >= 0.4 ? '#FFC107' : '#4CAF50'
              }}>
                {commune.maxRisk >= 0.8 ? 'CRITIQUE' :
                 commune.maxRisk >= 0.6 ? 'ÉLEVÉ' :
                 commune.maxRisk >= 0.4 ? 'MOYEN' : 'FAIBLE'}
              </div>
            </div>

            <div className="commune-metrics">
              <div className="metric-item">
                <span className="metric-label">Quartiers:</span>
                <span className="metric-value">{commune.neighborhoods.length}</span>
              </div>
              <div className="metric-item">
                <span className="metric-label">Risque moyen:</span>
                <span className="metric-value">{(commune.avgRisk * 100).toFixed(1)}%</span>
              </div>
              <div className="metric-item">
                <span className="metric-label">Risque max:</span>
                <span className="metric-value">{(commune.maxRisk * 100).toFixed(1)}%</span>
              </div>
            </div>

            <div className="commune-risk-breakdown">
              <div className="risk-bar">
                <div className="risk-segment critical" style={{
                  width: `${(commune.riskCounts.critical / commune.neighborhoods.length) * 100}%`,
                  backgroundColor: '#F44336'
                }}></div>
                <div className="risk-segment high" style={{
                  width: `${(commune.riskCounts.high / commune.neighborhoods.length) * 100}%`,
                  backgroundColor: '#FF9800'
                }}></div>
                <div className="risk-segment medium" style={{
                  width: `${(commune.riskCounts.medium / commune.neighborhoods.length) * 100}%`,
                  backgroundColor: '#FFC107'
                }}></div>
                <div className="risk-segment low" style={{
                  width: `${(commune.riskCounts.low / commune.neighborhoods.length) * 100}%`,
                  backgroundColor: '#4CAF50'
                }}></div>
              </div>
              <div className="risk-legend">
                <span>🔴 {commune.riskCounts.critical}</span>
                <span>🟠 {commune.riskCounts.high}</span>
                <span>🟡 {commune.riskCounts.medium}</span>
                <span>🟢 {commune.riskCounts.low}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CommuneStats;

