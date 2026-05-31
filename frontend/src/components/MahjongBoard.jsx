import { useState } from 'react';
import './MahjongBoard.css';

// ── Tile metadata ─────────────────────────────────────────────────────────────

const TILE_DISPLAY = {
  '1m':'1m','2m':'2m','3m':'3m','4m':'4m','5m':'5m','6m':'6m','7m':'7m','8m':'8m','9m':'9m',
  '1p':'1p','2p':'2p','3p':'3p','4p':'4p','5p':'5p','6p':'6p','7p':'7p','8p':'8p','9p':'9p',
  '1s':'1s','2s':'2s','3s':'3s','4s':'4s','5s':'5s','6s':'6s','7s':'7s','8s':'8s','9s':'9s',
  '1z':'東','2z':'南','3z':'西','4z':'北','5z':'白','6z':'發','7z':'中',
};

function tileLabel(t) { return TILE_DISPLAY[t] || t; }
function tileSuit(t) {
  const s = t?.[1];
  if (s === 'm') return 'man';
  if (s === 'p') return 'pin';
  if (s === 's') return 'sou';
  return 'honor';
}

// ── Tile component ────────────────────────────────────────────────────────────

function Tile({ tile, selected, onClick, disabled, last }) {
  return (
    <div
      className={[
        'mj-tile',
        `mj-tile--${tileSuit(tile)}`,
        selected  ? 'mj-tile--selected' : '',
        disabled  ? 'mj-tile--disabled' : '',
        last      ? 'mj-tile--last'     : '',
      ].join(' ')}
      onClick={!disabled ? onClick : undefined}
      title={tile}
    >
      {tileLabel(tile)}
    </div>
  );
}

function TileBack({ count, riichi }) {
  return (
    <div className="mj-tile-back-group">
      {riichi && <span className="mj-riichi-badge">RIICHI</span>}
      <div className="mj-tile-backs">
        {Array.from({ length: Math.min(count, 14) }).map((_, i) => (
          <div key={i} className="mj-tile mj-tile--back" />
        ))}
      </div>
      <span className="mj-tile-count">{count} tiles</span>
    </div>
  );
}

// ── Discard pile ──────────────────────────────────────────────────────────────

function DiscardPile({ seat, tiles, lastDiscard, lastDiscardSeat, label }) {
  return (
    <div className="mj-discard-pile">
      <div className="mj-discard-label">{label}</div>
      <div className="mj-discard-tiles">
        {tiles.length === 0
          ? <span className="mj-discard-empty">—</span>
          : tiles.map((t, i) => (
              <div
                key={i}
                className={[
                  'mj-tile mj-tile--small',
                  `mj-tile--${tileSuit(t)}`,
                  lastDiscardSeat === seat && i === tiles.length - 1 ? 'mj-tile--last' : '',
                ].join(' ')}
                title={t}
              >
                {tileLabel(t)}
              </div>
            ))
        }
      </div>
    </div>
  );
}

// ── Main board ────────────────────────────────────────────────────────────────

