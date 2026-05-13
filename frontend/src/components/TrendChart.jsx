import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './TrendChart.css';

const TrendChart = ({ data, neighborhoods = [] }) => {
  // Transform data for Recharts
  const chartData = React.useMemo(() => {
    if (!data || !Array.isArray(data)) return [];

    // Group by date
    const dateMap = {};
    
    data.forEach(item => {
      const date = item.date || item.timestamp?.split('T')[0];
      if (!date) return;

      if (!dateMap[date]) {
        dateMap[date] = { date };
      }

      const neighborhood = item.neighborhood || 'Unknown';
      dateMap[date][neighborhood] = (item.probability || item.flood_probability || 0) * 100;
    });

    return Object.values(dateMap).sort((a, b) => 
      new Date(a.date) - new Date(b.date)
    );
  }, [data]);

  const getNeighborhoodColor = (index) => {
    const colors = [
      '#2196F3', '#F44336', '#FF9800', '#4CAF50', 
      '#9C27B0', '#00BCD4', '#FFC107', '#795548'
    ];
    return colors[index % colors.length];
  };

  if (chartData.length === 0) {
    return (
      <div className="trend-chart-empty">
        <p>📊 Aucune donnée de tendance disponible</p>
        <p className="empty-hint">Les données de prévision apparaîtront ici</p>
      </div>
    );
  }

  return (
    <div className="trend-chart-container">
      <div className="chart-header">
        <h3>📈 Évolution des Risques</h3>
        <p className="chart-subtitle">Prévisions sur 7 jours</p>
      </div>
      
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
          <XAxis 
            dataKey="date" 
            stroke="#666"
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => {
              const date = new Date(value);
              return `${date.getDate()}/${date.getMonth() + 1}`;
            }}
          />
          <YAxis 
            stroke="#666"
            tick={{ fontSize: 12 }}
            domain={[0, 100]}
            tickFormatter={(value) => `${value}%`}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: 'white', 
              border: '1px solid #E0E0E0',
              borderRadius: '8px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
            }}
            formatter={(value) => [`${value.toFixed(1)}%`, 'Probabilité']}
            labelFormatter={(label) => `Date: ${new Date(label).toLocaleDateString('fr-FR')}`}
          />
          <Legend 
            wrapperStyle={{ paddingTop: '20px' }}
            iconType="line"
          />
          {neighborhoods.map((neighborhood, index) => (
            <Line
              key={neighborhood}
              type="monotone"
              dataKey={neighborhood}
              stroke={getNeighborhoodColor(index)}
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
              name={neighborhood}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>

      {neighborhoods.length === 0 && (
        <div className="chart-info">
          <p>Sélectionnez des quartiers pour comparer leurs tendances</p>
        </div>
      )}
    </div>
  );
};

export default TrendChart;

