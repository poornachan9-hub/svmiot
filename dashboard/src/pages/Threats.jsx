/**
 * SecureIoT-X — Threat Monitor Page.
 */
import { useState, useEffect } from 'react';
import { Shield, AlertTriangle, Eye, Ban } from 'lucide-react';
import { BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import api from '../services/api';

const DEMO_THREATS = [
  { id: 'THR-001', device: 'ESP32_003', type: 'DDoS', severity: 'CRITICAL', risk: 91.2, action: 'ISOLATE', status: 'RESOLVED', time: '2 min ago' },
  { id: 'THR-002', device: 'ESP32_007', type: 'Port Scan', severity: 'HIGH', risk: 72.5, action: 'MONITOR', status: 'ACTIVE', time: '5 min ago' },
  { id: 'THR-003', device: 'ESP32_001', type: 'Brute Force', severity: 'MEDIUM', risk: 55.0, action: 'MONITOR', status: 'ACTIVE', time: '12 min ago' },
  { id: 'THR-004', device: 'ESP32_005', type: 'Suspicious Traffic', severity: 'MEDIUM', risk: 42.3, action: 'ALLOW', status: 'VERIFIED', time: '18 min ago' },
  { id: 'THR-005', device: 'ESP32_003', type: 'Spoofing', severity: 'HIGH', risk: 78.1, action: 'ISOLATE', status: 'RESOLVED', time: '25 min ago' },
];

export default function Threats() {
  const [threats, setThreats] = useState([]);

  const severityChart = [
    { name: 'Critical', count: 1, fill: '#ef4444' },
    { name: 'High', count: 2, fill: '#f97316' },
    { name: 'Medium', count: 2, fill: '#f59e0b' },
    { name: 'Low', count: 0, fill: '#10b981' },
  ];

  useEffect(() => {
    api.getThreats().then(data => {
      setThreats(data.length ? data : DEMO_THREATS);
    }).catch(() => setThreats(DEMO_THREATS));
  }, []);

  return (
    <div className="page">
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon red"><Shield size={22} /></div>
          <div className="stat-content">
            <h3>{threats.length}</h3>
            <p>Total Threats</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon yellow"><AlertTriangle size={22} /></div>
          <div className="stat-content">
            <h3>{threats.filter(t => t.status === 'ACTIVE').length}</h3>
            <p>Active Threats</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green"><Eye size={22} /></div>
          <div className="stat-content">
            <h3>{threats.filter(t => t.status === 'RESOLVED').length}</h3>
            <p>Resolved</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon purple"><Ban size={22} /></div>
          <div className="stat-content">
            <h3>{threats.filter(t => t.action === 'ISOLATE').length}</h3>
            <p>Devices Isolated</p>
          </div>
        </div>
      </div>

      <div className="charts-grid">
        <div className="card">
          <div className="card-header">
            <div className="card-title">Threat Log</div>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th><th>Device</th><th>Type</th><th>Severity</th>
                <th>Risk</th><th>Action</th><th>Status</th><th>Time</th>
              </tr>
            </thead>
            <tbody>
              {threats.map((t, i) => (
                <tr key={t.id || i}>
                  <td style={{ fontFamily: 'JetBrains Mono', fontSize: 12, color: 'var(--accent-cyan)' }}>{t.id}</td>
                  <td>{t.device || t.device_id}</td>
                  <td>{t.type || t.attack_type}</td>
                  <td><span className={`severity-badge ${(t.severity||'').toLowerCase()}`}>{t.severity}</span></td>
                  <td style={{ fontWeight: 600, color: t.risk > 70 ? 'var(--accent-red)' : 'var(--text-secondary)' }}>{typeof t.risk === 'number' ? t.risk.toFixed(1) : t.risk_score}</td>
                  <td><span className={`severity-badge ${t.action === 'ISOLATE' ? 'critical' : 'medium'}`}>{t.action}</span></td>
                  <td><span className={`status-badge ${(t.status||'').toLowerCase() === 'active' ? 'isolated' : 'online'}`}>{t.status}</span></td>
                  <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{t.time || 'Just now'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">By Severity</div>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={severityChart}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1a2138', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#e2e8f0' }} />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {severityChart.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
