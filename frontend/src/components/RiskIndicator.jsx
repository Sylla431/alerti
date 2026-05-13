import React from 'react';
import './RiskIndicator.css';

const RiskIndicator = ({ probability, riskLevel, size = 'medium', showLabel = true, animated = true }) => {
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

  const getRiskGradient = (risk) => {
    const gradients = {
      critical: 'linear-gradient(135deg, #F44336 0%, #D32F2F 100%)',
      high: 'linear-gradient(135deg, #FF9800 0%, #F57C00 100%)',
      medium: 'linear-gradient(135deg, #FFC107 0%, #FFA000 100%)',
      low: 'linear-gradient(135deg, #4CAF50 0%, #388E3C 100%)',
      none: 'linear-gradient(135deg, #9E9E9E 0%, #616161 100%)'
    };
    return gradients[risk] || '#757575';
  };

  const getWeatherIcon = (risk) => {
    const icons = {
      critical: '🌊',
      high: '⛈️',
      medium: '🌧️',
      low: '☁️',
      none: '☀️'
    };
    return icons[risk] || '☀️';
  };

  const sizeClasses = {
    small: 'risk-indicator-small',
    medium: 'risk-indicator-medium',
    large: 'risk-indicator-large'
  };

  const percentage = Math.round(probability * 100);
  const color = getRiskColor(riskLevel);
  const gradient = getRiskGradient(riskLevel);
  const icon = getWeatherIcon(riskLevel);

  // Calculate stroke-dasharray for circular progress
  const radius = size === 'small' ? 30 : size === 'large' ? 50 : 40;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;

  return (
    <div className={`risk-indicator ${sizeClasses[size]}`}>
      <div className="risk-indicator-container">
        {/* Circular Gauge */}
        <div className="circular-gauge">
          <svg className="gauge-svg" width={radius * 2 + 20} height={radius * 2 + 20}>
            {/* Background circle */}
            <circle
              cx={radius + 10}
              cy={radius + 10}
              r={radius}
              fill="none"
              stroke="#E0E0E0"
              strokeWidth="8"
            />
            {/* Progress circle */}
            <circle
              cx={radius + 10}
              cy={radius + 10}
              r={radius}
              fill="none"
              stroke={color}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              className={animated ? 'gauge-progress-animated' : ''}
              style={{
                transform: 'rotate(-90deg)',
                transformOrigin: `${radius + 10}px ${radius + 10}px`,
                transition: animated ? 'stroke-dashoffset 1s ease-in-out' : 'none'
              }}
            />
          </svg>
          <div className="gauge-content">
            <div className="gauge-icon">{icon}</div>
            <div className="gauge-percentage">{percentage}%</div>
          </div>
        </div>

        {/* Horizontal Progress Bar */}
        <div className="progress-bar-container">
          <div className="progress-bar-background">
            <div
              className="progress-bar-fill"
              style={{
                width: `${percentage}%`,
                background: gradient,
                transition: animated ? 'width 1s ease-in-out' : 'none'
              }}
            >
              <div className="progress-bar-wave" style={{ background: gradient }}></div>
            </div>
          </div>
          {showLabel && (
            <div className="risk-label" style={{ color }}>
              {riskLevel.toUpperCase()}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RiskIndicator;

