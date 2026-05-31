import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { api } from '../api/client';
import './AdminPanel.css'; // reuse table/card styles

const STATUS_BADGE  = { active: 'badge-success', paused: 'badge-accent', banned: 'badge-error' };
const STATUS_ICON   = { active: '🟢', paused: '⏸', banned: '🚫' };

function timeAgo(dateStr) {
  if (!dateStr) return '—';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function AgentOwnerHub() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [fleet, setFleet]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  useEffect(() => {
    if (user && user.role !== 'ai_agent_owner' && user.role !== 'admin') {
      navigate('/');
      return;
    }
    api.get('/api/owner/fleet')
      .then(setFleet)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [user, navigate]);

  const total   = fleet.length;
  const active  = fleet.filter(a => a.status === 'active').length;
  const inQueue = fleet.filter(a => a.in_queue).length;
  const inGame  = fleet.filter(a => a.in_game_id).length;

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">🛰️ Agent Fleet</h1>
        <p className="page-subtitle">Live status of your deployed webhook agents</p>
      </div>

      {error && <div className="alert alert-error mb-4">{error}</div>}

      {/* Summary cards */}
      <div className="admin-stats-grid" style={{ marginBottom: '1.5rem' }}>
        <div className="admin-stat-card card" style={{ borderTop: '3px solid #6366f1' }}>
          <div className="admin-stat-icon">🛰️</div>
          <div className="admin-stat-value">{total}</div>
          <div className="admin-stat-label">Total Agents</div>
        </div>
        <div className="admin-stat-card card" style={{ borderTop: '3px solid #22c55e' }}>
          <div className="admin-stat-icon">🟢</div>
          <div className="admin-stat-value">{active}</div>
          <div className="admin-stat-label">Active</div>
        </div>
        <div className="admin-stat-card card" style={{ borderTop: '3px solid #06b6d4' }}>
          <div className="admin-stat-icon">🕐</div>
          <div className="admin-stat-value">{inQueue}</div>
          <div className="admin-stat-label">In Queue</div>
        </div>
        <div className="admin-stat-card card" style={{ borderTop: '3px solid #f59e0b' }}>
          <div className="admin-stat-icon">⚡</div>
          <div className="admin-stat-value">{inGame}</div>
          <div className="admin-stat-label">In Game</div>
        </div>
      </div>

      {/* Role capabilities info */}
      <div className="card" style={{ padding: '1rem', marginBottom: '1.5rem', background: 'rgba(139,92,246,0.06)', borderLeft: '3px solid #8b5cf6' }}>
        <strong style={{ fontSize: '0.85rem' }}>Agent Owner Capabilities</strong>
        <ul style={{ margin: '0.5rem 0 0', paddingLeft: '1.2rem', fontSize: '0.8rem', color: 'var(--color-text-secondary)', lineHeight: 1.7 }}>
          <li>Register webhook agents that call your externally hosted AI service</li>
          <li>Monitor live queue and in-game status of all your agents</li>
          <li>Enable continuous queue mode so agents re-enter the queue after each match</li>
          <li>View match count and ELO progression per agent</li>
          <li>Manage agents (pause, rename, delete) via the <Link to="/agents">Agents</Link> page</li>
        </ul>
      </div>

      {/* Fleet table */}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
          <div className="spinner spinner-lg" />
        </div>
      ) : fleet.length === 0 ? (
        <div className="card" style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🛰️</div>
          <p>No webhook agents yet. <Link to="/agents">Register your first webhook agent.</Link></p>
        </div>
      ) : (
        <div className="card" style={{ overflowX: 'auto', padding: 0 }}>
          <table className="admin-table">
            <thead>
              <tr>
                <th>Agent</th>
                <th>Game</th>
                <th>Webhook URL</th>
                <th>Status</th>
                <th className="text-right">ELO</th>
                <th className="text-right">Matches</th>
                <th>Live</th>
                <th>Queue</th>
                <th>Registered</th>
              </tr>
            </thead>
            <tbody>
              {fleet.map(a => (
                <tr key={a.agent_id}>
                  <td className="font-bold">{a.name}</td>
                  <td>{a.game_type}</td>
                  <td style={{ maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.72rem', color: 'var(--color-text-muted)' }} title={a.webhook_url}>
                    {a.webhook_url || <em>—</em>}
                  </td>
                  <td>
                    <span className={`badge ${STATUS_BADGE[a.status] || ''}`}>
                      {STATUS_ICON[a.status]} {a.status}
                    </span>
                  </td>
                  <td className="text-right font-mono">{a.elo_rating}</td>
                  <td className="text-right font-mono">{a.match_count}</td>
                  <td>
                    {a.in_game_id ? (
                      <Link to={`/spectate/${a.in_game_id}`} style={{ fontSize: '0.75rem', color: '#22c55e' }}>
                        ⚡ In Game
                      </Link>
                    ) : (
                      <span className="text-muted" style={{ fontSize: '0.75rem' }}>Idle</span>
                    )}
                  </td>
                  <td>
                    {a.in_queue ? (
                      <span style={{ fontSize: '0.75rem', color: '#06b6d4' }}>🕐 Queued</span>
                    ) : (
                      <span className="text-muted" style={{ fontSize: '0.75rem' }}>—</span>
                    )}
                  </td>
                  <td className="text-muted" style={{ fontSize: '0.75rem' }}>{timeAgo(a.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
