import { useState, useEffect } from 'react';
import { api } from '../api/client';
import './MatchHistory.css';

const OUTCOME_CONFIG = {
  win:  { icon: '✅', label: 'Win',  className: 'outcome-win' },
  loss: { icon: '❌', label: 'Loss', className: 'outcome-loss' },
  draw: { icon: '🤝', label: 'Draw', className: 'outcome-draw' },
};

const GAME_ICONS = {
  chess: '♟️',
  poker: '🃏',
};

function timeAgo(dateStr) {
  if (!dateStr) return '—';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function MatchHistory() {
  const [matches, setMatches] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const perPage = 15;

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true);
      try {
        const data = await api.get(`/api/history?page=${page}&per_page=${perPage}`);
        setMatches(data.matches || []);
        setTotal(data.total || 0);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [page]);

  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">📊 Match History</h1>
        <p className="page-subtitle">Your complete game timeline with results and ELO changes</p>
      </div>

      {loading ? (
        <div className="mh-loading">
          <div className="spinner spinner-lg" />
        </div>
      ) : matches.length === 0 ? (
        <div className="card mh-empty">
          <span className="mh-empty-icon">🕐</span>
          <h2>No matches yet</h2>
          <p className="text-muted">Play some games and your history will appear here!</p>
        </div>
      ) : (
        <>
          <div className="mh-list">
            {matches.map((m) => {
              const outcome = OUTCOME_CONFIG[m.outcome] || OUTCOME_CONFIG.loss;
              const gameIcon = GAME_ICONS[m.game_type] || '🎮';
              const eloChange = m.elo_change;
              const eloClass = eloChange > 0 ? 'elo-positive' : eloChange < 0 ? 'elo-negative' : 'elo-neutral';
              const eloStr = eloChange > 0 ? `+${eloChange}` : eloChange != null ? `${eloChange}` : '—';

              return (
                <div key={m.match_id} className={`card card-hover mh-card ${outcome.className}`} id={`match-${m.match_id}`}>
                  <div className="mh-card-left">
                    <span className="mh-game-icon">{gameIcon}</span>
                    <div className="mh-card-info">
                      <div className="mh-game-type">{m.game_type}</div>
                      <div className="mh-opponents text-muted">
                        vs {m.opponents.join(', ')}
                      </div>
                    </div>
                  </div>

                  <div className="mh-card-center">
                    <span className={`mh-outcome-badge ${outcome.className}`}>
                      {outcome.icon} {outcome.label}
                    </span>
                  </div>

                  <div className="mh-card-right">
                    <div className={`mh-elo-change ${eloClass}`}>
                      <span className="mh-elo-delta font-mono">{eloStr}</span>
                      <span className="mh-elo-label">ELO</span>
                    </div>
                    <div className="mh-time text-muted">{timeAgo(m.ended_at)}</div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mh-pagination">
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                ← Prev
              </button>
              <span className="mh-page-info font-mono">
                {page} / {totalPages}
              </span>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
