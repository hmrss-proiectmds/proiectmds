import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import './Navbar.css';

const roleLabels = {
  human_player: '👤 Player',
  ai_developer: '👨‍💻 Developer',
  ai_agent_owner: '🤖 Agent Owner',
  admin: '🛡️ Admin',
};

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="navbar" id="main-navbar">
      <div className="navbar-inner">
        <Link to="/" className="navbar-brand">
          <span className="navbar-logo">🎲</span>
          <span className="navbar-title">GamePlatform</span>
        </Link>

        {user ? (
          <div className="navbar-links">
            <Link to="/" className="nav-link">Dashboard</Link>
            <Link to="/play" className="nav-link nav-link-play">▶ Play</Link>
            <Link to="/leaderboard" className="nav-link">Leaderboard</Link>
            <Link to="/history" className="nav-link">History</Link>
            <Link to="/spectate" className="nav-link">Spectate</Link>
            {(user.role === 'admin') && (
              <Link to="/admin" className="nav-link nav-link-admin">Admin</Link>
            )}
            <div className="navbar-user">
              <span className="badge badge-accent">{roleLabels[user.role]}</span>
              <span className="navbar-username">{user.username}</span>
              <span className="navbar-elo font-mono">{user.elo_rating} ELO</span>
              <button className="btn btn-ghost btn-sm" onClick={handleLogout}>
                Logout
              </button>
            </div>
          </div>
        ) : (
          <div className="navbar-links">
            <Link to="/login" className="btn btn-ghost btn-sm">Login</Link>
            <Link to="/register" className="btn btn-primary btn-sm">Register</Link>
          </div>
        )}
      </div>
    </nav>
  );
}
