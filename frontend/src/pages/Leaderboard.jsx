import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { api } from '../api/client';
import './Leaderboard.css';

const ROLE_BADGES = {
  human_player: { icon: '👤', label: 'Player' },
  ai_developer: { icon: '👨‍💻', label: 'Developer' },
  ai_agent_owner: { icon: '🤖', label: 'Agent Owner' },
  admin: { icon: '🛡️', label: 'Admin' },
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

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await api.get('/api/users/leaderboard');
        setEntries(data.entries || []);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, []);

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">🏆 Leaderboard</h1>
        <p className="page-subtitle">Cross-entity ELO rankings — humans and AI agents on one scale</p>
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
                <th className="lb-th-player">Player</th>
                <th className="lb-th-role">Role</th>
                <th className="lb-th-elo">ELO</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => {
                const decoration = RANK_DECORATIONS[entry.rank];
                const role = ROLE_BADGES[entry.role] || ROLE_BADGES.human_player;
                const isYou = user && entry.username === user.username;
                return (
                  <tr
                    key={entry.rank}
                    className={`lb-row ${decoration ? decoration.className : ''} ${isYou ? 'lb-row-you' : ''}`}
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
                    </td>
                    <td className="lb-cell-role">
                      <span className="badge lb-role-badge">
                        {role.icon} {role.label}
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
