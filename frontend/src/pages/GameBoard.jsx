import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useGameState } from '../hooks/useGameState';
import { api } from '../api/client';
import ChessBoard from '../components/ChessBoard';
import PokerBoard from '../components/PokerBoard';
import './GameBoard.css';

const SEAT_COLOR = { 1: 'White', 2: 'Black' };

export default function GameBoard() {
  const { gameId } = useParams();
  const navigate = useNavigate();
  const { gameState, connected, error, sendMove, sendResign } = useGameState(gameId);
  const [addingBot, setAddingBot] = useState(false);
  const [botError, setBotError] = useState('');

  const handleAddBot = async (botType) => {
    setAddingBot(true);
    setBotError('');
    try {
      await api.post(`/api/games/${gameId}/join_ai`, { bot_type: botType });
    } catch (err) {
      setBotError(err.message);
      setTimeout(() => setBotError(''), 3000);
    } finally {
      setAddingBot(false);
    }
  };

  if (!connected && !gameState) {
    return (
      <div className="page-container animate-fade-in">
        <div className="game-loading">
          <div className="spinner spinner-lg" />
          <p className="text-muted mt-4">Connecting to game…</p>
        </div>
      </div>
    );
  }

  if (!gameState) {
    return (
      <div className="page-container animate-fade-in">
        <div className="game-loading">
          <div className="spinner spinner-lg" />
          <p className="text-muted mt-4">Loading game state…</p>
        </div>
      </div>
    );
  }

  const {
    board,
    legal_moves = [],
    last_move,
    is_check,
    turn_seat,
    your_seat,
    status: gameStatus,
    game_over,
    result,
    move_stack_san = [],
    players = [],
    game_type,
    // Poker-specific fields
    your_hand,
    your_chips,
    chips = [],
    pot,
    action_log = [],
    chips_to_call = 0,
    max_seats = 2,
  } = gameState;

  const isPoker = game_type === 'poker';
  const yourPlayer = players.find((p) => p.seat === your_seat);
  const opponentPlayer = players.find((p) => p.seat !== your_seat);
  const isYourTurn = turn_seat === your_seat && !game_over;
  const isWaiting = gameStatus === 'waiting';

  const resultText = result
    ? result.result === 'draw'
      ? `Draw — ${(result.reason || '').replace(/_/g, ' ')}`
      : result.result === `player${your_seat}_win`
        ? `You won! — ${(result.reason || '').replace(/_/g, ' ')}`
        : `You lost — ${(result.reason || '').replace(/_/g, ' ')}`
    : null;

  // Format move history into pairs (chess only)
  const movePairs = [];
  if (!isPoker) {
    for (let i = 0; i < move_stack_san.length; i += 2) {
      movePairs.push({
        num: Math.floor(i / 2) + 1,
        white: move_stack_san[i],
        black: move_stack_san[i + 1] || '',
      });
    }
  }

  return (
    <div className="page-container animate-fade-in">
      <div className="game-layout">
        {/* Left column: board */}
        <div className="game-board-column">
          {/* Non-poker: opponent bar */}
          {!isPoker && (
            <div className="game-player-bar opponent">
              <div className="player-info">
                <span className="player-icon">
                  {opponentPlayer?.is_ai ? '🤖' : '👤'}
                </span>
                <span className="player-name">
                  {opponentPlayer?.username || 'Waiting…'}
                </span>
                {opponentPlayer && (
                  <span className="badge badge-accent font-mono">
                    {opponentPlayer.elo_rating} ELO
                  </span>
                )}
              </div>
              <span className="player-color">
                {SEAT_COLOR[opponentPlayer?.seat || (your_seat === 1 ? 2 : 1)]}
              </span>
            </div>
          )}

          {isPoker ? (
            <PokerBoard
              board={board || []}
              yourHand={your_hand || []}
              chips={chips}
              pot={pot || 0}
              legalMoves={isYourTurn ? legal_moves : []}
              turnSeat={turn_seat}
              yourSeat={your_seat}
              players={players}
              onMove={sendMove}
              disabled={!isYourTurn || game_over || isWaiting}
              actionLog={action_log}
              chipsToCall={chips_to_call}
            />
          ) : (
            <ChessBoard
              board={board}
              legalMoves={isYourTurn ? legal_moves : []}
              lastMove={last_move}
              isCheck={is_check}
              turnSeat={turn_seat}
              yourSeat={your_seat}
              onMove={sendMove}
              disabled={!isYourTurn || game_over || isWaiting}
            />
          )}

          {/* Non-poker: your info bar */}
          {!isPoker && (
            <div className="game-player-bar you">
              <div className="player-info">
                <span className="player-icon">👤</span>
                <span className="player-name">{yourPlayer?.username || 'You'}</span>
                {yourPlayer && (
                  <span className="badge badge-accent font-mono">
                    {yourPlayer.elo_rating} ELO
                  </span>
                )}
              </div>
              <span className="player-color">{SEAT_COLOR[your_seat]}</span>
            </div>
          )}
        </div>

        {/* Right column: info panel */}
        <div className="game-info-column">
          {/* Status card */}
          <div className="card game-status-card">
            {isWaiting && (
              <div className="game-status waiting">
                <div className="spinner" />
                <span>
                  Waiting for players… ({players.length}/{max_seats})
                </span>
                <span className="text-muted" style={{ fontSize: 'var(--text-xs)' }}>
                  Share this link to invite friends, or add AI bots below
                </span>

                {/* Current players in lobby */}
                <div style={{ width: '100%', marginTop: 'var(--space-3)' }}>
                  {players.map((p) => (
                    <div
                      key={p.seat}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 'var(--space-2)',
                        padding: '4px 0',
                        fontSize: 'var(--text-sm)',
                        borderBottom: '1px solid var(--color-border)',
                      }}
                    >
                      <span>{p.is_ai ? '🤖' : '👤'}</span>
                      <span style={{ fontWeight: 600 }}>
                        Seat {p.seat}: {p.seat === your_seat ? 'You' : p.username}
                      </span>
                    </div>
                  ))}
                  {/* Empty seats */}
                  {Array.from({ length: max_seats - players.length }, (_, i) => (
                    <div
                      key={`empty-${i}`}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 'var(--space-2)',
                        padding: '4px 0',
                        fontSize: 'var(--text-sm)',
                        color: 'var(--color-text-muted)',
                        borderBottom: '1px solid var(--color-border)',
                      }}
                    >
                      <span>⬜</span>
                      <span style={{ fontStyle: 'italic' }}>Open seat</span>
                    </div>
                  ))}
                </div>

                {/* Add Bot controls */}
                {players.length < max_seats && (
                  <div style={{ display: 'flex', gap: 'var(--space-2)', marginTop: 'var(--space-3)', flexWrap: 'wrap' }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleAddBot('random')}
                      disabled={addingBot}
                    >
                      🎲 Add Random Bot
                    </button>
                    <button
                      className="btn btn-sm lobby-btn-hf-sm"
                      onClick={() => handleAddBot(isPoker ? 'pokerbot' : 'chessbot')}
                      disabled={addingBot}
                      style={{
                        background: 'linear-gradient(135deg, #ff9d00, #ff6b00)',
                        color: '#fff',
                        border: 'none',
                      }}
                    >
                      🧠 Add HF AI Bot
                    </button>
                  </div>
                )}
                {botError && (
                  <div className="alert alert-error" style={{ marginTop: 'var(--space-2)', fontSize: 'var(--text-xs)' }}>
                    {botError}
                  </div>
                )}
              </div>
            )}
            {!isWaiting && !game_over && (
              <div className={`game-status ${isYourTurn ? 'your-turn' : 'opponent-turn'}`}>
                <span className="status-dot" />
                <span>{isYourTurn ? 'Your turn' : `Seat ${turn_seat}'s turn`}</span>
                {is_check && <span className="badge badge-error">CHECK</span>}
              </div>
            )}
            {game_over && (
              <div className="game-status game-over-status">
                <span className="game-over-icon">
                  {result?.result === `player${your_seat}_win`
                    ? '🏆'
                    : result?.result === 'draw'
                      ? '🤝'
                      : '😔'}
                </span>
                <span className="game-over-text">{resultText}</span>
              </div>
            )}
          </div>

          {error && <div className="alert alert-error">{error}</div>}

          {/* Player list (poker) */}
          {isPoker && (
            <div className="card" style={{ padding: 'var(--space-4)' }}>
              <h3 style={{ fontSize: 'var(--text-sm)', fontWeight: 700, marginBottom: 'var(--space-3)', color: 'var(--color-text-secondary)' }}>
                Players
              </h3>
              {players.map((p) => {
                const chipInfo = chips.find((c) => c.seat === p.seat);
                return (
                  <div
                    key={p.seat}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '4px 0',
                      borderBottom: '1px solid var(--color-border)',
                      opacity: chipInfo?.is_active === false ? 0.4 : 1,
                    }}
                  >
                    <span style={{ fontSize: 'var(--text-xs)' }}>
                      {p.is_ai ? '🤖' : '👤'}{' '}
                      {p.seat === your_seat ? <strong>You</strong> : p.username}
                    </span>
                    <span className="font-mono" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-success)' }}>
                      ${chipInfo?.chips ?? '?'}
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          {/* Move history (chess) */}
          {!isPoker && (
            <div className="card game-moves-card">
              <h3 className="game-moves-title">Moves</h3>
              <div className="game-moves-list">
                {movePairs.length === 0 ? (
                  <span className="text-muted" style={{ fontSize: 'var(--text-sm)' }}>
                    No moves yet
                  </span>
                ) : (
                  movePairs.map((pair) => (
                    <div key={pair.num} className="move-pair">
                      <span className="move-num">{pair.num}.</span>
                      <span className="move-san">{pair.white}</span>
                      <span className="move-san">{pair.black}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Actions */}
          {!game_over && !isWaiting && (
            <button
              className="btn btn-danger w-full"
              onClick={() => {
                if (confirm('Are you sure you want to resign?')) sendResign();
              }}
            >
              🏳️ {isPoker ? 'Quit Game' : 'Resign'}
            </button>
          )}
          {game_over && (
            <div className="game-over-actions">
              <button className="btn btn-primary w-full" onClick={() => navigate('/play')}>
                New Game
              </button>
              <button className="btn btn-secondary w-full" onClick={() => navigate('/')}>
                Dashboard
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
