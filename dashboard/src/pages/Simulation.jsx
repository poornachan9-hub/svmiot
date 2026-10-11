/**
 * SecureIoT-X — Simulation Lab & Red Team Testing Page.
 * All data comes from real backend pipeline — no setTimeout fake logs.
 * Works for ALL 10 registered simulation devices.
 */
import { useState, useEffect } from 'react';
import { Play, Flame, ShieldAlert, Cpu, Terminal, Zap, Radio, Unlock } from 'lucide-react';
import api from '../services/api';

const ATTACK_TYPES = [
  { id: 'DDoS', name: 'DDoS SYN Flood', desc: 'Volumetric TCP SYN flood overwhelming target edge node.', severity: 'CRITICAL', color: '#ef4444' },
  { id: 'DoS', name: 'DoS TCP Flood', desc: 'Single-source TCP flood designed to exhaust device connection table.', severity: 'CRITICAL', color: '#dc2626' },
  { id: 'Reconnaissance', name: 'Port Scan Recon', desc: 'Rapid SYN/ACK scanning across privileged ports (22, 80, 502, 1883).', severity: 'HIGH', color: '#f97316' },
  { id: 'Brute_Force', name: 'Brute Force Auth', desc: 'Dictionary attack against local MQTT authentication broker.', severity: 'HIGH', color: '#f59e0b' },
  { id: 'Spoofing', name: 'ARP Spoofing', desc: 'Poisoning ARP cache to intercept and alter sensor payloads.', severity: 'HIGH', color: '#8b5cf6' },
  { id: 'MITM', name: 'Man-in-the-Middle', desc: 'Intercepting unencrypted MQTT traffic between sensor and gateway.', severity: 'CRITICAL', color: '#e11d48' },
];

const SCENARIOS = [
  {
    id: 'ddos_attack',
    name: 'DDoS Attack Sequence',
    desc: 'Normal traffic → suspicious anomalies → full DDoS flood on target device.',
    duration: '3 stages',
  },
  {
    id: 'repeated_malicious',
    name: 'Repeated Malicious Activity',
    desc: 'Multiple consecutive attacks from the same device to test escalation logic.',
    duration: '7 events',
  },
  {
    id: 'full_demo',
    name: 'Full Demo (Mixed)',
    desc: 'Complete sequence: normal → suspicious → DDoS + Brute Force across multiple devices.',
    duration: '15 events',
  },
];

