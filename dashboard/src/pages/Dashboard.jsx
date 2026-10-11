/**
 * SecureIoT-X — Main Dashboard Page.
 * Real-time overview with stats, charts, live feed, and blockchain status.
 */
import { useState, useEffect, useCallback } from 'react';
import {
  Shield, Cpu, AlertTriangle, Activity, Link2, Brain,
  Zap, CheckCircle, XCircle
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';
import api from '../services/api';

const COLORS = ['#10b981', '#f59e0b', '#f97316', '#ef4444', '#8b5cf6', '#3b82f6'];

export default function Dashboard() {
  const [stats, setStats] = useState({
    total_devices: 0, online_devices: 0, total_threats: 0,
    critical_threats: 0, isolated_devices: 0, total_predictions: 0,
  });
  const [liveFeed, setLiveFeed] = useState([]);
  const [trafficData, setTrafficData] = useState([]);
  const [threatDistribution, setThreatDistribution] = useState([]);
  const [blockchainStatus, setBlockchainStatus] = useState(null);

  // Generate demo time-series data
  const generateTrafficData = useCallback(() => {
    const now = Date.now();
    return Array.from({ length: 24 }, (_, i) => ({
      time: new Date(now - (23 - i) * 3600000).toLocaleTimeString([], { hour: '2-digit' }),
      normal: Math.floor(Math.random() * 400 + 200),
      suspicious: Math.floor(Math.random() * 30 + 5),
      attacks: Math.floor(Math.random() * 8),
    }));
  }, []);

  useEffect(() => {
    setTrafficData(generateTrafficData());
    setThreatDistribution([
      { name: 'DDoS', value: 35 },
      { name: 'Port Scan', value: 25 },
      { name: 'Brute Force', value: 15 },
      { name: 'Spoofing', value: 12 },
      { name: 'MITM', value: 8 },
      { name: 'Other', value: 5 },
    ]);

    // Try to load real data
    api.getOverview().then(setStats).catch(() => {});
    api.getBlockchainStatus().then(setBlockchainStatus).catch(() => {});

    // Refresh every 5s
    const interval = setInterval(() => {
      api.getOverview().then(setStats).catch(() => {});
    }, 5000);

    return () => clearInterval(interval);
  }, [generateTrafficData]);

  // Simulate live feed
  useEffect(() => {
    const feedEvents = [
      { type: 'normal', msg: 'ESP32_001 telemetry received', device: 'ESP32_001', severity: 'low' },
      { type: 'normal', msg: 'ESP32_005 heartbeat OK', device: 'ESP32_005', severity: 'low' },
      { type: 'warning', msg: 'Unusual packet rate from ESP32_003', device: 'ESP32_003', severity: 'medium' },
      { type: 'normal', msg: 'ESP32_002 temperature: 23.4C', device: 'ESP32_002', severity: 'low' },
      { type: 'alert', msg: 'DDoS pattern detected on ESP32_003', device: 'ESP32_003', severity: 'critical' },
      { type: 'normal', msg: 'Blockchain block #4 validated', device: 'SYSTEM', severity: 'low' },
      { type: 'warning', msg: 'Port scan detected from 10.0.0.15', device: 'ESP32_007', severity: 'high' },
      { type: 'normal', msg: 'SIMULATION: AI inference sample Normal (98.2%)', device: 'ESP32_004', severity: 'low' },
    ];

    let idx = 0;
    const feedInterval = setInterval(() => {
      const event = feedEvents[idx % feedEvents.length];
      setLiveFeed(prev => [{
        ...event,
        id: Date.now(),
        time: new Date().toLocaleTimeString(),
      }, ...prev].slice(0, 20));
      idx++;
    }, 3000);

    return () => clearInterval(feedInterval);
  }, []);

  const getFeedIcon = (type) => {
    switch (type) {
      case 'alert': return <XCircle size={14} />;
      case 'warning': return <AlertTriangle size={14} />;
      default: return <CheckCircle size={14} />;
    }
  };

  const getFeedColor = (type) => {
    switch (type) {
      case 'alert': return 'var(--accent-red)';
      case 'warning': return 'var(--accent-yellow)';
      default: return 'var(--accent-green)';
    }
  };

  return (
    <div className="page">
      {/* Stats Row */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon cyan"><Cpu size={22} /></div>
          <div className="stat-content">
            <h3>{stats.total_devices}</h3>
            <p>Total Devices</p>
            <div className="stat-change positive">{stats.online_devices} online</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon red"><Shield size={22} /></div>
          <div className="stat-content">
            <h3>{stats.total_threats}</h3>
            <p>Threats Detected</p>
            <div className="stat-change negative">{stats.critical_threats} critical</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon purple"><Brain size={22} /></div>
          <div className="stat-content">
            <h3>{stats.total_predictions}</h3>
            <p>AI Predictions</p>
            <div className="stat-change positive">Live inference</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green"><Link2 size={22} /></div>
          <div className="stat-content">
            <h3>{blockchainStatus?.total_blocks || 0}</h3>
            <p>Blockchain Blocks</p>
            <div className="stat-change positive">
              {blockchainStatus?.is_valid ? 'Chain Valid' : 'Verifying...'}
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon yellow"><AlertTriangle size={22} /></div>
          <div className="stat-content">
            <h3>{stats.isolated_devices}</h3>
            <p>Isolated Devices</p>
            <div className="stat-change">SDN quarantined</div>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="charts-grid">
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Network Traffic Analysis</div>
              <div className="card-subtitle">Simulated traffic demo — not measured device traffic</div>
            </div>
            <Activity size={18} style={{ color: 'var(--accent-cyan)' }} />
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={trafficData}>
              <defs>
                <linearGradient id="gradNormal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="gradSusp" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="gradAttack" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  background: '#1a2138', border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 8, color: '#e2e8f0', fontSize: 12,
                }}
              />
              <Area type="monotone" dataKey="normal" stroke="#10b981" fill="url(#gradNormal)" strokeWidth={2} />
              <Area type="monotone" dataKey="suspicious" stroke="#f59e0b" fill="url(#gradSusp)" strokeWidth={2} />
              <Area type="monotone" dataKey="attacks" stroke="#ef4444" fill="url(#gradAttack)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Threat Distribution</div>
              <div className="card-subtitle">Synthetic demo distribution — not model evaluation</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={threatDistribution}
                cx="50%" cy="50%"
                innerRadius={60} outerRadius={100}
                paddingAngle={3}
                dataKey="value"
              >
                {threatDistribution.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: '#1a2138', border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 8, color: '#e2e8f0', fontSize: 12,
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
            {threatDistribution.map((item, i) => (
              <div key={item.name} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#94a3b8' }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS[i] }}></div>
                {item.name}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Live Feed + Recent Events */}
      <div className="charts-grid-equal">
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Simulated Event Feed</div>
              <div className="card-subtitle">Synthetic demo events — not live telemetry or model evaluation</div>
            </div>
            <Zap size={18} style={{ color: 'var(--accent-yellow)' }} />
          </div>
          <div className="live-feed">
            {liveFeed.map((item) => (
              <div key={item.id} className="feed-item">
                <div className="feed-icon" style={{
                  background: `${getFeedColor(item.type)}15`,
                  color: getFeedColor(item.type),
                }}>
                  {getFeedIcon(item.type)}
                </div>
                <div className="feed-content">
                  <p>{item.msg}</p>
                  <div className="feed-meta">{item.device} &middot; {item.time}</div>
                </div>
                <span className={`severity-badge ${item.severity}`}>{item.severity}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Security Pipeline</div>
              <div className="card-subtitle">End-to-end event processing flow</div>
            </div>
          </div>
          <div style={{ padding: '16px 0' }}>
            {['MQTT Ingestion', 'AI Inference', 'Risk Assessment', 'Response Engine', 'Blockchain Record', 'Dashboard Alert'].map((step, i) => (
              <div key={step} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '12px 16px', borderRadius: 8,
                background: i % 2 === 0 ? 'var(--bg-secondary)' : 'transparent',
                marginBottom: 4,
              }}>
                <div style={{
                  width: 28, height: 28, borderRadius: '50%',
                  background: `${COLORS[i % COLORS.length]}20`,
                  color: COLORS[i % COLORS.length],
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 12, fontWeight: 700, flexShrink: 0,
                }}>
                  {i + 1}
                </div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{step}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {['Collecting IoT telemetry', 'ML classification + anomaly', 'Weighted risk scoring',
                      'Automated response actions', 'Immutable audit trail', 'Real-time WebSocket'][i]}
                  </div>
                </div>
                <CheckCircle size={16} style={{ marginLeft: 'auto', color: 'var(--accent-green)' }} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
