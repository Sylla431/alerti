import React, { useState, useMemo } from 'react';
import NeighborhoodCard from './NeighborhoodCard';
import './NeighborhoodGrid.css';

const NeighborhoodGrid = ({ 
  neighborhoods, 
  predictions = {}, 
  onNeighborhoodClick,
  city 
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const [communeFilter, setCommuneFilter] = useState('all');
  const [sortBy, setSortBy] = useState('name');

  // Filter and sort neighborhoods
  const filteredNeighborhoods = useMemo(() => {
    let filtered = neighborhoods || [];

    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter(n => 
        n.name.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Filter by risk level
    if (riskFilter !== 'all') {
      filtered = filtered.filter(n => {
        const pred = predictions[n.name];
        const risk = pred?.risk_level || pred?.alert_level || 'none';
        return risk === riskFilter;
      });
    }

    // Filter by commune
    if (communeFilter !== 'all') {
      filtered = filtered.filter(n => {
        const pred = predictions[n.name];
        const commune = pred?.commune || n.commune;
        return commune === communeFilter;
      });
    }

    // Sort
    filtered = [...filtered].sort((a, b) => {
      const predA = predictions[a.name];
      const predB = predictions[b.name];
      
      if (sortBy === 'name') {
        return a.name.localeCompare(b.name);
      } else if (sortBy === 'probability') {
        const probA = predA?.flood_probability || 0;
        const probB = predB?.flood_probability || 0;
        return probB - probA; // Descending
      } else if (sortBy === 'risk') {
        const riskOrder = { critical: 4, high: 3, medium: 2, low: 1, none: 0 };
        const riskA = riskOrder[predA?.risk_level || predA?.alert_level || 'none'] || 0;
        const riskB = riskOrder[predB?.risk_level || predB?.alert_level || 'none'] || 0;
        return riskB - riskA; // Descending
      }
      return 0;
    });

    return filtered;
  }, [neighborhoods, predictions, searchTerm, riskFilter, communeFilter, sortBy]);

  const getRiskCounts = () => {
    const counts = { all: 0, critical: 0, high: 0, medium: 0, low: 0, none: 0 };
    neighborhoods?.forEach(n => {
      counts.all++;
      const pred = predictions[n.name];
      const risk = pred?.risk_level || pred?.alert_level || 'none';
      if (counts.hasOwnProperty(risk)) {
        counts[risk]++;
      }
    });
    return counts;
  };

  const riskCounts = getRiskCounts();

  // Get unique communes
  const communes = useMemo(() => {
    const communeSet = new Set();
    neighborhoods?.forEach(n => {
      const pred = predictions[n.name];
      const commune = pred?.commune || n.commune;
      if (commune) communeSet.add(commune);
    });
    return Array.from(communeSet).sort();
  }, [neighborhoods, predictions]);

  // Export function
  const exportToCSV = () => {
    const headers = ['Quartier', 'Commune', 'Probabilité (%)', 'Niveau de risque', 'Date mise à jour'];
    const rows = filteredNeighborhoods.map(n => {
      const pred = predictions[n.name];
      return [
        n.name,
        pred?.commune || n.commune || 'N/A',
        ((pred?.flood_probability || 0) * 100).toFixed(1),
        pred?.risk_level || pred?.alert_level || 'none',
        pred?.timestamp ? new Date(pred.timestamp).toLocaleDateString('fr-FR') : 'N/A'
      ];
    });

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `zones_risque_${city || 'mali'}_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="neighborhood-grid-container">
      <div className="grid-header">
        <h2>Quartiers de {city || 'Mali'}</h2>
        <div className="grid-stats">
          <span className="stat-item">
            Total: <strong>{neighborhoods?.length || 0}</strong>
          </span>
          <span className="stat-item">
            Affichés: <strong>{filteredNeighborhoods.length}</strong>
          </span>
          <button className="export-button" onClick={exportToCSV} title="Exporter en CSV">
            📥 Exporter CSV
          </button>
        </div>
      </div>

      <div className="grid-controls">
        <div className="search-box">
          <input
            type="text"
            placeholder="🔍 Rechercher un quartier..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="filter-group">
          <label>Filtrer par risque:</label>
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="filter-select"
          >
            <option value="all">Tous ({riskCounts.all})</option>
            <option value="critical">Critique ({riskCounts.critical})</option>
            <option value="high">Élevé ({riskCounts.high})</option>
            <option value="medium">Moyen ({riskCounts.medium})</option>
            <option value="low">Faible ({riskCounts.low})</option>
            <option value="none">Aucun ({riskCounts.none})</option>
          </select>
        </div>

        {communes.length > 0 && (
          <div className="filter-group">
            <label>Filtrer par commune:</label>
            <select
              value={communeFilter}
              onChange={(e) => setCommuneFilter(e.target.value)}
              className="filter-select"
            >
              <option value="all">Toutes les communes</option>
              {communes.map(commune => (
                <option key={commune} value={commune}>{commune}</option>
              ))}
            </select>
          </div>
        )}

        <div className="sort-group">
          <label>Trier par:</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="sort-select"
          >
            <option value="name">Nom</option>
            <option value="probability">Probabilité</option>
            <option value="risk">Niveau de risque</option>
          </select>
        </div>
      </div>

      {filteredNeighborhoods.length === 0 ? (
        <div className="no-results">
          <p>🔍 Aucun quartier trouvé</p>
          <p className="no-results-hint">
            {searchTerm ? 'Essayez de modifier votre recherche' : 'Aucun quartier disponible'}
          </p>
        </div>
      ) : (
        <div className="neighborhood-grid">
          {filteredNeighborhoods.map((neighborhood) => (
            <NeighborhoodCard
              key={neighborhood.name}
              neighborhood={neighborhood}
              prediction={predictions[neighborhood.name]}
              onClick={onNeighborhoodClick}
              city={city}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default NeighborhoodGrid;

