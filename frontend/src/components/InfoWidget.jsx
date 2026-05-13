import React, { useState, useEffect } from 'react';
import './InfoWidget.css';

const InfoWidget = ({ 
  type, 
  value, 
  label, 
  icon, 
  trend, 
  subtitle,
  color 
}) => {
  const [animatedValue, setAnimatedValue] = useState(0);

  useEffect(() => {
    if (typeof value === 'number') {
      const duration = 1000;
      const steps = 60;
      const increment = value / steps;
      const stepDuration = duration / steps;
      
      let current = 0;
      const timer = setInterval(() => {
        current += increment;
        if (current >= value) {
          setAnimatedValue(value);
          clearInterval(timer);
        } else {
          setAnimatedValue(Math.floor(current));
        }
      }, stepDuration);

      return () => clearInterval(timer);
    } else {
      setAnimatedValue(value);
    }
  }, [value]);

  const getTrendIcon = (trend) => {
    if (trend > 0) return '📈';
    if (trend < 0) return '📉';
    return '➡️';
  };

  const getTrendColor = (trend) => {
    if (trend > 0) return '#F44336';
    if (trend < 0) return '#4CAF50';
    return '#9E9E9E';
  };

  return (
    <div className={`info-widget info-widget-${type}`} style={{ borderTopColor: color }}>
      <div className="widget-header">
        <div className="widget-icon">{icon}</div>
        <div className="widget-label">{label}</div>
      </div>
      
      <div className="widget-body">
        <div className="widget-value" style={{ color }}>
          {typeof animatedValue === 'number' && type === 'number' 
            ? animatedValue.toLocaleString('fr-FR')
            : animatedValue}
        </div>
        
        {subtitle && (
          <div className="widget-subtitle">{subtitle}</div>
        )}

        {trend !== undefined && trend !== null && (
          <div 
            className="widget-trend"
            style={{ color: getTrendColor(trend) }}
          >
            <span>{getTrendIcon(trend)}</span>
            <span>{Math.abs(trend)}%</span>
          </div>
        )}
      </div>
    </div>
  );
};

// Predefined widget types
export const WidgetTypes = {
  TOTAL_NEIGHBORHOODS: {
    type: 'number',
    icon: '🏘️',
    label: 'Quartiers Surveillés',
    color: '#2196F3'
  },
  ACTIVE_ALERTS: {
    type: 'number',
    icon: '🚨',
    label: 'Alertes Actives',
    color: '#F44336'
  },
  HIGH_RISK: {
    type: 'text',
    icon: '⚠️',
    label: 'Quartier le plus à risque',
    color: '#FF9800'
  },
  WEATHER: {
    type: 'text',
    icon: '🌤️',
    label: 'Conditions Météo',
    color: '#00BCD4'
  }
};

export default InfoWidget;

