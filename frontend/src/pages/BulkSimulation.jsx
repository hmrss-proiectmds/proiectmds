import { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';
import './BulkSimulation.css';

const GAME_TYPES = ['chess', 'poker'];
const BOT_TYPES  = [
  { value: 'random',   label: '🎲 Random Bot',   desc: '~400 ELO — plays random legal moves' },
  { value: 'chessbot', label: '🧠 ChessBot AI',  desc: '~1500 ELO — HuggingFace chess model' },
  { value: 'pokerbot', label: '🤖 PokerBot AI',  desc: '~1200 ELO — HuggingFace poker model' },
];

function StatCard({ label, value, sub }) {
  return (
    <div className="stat-card">
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
      {sub && <span className="stat-sub">{sub}</span>}
    </div>
  );
}

function WinBar({ winsA, winsB, draws, total }) {
  const pA = total > 0 ? (winsA / total) * 100 : 0;
  const pB = total > 0 ? (winsB / total) * 100 : 0;
  const pD = total > 0 ? (draws  / total) * 100 : 0;
  return (
    <div className="win-bar-container">
      <div className="win-bar">
        <div className="win-bar-a" style={{ width: `${pA}%` }} title={`Bot A wins: ${winsA}`} />
        <div className="win-bar-d" style={{ width: `${pD}%` }} title={`Draws: ${draws}`} />
        <div className="win-bar-b" style={{ width: `${pB}%` }} title={`Bot B wins: ${winsB}`} />
      </div>
      <div className="win-bar-labels">
        <span className="label-a">Bot A {Math.round(pA)}%</span>
        {pD > 0 && <span className="label-d">Draws {Math.round(pD)}%</span>}
        <span className="label-b">Bot B {Math.round(pB)}%</span>
      </div>
    </div>
  );
}

export default function BulkSimulation() {
  const [gameType, setGameType]   = useState('chess');
  const [botA, setBotA]           = useState('random');
  const [botB, setBotB]           = useState('chessbot');
  const [numGames, setNumGames]   = useState(10);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState('');
  const [simulations, setSimulations] = useState([]);
  const [activeSimId, setActiveSimId] = useState(null);
  const [result, setResult]       = useState(null);
  const pollRef = useRef(null);

  const refreshList = async () => {
    try {
      const r = await api.get('/api/simulations');
      setSimulations(r);
    } catch {}
  };

  // Load past simulations on mount
  useEffect(() => {
    refreshList();
  }, []);

  // Poll active simulation
  useEffect(() => {
    if (!activeSimId) return;
    pollRef.current = setInterval(async () => {
      try {
        const sim = await api.get(`/api/simulations/${activeSimId}`);
        if (sim.state === 'SUCCESS') {
          clearInterval(pollRef.current);
          setResult(sim.result);
          setLoading(false);
          setActiveSimId(null);
          refreshList();
        } else if (sim.state === 'FAILURE') {
          clearInterval(pollRef.current);
          setError(sim.error || 'Simulation failed');
          setLoading(false);
          setActiveSimId(null);
        }
      } catch {
        clearInterval(pollRef.current);
        setLoading(false);
      }
    }, 1500);
    return () => clearInterval(pollRef.current);
  }, [activeSimId]);

  const handleStart = async (e) => {
    e.preventDefault();
    setError('');
    setResult(null);
    setLoading(true);
    try {
      const sim = await api.post('/api/simulations', {
        game_type: gameType,
        bot_a: botA,
        bot_b: botB,
        num_games: numGames,
      });
      if (sim.state === 'SUCCESS') {
        // Sync fallback — result is immediate
        setResult(sim.result);
        setLoading(false);
        refreshList();
      } else {
        setActiveSimId(sim.simulation_id);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to start simulation');
      setLoading(false);
    }
  };

  const handleDownload = async (simId, fmt) => {
    try {
      const blob = await api.get(`/api/simulations/${simId}/download?fmt=${fmt}`, {
        asBlob: true,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `simulation_${simId.slice(0, 8)}.${fmt}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError('Download failed');
    }
  };

  const loadSimResult = async (simId) => {
    try {
      const r = await api.get(`/api/simulations/${simId}`);
      if (r.result) setResult(r.result);
    } catch {}
  };

  const summary = result?.summary;

  return (
    <div className="page-container animate-fade-in">
      <div className="sim-layout">
        {/* ── Left: Config panel ── */}
        <div className="sim-config-col">
          <div className="card sim-config-card">
            <h2 className="sim-title">⚡ Bulk Simulation</h2>
            <p className="sim-subtitle">
              Run headless games between bots and analyse the results statistically.
            </p>

            <form onSubmit={handleStart} className="sim-form">
              <div className="sim-field">
                <label className="sim-label">Game Type</label>
                <div className="sim-toggle-row">
                  {GAME_TYPES.map((g) => (
                    <button
                      key={g}
                      type="button"
                      className={`sim-toggle ${gameType === g ? 'active' : ''}`}
                      onClick={() => setGameType(g)}
                    >
                      {g === 'chess' ? '♟️' : '🃏'} {g}
                    </button>
                  ))}
                </div>
              </div>

              <div className="sim-bots-row">
                <div className="sim-field">
                  <label className="sim-label">Bot A (Seat 1)</label>
                  <select className="form-input" value={botA} onChange={e => setBotA(e.target.value)}>
                    {BOT_TYPES.map(b => (
                      <option key={b.value} value={b.value}>{b.label}</option>
                    ))}
                  </select>
                  <span className="sim-bot-desc">{BOT_TYPES.find(b => b.value === botA)?.desc}</span>
                </div>
                <div className="sim-vs">VS</div>
                <div className="sim-field">
                  <label className="sim-label">Bot B (Seat 2)</label>
                  <select className="form-input" value={botB} onChange={e => setBotB(e.target.value)}>
                    {BOT_TYPES.map(b => (
                      <option key={b.value} value={b.value}>{b.label}</option>
                    ))}
                  </select>
                  <span className="sim-bot-desc">{BOT_TYPES.find(b => b.value === botB)?.desc}</span>
                </div>
              </div>

              <div className="sim-field">
                <label className="sim-label">Number of Games: <strong>{numGames}</strong></label>
                <input
                  type="range"
                  min={1}
                  max={200}
                  value={numGames}
                  onChange={e => setNumGames(Number(e.target.value))}
                  className="sim-slider"
                />
                <div className="sim-slider-labels">
                  <span>1</span><span>50</span><span>100</span><span>200</span>
                </div>
              </div>

              {error && <div className="alert alert-error">{error}</div>}

              <button
                type="submit"
                className="btn btn-primary w-full sim-run-btn"
                disabled={loading}
              >
                {loading ? (
                  <><div className="spinner" /> Running {numGames} games…</>
                ) : (
                  '▶ Run Simulation'
                )}
              </button>
            </form>
          </div>

          {/* Past simulations */}
          {simulations.length > 0 && (
            <div className="card sim-history-card">
              <h3 className="sim-section-title">Recent Simulations</h3>
              <div className="sim-history-list">
                {simulations.map((s) => (
                  <div key={s.simulation_id} className="sim-history-item">
                    <div className="sim-history-info">
                      <span className="sim-history-game">{s.game_type === 'chess' ? '♟️' : '🃏'} {s.game_type}</span>
                      <span className="sim-history-bots">{s.bot_a} vs {s.bot_b}</span>
                      <span className="sim-history-count">{s.num_games} games</span>
                    </div>
                    <div className="sim-history-actions">
                      <span className={`badge badge-${s.state === 'SUCCESS' ? 'success' : 'secondary'}`}>
                        {s.state === 'SUCCESS' ? '✓' : `${s.percent}%`}
                      </span>
                      {s.state === 'SUCCESS' && (
                        <button
                          className="btn btn-ghost btn-sm"
                          onClick={() => loadSimResult(s.simulation_id)}
                        >
                          View
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── Right: Results panel ── */}
        <div className="sim-results-col">
          {!result && !loading && (
            <div className="sim-empty-state">
              <div className="sim-empty-icon">📊</div>
              <p>Configure a simulation and click <strong>Run</strong> to see results here.</p>
            </div>
          )}

          {loading && (
            <div className="card sim-running-card">
              <div className="spinner spinner-lg" />
              <p className="sim-running-text">Running {numGames} games headlessly…</p>
              <p className="text-muted" style={{ fontSize: 'var(--text-xs)' }}>
                This may take a few seconds depending on game type and bot complexity.
              </p>
            </div>
          )}

          {result && summary && (
            <div className="sim-result-panel animate-fade-in">
              <div className="card sim-summary-card">
                <div className="sim-result-header">
                  <h3 className="sim-section-title">📊 Results</h3>
                  <div className="sim-download-btns">
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => handleDownload(result.simulation_id, 'json')}
                    >
                      ⬇ JSON
                    </button>
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => handleDownload(result.simulation_id, 'csv')}
                    >
                      ⬇ CSV
                    </button>
                  </div>
                </div>

                <div className="sim-meta">
                  <span>{result.game_type === 'chess' ? '♟️' : '🃏'} {result.game_type}</span>
                  <span className="sim-meta-sep">·</span>
                  <span>{result.num_games} games</span>
                  <span className="sim-meta-sep">·</span>
                  <span>{result.bot_a} vs {result.bot_b}</span>
                </div>

                <WinBar
                  winsA={summary.wins_a}
                  winsB={summary.wins_b}
                  draws={summary.draws}
                  total={result.num_games}
                />

                <div className="stat-grid">
                  <StatCard label="Bot A Wins" value={summary.wins_a} sub={`${(summary.win_rate_a * 100).toFixed(1)}%`} />
                  <StatCard label="Bot B Wins" value={summary.wins_b} sub={`${(summary.win_rate_b * 100).toFixed(1)}%`} />
                  <StatCard label="Draws"      value={summary.draws} />
                  <StatCard label="Errors"     value={summary.errors} />
                  <StatCard label="Avg Turns"  value={summary.avg_turns} />
                  <StatCard label="Avg Time"   value={`${summary.avg_duration_ms}ms`} />
                </div>
              </div>

              {/* Per-game table */}
              <div className="card">
                <h3 className="sim-section-title">Game Log</h3>
                <div className="sim-game-table-wrap">
                  <table className="sim-game-table">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Winner</th>
                        <th>Reason</th>
                        <th>Turns</th>
                        <th>Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(result.games || []).map((g, i) => {
                        const isWinA = g.winner === 'player1_win';
                        const isWinB = g.winner?.startsWith('player') && g.winner !== 'player1_win';
                        return (
                          <tr key={i} className={isWinA ? 'row-a' : isWinB ? 'row-b' : ''}>
                            <td className="font-mono">{i + 1}</td>
                            <td>
                              <span className={`badge badge-${isWinA ? 'accent' : isWinB ? 'secondary' : 'success'}`}>
                                {isWinA ? 'Bot A' : isWinB ? 'Bot B' : g.winner}
                              </span>
                            </td>
                            <td className="text-muted">{g.reason}</td>
                            <td className="font-mono">{g.turns}</td>
                            <td className="font-mono text-muted">{g.duration_ms}ms</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
