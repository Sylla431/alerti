"""
Utils package for Flood Forecast System
"""
from .config import (
    AFRICAN_LOCATIONS,
    ALERT_THRESHOLDS,
    MODEL_DIR,
    LSTM_SEQUENCE_LENGTH,
    LSTM_FORECAST_DAYS,
    CNN_INPUT_SIZE
)

__all__ = [
    'AFRICAN_LOCATIONS',
    'ALERT_THRESHOLDS',
    'MODEL_DIR',
    'LSTM_SEQUENCE_LENGTH',
    'LSTM_FORECAST_DAYS',
    'CNN_INPUT_SIZE'
]

