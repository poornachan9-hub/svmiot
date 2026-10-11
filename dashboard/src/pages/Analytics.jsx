/**
 * SecureIoT-X — Security Analytics & Risk Intelligence Page.
 * Deep-dive telemetry statistics, threat trends, protocol distribution, and zone vulnerability.
 */
import { useState, useEffect } from 'react';
import { Activity, ShieldAlert, BarChart2, Layers, TrendingUp, Cpu, Server } from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import api from '../services/api';

const PROTOCOL_DATA = [
  { name: 'MQTT / MQTTS', value: 54, color: '#00d4ff' },
  { name: 'HTTP / REST API', value: 22, color: '#3b82f6' },
  { name: 'CoAP (Constrained)', value: 14, color: '#8b5cf6' },
  { name: 'Raw TCP / Socket', value: 10, color: '#f59e0b' },
];

const ZONE_RISK_DATA = [
  { zone: 'Zone-A (Sensors)', normal: 450, suspicious: 12, attacks: 2, avgRisk: 14.2 },
  { zone: 'Zone-B (Access/Locks)', normal: 380, suspicious: 24, attacks: 8, avgRisk: 42.5 },
  { zone: 'Zone-C (HVAC/Env)', normal: 310, suspicious: 18, attacks: 3, avgRisk: 22.1 },
  { zone: 'Zone-D (Critical/Power)', normal: 290, suspicious: 45, attacks: 19, avgRisk: 78.4 },
];

const HOURLY_TRENDS = [
  { hour: '00:00', threats: 1, avgRisk: 12 },
  { hour: '02:00', threats: 0, avgRisk: 8 },
  { hour: '04:00', threats: 3, avgRisk: 28 },
  { hour: '06:00', threats: 2, avgRisk: 15 },
  { hour: '08:00', threats: 8, avgRisk: 52 },
  { hour: '10:00', threats: 14, avgRisk: 68 },
  { hour: '12:00', threats: 9, avgRisk: 44 },
  { hour: '14:00', threats: 18, avgRisk: 82 },
  { hour: '16:00', threats: 11, avgRisk: 59 },
  { hour: '18:00', threats: 7, avgRisk: 38 },
  { hour: '20:00', threats: 5, avgRisk: 29 },
  { hour: '22:00', threats: 2, avgRisk: 16 },
];

const TOP_TARGETS = [
  { id: 'ESP32_003', type: 'Camera Gateway', zone: 'Zone-B', attacks: 14, primaryThreat: 'DDoS SYN Flood', status: 'ISOLATED' },
  { id: 'ESP32_007', type: 'Power Controller', zone: 'Zone-D', attacks: 9, primaryThreat: 'Port Scan Recon', status: 'MONITORED' },
  { id: 'ESP32_001', type: 'Env Sensor', zone: 'Zone-A', attacks: 4, primaryThreat: 'Brute Force Auth', status: 'NORMAL' },
  { id: 'ESP32_005', type: 'Smart Thermostat', zone: 'Zone-C', attacks: 3, primaryThreat: 'Payload Tampering', status: 'NORMAL' },
];

