/**
 * SecureIoT-X — Header Bar.
 */
import { Bell, User } from 'lucide-react';

export default function Header({ title = 'Dashboard', systemStatus = 'online' }) {
  return (
    <header className="header">
      <div className="header-left">
        <h2>{title}</h2>
      </div>
      <div className="header-right">
        <div className={`status-indicator ${systemStatus}`}>
          <span className="pulse"></span>
          System {systemStatus === 'online' ? 'Online' : 'Offline'}
        </div>
        <button className="btn btn-outline" style={{ padding: '8px' }}>
          <Bell size={18} />
        </button>
        <button className="btn btn-outline" style={{ padding: '8px' }}>
          <User size={18} />
        </button>
      </div>
    </header>
  );
}
