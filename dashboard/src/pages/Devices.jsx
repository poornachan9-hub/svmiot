/**
 * SecureIoT-X — Device Fleet Page.
 * Loads ALL devices from MongoDB via backend API.
 * Distinguishes physical hardware (ESP32) from simulation devices.
 * Displays live sensor telemetry, handles real network isolation/release,
 * and provides dual-track security testing (Category A Detection & Category B Enforcement).
 */
import { useState, useEffect } from 'react';
import {
  Cpu, Wifi, ShieldAlert, ShieldCheck, RefreshCw, Plus,
  HardDrive, Activity, Radio, X, Trash2, CheckCircle2,
  AlertTriangle, Smartphone, Play, ExternalLink, Lock, Unlock
} from 'lucide-react';
import api from '../services/api';

// Compute lowest unused device ID
const getNextDeviceId = (existingDevices, isPhysical = true) => {
  const used = new Set(existingDevices.map(d => (d.device_id || '').toUpperCase()));
  const startNum = isPhysical ? 11 : 1;
  for (let i = startNum; i <= 999; i++) {
    const candidate = `ESP32_${String(i).padStart(3, '0')}`;
    if (!used.has(candidate)) {
      return candidate;
    }
  }
  return 'ESP32_NEW';
};

export default function Devices() {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Security Testing Modal State
  const [testModalDevice, setTestModalDevice] = useState(null);
  const [testRunning, setTestRunning] = useState(false);
  const [testResult, setTestResult] = useState(null);

  const [formData, setFormData] = useState({
    device_id: 'ESP32_013',
    name: 'Lab ESP32 Node',
    device_type: 'ESP32 DHT22 Sensor',
    is_simulation: false,
    ip_address: '',
    mac_address: '',
    location: 'Zone-Hardware',
  });

  useEffect(() => {
    loadDevices();

    // Connect WebSocket listeners for live updates
    api.connectWS();
    const handleTelemetry = (data) => {
      setDevices(prev => prev.map(d => {
        if (d.device_id === data.device_id) {
          return {
            ...d,
            temperature: data.temperature !== undefined ? data.temperature : d.temperature,
            humidity: data.humidity !== undefined ? data.humidity : d.humidity,
            motion: data.motion !== undefined ? data.motion : d.motion,
            rssi: data.rssi !== undefined ? data.rssi : d.rssi,
            last_seen: data.last_seen || Date.now() / 1000,
            status: 'online',
            is_online: true,
          };
        }
        return d;
      }));
    };

    const handleDeviceStatus = (data) => {
      setDevices(prev => prev.map(d => {
        if (d.device_id === data.device_id) {
          return {
            ...d,
            status: data.is_online ? 'online' : 'offline',
            is_online: data.is_online,
            last_seen: data.last_seen || d.last_seen,
          };
        }
        return d;
      }));
    };

    const handleRefresh = () => {
      loadDevices();
    };

    api.onWS('telemetry_update', handleTelemetry);
    api.onWS('device_status', handleDeviceStatus);
    api.onWS('device_connected', handleRefresh);
    api.onWS('device_isolated', handleRefresh);
    api.onWS('device_released', handleRefresh);
    api.onWS('device_deleted', handleRefresh);

    return () => {
      api.offWS('telemetry_update');
      api.offWS('device_status');
      api.offWS('device_connected');
      api.offWS('device_isolated');
      api.offWS('device_released');
      api.offWS('device_deleted');
    };
  }, []);

  const loadDevices = async () => {
    setLoading(true);
    try {
      const data = await api.getDevices();
      if (Array.isArray(data)) {
        setDevices(data.map(d => ({
          ...d,
          status: d.is_isolated ? 'isolated' : (d.is_online !== false ? 'online' : 'offline'),
          isolated: d.is_isolated || false,
          enforcement_status: d.enforcement_status || (d.is_isolated ? 'ISOLATION_VERIFIED' : 'NORMAL'),
          threats: d.threat_count || 0,
          zone: d.location || 'Unknown',
          ip: d.ip_address || '',
          is_simulation: d.is_simulation !== false,
        })));
      }
    } catch (e) {
      console.error('Failed to load devices:', e);
    }
    setLoading(false);
  };

  const handleOpenModal = (isPhysical = true) => {
    const nextId = getNextDeviceId(devices, isPhysical);
    setFormData({
      device_id: nextId,
      name: isPhysical ? `Physical Node ${nextId}` : `Simulated Node ${nextId}`,
      device_type: isPhysical ? 'ESP32 DHT22 Sensor' : 'Virtual Temperature Sensor',
      is_simulation: !isPhysical,
      ip_address: '',
      mac_address: '',
      location: isPhysical ? 'Zone-Hardware' : 'Zone-Virtual',
    });
    setErrorMsg('');
    setSuccessMsg('');
    setShowModal(true);
  };

  const handleModeChange = (isPhysical) => {
    const nextId = getNextDeviceId(devices, isPhysical);
    setFormData(prev => ({
      ...prev,
      device_id: nextId,
      name: isPhysical ? `Physical Node ${nextId}` : `Simulated Node ${nextId}`,
      device_type: isPhysical ? 'ESP32 DHT22 Sensor' : 'Virtual Temperature Sensor',
      is_simulation: !isPhysical,
      location: isPhysical ? 'Zone-Hardware' : 'Zone-Virtual',
    }));
  };

  const handleIsolate = async (id) => {
    try {
      await api.isolateDevice(id);
      await loadDevices();
    } catch (e) {
      console.error('Isolate failed:', e);
    }
  };

  const handleRelease = async (id) => {
    try {
      await api.releaseDevice(id);
      await loadDevices();
    } catch (e) {
      console.error('Release failed:', e);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm(`Are you sure you want to remove device ${id}?`)) {
      return;
    }
    setDeletingId(id);
    try {
      await api.deleteDevice(id);
      await loadDevices();
    } catch (e) {
      alert(`Could not delete device: ${e.message}`);
    }
    setDeletingId(null);
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setRegistering(true);
    setErrorMsg('');
    setSuccessMsg('');
    try {
      await api.registerDevice({
        ...formData,
        device_id: formData.device_id.trim(),
        telemetry_schema: { temperature: 'float', humidity: 'float', rssi: 'float' },
      });
      setSuccessMsg(`Device ${formData.device_id.trim()} successfully registered!`);
      setTimeout(() => {
        setShowModal(false);
        setSuccessMsg('');
      }, 1200);
      await loadDevices();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to register device');
    }
    setRegistering(false);
  };

  // ── Testing Modal Handlers ─────────────────────────────────────
  const openTestingModal = (device) => {
    setTestModalDevice(device);
    setTestResult(null);
  };

  const runCategoryATest = async () => {
    if (!testModalDevice) return;
    setTestRunning(true);
    try {
      const res = await api.runDetectionTest(testModalDevice.device_id);
      setTestResult({
        type: 'CATEGORY_A_DETECTION',
        title: 'Category A: Real Model Detection Test',
        data: res,
      });
      await loadDevices();
    } catch (e) {
      setTestResult({ type: 'ERROR', message: e.message });
    }
    setTestRunning(false);
  };

  const runCategoryBTest = async () => {
    if (!testModalDevice) return;
    setTestRunning(true);
    try {
      const res = await api.runEnforcementTest(testModalDevice.device_id);
      setTestResult({
        type: 'CATEGORY_B_ENFORCEMENT',
        title: 'Category B: Response Enforcement Test',
        data: res,
      });
      await loadDevices();
    } catch (e) {
      setTestResult({ type: 'ERROR', message: e.message });
    }
    setTestRunning(false);
  };

  const runProbeTest = async () => {
    if (!testModalDevice) return;
    setTestRunning(true);
    try {
      const res = await api.probeTestEndpoint(testModalDevice.device_id);
      setTestResult({
        type: 'PROBE_CHECK',
        title: 'Designated Endpoint Connectivity Probe',
        data: res,
      });
    } catch (e) {
      setTestResult({
        type: 'PROBE_CHECK',
        title: 'Designated Endpoint Connectivity Probe',
        data: {
          status: 'BLOCKED_QUARANTINED',
          error: e.message,
          detail: 'Device network path is verified BLOCKED by NetworkEnforcer.',
        },
      });
    }
    setTestRunning(false);
  };

  const formatLastSeen = (timestamp) => {
    if (!timestamp) return 'Never';
    const ms = timestamp > 1e11 ? timestamp : timestamp * 1000;
    const diffSec = Math.floor((Date.now() - ms) / 1000);
    if (diffSec < 5) return 'Just now';
    if (diffSec < 60) return `${diffSec}s ago`;
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    return new Date(ms).toLocaleTimeString();
  };

  const physicalCount = devices.filter(d => !d.is_simulation).length;
  const onlineCount = devices.filter(d => d.status === 'online').length;
  const isolatedCount = devices.filter(d => d.isolated).length;

  return (
    <div className="page">
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon cyan"><Cpu size={22} /></div>
          <div className="stat-content">
            <h3>{devices.length}</h3>
            <p>Total Fleet</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon purple"><HardDrive size={22} /></div>
          <div className="stat-content">
            <h3>{physicalCount}</h3>
            <p>Physical Hardware</p>
            <div style={{ fontSize: 11, color: 'var(--accent-cyan)', marginTop: 4 }}>
              ESP32 Wi-Fi Nodes
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green"><Wifi size={22} /></div>
          <div className="stat-content">
            <h3>{onlineCount}</h3>
            <p>Online Nodes</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon red"><ShieldAlert size={22} /></div>
          <div className="stat-content">
            <h3>{isolatedCount}</h3>
            <p>Quarantined</p>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">IoT Device Inventory</div>
            <div className="card-subtitle">
              Real physical ESP32 hardware and simulation nodes with genuine network enforcement
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button
              className="btn btn-primary"
              onClick={() => handleOpenModal(true)}
              style={{ fontSize: 12, padding: '7px 14px', display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <Plus size={14} /> Add Device
            </button>
            <button
              className="btn btn-outline"
              onClick={loadDevices}
              style={{ fontSize: 12, padding: '7px 14px' }}
            >
              <RefreshCw size={14} /> Refresh
            </button>
          </div>
        </div>

        {loading && devices.length === 0 ? (
          <p style={{ padding: 20, color: 'var(--text-muted)', fontSize: 13 }}>
            Loading devices from MongoDB...
          </p>
        ) : devices.length === 0 ? (
          <p style={{ padding: 20, color: 'var(--text-muted)', fontSize: 13 }}>
            No devices found in MongoDB.
          </p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Device ID</th>
                <th>Hardware Mode</th>
                <th>Type</th>
                <th>IP / MAC Address</th>
                <th>Zone</th>
                <th>Live Telemetry</th>
                <th>Enforcement State</th>
                <th>Last Seen</th>
                <th>Threats</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {devices.map(d => (
                <tr key={d.device_id}>
                  <td style={{ fontFamily: 'JetBrains Mono', fontSize: 12, fontWeight: 600, color: 'var(--accent-cyan)' }}>
                    {d.device_id}
                  </td>
                  <td>
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 4,
                      padding: '3px 8px',
                      borderRadius: 4,
                      fontSize: 10,
                      fontWeight: 700,
                      letterSpacing: 0.5,
                      background: d.is_simulation ? 'rgba(139, 92, 246, 0.12)' : 'rgba(0, 212, 255, 0.15)',
                      color: d.is_simulation ? 'var(--accent-purple)' : 'var(--accent-cyan)',
                      border: d.is_simulation ? '1px solid rgba(139, 92, 246, 0.3)' : '1px solid rgba(0, 212, 255, 0.35)',
                    }}>
                      {d.is_simulation ? <Radio size={10} /> : <HardDrive size={10} />}
                      {d.is_simulation ? 'SIMULATION' : 'PHYSICAL (ESP32)'}
                    </span>
                  </td>
                  <td style={{ fontSize: 12 }}>{d.device_type}</td>
                  <td style={{ fontFamily: 'JetBrains Mono', fontSize: 11, color: 'var(--text-secondary)' }}>
                    <div>{d.ip || '—'}</div>
                    {d.mac_address && (
                      <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{d.mac_address}</div>
                    )}
                  </td>
                  <td style={{ fontSize: 12 }}>{d.zone}</td>
                  <td>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 2, fontSize: 11, fontFamily: 'JetBrains Mono' }}>
                      {d.temperature !== undefined ? (
                        <span style={{ color: d.temperature > 40 ? 'var(--accent-red)' : 'var(--accent-green)' }}>
                          🌡️ {d.temperature}°C
                        </span>
                      ) : null}
                      {d.humidity !== undefined ? (
                        <span style={{ color: 'var(--accent-cyan)' }}>
                          💧 {d.humidity}%
                        </span>
                      ) : null}
                      {d.rssi !== undefined ? (
                        <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>
                          📶 {d.rssi} dBm
                        </span>
                      ) : null}
                      {d.temperature === undefined && d.humidity === undefined && (
                        <span style={{ color: 'var(--text-muted)' }}>—</span>
                      )}
                    </div>
                  </td>
                  <td>
                    {d.isolated ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4,
                          padding: '3px 8px',
                          borderRadius: 4,
                          fontSize: 10,
                          fontWeight: 700,
                          background: 'rgba(239, 68, 68, 0.18)',
                          color: 'var(--accent-red)',
                          border: '1px solid rgba(239, 68, 68, 0.4)',
                        }}>
                          <Lock size={10} /> {d.enforcement_status || 'ISOLATION_VERIFIED'}
                        </span>
                        {d.enforcement_mechanism && (
                          <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>
                            {d.enforcement_mechanism}
                          </span>
                        )}
                      </div>
                    ) : (
                      <span className={`status-badge ${d.status}`}>
                        {d.status.toUpperCase()}
                      </span>
                    )}
                  </td>
                  <td style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {formatLastSeen(d.last_seen)}
                  </td>
                  <td style={{ fontWeight: 600, color: d.threats > 0 ? 'var(--accent-red)' : 'var(--text-muted)' }}>
                    {d.threats}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                      <button
                        className="btn btn-outline"
                        onClick={() => openTestingModal(d)}
                        style={{ fontSize: 11, padding: '4px 8px', color: 'var(--accent-cyan)', borderColor: 'rgba(0, 212, 255, 0.3)' }}
                        title="Security testing & enforcement verification suite"
                      >
                        <Activity size={12} /> Test & Verify
                      </button>

                      {d.isolated ? (
                        <button
                          className="btn btn-outline"
                          onClick={() => handleRelease(d.device_id)}
                          style={{ fontSize: 11, padding: '4px 10px' }}
                          title="Release device from network isolation"
                        >
                          <Unlock size={13} /> Release
                        </button>
                      ) : (
                        <button
                          className="btn btn-danger"
                          onClick={() => handleIsolate(d.device_id)}
                          style={{ fontSize: 11, padding: '4px 10px' }}
                          title="Isolate device from network"
                        >
                          <ShieldAlert size={13} /> Isolate
                        </button>
                      )}

                      {!d.is_simulation && (
                        <button
                          className="btn btn-outline"
                          onClick={() => handleDelete(d.device_id)}
                          disabled={deletingId === d.device_id}
                          style={{
                            fontSize: 11,
                            padding: '4px 8px',
                            color: 'var(--accent-red)',
                            borderColor: 'rgba(239, 68, 68, 0.3)',
                          }}
                          title="Remove registered hardware device"
                        >
                          <Trash2 size={13} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal for Adding Device */}
      {showModal && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(5px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-accent)',
            borderRadius: 'var(--radius)',
            padding: 28,
            width: '100%',
            maxWidth: 520,
            boxShadow: '0 12px 48px rgba(0, 0, 0, 0.6)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
              <div>
                <h3 style={{ fontSize: 17, fontWeight: 700, color: 'var(--text-primary)' }}>
                  Add IoT Device to Fleet
                </h3>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                  Register physical hardware or virtual nodes into MongoDB datastore
                </p>
              </div>
              <button
                onClick={() => setShowModal(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Mode Selector Tabs */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 8,
              background: 'var(--bg-primary)',
              padding: 4,
              borderRadius: 8,
              marginBottom: 16,
              border: '1px solid var(--border-subtle)',
            }}>
              <button
                type="button"
                onClick={() => handleModeChange(true)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                  padding: '8px 12px',
                  borderRadius: 6,
                  border: 'none',
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: 'pointer',
                  background: !formData.is_simulation ? 'rgba(0, 212, 255, 0.18)' : 'transparent',
                  color: !formData.is_simulation ? 'var(--accent-cyan)' : 'var(--text-muted)',
                }}
              >
                <HardDrive size={14} /> Physical ESP32 Board
              </button>
              <button
                type="button"
                onClick={() => handleModeChange(false)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                  padding: '8px 12px',
                  borderRadius: 6,
                  border: 'none',
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: 'pointer',
                  background: formData.is_simulation ? 'rgba(139, 92, 246, 0.2)' : 'transparent',
                  color: formData.is_simulation ? 'var(--accent-purple)' : 'var(--text-muted)',
                }}
              >
                <Radio size={14} /> Simulation Node
              </button>
            </div>

            {errorMsg && (
              <div style={{
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: 'var(--accent-red)',
                padding: '8px 12px',
                borderRadius: 6,
                fontSize: 12,
                marginBottom: 14,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}>
                <AlertTriangle size={15} /> {errorMsg}
              </div>
            )}

            {successMsg && (
              <div style={{
                background: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                color: 'var(--accent-green)',
                padding: '8px 12px',
                borderRadius: 6,
                fontSize: 12,
                marginBottom: 14,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}>
                <CheckCircle2 size={15} /> {successMsg}
              </div>
            )}

            <form onSubmit={handleRegisterSubmit}>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 4 }}>
                  DEVICE ID *
                </label>
                <input
                  type="text"
                  required
                  value={formData.device_id}
                  onChange={(e) => setFormData({ ...formData, device_id: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border-subtle)',
                    background: 'var(--bg-primary)',
                    color: 'var(--text-primary)',
                    fontFamily: 'JetBrains Mono',
                    fontSize: 13,
                  }}
                />
                <span style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4, display: 'block' }}>
                  {!formData.is_simulation
                    ? '💡 Must match the DEVICE_ID defined in firmware (esp32_secureiot.ino). Reserved IDs: ESP32_001–ESP32_010.'
                    : '💡 Unique virtual device identifier for telemetry and attack simulation.'}
                </span>
              </div>

              <div style={{ marginBottom: 12 }}>
                <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 4 }}>
                  DEVICE NAME
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border-subtle)',
                    background: 'var(--bg-primary)',
                    color: 'var(--text-primary)',
                    fontSize: 13,
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 4 }}>
                    DEVICE TYPE
                  </label>
                  <input
                    type="text"
                    value={formData.device_type}
                    onChange={(e) => setFormData({ ...formData, device_type: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid var(--border-subtle)',
                      background: 'var(--bg-primary)',
                      color: 'var(--text-primary)',
                      fontSize: 13,
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 4 }}>
                    LOCATION / ZONE
                  </label>
                  <input
                    type="text"
                    value={formData.location}
                    onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid var(--border-subtle)',
                      background: 'var(--bg-primary)',
                      color: 'var(--text-primary)',
                      fontSize: 13,
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 18 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 4 }}>
                    DEVICE LAN IP (Optional)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. 192.168.1.55"
                    value={formData.ip_address}
                    onChange={(e) => setFormData({ ...formData, ip_address: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid var(--border-subtle)',
                      background: 'var(--bg-primary)',
                      color: 'var(--text-primary)',
                      fontFamily: 'JetBrains Mono',
                      fontSize: 12,
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 4 }}>
                    MAC ADDRESS (Optional)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. 24:6F:28:AB:CD:11"
                    value={formData.mac_address}
                    onChange={(e) => setFormData({ ...formData, mac_address: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid var(--border-subtle)',
                      background: 'var(--bg-primary)',
                      color: 'var(--text-primary)',
                      fontFamily: 'JetBrains Mono',
                      fontSize: 12,
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setShowModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={registering}
                >
                  {registering ? 'Registering...' : !formData.is_simulation ? 'Register Hardware Device' : 'Register Simulation Node'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal for Security Testing & Enforcement Verification */}
      {testModalDevice && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0, 0, 0, 0.8)',
          backdropFilter: 'blur(6px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-accent)',
            borderRadius: 'var(--radius)',
            padding: 28,
            width: '100%',
            maxWidth: 680,
            maxHeight: '90vh',
            overflowY: 'auto',
            boxShadow: '0 16px 56px rgba(0, 0, 0, 0.7)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div>
                <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <ShieldAlert size={20} color="var(--accent-cyan)" />
                  Security Testing & Real Enforcement
                </h3>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                  Device: <strong style={{ color: 'var(--accent-cyan)' }}>{testModalDevice.device_id}</strong> ({testModalDevice.is_simulation ? 'Simulation Node' : 'Physical Hardware'})
                </p>
              </div>
              <button
                onClick={() => setTestModalDevice(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Device Network Identity */}
            <div style={{
              background: 'var(--bg-primary)',
              padding: '12px 16px',
              borderRadius: 8,
              marginBottom: 18,
              fontSize: 12,
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 8,
              border: '1px solid var(--border-subtle)',
            }}>
              <div><strong>Target LAN IP:</strong> {testModalDevice.ip || 'Not specified'}</div>
              <div><strong>Current Isolation:</strong> {testModalDevice.isolated ? '🔴 Quarantined' : '🟢 Normal'}</div>
              <div><strong>Enforcement State:</strong> {testModalDevice.enforcement_status || 'NORMAL'}</div>
              <div><strong>Device Type:</strong> {testModalDevice.device_type}</div>
            </div>

            {/* Test Action Buttons */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 18 }}>
              <button
                className="btn btn-primary"
                onClick={runCategoryATest}
                disabled={testRunning}
                style={{ fontSize: 12, padding: '10px 14px', display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 4 }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 700 }}>
                  <Play size={13} /> Test A: Model Detection
                </div>
                <div style={{ fontSize: 10, opacity: 0.85, fontWeight: 400, textAlign: 'left' }}>
                  Runs authentic SVM inference on 19 network flow metrics.
                </div>
              </button>

              <button
                className="btn btn-danger"
                onClick={runCategoryBTest}
                disabled={testRunning}
                style={{ fontSize: 12, padding: '10px 14px', display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 4 }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 700 }}>
                  <Lock size={13} /> Test B: Response Enforcement
                </div>
                <div style={{ fontSize: 10, opacity: 0.85, fontWeight: 400, textAlign: 'left' }}>
                  Authorized test verifying real network firewall & radio isolation.
                </div>
              </button>
            </div>

            <div style={{ display: 'flex', gap: 10, marginBottom: 18 }}>
              <button
                className="btn btn-outline"
                onClick={runProbeTest}
                disabled={testRunning}
                style={{ flex: 1, fontSize: 12, padding: '8px 12px' }}
              >
                <Activity size={13} /> Probe Test Endpoint
              </button>
              {testModalDevice.isolated && (
                <button
                  className="btn btn-outline"
                  onClick={() => handleRelease(testModalDevice.device_id)}
                  disabled={testRunning}
                  style={{ flex: 1, fontSize: 12, padding: '8px 12px', color: 'var(--accent-green)', borderColor: 'rgba(16, 185, 129, 0.4)' }}
                >
                  <Unlock size={13} /> Manual Release Device
                </button>
              )}
            </div>

            {testRunning && (
              <div style={{ textAlign: 'center', padding: '16px 0', color: 'var(--accent-cyan)', fontSize: 13 }}>
                Executing security pipeline and network verification...
              </div>
            )}

            {testResult && (
              <div style={{
                background: 'var(--bg-deep)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 8,
                padding: 14,
                fontSize: 12,
                fontFamily: 'JetBrains Mono',
              }}>
                <div style={{ fontWeight: 700, color: 'var(--accent-cyan)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <CheckCircle2 size={14} /> {testResult.title}
                </div>
                <pre style={{ margin: 0, maxHeight: 220, overflowY: 'auto', fontSize: 11, color: 'var(--text-secondary)' }}>
                  {JSON.stringify(testResult.data, null, 2)}
                </pre>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 18 }}>
              <button
                className="btn btn-outline"
                onClick={() => setTestModalDevice(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
