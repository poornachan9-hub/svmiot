/**
 * SecureIoT-X — API Service Layer.
 * Handles all HTTP + WebSocket communication with the FastAPI backend.
 *
 * Docker: VITE_API_BASE=/api (nginx proxies to backend container)
 * Local:  falls back to http://localhost:8000/api
 */

const API_BASE = import.meta.env.VITE_API_BASE || (
  typeof window !== 'undefined' && (window.location.port === '3000' || window.location.port === '5173')
    ? '/api'
    : 'http://127.0.0.1:8000/api'
);

// Auto-detect WebSocket URL: if API is relative (Docker/Vite proxy), use same host
const _isRelative = API_BASE.startsWith('/');
const WS_BASE = _isRelative
  ? `${typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${typeof window !== 'undefined' ? window.location.host : '127.0.0.1:8000'}/ws`
  : 'ws://127.0.0.1:8000/ws';

class APIService {
  constructor() {
    this.token = typeof localStorage !== 'undefined' ? localStorage.getItem('secureiot_token') : null;
    this.ws = null;
    this.wsListeners = new Map();
  }

  // ── Auth Headers ────────────────────────────────────────
  get headers() {
    const h = { 'Content-Type': 'application/json' };
    if (this.token) h['Authorization'] = `Bearer ${this.token}`;
    return h;
  }

