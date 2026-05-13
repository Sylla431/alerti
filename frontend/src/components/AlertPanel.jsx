import React, { useState, useEffect } from 'react';
import './AlertPanel.css';

const AlertPanel = ({ alerts, showNeighborhoodBadge = true }) => {
  const [newAlerts, setNewAlerts] = useState([]);

  useEffect(() => {
    // Track new alerts for toast notifications
    if (alerts.length > 0) {
      const criticalAlerts = alerts.filter(a => a.alert_level === 'critical');
      if (criticalAlerts.length > 0) {
        setNewAlerts(criticalAlerts);
        // Show toast notification for critical alerts
        criticalAlerts.forEach(alert => {
          if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(`Alerte Critique: ${alert.location}`, {
              body: `Probabilité: ${(alert.flood_probability * 100).toFixed(1)}%`,
              icon: '/favicon.ico',
              tag: `alert-${alert.id}`
            });
          }
        });
      }
    }
  }, [alerts]);
  const getAlertIcon = (level) => {
    const icons = {
      critical: '🚨',
      high: '⚠️',
      medium: '⚠️',
      low: 'ℹ️',
      none: '✅'
    };
    return icons[level] || 'ℹ️';
  };

  const getAlertClass = (level) => {
    return `alert-item alert-${level}`;
  };

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

  // Request notification permission
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  // Extract neighborhood from location if it contains a comma
  const getNeighborhood = (location) => {
    if (!location) return null;
    const parts = location.split(',');
    return parts.length > 1 ? parts[0].trim() : null;
  };

  return (
    <div className="alert-panel">
      <div className="alert-panel-header">
        <h2>🚨 Alertes Actives</h2>
        {alerts.length > 0 && (
          <span className="alert-badge">{alerts.length}</span>
        )}
      </div>
      {alerts.length === 0 ? (
        <p className="no-alerts">Aucune alerte active</p>
      ) : (
        <div className="alerts-list">
          {alerts.map((alert) => {
            const neighborhood = getNeighborhood(alert.location);
            return (
              <div key={alert.id} className={getAlertClass(alert.alert_level)}>
                <div className="alert-header">
                  <span className="alert-icon">{getAlertIcon(alert.alert_level)}</span>
                  <div className="alert-title">
                    <span className="alert-location">{alert.location}</span>
                    {showNeighborhoodBadge && neighborhood && (
                      <span className="neighborhood-badge">🏘️ {neighborhood}</span>
                    )}
                    <span 
                      className="alert-level"
                      style={{ color: getRiskColor(alert.alert_level) }}
                    >
                      {alert.alert_level.toUpperCase()}
                    </span>
                  </div>
                </div>
              
              <div className="alert-body">
                <p className="alert-probability">
                  Probabilité d'inondation: {(alert.flood_probability * 100).toFixed(1)}%
                </p>
                <small className="alert-time">
                  {new Date(alert.timestamp).toLocaleString('fr-FR')}
                </small>
                
                {alert.coordinates && (
                  <div className="alert-coordinates">
                    📍 {alert.coordinates.lat?.toFixed(4)}, {alert.coordinates.lon?.toFixed(4)}
                  </div>
                )}
              </div>

              {alert.recommendations && alert.recommendations.length > 0 && (
                <div className="alert-recommendations">
                  <strong>Actions recommandées:</strong>
                  <ul>
                    {alert.recommendations.slice(0, 3).map((rec, i) => (
                      <li key={i}>{rec}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          );
        })}
        </div>
      )}
    </div>
  );
};

export default AlertPanel;

