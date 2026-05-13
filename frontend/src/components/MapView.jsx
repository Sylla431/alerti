import React, { useEffect, useRef, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, Polygon, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for default marker icons in React-Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const MapView = ({ predictions, alerts, countries, neighborhoods, city }) => {
  const mapRef = useRef(null);

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

  // Default center - adjust based on data
  let defaultCenter = [0, 20];
  let defaultZoom = 4;
  
  // If neighborhoods provided, center on Mali
  if (neighborhoods && neighborhoods.length > 0) {
    defaultCenter = [12.6392, -8.0029]; // Bamako, Mali
    defaultZoom = 11;
  } else if (city === 'Mali' || city === 'Bamako') {
    defaultCenter = [12.6392, -8.0029];
    defaultZoom = 11;
  }

  const [currentZoom, setCurrentZoom] = useState(defaultZoom);

  // Get all locations with coordinates
  const locations = [];

  // Add predictions
  Object.values(predictions).forEach(pred => {
    const coords = pred.coordinates || pred.prediction?.coordinates;
    if (coords && coords.lat && coords.lon) {
      locations.push({
        type: 'prediction',
        lat: coords.lat,
        lon: coords.lon,
        name: pred.location || 'Unknown',
        risk: pred.prediction?.risk_level || pred.risk_level || 'none',
        probability: pred.prediction?.flood_probability || pred.flood_probability || 0,
        timestamp: pred.timestamp
      });
    }
  });

  // Add alerts
  alerts.forEach(alert => {
    if (alert.coordinates && alert.coordinates.lat && alert.coordinates.lon) {
      locations.push({
        type: 'alert',
        lat: alert.coordinates.lat,
        lon: alert.coordinates.lon,
        name: alert.location,
        risk: alert.alert_level,
        probability: alert.flood_probability,
        timestamp: alert.timestamp,
        recommendations: alert.recommendations
      });
    }
  });

  // Add neighborhoods if provided
  if (neighborhoods && Array.isArray(neighborhoods)) {
    neighborhoods.forEach(neighborhood => {
      if (neighborhood.coordinates && neighborhood.coordinates.lat && neighborhood.coordinates.lon) {
        const pred = predictions?.[neighborhood.name];
        locations.push({
          type: 'neighborhood',
          lat: neighborhood.coordinates.lat,
          lon: neighborhood.coordinates.lon,
          name: neighborhood.name,
          risk: pred?.risk_level || pred?.alert_level || 'none',
          probability: pred?.flood_probability || 0,
          city: city,
          polygon: neighborhood.polygon, // Add polygon if available
          bbox: neighborhood.bbox
        });
      }
    });
  }

  // Add countries
  if (countries) {
    Object.entries(countries).forEach(([code, country]) => {
      if (country.coordinates && country.coordinates.lat && country.coordinates.lon) {
        // Check if not already in locations
        const exists = locations.some(
          loc => 
            Math.abs(loc.lat - country.coordinates.lat) < 0.1 &&
            Math.abs(loc.lon - country.coordinates.lon) < 0.1
        );
        
        if (!exists) {
          locations.push({
            type: 'country',
            lat: country.coordinates.lat,
            lon: country.coordinates.lon,
            name: country.name,
            risk: 'none',
            probability: 0
          });
        }
      }
    });
  }

  return (
    <div className="map-view">
      <h2>🗺️ Carte Interactive</h2>
      <div className="map-container">
        <MapContainer
          center={defaultCenter}
          zoom={defaultZoom}
          style={{ height: '400px', width: '100%' }}
          ref={mapRef}
          whenCreated={(mapInstance) => {
            mapRef.current = mapInstance;
            setCurrentZoom(mapInstance.getZoom());
            mapInstance.on('zoomend', () => {
              setCurrentZoom(mapInstance.getZoom());
            });
          }}
        >
          <TileLayer
            // attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          
          {locations.map((loc, index) => {
            const color = getRiskColor(loc.risk);
            
            // For neighborhoods with polygons, show polygon instead of circle
            // Only show if zoom level is appropriate (zoom >= 11 for neighborhoods)
            const showNeighborhoodPolygon = loc.type === 'neighborhood' && loc.polygon && currentZoom >= 11;
            const showNeighborhoodCircle = loc.type === 'neighborhood' && !loc.polygon && currentZoom >= 10;
            
            // Adjust radius based on type and zoom level (for non-polygon elements)
            const zoomFactor = Math.max(1, currentZoom / 10);
            
            let baseRadius;
            if (loc.type === 'alert') {
              baseRadius = 800; // 8km base
            } else if (loc.type === 'neighborhood') {
              baseRadius = 300; // 300m base - fallback if no polygon
            } else if (loc.type === 'prediction') {
              baseRadius = 0; // 4km base
            } else if (loc.type === 'country') {
              baseRadius = 50000; // 50km for countries
            } else {
              baseRadius = 2000; // 2km default
            }
            
            const radius = baseRadius * (1.5 / zoomFactor);
            
            // Determine if element should be visible based on zoom
            const isVisible = 
              (loc.type === 'neighborhood' && (showNeighborhoodPolygon || showNeighborhoodCircle)) ||
              (loc.type === 'alert' && currentZoom >= 8) ||
              (loc.type === 'prediction' && currentZoom >= 9) ||
              (loc.type === 'country' && currentZoom <= 6) ||
              (loc.type !== 'neighborhood' && loc.type !== 'alert' && loc.type !== 'prediction' && loc.type !== 'country');
            
            if (!isVisible) return null;
            
            return (
              <React.Fragment key={`${loc.type}-${index}`}>
                {/* Use Polygon for neighborhoods with polygon data */}
                {showNeighborhoodPolygon ? (
                  <Polygon
                    positions={loc.polygon}
                    pathOptions={{
                      color: color,
                      fillColor: color,
                      fillOpacity: 0.2,
                      weight: 2.5,
                      opacity: 0.8
                    }}
                    eventHandlers={{
                      mouseover: (e) => {
                        const layer = e.target;
                        layer.setStyle({
                          weight: 3.5,
                          fillOpacity: 0.3
                        });
                      },
                      mouseout: (e) => {
                        const layer = e.target;
                        layer.setStyle({
                          weight: 2.5,
                          fillOpacity: 0.2
                        });
                      }
                    }}
                  />
                ) : (
                  /* Use Circle for other types or neighborhoods without polygon */
                  <Circle
                    center={[loc.lat, loc.lon]}
                    radius={radius}
                    pathOptions={{
                      color: color,
                      fillColor: color,
                      fillOpacity: loc.type === 'alert' ? 0.25 : loc.type === 'neighborhood' ? 0.15 : 0.2,
                      weight: loc.type === 'alert' ? 3 : loc.type === 'neighborhood' ? 2 : 2.5,
                      opacity: loc.type === 'alert' ? 0.9 : loc.type === 'neighborhood' ? 0.7 : 0.8,
                      dashArray: loc.type === 'neighborhood' ? '8, 4' : undefined
                    }}
                    ref={(circleRef) => {
                      if (circleRef) {
                        const element = circleRef.getElement();
                        if (element) {
                          element.classList.add('risk-circle', `risk-${loc.risk}`);
                        }
                      }
                    }}
                    eventHandlers={{
                      mouseover: (e) => {
                        const layer = e.target;
                        layer.setStyle({
                          weight: layer.options.weight + 1,
                          fillOpacity: Math.min(0.4, layer.options.fillOpacity + 0.1)
                        });
                      },
                      mouseout: (e) => {
                        const layer = e.target;
                        layer.setStyle({
                          weight: loc.type === 'alert' ? 3 : loc.type === 'neighborhood' ? 2 : 2.5,
                          fillOpacity: loc.type === 'alert' ? 0.25 : loc.type === 'neighborhood' ? 0.15 : 0.2
                        });
                      }
                    }}
                  />
                )}
                <Marker position={[loc.lat, loc.lon]}>
                  <Popup>
                    <div className="map-popup">
                      <h3>{loc.name}</h3>
                      <p>
                        <strong>Type:</strong> {
                          loc.type === 'alert' ? '🚨 Alerte' :
                          loc.type === 'prediction' ? '🔮 Prédiction' :
                          loc.type === 'neighborhood' ? '🏘️ Quartier' :
                          '🌍 Pays'
                        }
                      </p>
                      {loc.risk !== 'none' && (
                        <>
                          <p>
                            <strong>Niveau:</strong> {loc.risk.toUpperCase()}
                          </p>
                          <p>
                            <strong>Probabilité:</strong> {(loc.probability * 100).toFixed(1)}%
                          </p>
                        </>
                      )}
                      {loc.timestamp && (
                        <p>
                          <small>{new Date(loc.timestamp).toLocaleString('fr-FR')}</small>
                        </p>
                      )}
                      {loc.recommendations && loc.recommendations.length > 0 && (
                        <div className="popup-recommendations">
                          <strong>Recommandations:</strong>
                          <ul>
                            {loc.recommendations.slice(0, 2).map((rec, i) => (
                              <li key={i}>{rec}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </Popup>
                </Marker>
              </React.Fragment>
            );
          })}
        </MapContainer>
      </div>
      
      <div className="map-legend">
        <h4>Légende:</h4>
        <div className="legend-items">
          <div className="legend-item">
            <div className="legend-color" style={{ backgroundColor: '#F44336' }}></div>
            <span>Critique</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{ backgroundColor: '#FF9800' }}></div>
            <span>Élevé</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{ backgroundColor: '#FFC107' }}></div>
            <span>Moyen</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{ backgroundColor: '#4CAF50' }}></div>
            <span>Faible</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MapView;

