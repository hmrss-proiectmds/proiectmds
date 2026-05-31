import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import './Navbar.css';

const roleLabels = {
  human_player: '👤 Player',
  ai_developer: '👨\u200d💻 Developer',
  ai_agent_owner: '🤖 Agent Owner',
  admin: '🛡️ Admin',
};

// roles that can register or manage agents
const AGENT_ROLES = new Set(['ai_developer', 'ai_agent_owner', 'admin']);
// roles that can run bulk simulations
const SIM_ROLES   = new Set(['ai_developer', 'admin']);

const NAV_ITEMS = [
  { to: '/',            label: 'Dashboard',   icon: '⊞' },
  { to: '/play',        label: 'Play',         icon: '▶', className: 'nav-link-play' },
  { to: '/agents',      label: 'Agents',       icon: '🤖', roles: AGENT_ROLES },
  { to: '/simulations', label: 'Simulate',     icon: '⚡', roles: SIM_ROLES },
  { to: '/developer',   label: 'Dev Tools',    icon: '🔬', roles: SIM_ROLES },
  { to: '/owner',       label: 'Fleet',        icon: '🛰️', roles: new Set(['ai_agent_owner', 'admin']) },
  { to: '/leaderboard', label: 'Leaderboard',  icon: '🏆' },
  { to: '/history',     label: 'History',      icon: '📜' },
  { to: '/spectate',    label: 'Spectate',     icon: '👁️' },
  { to: '/about',       label: 'About',        icon: 'ℹ️' },
];

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="navbar" id="main-navbar">
      <div className="navbar-inner">
        {/* Brand */}
        <Link to="/" className="navbar-brand">
          <span className="navbar-logo">🎲</span>
          <span className="navbar-title">GamePlatform</span>
        </Link>

        {user ? (
          <>
            {/* Nav links */}
            <div className="navbar-links">
              {NAV_ITEMS.map(({ to, label, icon, className, roles }) => {
                if (roles && !roles.has(user.role)) return null;
                const isActive = location.pathname === to || (to !== '/' && location.pathname.startsWith(to));
                return (
                  <Link
                    key={to}
                    to={to}
                    className={`nav-link ${className || ''} ${isActive ? 'nav-link-active' : ''}`}
                  >
                    <span className="nav-icon">{icon}</span>
                    {label}
                  </Link>
                );
              })}
              {user.role === 'admin' && (
                <Link
                  to="/admin"
                  className={`nav-link nav-link-admin ${location.pathname === '/admin' ? 'nav-link-active' : ''}`}
                >
                  <span className="nav-icon">🛡️</span>
                  Admin
                </Link>
              )}
            </div>

            {/* User info — pinned to bottom */}
            <div className="navbar-user">
              <div className="navbar-user-row">
                <span className="navbar-username">{user.username}</span>
                <span className="navbar-elo">{user.elo_rating} ELO</span>
              </div>
              <span className="badge badge-accent" style={{ alignSelf: 'flex-start' }}>
                {roleLabels[user.role] || '👤 Player'}
              </span>
              <button className="btn btn-ghost btn-sm w-full" onClick={handleLogout}>
                Logout
              </button>
            </div>
          </>
        ) : (
          <div className="navbar-links">
            <Link to="/login"    className="btn btn-ghost btn-sm">Login</Link>
            <Link to="/register" className="btn btn-primary btn-sm">Register</Link>
          </div>
        )}
      </div>
    </nav>
  );
}
