/**
 * SecureIoT-X — System Logs & Audit Trail Page.
 * Real-time monitoring of all subsystems: AI Engine, Response Engine, SDN Controller, MQTT Broker, Blockchain.
 */
import { useState, useEffect } from 'react';
import { Terminal, Search, Download, RefreshCw, FileText } from 'lucide-react';
import api from '../services/api';

const DEMO_LOGS = [
  { id: 101, level: 'INFO', service: 'AI_ENGINE', message: 'Model inference executed for ESP32_001. Flow classified: Normal (0.992).', device_id: 'ESP32_001', timestamp: '2026-09-06T05:54:12Z' },
  { id: 102, level: 'WARN', service: 'MQTT_BROKER', message: 'High packet arrival rate detected from ESP32_003: 1420 pps.', device_id: 'ESP32_003', timestamp: '2026-09-06T05:55:01Z' },
  { id: 103, level: 'CRITICAL', service: 'AI_ENGINE', message: 'DDoS SYN Flood detected on ESP32_003! Risk score calculated: 91.2/100.', device_id: 'ESP32_003', timestamp: '2026-09-06T05:55:02Z' },
  { id: 104, level: 'CRITICAL', service: 'RESPONSE_ENGINE', message: 'Automated policy triggered: ISOLATE ESP32_003 immediately.', device_id: 'ESP32_003', timestamp: '2026-09-06T05:55:02Z' },
  { id: 105, level: 'WARN', service: 'SDN_CONTROLLER', message: 'OpenFlow drop rule pushed to switch s1 port 3. Device ESP32_003 isolated.', device_id: 'ESP32_003', timestamp: '2026-09-06T05:55:03Z' },
  { id: 106, level: 'SUCCESS', service: 'BLOCKCHAIN_NODE', message: 'Security event EVT-90214 recorded into Block #1. Hash: 008a21bf... Nonce: 319.', device_id: 'ESP32_003', timestamp: '2026-09-06T05:55:04Z' },
  { id: 107, level: 'INFO', service: 'SYSTEM', message: 'System health check passed: All 6 microservices operational.', device_id: 'SYSTEM', timestamp: '2026-09-06T05:56:00Z' },
  { id: 108, level: 'WARN', service: 'AI_ENGINE', message: 'Deep Autoencoder reconstruction error spike: 0.051 (Threshold: 0.042) on ESP32_007.', device_id: 'ESP32_007', timestamp: '2026-09-06T05:56:45Z' },
  { id: 109, level: 'INFO', service: 'RESPONSE_ENGINE', message: 'Action decided for ESP32_007: MONITOR (Risk: 62.0, Severity: HIGH).', device_id: 'ESP32_007', timestamp: '2026-09-06T05:56:46Z' },
];

const DEMO_AUDIT = [
  { audit_id: 'AUD-001', action: 'DEVICE_ISOLATION', entity_type: 'DEVICE', entity_id: 'ESP32_003', user_id: 'AI_RESPONSE_ENGINE', severity: 'CRITICAL', details: 'Automated isolation due to DDoS SYN flood (Risk 91.2)', timestamp: '2026-09-06T05:55:03Z' },
  { audit_id: 'AUD-002', action: 'BLOCK_MINED', entity_type: 'BLOCKCHAIN', entity_id: 'BLOCK_1', user_id: 'BLOCKCHAIN_DAEMON', severity: 'LOW', details: 'Proof-of-work solved with difficulty 2', timestamp: '2026-09-06T05:55:04Z' },
  { audit_id: 'AUD-003', action: 'DEVICE_REGISTRATION', entity_type: 'DEVICE', entity_id: 'ESP32_008', user_id: 'ADMIN', severity: 'LOW', details: 'New water meter sensor registered in Zone-D', timestamp: '2026-09-06T05:40:10Z' },
  { audit_id: 'AUD-004', action: 'POLICY_UPDATE', entity_type: 'SDN', entity_id: 'FLOW_TABLE_0', user_id: 'ADMIN', severity: 'MEDIUM', details: 'Updated rate limit threshold to 1500 pps for Zone-A', timestamp: '2026-09-06T05:30:00Z' },
];

