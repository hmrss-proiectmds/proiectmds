import { useParams, useNavigate } from 'react-router-dom';
import { useGameState } from '../hooks/useGameState';
import ChessBoard from '../components/ChessBoard';
import './GameBoard.css';

const SEAT_COLOR = { 1: 'White', 2: 'Black' };

export default function GameBoard() {
  const { gameId } = useParams();
  const navigate = useNavigate();
  const { gameState, connected, error, sendMove, sendResign } = useGameState(gameId);

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
  } = gameState;

  const yourPlayer = players.find((p) => p.seat === your_seat);
  const opponentPlayer = players.find((p) => p.seat !== your_seat);
  const isYourTurn = turn_seat === your_seat && !game_over;
  const isWaiting = gameStatus === 'waiting';

  const resultText = result
    ? result.result === 'draw'
      ? `Draw — ${result.reason.replace(/_/g, ' ')}`
      : result.result === `player${your_seat}_win`
        ? `You won! — ${result.reason.replace(/_/g, ' ')}`
        : `You lost — ${result.reason.replace(/_/g, ' ')}`
    : null;

  // Format move history into pairs
  const movePairs = [];
  for (let i = 0; i < move_stack_san.length; i += 2) {
    movePairs.push({
      num: Math.floor(i / 2) + 1,
      white: move_stack_san[i],
      black: move_stack_san[i + 1] || '',
    });
  }

  return (
    <div className="page-container animate-fade-in">
      <div className="game-layout">
        {/* Left column: board */}
        <div className="game-board-column">
          {/* Opponent info */}
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

          {/* Your info */}
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
        </div>

        {/* Right column: info panel */}
        <div className="game-info-column">
          {/* Status card */}
          <div className="card game-status-card">
            {isWaiting && (
              <div className="game-status waiting">
                <div className="spinner" />
                <span>Waiting for opponent…</span>
                <span className="text-muted" style={{ fontSize: 'var(--text-xs)' }}>
                  Share this link to invite a friend
                </span>
              </div>
            )}
            {!isWaiting && !game_over && (
              <div className={`game-status ${isYourTurn ? 'your-turn' : 'opponent-turn'}`}>
                <span className="status-dot" />
                <span>{isYourTurn ? 'Your turn' : "Opponent's turn"}</span>
                {is_check && <span className="badge badge-error">CHECK</span>}
              </div>
            )}
            {game_over && (
              <div className="game-status game-over-status">
                <span className="game-over-icon">
                  {result?.result === `player${your_seat}_win` ? '🏆' : result?.result === 'draw' ? '🤝' : '😔'}
                </span>
                <span className="game-over-text">{resultText}</span>
              </div>
            )}
          </div>

          {error && <div className="alert alert-error">{error}</div>}

          {/* Move history */}
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

          {/* Actions */}
          {!game_over && !isWaiting && (
            <button
              className="btn btn-danger w-full"
              onClick={() => {
                if (confirm('Are you sure you want to resign?')) sendResign();
              }}
            >
              🏳️ Resign
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
