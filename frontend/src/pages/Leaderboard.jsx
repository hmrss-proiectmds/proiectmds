import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { api } from '../api/client';
import './Leaderboard.css';

const ROLE_BADGES = {
  human_player:   { icon: '👤', label: 'Player',      cls: '' },
  ai_developer:   { icon: '👨‍💻', label: 'Developer',   cls: 'badge-developer' },
  ai_agent_owner: { icon: '🤖', label: 'Agent Owner', cls: 'badge-owner' },
  admin:          { icon: '🛡️', label: 'Admin',       cls: 'badge-admin' },
  agent:          { icon: '🤖', label: 'AI Agent',    cls: 'badge-agent' },
};

const RANK_DECORATIONS = {
  1: { medal: '🥇', className: 'rank-gold' },
  2: { medal: '🥈', className: 'rank-silver' },
  3: { medal: '🥉', className: 'rank-bronze' },
};

export default function Leaderboard() {
  const { user } = useAuth();
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [includeAgents, setIncludeAgents] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const data = await api.get(`/api/users/leaderboard?include_agents=${includeAgents}`);
        setEntries(data.entries || []);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [includeAgents]);

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">🏆 Leaderboard</h1>
        <p className="page-subtitle">Cross-entity ELO rankings — humans and AI agents on one scale</p>
      </div>

      {/* Filter toggle */}
      <div className="lb-filters">
        <label className="lb-toggle-label">
          <input
            id="lb-toggle-agents"
            type="checkbox"
            checked={includeAgents}
            onChange={e => setIncludeAgents(e.target.checked)}
          />
          Show AI Agents
        </label>
      </div>

      {loading ? (
        <div className="lb-loading">
          <div className="spinner spinner-lg" />
        </div>
      ) : entries.length === 0 ? (
        <div className="card lb-empty">
          <span className="lb-empty-icon">📊</span>
          <p>No players registered yet. Be the first!</p>
        </div>
      ) : (
        <div className="lb-table-wrapper card">
          <table className="lb-table" id="leaderboard-table">
            <thead>
              <tr>
                <th className="lb-th-rank">Rank</th>
                <th className="lb-th-player">Player / Agent</th>
                <th className="lb-th-role">Type</th>
                <th className="lb-th-elo">ELO</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => {
                const decoration = RANK_DECORATIONS[entry.rank];
                const badge = ROLE_BADGES[entry.role] || ROLE_BADGES.human_player;
                const isYou = user && entry.username === user.username && entry.entity_type === 'human';
                return (
                  <tr
                    key={`${entry.rank}-${entry.username}`}
                    className={`lb-row ${decoration ? decoration.className : ''} ${isYou ? 'lb-row-you' : ''} ${entry.entity_type === 'agent' ? 'lb-row-agent' : ''}`}
                    id={`lb-rank-${entry.rank}`}
                  >
                    <td className="lb-cell-rank">
                      {decoration ? (
                        <span className="lb-medal">{decoration.medal}</span>
                      ) : (
                        <span className="lb-rank-num">{entry.rank}</span>
                      )}
                    </td>
                    <td className="lb-cell-player">
                      <span className="lb-username">{entry.username}</span>
                      {isYou && <span className="badge badge-accent lb-you-badge">You</span>}
                      {entry.game_type && (
                        <span className="lb-game-chip">
                          {entry.game_type === 'chess' ? '♟️' : '🃏'} {entry.game_type}
                        </span>
                      )}
                    </td>
                    <td className="lb-cell-role">
                      <span className={`badge lb-role-badge ${badge.cls}`}>
                        {badge.icon} {badge.label}
                      </span>
                    </td>
                    <td className="lb-cell-elo">
                      <span className="lb-elo font-mono">{entry.elo_rating}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
