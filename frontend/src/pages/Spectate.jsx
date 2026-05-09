import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import ChessBoard from '../components/ChessBoard';
import PokerBoard from '../components/PokerBoard';
import './Spectate.css';

const GAME_ICONS = { chess: '♟️', poker: '🃏' };
const WS_BASE = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`;

/**
 * Spectate page — two modes:
 * 1. /spectate — lists active games
 * 2. /spectate/:gameId — live spectator view of a specific game
 */
export default function Spectate() {
  const { gameId } = useParams();

  if (gameId) {
    return <SpectateGame gameId={gameId} />;
  }
  return <SpectateList />;
}


function SpectateList() {
  const navigate = useNavigate();
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchGames = useCallback(async () => {
    try {
      const data = await api.get('/api/games/active');
      setGames(data.games || []);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGames();
    const interval = setInterval(fetchGames, 3000);
    return () => clearInterval(interval);
  }, [fetchGames]);

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">👁️ Spectate</h1>
        <p className="page-subtitle">Watch live games in progress — AI vs AI, humans, or mixed lobbies</p>
      </div>

      {loading ? (
        <div className="spec-loading"><div className="spinner spinner-lg" /></div>
      ) : games.length === 0 ? (
        <div className="card spec-empty">
          <span className="spec-empty-icon">📡</span>
          <h2>No active games</h2>
          <p className="text-muted">When a game is in progress, you'll see it here.</p>
        </div>
      ) : (
        <div className="spec-game-list">
          {games.map((game) => {
            const icon = GAME_ICONS[game.game_type] || '🎮';
            const playerNames = game.players.map((p) => p.username).join(' vs ');
            return (
              <div
                key={game.game_id}
                className="card card-hover spec-game-card"
                onClick={() => navigate(`/spectate/${game.game_id}`)}
                id={`spectate-${game.game_id}`}
              >
                <div className="spec-game-header">
                  <span className="spec-game-icon">{icon}</span>
                  <span className="spec-game-type">{game.game_type}</span>
                  <span className="badge badge-success spec-live-badge">
                    <span className="spec-live-dot" /> LIVE
                  </span>
                </div>
                <div className="spec-game-players">{playerNames}</div>
                <div className="spec-game-meta text-muted">
                  {game.players.length}/{game.max_seats} players
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}


function SpectateGame({ gameId }) {
  const navigate = useNavigate();
  const [gameState, setGameState] = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    const wsUrl = `${WS_BASE}/api/games/ws/${gameId}/spectate`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'game_state') {
        setGameState(data);
      }
    };

    return () => {
      ws.close();
    };
  }, [gameId]);

  if (!gameState) {
    return (
      <div className="page-container animate-fade-in">
        <div className="spec-connecting">
          <div className="spinner spinner-lg" />
          <p>Connecting to game...</p>
        </div>
      </div>
    );
  }

  const {
    game_type,
    status,
    players = [],
    board,
    your_hand,
    chips = [],
    pot,
    action_log = [],
    turn_seat,
    chips_to_call = 0,
    hand_number = 1,
    hand_phase = '',
    hand_just_ended = false,
    showdown_info = null,
    legal_moves = [],
    last_move,
    is_check,
    game_over,
    result,
    move_stack_san = [],
  } = gameState;

  const isPoker = game_type === 'poker';

  const resultText = game_over && result
    ? result.result === 'draw'
      ? `Draw — ${(result.reason || '').replace(/_/g, ' ')}`
      : `${result.result.replace(/_/g, ' ')} — ${(result.reason || '').replace(/_/g, ' ')}`
    : null;

  return (
    <div className="page-container animate-fade-in">
      <div className="spec-header">
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('/spectate')}>
          ← Back to list
        </button>
        <div className="spec-header-info">
          <span className="spec-game-icon">{GAME_ICONS[game_type] || '🎮'}</span>
          <span className="spec-header-type">{game_type}</span>
          <span className={`badge ${connected ? 'badge-success' : 'badge-accent'}`}>
            {connected ? '🔴 LIVE' : 'Disconnected'}
          </span>
          <span className="badge badge-accent">👁️ Spectating</span>
        </div>
      </div>

      {game_over && resultText && (
        <div className="spec-result-banner card">
          <span className="spec-result-text">{resultText}</span>
        </div>
      )}

      <div className="spec-board-area">
        {isPoker ? (
          <PokerBoard
            board={board || []}
            yourHand={[]}
            chips={chips}
            pot={pot || 0}
            legalMoves={[]}
            turnSeat={turn_seat}
            yourSeat={0}
            players={players}
            onMove={() => {}}
            disabled={true}
            actionLog={action_log}
            chipsToCall={chips_to_call}
            handNumber={hand_number}
            handPhase={hand_phase}
            handJustEnded={hand_just_ended}
            showdownInfo={showdown_info}
          />
        ) : (
          <ChessBoard
            board={board}
            legalMoves={[]}
            lastMove={last_move}
            isCheck={is_check}
            turnSeat={turn_seat}
            yourSeat={0}
            onMove={() => {}}
            disabled={true}
          />
        )}
      </div>

      {/* Player list */}
      <div className="spec-players card">
        <h3 className="spec-players-title">Players</h3>
        <div className="spec-players-list">
          {players.map((p) => (
            <div key={p.seat} className={`spec-player ${p.seat === turn_seat ? 'is-turn' : ''}`}>
              <span className="spec-player-icon">{p.is_ai ? '🤖' : '👤'}</span>
              <span className="spec-player-name">{p.username}</span>
              <span className="spec-player-elo font-mono">{p.elo_rating} ELO</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
