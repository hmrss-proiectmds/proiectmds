import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { api } from '../api/client';
import './AdminPanel.css'; // reuse table/card styles

const STATUS_BADGE = {
  active: 'badge-success',
  paused: 'badge-accent',
  banned: 'badge-error',
};

function WinBar({ wins, losses, draws }) {
  const total = wins + losses + draws;
  if (total === 0) return <span style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>No matches</span>;
  const wPct = (wins / total) * 100;
  const lPct = (losses / total) * 100;
  const dPct = (draws / total) * 100;
  return (
    <div style={{ display: 'flex', height: 8, borderRadius: 4, overflow: 'hidden', width: 120, gap: 1 }}>
      {wins > 0 && <div style={{ width: `${wPct}%`, background: '#22c55e' }} title={`${wins}W`} />}
      {draws > 0 && <div style={{ width: `${dPct}%`, background: '#f59e0b' }} title={`${draws}D`} />}
      {losses > 0 && <div style={{ width: `${lPct}%`, background: '#ef4444' }} title={`${losses}L`} />}
    </div>
  );
}

export default function DeveloperDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [analytics, setAnalytics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (user && user.role !== 'ai_developer' && user.role !== 'admin') {
      navigate('/');
      return;
    }
    api.get('/api/developer/analytics')
      .then(setAnalytics)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [user, navigate]);

  const totalMatches  = analytics.reduce((s, a) => s + a.total_matches, 0);
  const totalWins     = analytics.reduce((s, a) => s + a.wins, 0);
  const totalFinished = analytics.reduce((s, a) => s + a.wins + a.losses + a.draws, 0);
  const overallWR     = totalFinished > 0 ? ((totalWins / totalFinished) * 100).toFixed(1) : '—';

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">🔬 Developer Analytics</h1>
        <p className="page-subtitle">Per-agent performance breakdown for your uploaded and webhook agents</p>
      </div>

      {error && <div className="alert alert-error mb-4">{error}</div>}

      {/* Summary cards */}
      <div className="admin-stats-grid" style={{ marginBottom: '1.5rem' }}>
        <div className="admin-stat-card card" style={{ borderTop: '3px solid #6366f1' }}>
          <div className="admin-stat-icon">🤖</div>
          <div className="admin-stat-value">{analytics.length}</div>
          <div className="admin-stat-label">Your Agents</div>
        </div>
        <div className="admin-stat-card card" style={{ borderTop: '3px solid #06b6d4' }}>
          <div className="admin-stat-icon">🎮</div>
          <div className="admin-stat-value">{totalMatches}</div>
          <div className="admin-stat-label">Total Matches</div>
        </div>
        <div className="admin-stat-card card" style={{ borderTop: '3px solid #22c55e' }}>
          <div className="admin-stat-icon">📊</div>
          <div className="admin-stat-value">{overallWR}{overallWR !== '—' && '%'}</div>
          <div className="admin-stat-label">Overall Win Rate</div>
        </div>
        <div className="admin-stat-card card" style={{ borderTop: '3px solid #f59e0b' }}>
          <div className="admin-stat-icon">⚡</div>
          <div className="admin-stat-value" style={{ fontSize: '0.9rem' }}>
            <Link to="/simulations" style={{ color: 'inherit' }}>Run Simulation</Link>
          </div>
          <div className="admin-stat-label">Bulk Test Tool</div>
        </div>
      </div>

      {/* Role capabilities info */}
      <div className="card" style={{ padding: '1rem', marginBottom: '1.5rem', background: 'rgba(99,102,241,0.06)', borderLeft: '3px solid #6366f1' }}>
        <strong style={{ fontSize: '0.85rem' }}>Developer Capabilities</strong>
        <ul style={{ margin: '0.5rem 0 0', paddingLeft: '1.2rem', fontSize: '0.8rem', color: 'var(--color-text-secondary)', lineHeight: 1.7 }}>
          <li>Upload Python agent scripts via the <Link to="/agents">Agents</Link> page</li>
          <li>Register webhook agents pointing to your hosted service</li>
          <li>Run bulk simulations (up to 200 games) via <Link to="/simulations">Simulate</Link></li>
          <li>View full request/response payloads in decision logs</li>
          <li>Download decision logs as JSON or CSV</li>
        </ul>
      </div>

      {/* Analytics table */}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
          <div className="spinner spinner-lg" />
        </div>
      ) : analytics.length === 0 ? (
        <div className="card" style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🤖</div>
          <p>No agents yet. <Link to="/agents">Register or upload your first agent.</Link></p>
        </div>
      ) : (
        <div className="card" style={{ overflowX: 'auto', padding: 0 }}>
          <table className="admin-table">
            <thead>
              <tr>
                <th>Agent</th>
                <th>Game</th>
                <th>Mode</th>
                <th>Status</th>
                <th className="text-right">ELO</th>
                <th className="text-right">Matches</th>
                <th>W / D / L</th>
                <th>Win Rate</th>
                <th>Breakdown</th>
              </tr>
            </thead>
            <tbody>
              {analytics.map(a => (
                <tr key={a.agent_id}>
                  <td className="font-bold">{a.name}</td>
                  <td>{a.game_type}</td>
                  <td className="text-muted" style={{ fontSize: '0.75rem' }}>
                    {a.integration_mode === 'webhook' ? '🔗 webhook' : '📄 upload'}
                  </td>
                  <td>
                    <span className={`badge ${STATUS_BADGE[a.status] || ''}`}>{a.status}</span>
                  </td>
                  <td className="text-right font-mono">{a.elo_rating}</td>
                  <td className="text-right font-mono">{a.total_matches}</td>
                  <td className="font-mono" style={{ fontSize: '0.78rem' }}>
                    <span style={{ color: '#22c55e' }}>{a.wins}W</span>
                    {' / '}
                    <span style={{ color: '#f59e0b' }}>{a.draws}D</span>
                    {' / '}
                    <span style={{ color: '#ef4444' }}>{a.losses}L</span>
                  </td>
                  <td className="font-mono">
                    {a.wins + a.losses + a.draws > 0
                      ? <strong style={{ color: a.win_rate >= 50 ? '#22c55e' : '#ef4444' }}>{a.win_rate}%</strong>
                      : <span className="text-muted">—</span>}
                  </td>
                  <td>
                    <WinBar wins={a.wins} losses={a.losses} draws={a.draws} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
