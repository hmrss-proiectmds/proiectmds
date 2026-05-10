import { useState, useEffect, useRef } from 'react';
import './PokerBoard.css';

const SUIT_COLORS = { '♠': '#1e293b', '♣': '#1e293b', '♥': '#ef4444', '♦': '#ef4444' };

const HAND_RANKINGS = [
  { rank: 1, name: 'Royal Flush',     example: 'A♠ K♠ Q♠ J♠ T♠',     desc: 'A, K, Q, J, 10 of the same suit' },
  { rank: 2, name: 'Straight Flush',  example: '9♥ 8♥ 7♥ 6♥ 5♥',     desc: 'Five sequential cards of the same suit' },
  { rank: 3, name: 'Four of a Kind',  example: 'K♠ K♥ K♦ K♣ 3♠',     desc: 'Four cards of the same rank' },
  { rank: 4, name: 'Full House',      example: 'J♠ J♥ J♦ 8♣ 8♠',     desc: 'Three of a kind + a pair' },
  { rank: 5, name: 'Flush',           example: 'A♦ J♦ 8♦ 6♦ 2♦',     desc: 'Five cards of the same suit' },
  { rank: 6, name: 'Straight',        example: 'T♠ 9♥ 8♦ 7♣ 6♠',     desc: 'Five sequential cards, any suit' },
  { rank: 7, name: 'Three of a Kind', example: '7♠ 7♥ 7♦ K♣ 2♠',     desc: 'Three cards of the same rank' },
  { rank: 8, name: 'Two Pair',        example: 'A♠ A♥ 9♦ 9♣ 4♠',     desc: 'Two different pairs' },
  { rank: 9, name: 'One Pair',        example: 'Q♠ Q♥ 8♦ 5♣ 3♠',     desc: 'Two cards of the same rank' },
  { rank: 10, name: 'High Card',      example: 'A♠ J♥ 8♦ 5♣ 2♠',     desc: 'No matching cards' },
];

const ACTION_ICONS = {
  FOLD: '🏳️',
  CHECK: '✅',
  CALL: '📞',
  RAISE: '⬆️',
  ALLIN: '🔥',
};

const ACTION_LABELS = {
  FOLD: 'Fold',
  CHECK: 'Check',
  CALL: 'Call',
  RAISE: 'Raise',
  ALLIN: 'All In',
};

function CardFace({ card, className = '' }) {
  if (!card) return null;
  const suit = card.slice(-1);
  const rank = card.slice(0, -1);
  const color = SUIT_COLORS[suit] || '#1e293b';
  return (
    <div className={`poker-card ${className}`} style={{ color }}>
      <span className="card-rank">{rank}</span>
      <span className="card-suit">{suit}</span>
    </div>
  );
}

function CardBack() {
  return <div className="poker-card card-back" />;
}

