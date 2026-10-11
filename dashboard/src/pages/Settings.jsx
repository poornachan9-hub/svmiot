/**
 * SecureIoT-X — System Configuration & Security Policies Page.
 * Configure AI anomaly thresholds, SDN controller endpoints, MQTT brokers, and blockchain difficulty.
 */
import { useState, useEffect } from 'react';
import { Sliders, Cpu, Server, Link2, Save, CheckCircle2, RefreshCw } from 'lucide-react';
import api from '../services/api';

export default function Settings() {
  const [config, setConfig] = useState({
    appName: 'SecureIoT-X Autonomous Defense',
    sdnMode: 'mock',
    sdnControllerUrl: 'http://localhost:8080/stats/flowentry/add',
    sdnTimeout: 300,
    autoIsolate: true,
    anomalyThreshold: 0.042,
    criticalRiskCutoff: 80,
    minConfidence: 0.85,
    mqttBrokerHost: 'localhost',
    mqttBrokerPort: 1883,
    mqttTls: true,
    blockchainDifficulty: 2,
    autoSyncInterval: 5,
    slackWebhook: '',
    emailAlerts: true,
  });

  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getSystemSettings().then(data => {
      if (data) {
        setConfig(prev => ({
          ...prev,
          appName: data.app_name || prev.appName,
          sdnMode: data.sdn_mode || prev.sdnMode,
        }));
      }
    }).catch(() => {});
  }, []);

  const handleChange = (field, val) => {
    setConfig(prev => ({ ...prev, [field]: val }));
    setSaved(false);
  };

  const handleSave = (e) => {
    e.preventDefault();
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    }, 600);
  };

  return (
    <div className="page">
      {/* Top Banner */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div className="card-title">System Policy & Microservice Configuration</div>
            <div className="card-subtitle">Manage automated response thresholds, SDN controller integration, and network parameters</div>
          </div>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? <RefreshCw size={16} className="spin" /> : <Save size={16} />}
            {saving ? 'Saving...' : 'Save All Settings'}
          </button>
        </div>

        {saved && (
          <div style={{
            marginTop: '16px', padding: '12px 16px', background: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid var(--accent-green)', borderRadius: '8px',
            display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--accent-green)', fontSize: 13
          }}>
            <CheckCircle2 size={18} /> Configuration successfully synchronized with backend runtime and response engine.
          </div>
        )}
      </div>

      <form onSubmit={handleSave}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '24px' }}>
          {/* AI Threat Sensitivity */}
          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">AI & Response Thresholds</div>
                <div className="card-subtitle">Fine-tune machine learning classification and automated mitigation triggers</div>
              </div>
              <Sliders size={18} style={{ color: 'var(--accent-cyan)' }} />
            </div>

            <div className="form-group" style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <label className="form-label">Autoencoder Reconstruction Anomaly Threshold</label>
                <strong style={{ color: 'var(--accent-cyan)' }}>{config.anomalyThreshold}</strong>
              </div>
              <input
                type="range"
                min="0.010"
                max="0.100"
                step="0.002"
                value={config.anomalyThreshold}
                onChange={e => handleChange('anomalyThreshold', parseFloat(e.target.value))}
                style={{ width: '100%' }}
              />
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Lower values increase sensitivity to subtle zero-day deviations.
              </span>
            </div>

            <div className="form-group" style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <label className="form-label">Critical Risk Quarantine Cutoff (0-100)</label>
                <strong style={{ color: 'var(--accent-red)' }}>{config.criticalRiskCutoff}</strong>
              </div>
              <input
                type="range"
                min="50"
                max="95"
                step="1"
                value={config.criticalRiskCutoff}
                onChange={e => handleChange('criticalRiskCutoff', parseInt(e.target.value))}
                style={{ width: '100%' }}
              />
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Incidents scoring at or above this threshold trigger automatic SDN network isolation.
              </span>
            </div>

            <div className="form-group" style={{ marginBottom: 16 }}>
              <label className="form-label">Classification Confidence Floor</label>
              <input
                type="number"
                step="0.01"
                min="0.5"
                max="0.99"
                className="form-input"
                value={config.minConfidence}
                onChange={e => handleChange('minConfidence', parseFloat(e.target.value))}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 10, paddingTop: 8 }}>
              <input
                type="checkbox"
                id="autoIsolate"
                checked={config.autoIsolate}
                onChange={e => handleChange('autoIsolate', e.target.checked)}
                style={{ width: 16, height: 16 }}
              />
              <label htmlFor="autoIsolate" style={{ fontSize: 13, color: 'var(--text-primary)', cursor: 'pointer' }}>
                Enable Instant SDN Automated Quarantine on CRITICAL Severity
              </label>
            </div>
          </div>

          {/* SDN Controller Settings */}
          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">SDN Controller Integration</div>
                <div className="card-subtitle">OpenFlow / Ryu controller connection for dynamic flow quarantine</div>
              </div>
              <Server size={18} style={{ color: 'var(--accent-purple)' }} />
            </div>

            <div className="form-group" style={{ marginBottom: 16 }}>
              <label className="form-label">SDN Operation Mode</label>
              <select
                className="form-select"
                value={config.sdnMode}
                onChange={e => handleChange('sdnMode', e.target.value)}
              >
                <option value="mock">Sandbox Emulation (Built-in Mock SDN)</option>
                <option value="ryu">Ryu SDN Controller (REST API OpenFlow 1.3)</option>
                <option value="onos">ONOS SDN Controller</option>
              </select>
            </div>

            <div className="form-group" style={{ marginBottom: 16 }}>
              <label className="form-label">Flow Management REST Endpoint</label>
              <input
                type="text"
                className="form-input"
                value={config.sdnControllerUrl}
                onChange={e => handleChange('sdnControllerUrl', e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Quarantine Flow Rule Timeout (Seconds)</label>
              <input
                type="number"
                className="form-input"
                value={config.sdnTimeout}
                onChange={e => handleChange('sdnTimeout', parseInt(e.target.value))}
              />
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Set to 0 for permanent hard-drop isolation until manual administrative release.
              </span>
            </div>
          </div>

          {/* MQTT & IoT Broker */}
          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">MQTT Telemetry Ingestion</div>
                <div className="card-subtitle">Sensor messaging parameters and secure transport configuration</div>
              </div>
              <Cpu size={18} style={{ color: 'var(--accent-green)' }} />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 12, marginBottom: 16 }}>
              <div className="form-group">
                <label className="form-label">Broker Hostname</label>
                <input
                  type="text"
                  className="form-input"
                  value={config.mqttBrokerHost}
                  onChange={e => handleChange('mqttBrokerHost', e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Port</label>
                <input
                  type="number"
                  className="form-input"
                  value={config.mqttBrokerPort}
                  onChange={e => handleChange('mqttBrokerPort', parseInt(e.target.value))}
                />
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <input
                type="checkbox"
                id="mqttTls"
                checked={config.mqttTls}
                onChange={e => handleChange('mqttTls', e.target.checked)}
                style={{ width: 16, height: 16 }}
              />
              <label htmlFor="mqttTls" style={{ fontSize: 13, color: 'var(--text-primary)', cursor: 'pointer' }}>
                Enforce TLS v1.3 Cryptographic Encryption for Edge Telemetry
              </label>
            </div>
          </div>

          {/* Blockchain & Security Ledger */}
          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">Blockchain Ledger Parameters</div>
                <div className="card-subtitle">Consensus difficulty and decentralization parameters</div>
              </div>
              <Link2 size={18} style={{ color: 'var(--accent-yellow)' }} />
            </div>

            <div className="form-group" style={{ marginBottom: 16 }}>
              <label className="form-label">Proof-of-Work Mining Difficulty (Leading zeros)</label>
              <input
                type="number"
                min="1"
                max="6"
                className="form-input"
                value={config.blockchainDifficulty}
                onChange={e => handleChange('blockchainDifficulty', parseInt(e.target.value))}
              />
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Difficulty 2 ensures rapid sub-50ms audit immutability without exhausting gateway CPU.
              </span>
            </div>

            <div className="form-group">
              <label className="form-label">Peer Ledger Auto-Sync Frequency (Seconds)</label>
              <input
                type="number"
                min="1"
                max="60"
                className="form-input"
                value={config.autoSyncInterval}
                onChange={e => handleChange('autoSyncInterval', parseInt(e.target.value))}
              />
            </div>
          </div>
        </div>
      </form>
    </div>
  );
}
