import React from 'react';
import { BarChart, Globe, Shield, Server, Network } from 'lucide-react';

interface DatasetInsights {
  top_ports: Array<{ [key: string]: number }>;
  top_protocols: Array<{ [key: string]: number }>;
  top_software: Array<{ [key: string]: number }>;
  top_asns: Array<{ [key: string]: number }>;
  countries: Array<{ [key: string]: number }>;
}

interface InsightsPanelProps {
  insights: DatasetInsights;
  totalHosts: number;
}

const InsightsPanel: React.FC<InsightsPanelProps> = ({ insights, totalHosts }) => {
  const renderTopItems = (items: Array<{ [key: string]: number }>, title: string, icon: React.ReactNode) => (
    <div style={{
      backgroundColor: 'white',
      padding: '1rem',
      borderRadius: '8px',
      border: '1px solid #e5e5e5'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
        {icon}
        <h3 style={{ margin: 0, color: '#333' }}>{title}</h3>
      </div>
      <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
        {items.slice(0, 10).map((item, index) => {
          const [key, value] = Object.entries(item)[0];
          return (
            <div key={index} style={{
              display: 'flex',
              justifyContent: 'space-between',
              padding: '0.25rem 0',
              borderBottom: index < items.length - 1 ? '1px solid #f5f5f5' : 'none'
            }}>
              <span style={{ color: '#333' }}>{key}</span>
              <span style={{ 
                color: '#666', 
                backgroundColor: '#f5f5f5', 
                padding: '0.1rem 0.5rem', 
                borderRadius: '12px', 
                fontSize: '0.875rem' 
              }}>
                {value}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );

  return (
    <div style={{ marginBottom: '2rem' }}>
      <div style={{
        backgroundColor: 'white',
        padding: '1rem 1.5rem',
        borderRadius: '8px',
        border: '1px solid #e5e5e5',
        marginBottom: '1rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <BarChart size={24} color="#007bff" />
          <h2 style={{ margin: 0, color: '#333' }}>Dataset Insights</h2>
        </div>
        <p style={{ margin: 0, color: '#666' }}>
          Analysis of {totalHosts} hosts in the dataset
        </p>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '1rem'
      }}>
        {renderTopItems(insights.top_ports, 'Top Ports', <Server size={20} color="#007bff" />)}
        {renderTopItems(insights.top_protocols, 'Top Protocols', <Network size={20} color="#28a745" />)}
        {renderTopItems(insights.top_software, 'Top Software', <Shield size={20} color="#dc3545" />)}
        {renderTopItems(insights.top_asns, 'Top ASNs', <Network size={20} color="#6f42c1" />)}
        {renderTopItems(insights.countries, 'Countries', <Globe size={20} color="#fd7e14" />)}
      </div>
    </div>
  );
};

export default InsightsPanel;