export default function SystemLogs() {
  const [activeTab, setActiveTab] = useState('logs'); // 'logs' | 'audit'
  const [logs, setLogs] = useState(DEMO_LOGS);
  const [auditTrail, setAuditTrail] = useState(DEMO_AUDIT);
  const [filterLevel, setFilterLevel] = useState('ALL');
  const [filterService, setFilterService] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const [systemData, auditData] = await Promise.all([
        api.getSystemLogs().catch(() => DEMO_LOGS),
        api.getAuditTrail().catch(() => DEMO_AUDIT),
      ]);
      if (Array.isArray(systemData) && systemData.length > 0) setLogs(systemData);
      if (Array.isArray(auditData) && auditData.length > 0) setAuditTrail(auditData);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  // Filter logs
  const filteredLogs = logs.filter(l => {
    if (filterLevel !== 'ALL' && l.level !== filterLevel) return false;
    if (filterService !== 'ALL' && l.service !== filterService) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (l.message || '').toLowerCase().includes(q) ||
             (l.device_id || '').toLowerCase().includes(q) ||
             (l.service || '').toLowerCase().includes(q);
    }
    return true;
  });

  const getLevelColor = (lvl) => {
    switch (lvl) {
      case 'CRITICAL':
      case 'ERROR': return 'var(--accent-red)';
      case 'WARN': return 'var(--accent-yellow)';
      case 'SUCCESS': return 'var(--accent-green)';
      default: return 'var(--accent-cyan)';
    }
  };

  return (
    <div className="page">
      {/* Header controls: Tab Switcher & Actions */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className={`btn ${activeTab === 'logs' ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setActiveTab('logs')}
            >
              <Terminal size={16} /> Live System Logs ({filteredLogs.length})
            </button>
            <button
              className={`btn ${activeTab === 'audit' ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setActiveTab('audit')}
            >
              <FileText size={16} /> Immutable Audit Trail ({auditTrail.length})
            </button>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-outline" onClick={fetchLogs} disabled={loading} style={{ fontSize: 12 }}>
              <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh
            </button>
            <button
              className="btn btn-outline"
              style={{ fontSize: 12 }}
              onClick={() => {
                const dataStr = JSON.stringify(activeTab === 'logs' ? logs : auditTrail, null, 2);
                const blob = new Blob([dataStr], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `secureiot_${activeTab}_export.json`;
                a.click();
              }}
            >
              <Download size={14} /> Export JSON
            </button>
          </div>
        </div>

        {/* Filters Row */}
        {activeTab === 'logs' && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginTop: '16px', alignItems: 'center' }}>
            <div style={{ position: 'relative', flex: '1', minWidth: '200px' }}>
              <Search size={16} style={{ position: 'absolute', left: 12, top: 12, color: 'var(--text-muted)' }} />
              <input
                type="text"
                className="form-input"
                placeholder="Search logs by keyword, device, or trace ID..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                style={{ paddingLeft: '36px' }}
              />
            </div>

            <select
              className="form-select"
              value={filterLevel}
              onChange={e => setFilterLevel(e.target.value)}
              style={{ width: '160px' }}
            >
              <option value="ALL">All Levels</option>
              <option value="INFO">INFO</option>
              <option value="WARN">WARN</option>
              <option value="ERROR">ERROR</option>
              <option value="CRITICAL">CRITICAL</option>
              <option value="SUCCESS">SUCCESS</option>
            </select>

            <select
              className="form-select"
              value={filterService}
              onChange={e => setFilterService(e.target.value)}
              style={{ width: '180px' }}
            >
              <option value="ALL">All Services</option>
              <option value="AI_ENGINE">AI_ENGINE</option>
              <option value="RESPONSE_ENGINE">RESPONSE_ENGINE</option>
              <option value="SDN_CONTROLLER">SDN_CONTROLLER</option>
              <option value="MQTT_BROKER">MQTT_BROKER</option>
              <option value="BLOCKCHAIN_NODE">BLOCKCHAIN_NODE</option>
              <option value="SYSTEM">SYSTEM</option>
            </select>
          </div>
        )}
      </div>

      {/* Main Tab Content */}
      {activeTab === 'logs' ? (
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Console Stream</div>
              <div className="card-subtitle">Real-time structured logs with correlation identifiers</div>
            </div>
          </div>

          <div style={{
            background: '#090d19',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '8px',
            padding: '16px',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '12px',
            maxHeight: '600px',
            overflowY: 'auto',
          }}>
            {filteredLogs.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
                No logs match the selected filters.
              </div>
            ) : (
              filteredLogs.map(l => (
                <div
                  key={l.id}
                  style={{
                    display: 'flex',
                    alignItems: 'baseline',
                    gap: '12px',
                    padding: '6px 0',
                    borderBottom: '1px solid rgba(255,255,255,0.03)',
                  }}
                >
                  <span style={{ color: '#475569', whiteSpace: 'nowrap' }}>
                    {l.timestamp ? new Date(l.timestamp).toLocaleTimeString() : '00:00:00'}
                  </span>
                  <span style={{
                    color: getLevelColor(l.level),
                    fontWeight: 700,
                    width: '70px',
                    textAlign: 'right',
                    whiteSpace: 'nowrap',
                  }}>
                    [{l.level}]
                  </span>
                  <span style={{ color: 'var(--accent-purple)', width: '150px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    [{l.service}]
                  </span>
                  <span style={{ color: 'var(--accent-cyan)', width: '90px', whiteSpace: 'nowrap' }}>
                    {l.device_id || '-'}
                  </span>
                  <span style={{ color: 'var(--text-primary)', flex: 1 }}>
                    {l.message}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      ) : (
        /* Audit Trail Table */
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Security Audit Ledger</div>
              <div className="card-subtitle">Legally compliant immutable security events and administrative actions</div>
            </div>
          </div>

          <table className="data-table">
            <thead>
              <tr>
                <th>Audit ID</th>
                <th>Action</th>
                <th>Entity</th>
                <th>Target ID</th>
                <th>Actor</th>
                <th>Severity</th>
                <th>Details</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {auditTrail.map(a => (
                <tr key={a.audit_id}>
                  <td style={{ fontFamily: 'JetBrains Mono', color: 'var(--accent-cyan)' }}>{a.audit_id}</td>
                  <td style={{ fontWeight: 600 }}>{a.action}</td>
                  <td><span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{a.entity_type}</span></td>
                  <td style={{ fontFamily: 'JetBrains Mono' }}>{a.entity_id}</td>
                  <td><strong style={{ color: 'var(--text-secondary)' }}>{a.user_id}</strong></td>
                  <td>
                    <span className={`severity-badge ${(a.severity || 'low').toLowerCase()}`}>
                      {a.severity}
                    </span>
                  </td>
                  <td style={{ fontSize: 12, color: 'var(--text-secondary)', maxWidth: '280px' }}>
                    {a.details}
                  </td>
                  <td style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {a.timestamp ? new Date(a.timestamp).toLocaleString() : 'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