/** Parse a log entry like "Seat 3: RAISE $50" into structured data */
function parseLogEntry(entry) {
  const match = entry.match(/^Seat (\d+): (.+)$/);
  if (!match) return { seat: 0, action: entry, amount: null };
  const seat = parseInt(match[1], 10);
  const rest = match[2];
  const parts = rest.split(' ');
  const action = parts[0];
  const amount = parts[1] ? parts[1].replace('$', '') : null;
  return { seat, action, amount };
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
  handNumber = 1,
  handPhase = '',
  handJustEnded = false,
  showdownInfo = null,
}) {
  const [raiseAmt, setRaiseAmt] = useState('');
  const [showRankings, setShowRankings] = useState(false);
  const [flashAction, setFlashAction] = useState(null);
  const prevLogLen = useRef(actionLog.length);
  const feedRef = useRef(null);

  // Flash the latest action when log grows
  useEffect(() => {
    if (actionLog.length > prevLogLen.current) {
      const latest = actionLog[actionLog.length - 1];
      const parsed = parseLogEntry(latest);
      const player = players.find((p) => p.seat === parsed.seat);
      setFlashAction({
        ...parsed,
        username: player?.username || `Seat ${parsed.seat}`,
        isAi: player?.is_ai ?? false,
      });
      // Clear flash after animation
      const timer = setTimeout(() => setFlashAction(null), 2000);
      prevLogLen.current = actionLog.length;
      return () => clearTimeout(timer);
    }
    prevLogLen.current = actionLog.length;
  }, [actionLog, players]);

  // Auto-scroll feed
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [actionLog]);

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

  const otherPlayers = players.filter((p) => p.seat !== yourSeat);

  return (
    <div className="poker-board">
      {/* ── Flash banner for latest action ── */}
      {flashAction && (
        <div className={`action-flash action-flash-${flashAction.action.toLowerCase()}`} key={actionLog.length}>
          <span className="flash-icon">{ACTION_ICONS[flashAction.action] || '🎯'}</span>
          <span className="flash-text">
            <strong>{flashAction.username}</strong>{' '}
            {ACTION_LABELS[flashAction.action] || flashAction.action}
            {flashAction.amount && <span className="flash-amount"> ${flashAction.amount}</span>}
          </span>
        </div>
      )}

      {/* ── Opponents around the table ── */}
      <div className="poker-opponents">
        {otherPlayers.map((p) => {
          const chipInfo = chips.find((c) => c.seat === p.seat);
          const isTurn = turnSeat === p.seat;
          // Find latest action by this player
          const lastAction = [...actionLog].reverse().find((e) => e.startsWith(`Seat ${p.seat}:`));
          const parsedAction = lastAction ? parseLogEntry(lastAction) : null;
          const isWinner = handJustEnded && showdownInfo?.winners?.some((w) => w.seat === p.seat);
          return (
            <div key={p.seat} className={`poker-opponent ${isTurn ? 'is-turn' : ''} ${isWinner ? 'is-winner' : ''}`}>
              <div className="opponent-avatar">
                {isWinner ? '🏆' : p.is_ai ? '🤖' : '👤'}
              </div>
              <span className="opponent-name">{p.username}</span>
              <span className="opponent-chips">${chipInfo?.chips ?? '?'}</span>
              {/* Last action badge */}
              {parsedAction && (
                <span className={`opponent-action-badge action-${parsedAction.action.toLowerCase()}`}>
                  {ACTION_ICONS[parsedAction.action]} {parsedAction.action}
                  {parsedAction.amount ? ` $${parsedAction.amount}` : ''}
                </span>
              )}
              <div className="opponent-cards">
                {/* During showdown, don't show cards here — the overlay handles it */}
                {handJustEnded ? null : (
                  <><CardBack /><CardBack /></>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Table center ── */}
      <div className="poker-table-felt">
        {/* Hand info bar */}
        <div className="poker-hand-info">
          <span className="hand-number">Hand #{handNumber}</span>
          {handJustEnded ? (
            <span className="hand-phase phase-showdown">SHOWDOWN</span>
          ) : handPhase ? (
            <span className={`hand-phase phase-${handPhase.toLowerCase()}`}>{handPhase}</span>
          ) : null}
        </div>

        {/* Showdown overlay */}
        {handJustEnded && (
          <div className="showdown-overlay">
            {showdownInfo?.winners?.length > 0 ? (
              <div className="showdown-content">
                <div className="showdown-title">🃏 Showdown</div>
                {showdownInfo.winners.map((w, i) => {
                  const winnerPlayer = players.find((p) => p.seat === w.seat);
                  // Only show up to 2 hole cards (guard against stale data)
                  const holeCards = (w.cards || []).slice(0, 2);
                  return (
                    <div key={w.seat} className="showdown-winner">
                      <div className="showdown-winner-header">
                        <span className="showdown-trophy">🏆</span>
                        <span className="showdown-winner-name">
                          {winnerPlayer?.username || `Seat ${w.seat}`}
                        </span>
                      </div>
                      {holeCards.length > 0 && (
                        <div className="showdown-winner-cards">
                          {holeCards.map((card, ci) => (
                            <CardFace key={ci} card={card} className="card-reveal" />
                          ))}
                        </div>
                      )}
                      <span className="showdown-hand-name">{w.hand_name}</span>
                      <span className="showdown-amount">+${w.amount_won}</span>
                    </div>
                  );
                })}
                <span className="showdown-dealing">⏳ Dealing next hand...</span>
              </div>
            ) : (
              <span className="showdown-text">🏆 Hand Over — Dealing next hand...</span>
            )}
          </div>
        )}

        <div className="poker-pot-display">
          <span className="pot-label">Pot</span>
          <span className="pot-amount">${pot}</span>
        </div>
        <div className="poker-community">
          {[0, 1, 2, 3, 4].map((i) =>
            board[i] ? (
              <CardFace key={i} card={board[i]} className="card-deal-in" />
            ) : (
              <div key={i} className="poker-card card-placeholder" />
            )
          )}
        </div>
      </div>

      {/* ── Your hand ── */}
      <div className="poker-your-area">
        <div className="your-cards">
          {handJustEnded ? (
            // During showdown: hide cards here to avoid duplication with the overlay
            null
          ) : yourHand.length === 0 ? (
            <span className="text-muted">Waiting for deal…</span>
          ) : (
            yourHand.map((c, i) => <CardFace key={i} card={c} className="card-deal-in" />)
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
                  ? 'poker-btn-fold'
                  : a === 'CALL'
                    ? 'poker-btn-call'
                    : a === 'CHECK'
                      ? 'poker-btn-check'
                      : a === 'ALLIN'
                        ? 'poker-btn-allin'
                        : 'btn-secondary'
              }`}
              onClick={() => handleAction(a)}
            >
              <span className="action-btn-icon">{ACTION_ICONS[a]}</span>
              {ACTION_LABELS[a] || a}
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
                className="btn poker-btn-call poker-action-btn"
                onClick={handleRaise}
                disabled={
                  !raiseAmt ||
                  parseInt(raiseAmt, 10) < minRaise ||
                  parseInt(raiseAmt, 10) > maxRaise
                }
              >
                <span className="action-btn-icon">⬆️</span>
                Raise ${raiseAmt || minRaise}
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Action feed (visual, not a log dump) ── */}
      {actionLog.length > 0 && (
        <div className="poker-action-feed" ref={feedRef}>
          <div className="feed-title">Action Feed</div>
          <div className="feed-entries">
            {actionLog.slice(-10).map((entry, i) => {
              const p = parseLogEntry(entry);
              const player = players.find((pl) => pl.seat === p.seat);
              const isLatest = i === Math.min(actionLog.length, 10) - 1;
              return (
                <div key={i} className={`feed-entry ${isLatest ? 'feed-entry-latest' : ''}`}>
                  <span className="feed-icon">{player?.is_ai ? '🤖' : '👤'}</span>
                  <span className="feed-seat">S{p.seat}</span>
                  <span className={`feed-action-badge action-${p.action.toLowerCase()}`}>
                    {ACTION_ICONS[p.action]} {p.action}
                  </span>
                  {p.amount && <span className="feed-amount">${p.amount}</span>}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Hand ranking reference ── */}
      <div className="hand-rankings-toggle">
        <button
          className="btn btn-ghost btn-sm"
          onClick={() => setShowRankings(!showRankings)}
        >
          📋 {showRankings ? 'Hide' : 'Show'} Hand Rankings
        </button>
      </div>

      {showRankings && (
        <div className="hand-rankings-panel animate-fade-in">
          <h4 className="rankings-title">Poker Hand Rankings</h4>
          <div className="rankings-list">
            {HAND_RANKINGS.map((h) => (
              <div key={h.rank} className="ranking-row">
                <span className="ranking-num">#{h.rank}</span>
                <div className="ranking-info">
                  <span className="ranking-name">{h.name}</span>
                  <span className="ranking-example">{h.example}</span>
                </div>
                <span className="ranking-desc">{h.desc}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
