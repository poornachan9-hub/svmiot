/**
 * SecureIoT-X — Main Application Root.
 * Configures routing, sidebar navigation, dynamic headers, and global WebSocket connection.
 */
import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';

import Sidebar from './components/Sidebar';
import Header from './components/Header';

import Dashboard from './pages/Dashboard';
import Threats from './pages/Threats';
import Devices from './pages/Devices';
import AIModels from './pages/AIModels';
import Blockchain from './pages/Blockchain';
import Analytics from './pages/Analytics';
import ModelAnalytics from './pages/ModelAnalytics';
import Simulation from './pages/Simulation';
import SystemLogs from './pages/SystemLogs';
import Settings from './pages/Settings';

import api from './services/api';

const ROUTE_TITLES = {
  '/': 'Security Operations Center',
  '/threats': 'Threat Monitor & Incident Response',
  '/devices': 'Connected IoT Device Fleet',
  '/ai-models': 'AI Detection Engine & Models',
  '/blockchain': 'Blockchain Audit Ledger',
  '/analytics': 'Security Analytics & Risk Intelligence',
  '/model-analytics': 'Model Analytics · Deduplicated Evaluation',
  '/simulation': 'Simulation Lab & Red Team Testing',
  '/logs': 'System Logs & Audit Trail',
  '/settings': 'System Policies & Microservice Configuration',
};

function AppContent() {
  const location = useLocation();
  const [threatCount, setThreatCount] = useState(0);
  const [systemStatus, setSystemStatus] = useState('checking');

  const pageTitle = ROUTE_TITLES[location.pathname] || 'SecureIoT-X';

  useEffect(() => {
    // Check backend health
    api.getHealth()
      .then(() => setSystemStatus('online'))
      .catch(() => setSystemStatus('offline'));

    // Connect WebSocket
    try {
      api.connectWS();

      api.onWS('threat_detected', (evt) => {
        console.log('[WS Alert] Threat detected:', evt);
        setThreatCount(prev => prev + 1);
      });

      api.onWS('device_isolated', (evt) => {
        console.log('[WS Alert] Device isolated:', evt);
      });
    } catch (e) {
      console.warn('WebSocket init warning:', e);
    }

    return () => {
      api.offWS('threat_detected');
      api.offWS('device_isolated');
    };
  }, []);

  return (
    <div className="app-layout">
      <Sidebar threatCount={threatCount} />
      <div className="main-content">
        <Header title={pageTitle} systemStatus={systemStatus} />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/threats" element={<Threats />} />
          <Route path="/devices" element={<Devices />} />
          <Route path="/ai-models" element={<AIModels />} />
          <Route path="/blockchain" element={<Blockchain />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/model-analytics" element={<ModelAnalytics />} />
          <Route path="/simulation" element={<Simulation />} />
          <Route path="/logs" element={<SystemLogs />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}