export default function Simulation() {
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState('ESP32_003');
  const [activeSimulation, setActiveSimulation] = useState(false);
  const [simLogs, setSimLogs] = useState([
    { id: 1, time: new Date().toLocaleTimeString(), type: 'INFO', msg: 'Simulation Lab initialized. Connecting to backend...' },
  ]);
  const [simStats, setSimStats] = useState({ eventsSent: 0, threatsTriggered: 0, automatedMitigations: 0 });

  // Fetch devices on mount
  useEffect(() => {
    loadDevices();
  }, []);

  const loadDevices = async () => {
    try {
      const devs = await api.getSimDevices();
      setDevices(devs);
      addLog('SUCCESS', `Loaded ${devs.length} simulation devices from MongoDB.`);
    } catch (e) {
      addLog('ERROR', `Could not load devices: ${e.message}. Is the backend running?`);
    }
  };

  const addLog = (type, msg) => {
    setSimLogs(prev => [
      { id: Date.now() + Math.random(), time: new Date().toLocaleTimeString(), type, msg },
      ...prev
    ].slice(0, 80));
  };

  const handleInjectAttack = async (atk) => {
    setActiveSimulation(true);
    addLog('INFO', `[INJECT] Launching ${atk.name} against ${selectedDevice}...`);

    try {
      const result = await api.simulateAttack(selectedDevice, atk.id);

      // Log each pipeline step from the real backend response
      if (result.pipeline) {
        result.pipeline.forEach(step => {
          const stepType = step.status === 'OK' ? 'SUCCESS' :
                          step.status === 'ERROR' ? 'ERROR' :
                          step.status === 'NOT_CONNECTED' ? 'WARN' : 'INFO';
          addLog(stepType, `[${step.step}] ${step.detail}`);
        });
      }

      // Summary log
      addLog(result.severity === 'CRITICAL' || result.severity === 'HIGH' ? 'CRITICAL' : 'INFO',
        `[RESULT] Prediction=${result.prediction} Confidence=${(result.confidence * 100).toFixed(1)}% ` +
        `Risk=${result.risk_score} Severity=${result.severity} Action=${result.action}`
      );

      if (result.tx_hash) {
        addLog('SUCCESS', `[BLOCKCHAIN] Ganache Tx: ${result.tx_hash.substring(0, 20)}... Block #${result.ganache_block}`);
      }

      // Telegram notification status
      if (result.telegram) {
        const tg = result.telegram;
        if (tg.sent) {
          addLog('SUCCESS', `[TELEGRAM] ✉️ Alert sent! Message ID: ${tg.message_id}`);
        } else if (tg.reason === 'TELEGRAM_NOT_CONFIGURED') {
          addLog('INFO', `[TELEGRAM] Not configured — set TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID in .env`);
        } else if (tg.reason) {
          addLog('INFO', `[TELEGRAM] Skipped — ${tg.reason}`);
        } else {
          addLog('WARN', `[TELEGRAM] Failed — ${tg.error || 'unknown error'}`);
        }
      }

      if (result.isolation_applied) {
        addLog('CRITICAL', `[ISOLATION] Device ${selectedDevice} is now ISOLATED.`);
      }

      // Update stats
      setSimStats(prev => ({
        eventsSent: prev.eventsSent + 1,
        threatsTriggered: prev.threatsTriggered + (result.severity === 'HIGH' || result.severity === 'CRITICAL' ? 1 : 0),
        automatedMitigations: prev.automatedMitigations + (result.isolation_applied ? 1 : 0),
      }));

      // Refresh devices to show updated isolation state
      await loadDevices();
    } catch (e) {
      addLog('ERROR', `Simulation failed: ${e.message}`);
    }
    setActiveSimulation(false);
  };

  const handleRelease = async (deviceId) => {
    addLog('INFO', `[RELEASE] Requesting release for ${deviceId}...`);
    try {
      const result = await api.releaseSimDevice(deviceId);
      addLog('SUCCESS', `[RELEASE] ${deviceId} → ${result.status || 'NORMAL'}`);
      await loadDevices();
    } catch (e) {
      addLog('ERROR', `Release failed: ${e.message}`);
    }
  };

  const handleRunScenario = async (sc) => {
    setActiveSimulation(true);
    addLog('INFO', `[SCENARIO] Starting: "${sc.name}"...`);

    try {
      const result = await api.runScenario(sc.id);
      addLog('SUCCESS', `[SCENARIO] Generated ${result.events_generated} events.`);

      // Log summary of events
      const attacks = (result.events || []).filter(e => e.severity === 'HIGH' || e.severity === 'CRITICAL');
      if (attacks.length > 0) {
        attacks.forEach(ev => {
          addLog('WARN', `[EVENT] ${ev.device_id} → ${ev.prediction || ev.label} (Risk: ${ev.risk_score}, Action: ${ev.action})`);
        });
        setSimStats(prev => ({
          eventsSent: prev.eventsSent + result.events_generated,
          threatsTriggered: prev.threatsTriggered + attacks.length,
          automatedMitigations: prev.automatedMitigations,
        }));
      } else {
        setSimStats(prev => ({ ...prev, eventsSent: prev.eventsSent + result.events_generated }));
      }
    } catch (e) {
      addLog('ERROR', `Scenario failed: ${e.message}`);
    }
    await loadDevices();
    setActiveSimulation(false);
  };

  const isolatedCount = devices.filter(d => d.is_isolated).length;

  return (
    <div className="page">
      {/* Top Stat Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon cyan"><Zap size={22} /></div>
          <div className="stat-content">
            <h3>{simStats.eventsSent}</h3>
            <p>Simulated Events</p>
            <div className="stat-change positive">Active Sandbox</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon red"><Flame size={22} /></div>
          <div className="stat-content">
            <h3>{simStats.threatsTriggered}</h3>
            <p>Attacks Detected</p>
            <div className="stat-change negative">Real SVM Inference</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green"><ShieldAlert size={22} /></div>
          <div className="stat-content">
            <h3>{simStats.automatedMitigations}</h3>
            <p>Auto-Isolations</p>
            <div className="stat-change positive">{isolatedCount} devices isolated</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon purple"><Cpu size={22} /></div>
          <div className="stat-content">
            <h3>Target</h3>
            <p>{selectedDevice}</p>
            <div className="stat-change">{devices.length} devices loaded</div>
          </div>
        </div>
      </div>

      {/* Target Device Selector — ALL devices from MongoDB */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '16px' }}>
          <div>
            <div className="card-title">Target IoT Device Selection</div>
            <div className="card-subtitle">Choose any device from the MongoDB simulation registry</div>
          </div>
          <button className="btn btn-outline" onClick={loadDevices} style={{ fontSize: 11, padding: '5px 12px' }}>
            ↻ Refresh
          </button>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '12px' }}>
          {devices.map(d => {
            const isIsolated = d.is_isolated;
            const isSelected = selectedDevice === d.device_id;
            return (
              <button
                key={d.device_id}
                className={`btn ${isSelected ? 'btn-primary' : isIsolated ? 'btn-danger' : 'btn-outline'}`}
                onClick={() => setSelectedDevice(d.device_id)}
                style={{
                  fontSize: 11,
                  padding: '6px 12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  opacity: isIsolated && !isSelected ? 0.8 : 1,
                }}
              >
                <span style={{
                  width: 7,
                  height: 7,
                  borderRadius: '50%',
                  background: isIsolated ? '#ef4444' : '#10b981',
                  display: 'inline-block',
                }} />
                {d.device_id}
                {isIsolated && (
                  <button
                    className="btn btn-outline"
                    onClick={(e) => { e.stopPropagation(); handleRelease(d.device_id); }}
                    style={{ fontSize: 9, padding: '2px 6px', marginLeft: 4 }}
                    title="Release device"
                  >
                    <Unlock size={10} /> Release
                  </button>
                )}
              </button>
            );
          })}
          {devices.length === 0 && (
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              No devices loaded. Is MongoDB & backend running?
            </span>
          )}
        </div>
      </div>

      {/* Attack Injection Controls Grid */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header">
          <div>
            <div className="card-title">Attack Vectors & Traffic Injection</div>
            <div className="card-subtitle">Inject attack features → real SVM prediction → risk → isolation → MongoDB → Ganache</div>
          </div>
          <Flame size={18} style={{ color: 'var(--accent-red)' }} />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
          {ATTACK_TYPES.map(atk => (
            <div
              key={atk.id}
              style={{
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '14px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>{atk.name}</span>
                  <span className={`severity-badge ${atk.severity.toLowerCase()}`} style={{ fontSize: 10 }}>{atk.severity}</span>
                </div>
                <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 12, minHeight: 32 }}>
                  {atk.desc}
                </p>
              </div>
              <button
                className="btn btn-danger"
                onClick={() => handleInjectAttack(atk)}
                disabled={activeSimulation}
                style={{ fontSize: 11, padding: '7px 10px', width: '100%' }}
              >
                <Zap size={13} /> Inject → {selectedDevice}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Two Columns: Full Scenarios & Real-Time Defense Terminal */}
      <div className="charts-grid">
        {/* Scenarios */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Predefined Scenarios</div>
              <div className="card-subtitle">Execute multi-event attack sequences</div>
            </div>
            <Radio size={18} style={{ color: 'var(--accent-cyan)' }} />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {SCENARIOS.map(sc => (
              <div
                key={sc.id}
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '14px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, color: 'var(--accent-cyan)', fontSize: 13 }}>{sc.name}</span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)', background: 'var(--bg-card)', padding: '2px 8px', borderRadius: 4 }}>
                    {sc.duration}
                  </span>
                </div>
                <p style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 10 }}>
                  {sc.desc}
                </p>
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <button
                    className="btn btn-outline"
                    onClick={() => handleRunScenario(sc)}
                    disabled={activeSimulation}
                    style={{ fontSize: 11, padding: '5px 12px' }}
                  >
                    <Play size={12} /> Run Scenario
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Real-time Defense Terminal */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Live Defense Execution Terminal</div>
              <div className="card-subtitle">Real-time trace from backend pipeline (no simulated logs)</div>
            </div>
            <Terminal size={18} style={{ color: 'var(--accent-green)' }} />
          </div>

          <div style={{
            background: '#0a0d18',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '8px',
            padding: '14px',
            height: '380px',
            overflowY: 'auto',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 11,
            lineHeight: 1.6,
          }}>
            {simLogs.map(log => {
              let color = '#94a3b8';
              if (log.type === 'SUCCESS') color = 'var(--accent-green)';
              if (log.type === 'WARN') color = 'var(--accent-yellow)';
              if (log.type === 'CRITICAL' || log.type === 'ERROR') color = 'var(--accent-red)';
              if (log.type === 'INFO') color = 'var(--accent-cyan)';

              return (
                <div key={log.id} style={{ marginBottom: 4, display: 'flex', gap: 8 }}>
                  <span style={{ color: '#475569', flexShrink: 0 }}>[{log.time}]</span>
                  <span style={{ color, flex: 1, wordBreak: 'break-all' }}>{log.msg}</span>
                </div>
              );
            })}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10 }}>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {activeSimulation ? '⟳ Running pipeline...' : '● Idle & monitoring'}
            </span>
            <button className="btn btn-outline" onClick={() => setSimLogs([])} style={{ fontSize: 11, padding: '4px 10px' }}>
              Clear Terminal
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