export default function MahjongBoard({
  yourHand       = [],
  yourSeat       = 1,
  otherPlayers   = {},
  discards       = {},
  legalMoves     = [],
  currentSeat,
  lastDiscard,
  lastDiscardSeat,
  wallRemaining  = 0,
  riichiStatus   = {},
  winnerSeat,
  winType,
  lastAction,
  players        = [],
  onMove,
  disabled,
}) {
  const [selected, setSelected] = useState(null);

  const isYourTurn = !disabled && legalMoves.length > 0;
  const canTsumo   = legalMoves.includes('TSUMO');
  const discardMoves  = legalMoves.filter(m => m.startsWith('DISCARD_'));
  const riichiMoves   = legalMoves.filter(m => m.startsWith('RIICHI_'));

  const canDiscard = selected && discardMoves.includes(`DISCARD_${selected}`);
  const canRiichi  = selected && riichiMoves.includes(`RIICHI_${selected}`);

  // Relative seat positions around the table
  const across = ((yourSeat + 1) % 4) + 1;
  const right  = (yourSeat % 4) + 1;
  const left   = ((yourSeat + 2) % 4) + 1;

  function seatName(s) {
    const p = players.find(p => p.seat === s);
    return p ? p.username : `Seat ${s}`;
  }

  function handleDiscard() {
    if (canDiscard) { onMove(`DISCARD_${selected}`); setSelected(null); }
  }
  function handleRiichi() {
    if (canRiichi) { onMove(`RIICHI_${selected}`); setSelected(null); }
  }
  function handleTsumo() {
    if (canTsumo) onMove('TSUMO');
  }

  return (
    <div className="mj-board">

      {/* ── Top opponent (across) ── */}
      <div className="mj-opponent mj-opponent--top">
        <div className="mj-opponent-label">
          {seatName(across)}
          {riichiStatus[String(across)] && <span className="mj-riichi-badge">RIICHI</span>}
          {currentSeat === across && <span className="mj-turn-indicator">▶</span>}
        </div>
        <TileBack
          count={otherPlayers[String(across)]?.count ?? 0}
          riichi={riichiStatus[String(across)]}
        />
      </div>

      {/* ── Middle row: left / table / right ── */}
      <div className="mj-middle-row">

        {/* Left opponent */}
        <div className="mj-opponent mj-opponent--side mj-opponent--left">
          <div className="mj-opponent-label">
            {seatName(left)}
            {riichiStatus[String(left)] && <span className="mj-riichi-badge">R</span>}
            {currentSeat === left && <span className="mj-turn-indicator">▶</span>}
          </div>
          <TileBack
            count={otherPlayers[String(left)]?.count ?? 0}
            riichi={riichiStatus[String(left)]}
          />
        </div>

        {/* Centre: discard piles */}
        <div className="mj-table">
          <div className="mj-discard-grid">
            <DiscardPile seat={across}         tiles={discards[String(across)] ?? []}  lastDiscard={lastDiscard} lastDiscardSeat={lastDiscardSeat} label={`Seat ${across}`} />
            <div className="mj-discard-row-sides">
              <DiscardPile seat={left}  tiles={discards[String(left)]  ?? []} lastDiscard={lastDiscard} lastDiscardSeat={lastDiscardSeat} label={`Seat ${left}`}  />
              <div className="mj-table-center">
                <div className="mj-wall-count">{wallRemaining}<br/><span>tiles left</span></div>
              </div>
              <DiscardPile seat={right} tiles={discards[String(right)] ?? []} lastDiscard={lastDiscard} lastDiscardSeat={lastDiscardSeat} label={`Seat ${right}`} />
            </div>
            <DiscardPile seat={yourSeat} tiles={discards[String(yourSeat)] ?? []} lastDiscard={lastDiscard} lastDiscardSeat={lastDiscardSeat} label="You" />
          </div>

          {lastAction && (
            <div className="mj-last-action">{lastAction}</div>
          )}
        </div>

        {/* Right opponent */}
        <div className="mj-opponent mj-opponent--side mj-opponent--right">
          <div className="mj-opponent-label">
            {seatName(right)}
            {riichiStatus[String(right)] && <span className="mj-riichi-badge">R</span>}
            {currentSeat === right && <span className="mj-turn-indicator">▶</span>}
          </div>
          <TileBack
            count={otherPlayers[String(right)]?.count ?? 0}
            riichi={riichiStatus[String(right)]}
          />
        </div>
      </div>

      {/* ── Your hand ── */}
      <div className="mj-your-hand-section">
        {riichiStatus[String(yourSeat)] && (
          <div className="mj-riichi-declared">🔴 RIICHI declared — you must discard the drawn tile</div>
        )}

        <div className="mj-your-hand">
          {yourHand.map((tile, i) => (
            <Tile
              key={`${tile}-${i}`}
              tile={tile}
              selected={selected === tile}
              onClick={() => setSelected(selected === tile ? null : tile)}
              disabled={!isYourTurn}
              last={i === yourHand.length - 1}
            />
          ))}
        </div>

        {isYourTurn && (
          <div className="mj-actions">
            <button
              className="btn btn-primary mj-action-btn"
              onClick={handleDiscard}
              disabled={!canDiscard}
            >
              Discard
            </button>
            {riichiMoves.length > 0 && (
              <button
                className="btn mj-action-btn mj-action-btn--riichi"
                onClick={handleRiichi}
                disabled={!canRiichi}
              >
                RIICHI!
              </button>
            )}
            {canTsumo && (
              <button
                className="btn mj-action-btn mj-action-btn--tsumo"
                onClick={handleTsumo}
              >
                TSUMO!
              </button>
            )}
          </div>
        )}

        {!isYourTurn && !winnerSeat && winType !== 'ryuukyoku' && (
          <div className="mj-waiting">Waiting for Seat {currentSeat}…</div>
        )}
      </div>
    </div>
  );
}