export default function Analytics() {
  const [overview, setOverview] = useState(null);

  useEffect(() => {
    api.getOverview().then(setOverview).catch(() => {});
  }, []);

  return (
    <div className="page">
      {/* Top Stat Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon cyan"><Activity size={22} /></div>
          <div className="stat-content">
            <h3>1.42M</h3>
            <p>24h Flow Packets</p>
            <div className="stat-change positive">+14% vs yesterday</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon yellow"><TrendingUp size={22} /></div>
          <div className="stat-content">
            <h3>0.024</h3>
            <p>Mean Anomaly Score</p>
            <div className="stat-change positive">Normal baseline</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon red"><ShieldAlert size={22} /></div>
          <div className="stat-content">
            <h3>{overview?.total_threats ? `${overview.total_threats} Total` : '34 Total'}</h3>
            <p>Mitigated Incidents</p>
            <div className="stat-change negative">99.8% Automated</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green"><Layers size={22} /></div>
          <div className="stat-content">
            <h3>4 Zones</h3>
            <p>Micro-Segmented</p>
            <div className="stat-change positive">SDN Policies Active</div>
          </div>
        </div>
      </div>

      {/* Main Charts: Threat Volume & Risk Score Trends */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header">
          <div>
            <div className="card-title">Threat Velocity & Risk Score Dynamics (24h)</div>
            <div className="card-subtitle">Correlation between incident volume and collective fleet risk score</div>
          </div>
          <BarChart2 size={18} style={{ color: 'var(--accent-cyan)' }} />
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={HOURLY_TRENDS}>
            <defs>
              <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.35}/>
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="threatGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.4}/>
                <stop offset="95%" stopColor="#00d4ff" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="hour" tick={{ fill: '#64748b', fontSize: 11 }} />
            <YAxis yAxisId="left" tick={{ fill: '#00d4ff', fontSize: 11 }} label={{ value: 'Incidents', angle: -90, position: 'insideLeft', fill: '#00d4ff', fontSize: 11 }} />
            <YAxis yAxisId="right" orientation="right" tick={{ fill: '#ef4444', fontSize: 11 }} label={{ value: 'Risk Score', angle: 90, position: 'insideRight', fill: '#ef4444', fontSize: 11 }} />
            <Tooltip contentStyle={{ background: '#1a2138', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#e2e8f0' }} />
            <Legend />
            <Area yAxisId="left" type="monotone" dataKey="threats" name="Threat Incidents" stroke="#00d4ff" fill="url(#threatGrad)" strokeWidth={2} />
            <Area yAxisId="right" type="monotone" dataKey="avgRisk" name="Average Risk Score" stroke="#ef4444" fill="url(#riskGrad)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Two Columns: Protocol Distribution & Zone Vulnerability */}
      <div className="charts-grid">
        {/* Protocol Distribution */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">IoT Ingestion Protocol Distribution</div>
              <div className="card-subtitle">Traffic volume share across message brokers</div>
            </div>
            <Server size={18} style={{ color: 'var(--accent-cyan)' }} />
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={PROTOCOL_DATA}
                cx="50%" cy="50%"
                innerRadius={65} outerRadius={95}
                paddingAngle={4}
                dataKey="value"
              >
                {PROTOCOL_DATA.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: '#1a2138', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#e2e8f0' }} formatter={(val) => [`${val}%`, 'Share']} />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '8px' }}>
            {PROTOCOL_DATA.map(item => (
              <div key={item.name} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-secondary)' }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: item.color }}></div>
                <span>{item.name}: <strong style={{ color: 'var(--text-primary)' }}>{item.value}%</strong></span>
              </div>
            ))}
          </div>
        </div>

        {/* Zone Risk Vulnerability */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Security Zone Threat Profiles</div>
              <div className="card-subtitle">Normal traffic vs. attacks across micro-segments</div>
            </div>
            <Layers size={18} style={{ color: 'var(--accent-purple)' }} />
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={ZONE_RISK_DATA}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="zone" tick={{ fill: '#64748b', fontSize: 10 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1a2138', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#e2e8f0' }} />
              <Legend />
              <Bar dataKey="normal" name="Normal Flows" fill="#10b981" radius={[4, 4, 0, 0]} />
              <Bar dataKey="suspicious" name="Suspicious" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              <Bar dataKey="attacks" name="Attacks" fill="#ef4444" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Bottom Table: Top Targeted Fleet Endpoints */}
      <div className="card" style={{ marginTop: '24px' }}>
        <div className="card-header">
          <div>
            <div className="card-title">Top Targeted Fleet Endpoints</div>
            <div className="card-subtitle">Devices undergoing repeated intrusion attempts</div>
          </div>
          <Cpu size={18} style={{ color: 'var(--accent-red)' }} />
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Device ID</th>
              <th>Hardware Type</th>
              <th>Network Zone</th>
              <th>Incident Count</th>
              <th>Primary Attack Vector</th>
              <th>SDN Defense State</th>
            </tr>
          </thead>
          <tbody>
            {TOP_TARGETS.map(t => (
              <tr key={t.id}>
                <td style={{ fontFamily: 'JetBrains Mono', color: 'var(--accent-cyan)', fontWeight: 600 }}>{t.id}</td>
                <td>{t.type}</td>
                <td>{t.zone}</td>
                <td style={{ fontWeight: 700, color: 'var(--accent-red)' }}>{t.attacks}</td>
                <td><span className="severity-badge high">{t.primaryThreat}</span></td>
                <td>
                  <span className={`status-badge ${t.status === 'ISOLATED' ? 'isolated' : t.status === 'MONITORED' ? 'pending' : 'online'}`}>
                    {t.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
