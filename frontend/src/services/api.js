/**
 * API Client for Flood Forecast System
 */
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },

  // Bamako LSTM prediction (commune/quartier)
  predictBamako: ({ commune, neighborhood, targetDate } = {}) => {
    return api.post('/api/bamako/predict', {
      commune,
      neighborhood,
      target_date: targetDate,
    });
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error.response?.data || error.message);
  }
);

// API methods
export const floodAPI = {
  // Get prediction
  predict: (location, lat, lon, country) => {
    return api.post('/api/predict', {
      location,
      latitude: lat,
      longitude: lon,
      country,
    });
  },

  // Get meteo prediction only
  predictMeteo: (location, lat, lon) => {
    return api.post('/api/predict-meteo', {
      location,
      latitude: lat,
      longitude: lon,
    });
  },

  // Get image prediction only
  predictImage: (location, lat, lon, bbox) => {
    return api.post('/api/predict-image', {
      location,
      latitude: lat,
      longitude: lon,
      bbox,
    });
  },

  // Get all alerts
  getAlerts: (country, minRisk) => {
    return api.get('/api/alerts', {
      params: { country, min_risk: minRisk },
    });
  },

  // Get forecast for country
  getForecast: (country) => {
    return api.get(`/api/forecast/${country}`);
  },

  // Get satellite image
  getSatelliteImage: (location, lat, lon, bbox) => {
    return api.get(`/api/satellite-image/${location}`, {
      params: { lat, lon, bbox: bbox?.join(',') },
    });
  },

  // Get list of countries
  getCountries: () => {
    return api.get('/api/countries');
  },

  // Subscribe to alerts
  subscribe: (email, phone, location, country, whatsapp, deviceToken, neighborhood) => {
    return api.post('/api/alert/subscribe', {
      email,
      phone,
      location,
      country,
      whatsapp,
      device_token: deviceToken,
      neighborhood,
    });
  },

  // Mali neighborhoods
  getMaliNeighborhoods: (city = 'bamako') => {
    return api.get('/api/mali/neighborhoods', {
      params: { city },
    });
  },

  // Predict neighborhood
  predictNeighborhood: (neighborhood, city = 'bamako') => {
    return api.post('/api/predict/neighborhood', {
      neighborhood,
      city,
    });
  },

  // Predict commune/neighborhood in Bamako using dedicated LSTM
  predictBamako: ({ commune, neighborhood }) => {
    return api.post('/api/bamako/predict', {
      commune,
      neighborhood,
    });
  },

  // Get neighborhood forecast (GET method)
  getNeighborhoodForecast: (neighborhoodName, city = 'bamako') => {
    return api.get(`/api/mali/neighborhood/${neighborhoodName}/predict`, {
      params: { city },
    });
  },

  // Subscribe to push notifications
  subscribePush: (deviceToken, location, neighborhood) => {
    return api.post('/api/subscribe/push', {
      device_token: deviceToken,
      location,
      neighborhood,
    });
  },
};

export default api;

