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

function downloadJson(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function MoveList({ matchId, gameType, opponents, onClose }) {
  const [moves, setMoves] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get(`/api/history/${matchId}/moves`)
      .then(setMoves)
      .catch(() => setError('Could not load moves.'));
  }, [matchId]);

  if (error) return <div className="mh-moves-error">{error}</div>;
  if (!moves) return <div className="mh-moves-loading"><div className="spinner spinner-sm" /></div>;
  if (moves.length === 0) return <div className="mh-moves-empty">No moves recorded for this game.</div>;

  // Pair moves chess-style: [white, black] per row
  const rows = [];
  if (gameType === 'chess') {
    for (let i = 0; i < moves.length; i += 2) {
      rows.push({ n: Math.floor(i / 2) + 1, w: moves[i], b: moves[i + 1] });
    }
  } else {
    moves.forEach((m, i) => rows.push({ n: i + 1, single: m }));
  }

  const handleDownload = () => {
    downloadJson(
      { match_id: matchId, game_type: gameType, opponents, moves },
      `match_${matchId.slice(0, 8)}.json`
    );
  };

  return (
    <div className="mh-moves-panel">
      <div className="mh-moves-header">
        <span className="mh-moves-title">Move List</span>
        <div className="mh-moves-actions">
          <button className="btn btn-ghost btn-xs" onClick={handleDownload}>
            ⬇ Download JSON
          </button>
          <button className="btn btn-ghost btn-xs" onClick={onClose}>✕</button>
        </div>
      </div>

      <div className="mh-moves-scroll">
        {gameType === 'chess' ? (
          <table className="mh-moves-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Seat {rows[0]?.w?.seat ?? 1}</th>
                <th>Seat {rows[0]?.b?.seat ?? 2}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ n, w, b }) => (
                <tr key={n}>
                  <td className="mh-move-num">{n}.</td>
                  <td className="mh-move-san">{w?.san || '—'}</td>
                  <td className="mh-move-san">{b?.san || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <ol className="mh-moves-plain">
            {rows.map(({ n, single: m }) => (
              <li key={n}>
                <span className="mh-move-num">{n}.</span>
                <span className="mh-move-seat">Seat {m.seat}</span>
                <span className="mh-move-san">{m.san}</span>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}

export default function MatchHistory() {
  const [matches, setMatches] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState(null);
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

  const toggleExpand = (id) => setExpandedId(prev => (prev === id ? null : id));

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
              const isExpanded = expandedId === m.match_id;

              return (
                <div key={m.match_id} className={`card mh-card-wrapper ${outcome.className}`}>
                  <div className="mh-card">
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
                      <button
                        className={`btn btn-ghost btn-xs mh-expand-btn ${isExpanded ? 'active' : ''}`}
                        onClick={() => toggleExpand(m.match_id)}
                        title={isExpanded ? 'Hide moves' : 'View moves'}
                      >
                        {isExpanded ? '▲ Hide' : '▼ Moves'}
                      </button>
                    </div>
                  </div>

                  {isExpanded && (
                    <MoveList
                      matchId={m.match_id}
                      gameType={m.game_type}
                      opponents={m.opponents}
                      onClose={() => setExpandedId(null)}
                    />
                  )}
                </div>
              );
            })}
          </div>

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
