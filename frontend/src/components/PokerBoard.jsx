import { useState } from 'react';
import './PokerBoard.css';

const SUIT_COLORS = { '♠': '#1e293b', '♣': '#1e293b', '♥': '#ef4444', '♦': '#ef4444' };

function CardFace({ card }) {
  if (!card) return null;
  const suit = card.slice(-1);
  const rank = card.slice(0, -1);
  const color = SUIT_COLORS[suit] || '#f1f5f9';
  return (
    <div className="poker-card" style={{ color }}>
      <span className="card-rank">{rank}</span>
      <span className="card-suit">{suit}</span>
    </div>
  );
}

function CardBack() {
  return <div className="poker-card card-back" />;
}

export default function PokerBoard({
  board = [],
  yourHand = [],
  chips = [],
  pot = 0,
  legalMoves = [],
  turnSeat,
  yourSeat,
  players = [],
  onMove,
  disabled,
  actionLog = [],
  chipsToCall = 0,
}) {
  const [raiseAmt, setRaiseAmt] = useState('');

  // Parse RAISE range from legal_moves
  const raiseMove = legalMoves.find((m) => m.startsWith('RAISE'));
  let minRaise = 0;
  let maxRaise = 0;
  if (raiseMove) {
    const parts = raiseMove.split(' ');
    minRaise = parseInt(parts[1], 10) || 0;
    maxRaise = parseInt(parts[2], 10) || 0;
  }
  const simpleActions = legalMoves
    .map((m) => m.split(' ')[0])
    .filter((a) => a !== 'RAISE');
  const canRaise = !!raiseMove;

  const handleAction = (action) => {
    if (disabled) return;
    onMove(action);
  };

  const handleRaise = () => {
    const amt = parseInt(raiseAmt, 10);
    if (!isNaN(amt) && amt >= minRaise && amt <= maxRaise) {
      onMove(`RAISE ${amt}`);
      setRaiseAmt('');
    }
  };

  // Split players into "you" and "others" for display
  const otherPlayers = players.filter((p) => p.seat !== yourSeat);

  return (
    <div className="poker-board">
      {/* ── Opponents around the table ── */}
      <div className="poker-opponents">
        {otherPlayers.map((p) => {
          const chipInfo = chips.find((c) => c.seat === p.seat);
          const isTurn = turnSeat === p.seat;
          return (
            <div key={p.seat} className={`poker-opponent ${isTurn ? 'is-turn' : ''}`}>
              <div className="opponent-avatar">
                {p.is_ai ? '🤖' : '👤'}
              </div>
              <span className="opponent-name">{p.username}</span>
              <span className="opponent-chips">${chipInfo?.chips ?? '?'}</span>
              <div className="opponent-cards">
                <CardBack />
                <CardBack />
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Table center ── */}
      <div className="poker-table-felt">
        <div className="poker-pot-display">
          <span className="pot-label">Pot</span>
          <span className="pot-amount">${pot}</span>
        </div>
        <div className="poker-community">
          {[0, 1, 2, 3, 4].map((i) =>
            board[i] ? (
              <CardFace key={i} card={board[i]} />
            ) : (
              <div key={i} className="poker-card card-placeholder" />
            )
          )}
        </div>
      </div>

      {/* ── Your hand ── */}
      <div className="poker-your-area">
        <div className="your-cards">
          {yourHand.length === 0 ? (
            <span className="text-muted">Waiting for deal…</span>
          ) : (
            yourHand.map((c, i) => <CardFace key={i} card={c} />)
          )}
        </div>
        <div className="your-info">
          <span className="your-name">You (Seat {yourSeat})</span>
          <span className="your-chips">
            ${chips.find((c) => c.seat === yourSeat)?.chips ?? '?'}
          </span>
        </div>
      </div>

      {/* ── Action buttons ── */}
      {!disabled && legalMoves.length > 0 && (
        <div className="poker-actions">
          {simpleActions.map((a) => (
            <button
              key={a}
              className={`btn poker-action-btn ${
                a === 'FOLD'
                  ? 'btn-danger'
                  : a === 'CALL'
                    ? 'btn-primary'
                    : 'btn-secondary'
              }`}
              onClick={() => handleAction(a)}
            >
              {a}
              {a === 'CALL' && chipsToCall > 0 && (
                <span className="action-amount">${chipsToCall}</span>
              )}
            </button>
          ))}
          {canRaise && (
            <div className="poker-raise-group">
              <input
                type="range"
                className="raise-slider"
                min={minRaise}
                max={maxRaise}
                value={raiseAmt || minRaise}
                onChange={(e) => setRaiseAmt(e.target.value)}
              />
              <input
                type="number"
                className="form-input raise-input"
                value={raiseAmt}
                onChange={(e) => setRaiseAmt(e.target.value)}
                placeholder={`$${minRaise}`}
                min={minRaise}
                max={maxRaise}
              />
              <button
                className="btn btn-primary poker-action-btn"
                onClick={handleRaise}
                disabled={
                  !raiseAmt ||
                  parseInt(raiseAmt, 10) < minRaise ||
                  parseInt(raiseAmt, 10) > maxRaise
                }
              >
                RAISE ${raiseAmt || minRaise}
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Action log ── */}
      {actionLog.length > 0 && (
        <div className="poker-log">
          {actionLog.slice(-6).map((entry, i) => (
            <div key={i} className="log-entry">{entry}</div>
          ))}
        </div>
      )}
    </div>
  );
}
