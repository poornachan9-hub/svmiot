/**
 * SecureIoT-X — Sidebar Navigation.
 */
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Shield, Cpu, Brain, Link2, Activity, ChartNoAxesCombined,
  Settings, Terminal, Play
} from 'lucide-react';

const navSections = [
  {
    title: 'Overview',
    items: [
      { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
      { to: '/threats', icon: Shield, label: 'Threat Monitor', badge: null },
      { to: '/devices', icon: Cpu, label: 'Device Fleet' },
    ]
  },
  {
    title: 'Intelligence',
    items: [
      { to: '/ai-models', icon: Brain, label: 'AI Models' },
      { to: '/blockchain', icon: Link2, label: 'Blockchain Ledger' },
      { to: '/analytics', icon: Activity, label: 'Analytics' },
      { to: '/model-analytics', icon: ChartNoAxesCombined, label: 'Model Analytics' },
    ]
  },
  {
    title: 'Operations',
    items: [
      { to: '/simulation', icon: Play, label: 'Simulation Lab' },
      { to: '/logs', icon: Terminal, label: 'System Logs' },
      { to: '/settings', icon: Settings, label: 'Settings' },
    ]
  }
];

export default function Sidebar({ threatCount = 0 }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="logo-icon">SX</div>
        <div>
          <h1>SecureIoT-X</h1>
          <span className="version">v1.0.0</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navSections.map((section) => (
          <div key={section.title} className="nav-section">
            <div className="nav-section-title">{section.title}</div>
            {section.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                end={item.to === '/'}
              >
                <item.icon size={18} />
                {item.label}
                {item.label === 'Threat Monitor' && threatCount > 0 && (
                  <span className="badge">{threatCount}</span>
                )}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
    </aside>
  );
}
