import React, { useEffect } from 'react';
import './ToastNotification.css';

const ToastNotification = ({ message, type = 'info', onClose, duration = 5000 }) => {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        if (onClose) onClose();
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);

  const getIcon = () => {
    switch (type) {
      case 'critical':
      case 'error':
        return '🚨';
      case 'warning':
        return '⚠️';
      case 'success':
        return '✅';
      default:
        return 'ℹ️';
    }
  };

  const getTypeClass = () => {
    return `toast toast-${type}`;
  };

  return (
    <div className={getTypeClass()}>
      <div className="toast-icon">{getIcon()}</div>
      <div className="toast-message">{message}</div>
      {onClose && (
        <button className="toast-close" onClick={onClose}>×</button>
      )}
    </div>
  );
};

export default ToastNotification;

