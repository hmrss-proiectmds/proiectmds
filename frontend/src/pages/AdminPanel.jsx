import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useAuth } from '../hooks/useAuth';
import './AdminPanel.css';
import './Placeholder.css';

function StatCard({ icon, label, value, color }) {
  return (
    <div className="admin-stat-card card" style={{ borderTop: `3px solid ${color}` }}>
      <div className="admin-stat-icon">{icon}</div>
      <div className="admin-stat-value">{value ?? '—'}</div>
      <div className="admin-stat-label">{label}</div>
    </div>
  );
}

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

function getToken() {
  return localStorage.getItem('access_token');
}

export default function AdminPanel() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [agents, setAgents] = useState([]);
  const [activeGames, setActiveGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState('');
  const [activeTab, setActiveTab] = useState('overview');

  const load = async () => {
    setLoading(true);
    try {
      const [s, u, a, g] = await Promise.all([
        api.get('/api/admin/stats'),
        api.get('/api/admin/users'),
        api.get('/api/admin/agents'),
        api.get('/api/admin/active-games'),
      ]);
      setStats(s);
      setUsers(u);
      setAgents(a);
      setActiveGames(g);
    } catch (err) {
      setActionMsg(`Error loading data: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const agentAction = async (agentId, action) => {
    setActionMsg('');
    try {
      const data = await fetch(`/api/admin/agents/${agentId}/${action}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then(r => r.json());
      setActionMsg(data.detail || `Agent ${action}d.`);
      load();
    } catch (err) {
      setActionMsg(err.message);
    }
  };

  if (user?.role !== 'admin') {
    return (
      <div className="page-container">
        <div className="placeholder-card card">
          <span className="placeholder-icon">🚫</span>
          <h2>Access Denied</h2>
          <p>This page requires admin privileges.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">🛡️ Admin Panel</h1>
        <p className="page-subtitle">Platform moderation and oversight dashboard</p>
      </div>

      {actionMsg && (
        <div className="admin-action-msg" onClick={() => setActionMsg('')}>
          {actionMsg} <span style={{ opacity: 0.5, fontSize: '0.8em' }}>(click to dismiss)</span>
        </div>
      )}

      {/* Tabs */}
      <div className="admin-tabs">
        {['overview', 'users', 'agents', 'games'].map(tab => (
          <button
            key={tab}
            id={`admin-tab-${tab}`}
            className={`admin-tab ${activeTab === tab ? 'admin-tab--active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {{ overview: '📊 Overview', users: '👥 Users', agents: '🤖 Agents', games: '🎮 Active Games' }[tab]}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
          <div className="spinner spinner-lg" />
        </div>
      ) : (
        <>
          {/* ── Overview ── */}
          {activeTab === 'overview' && stats && (
            <div className="admin-stats-grid">
              <StatCard icon="👥" label="Total Users" value={stats.total_users} color="#6366f1" />
              <StatCard icon="🤖" label="Total Agents" value={stats.total_agents} color="#8b5cf6" />
              <StatCard icon="🎮" label="Total Matches" value={stats.total_matches} color="#06b6d4" />
              <StatCard icon="⚡" label="Active Games" value={stats.active_games} color="#22c55e" />
              <StatCard icon="✅" label="Active Agents" value={stats.active_agents} color="#f59e0b" />
            </div>
          )}

          {/* ── Users ── */}
          {activeTab === 'users' && (
            <div className="card" style={{ overflowX: 'auto', padding: 0 }}>
              <table className="admin-table" id="admin-users-table">
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th className="text-right">ELO</th>
                    <th>Joined</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map(u => (
                    <tr key={u.id}>
                      <td className="font-bold">{u.username}</td>
                      <td className="text-muted">{u.email}</td>
                      <td><span className="badge">{u.role}</span></td>
                      <td className="text-right font-mono">{u.elo_rating}</td>
                      <td className="text-muted">{timeAgo(u.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* ── Agents ── */}
          {activeTab === 'agents' && (
            <div className="card" style={{ overflowX: 'auto', padding: 0 }}>
              <table className="admin-table" id="admin-agents-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Game</th>
                    <th>Mode</th>
                    <th>Status</th>
                    <th className="text-right">ELO</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {agents.map(a => (
                    <tr key={a.id}>
                      <td className="font-bold">{a.name}</td>
                      <td>{a.game_type}</td>
                      <td className="text-muted">{a.integration_mode}</td>
                      <td>
                        <span className={`badge ${a.status === 'active' ? 'badge-success' : a.status === 'banned' ? 'badge-error' : 'badge-accent'}`}>
                          {a.status}
                        </span>
                      </td>
                      <td className="text-right font-mono">{a.elo_rating}</td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.4rem' }}>
                          {a.status !== 'banned' && (
                            <button
                              className="btn btn-sm btn-ghost"
                              style={{ fontSize: '0.75rem' }}
                              onClick={() => agentAction(a.id, a.status === 'paused' ? 'unpause' : 'pause')}
                            >
                              {a.status === 'paused' ? '▶ Unpause' : '⏸ Pause'}
                            </button>
                          )}
                          {a.status !== 'banned' && (
                            <button
                              className="btn btn-sm"
                              style={{ fontSize: '0.75rem', background: 'rgba(239,68,68,0.12)', color: '#ef4444' }}
                              onClick={() => agentAction(a.id, 'ban')}
                            >
                              🚫 Ban
                            </button>
                          )}
                          {a.status === 'banned' && <span className="text-muted" style={{ fontSize: '0.78rem' }}>Banned</span>}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* ── Active Games ── */}
          {activeTab === 'games' && (
            <div className="card" style={{ overflowX: 'auto', padding: 0 }}>
              {activeGames.length === 0 ? (
                <p style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>No active games right now.</p>
              ) : (
                <table className="admin-table" id="admin-games-table">
                  <thead>
                    <tr>
                      <th>Game ID</th>
                      <th>Type</th>
                      <th>Players</th>
                      <th>Started</th>
                      <th className="text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeGames.map(g => (
                      <tr key={g.game_id}>
                        <td className="font-mono" style={{ fontSize: '0.75rem' }}>{g.game_id.slice(0, 8)}…</td>
                        <td>{g.game_type}</td>
                        <td>{g.players.join(' vs ')}</td>
                        <td className="text-muted">{timeAgo(g.started_at)}</td>
                        <td className="text-right">
                          <button className="btn btn-sm btn-accent" onClick={() => window.location.href = `/spectate/${g.game_id}`}>🔴 Spectate</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