  // ── Generic Fetch ───────────────────────────────────────
  async request(path, options = {}) {
    const url = `${API_BASE}${path}`;
    try {
      const resp = await fetch(url, {
        headers: this.headers,
        ...options,
      });
      if (!resp.ok) {
        // If relative proxy gives 404 in dev, try direct 127.0.0.1:8000
        if (resp.status === 404 && API_BASE === '/api') {
          const directResp = await fetch(`http://127.0.0.1:8000/api${path}`, {
            headers: this.headers,
            ...options,
          });
          if (directResp.ok) {
            return directResp.json();
          }
        }
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${resp.status}`);
      }
      return resp.json();
    } catch (e) {
      // If relative fetch failed due to network error, try direct backend fallback
      if (API_BASE === '/api') {
        try {
          const directResp = await fetch(`http://127.0.0.1:8000/api${path}`, {
            headers: this.headers,
            ...options,
          });
          if (directResp.ok) {
            return directResp.json();
          }
          const err = await directResp.json().catch(() => ({}));
          throw new Error(err.detail || `HTTP ${directResp.status}`);
        } catch {
          // If direct fallback also failed, rethrow original useful error
        }
      }
      console.error(`API error [${path}]:`, e.message);
      throw e;
    }
  }

  // ── Auth ────────────────────────────────────────────────
  async login(username, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    this.token = data.access_token;
    localStorage.setItem('secureiot_token', data.access_token);
    return data;
  }

  logout() {
    this.token = null;
    localStorage.removeItem('secureiot_token');
  }

  // ── Health ──────────────────────────────────────────────
  async getHealth() { return this.request('/health'); }

  // ── Devices ─────────────────────────────────────────────
  async getDevices() { return this.request('/devices'); }
  async registerDevice(deviceData) {
    return this.request('/devices', {
      method: 'POST',
      body: JSON.stringify(deviceData),
    });
  }
  async isolateDevice(id) { return this.request(`/devices/${id}/isolate`, { method: 'POST' }); }
  async releaseDevice(id) { return this.request(`/devices/${id}/release`, { method: 'POST' }); }
  async deleteDevice(id) { return this.request(`/devices/${id}`, { method: 'DELETE' }); }
  async getEnforcementDetails(id) { return this.request(`/devices/${id}/enforcement`); }
  async probeTestEndpoint(id) { return this.request(`/devices/probe/test?device_id=${id}`); }
  async runDetectionTest(id) { return this.request(`/devices/${id}/test/detection`, { method: 'POST' }); }
  async runEnforcementTest(id) { return this.request(`/devices/${id}/test/enforcement`, { method: 'POST' }); }
  async getDeviceTelemetry(deviceId, limit = 50) {
    return this.request(`/devices/${deviceId}/telemetry?limit=${limit}`);
  }
  async getRecentTelemetry(limit = 50) {
    return this.request(`/devices/telemetry/recent?limit=${limit}`);
  }

  // ── Predictions ─────────────────────────────────────────
  async predict(deviceId, features) {
    return this.request('/predict', {
      method: 'POST',
      body: JSON.stringify({ device_id: deviceId, features }),
    });
  }
  async getPredictions(limit = 50) { return this.request(`/predictions?limit=${limit}`); }

  // ── Threats ─────────────────────────────────────────────
  async getThreats(limit = 50) { return this.request(`/threats?limit=${limit}`); }

  // ── Blockchain ──────────────────────────────────────────
  async getBlockchainStatus() { return this.request('/blockchain/status'); }
  async getBlocks(limit = 20) { return this.request(`/blockchain/blocks?limit=${limit}`); }
  async validateChain() { return this.request('/blockchain/verify', { method: 'POST' }); }
  async tamperTest() { return this.request('/blockchain/tamper-test', { method: 'POST' }); }

  // ── Analytics ───────────────────────────────────────────
  async getOverview() { return this.request('/analytics/overview'); }
  async getAIMetrics() { return this.request('/analytics/metrics'); }
  async getModelComparison() { return this.request('/analytics/comparison'); }
  async getModelEvaluation() { return this.request('/analytics/model-evaluation'); }

  // ── Models ──────────────────────────────────────────────
  async getModels() { return this.request('/models'); }
  async getModelReport() { return this.request('/models/report'); }
  async getModelSample() { return this.request('/models/sample'); }
  async getEvaluationRuns() { return this.request('/models/evaluation-runs'); }
  async getEvaluationReport(runId = 'deduplicated') {
    return this.request(`/models/evaluation-report?run_id=${encodeURIComponent(runId)}`);
  }
  async activateModel(name, version) {
    const versionQuery = version ? `?version=${encodeURIComponent(version)}` : '';
    return this.request(`/models/${encodeURIComponent(name)}/activate${versionQuery}`, { method: 'POST' });
  }

  // ── Simulation ──────────────────────────────────────────
  async simulateAttack(deviceId, attackType) {
    return this.request('/simulate/attack', {
      method: 'POST',
      body: JSON.stringify({ device_id: deviceId, attack_type: attackType }),
    });
  }
  async releaseSimDevice(deviceId) {
    return this.request('/simulate/release', {
      method: 'POST',
      body: JSON.stringify({ device_id: deviceId }),
    });
  }
  async getSimDevices() { return this.request('/simulate/devices'); }
  async simulateEvent(type = 'normal') {
    return this.request(`/simulate/event?event_type=${type}`, { method: 'POST' });
  }
  async runScenario(scenario) {
    return this.request('/simulate/scenario', {
      method: 'POST',
      body: JSON.stringify({ scenario }),
    });
  }
  async getScenarios() { return this.request('/simulate/scenarios'); }

  // ── Ganache ─────────────────────────────────────────────
  async getGanacheStatus() { return this.request('/blockchain/ganache/status'); }
  async verifyGanacheTx(txHash) { return this.request(`/blockchain/ganache/verify/${txHash}`); }

  // ── System ──────────────────────────────────────────────
  async getSystemLogs(limit = 100) { return this.request(`/system/logs?limit=${limit}`); }
  async getAuditTrail(limit = 100) { return this.request(`/system/audit?limit=${limit}`); }
  async getSystemSettings() { return this.request('/system/settings'); }

  // ── WebSocket ───────────────────────────────────────────
  connectWS() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return;

    this.ws = new WebSocket(WS_BASE);

    this.ws.onopen = () => console.log('[WS] Connected');

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const listeners = this.wsListeners.get(data.type) || [];
        listeners.forEach(cb => cb(data.data));
      } catch (e) {
        console.warn('[WS] Parse error:', e);
      }
    };

    this.ws.onclose = () => {
      console.log('[WS] Disconnected, reconnecting in 3s...');
      setTimeout(() => this.connectWS(), 3000);
    };

    this.ws.onerror = (err) => console.error('[WS] Error:', err);
  }

  onWS(type, callback) {
    if (!this.wsListeners.has(type)) this.wsListeners.set(type, []);
    this.wsListeners.get(type).push(callback);
  }

  offWS(type) {
    this.wsListeners.delete(type);
  }
}

export const api = new APIService();
export default api;
