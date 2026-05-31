import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { api } from '../api/client';
import './GameLobby.css';

const GAME_TYPE_INFO = {
  chess:   { icon: '♟️', name: 'Chess',   players: '2 players'  },
  poker:   { icon: '🃏', name: 'Poker',   players: '3-7 players' },
  mahjong: { icon: '🀄', name: 'Mahjong', players: '4 players'  },
};

const HF_BOT_TYPE = {
  chess:   'chessbot',
  poker:   'pokerbot',
  mahjong: 'mahjongbot',
};

const HF_BOT_LABEL = {
  chess:   'ChessBot',
  poker:   'PokerBot',
  mahjong: 'MahjongBot',
};

export default function GameLobby() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [openGames, setOpenGames] = useState([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  // Creation form
  const [gameType, setGameType] = useState('chess');
  const [maxPlayers, setMaxPlayers] = useState(6);

  const fetchOpenGames = useCallback(async () => {
    try {
      const data = await api.get('/api/games/open');
      setOpenGames(data.games || []);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchOpenGames();
    const interval = setInterval(fetchOpenGames, 3000);
    return () => clearInterval(interval);
  }, [fetchOpenGames]);

  const handleCreate = async (vsAi, botType = 'random') => {
    setCreating(true);
    setError('');
    try {
      const game = await api.post('/api/games', {
        game_type: gameType,
        vs_ai: vsAi,
        bot_type: botType,
        max_players: gameType === 'poker' ? maxPlayers : gameType === 'mahjong' ? 4 : 2,
      });
      navigate(`/game/${game.game_id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleJoin = async (gameId) => {
    setLoading(true);
    setError('');
    try {
      await api.post(`/api/games/${gameId}/join`);
      navigate(`/game/${gameId}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddAi = async (gameId, botType) => {
    setLoading(true);
    setError('');
    try {
      await api.post(`/api/games/${gameId}/join_ai`, { bot_type: botType });
      fetchOpenGames();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const isPoker   = gameType === 'poker';
  const isMahjong = gameType === 'mahjong';

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">🎮 Game Lobby</h1>
        <p className="page-subtitle">Create a new game or join an open match</p>
      </div>

      {error && <div className="alert alert-error mb-4">{error}</div>}

      {/* ── Game type selector ── */}
      <div className="lobby-create-section">
        <h2 className="lobby-section-title">Start a New Game</h2>

        <div className="lobby-game-type-selector">
          {Object.entries(GAME_TYPE_INFO).map(([type, info]) => (
            <button
              key={type}
              className={`btn lobby-type-btn ${gameType === type ? 'active' : ''}`}
              onClick={() => setGameType(type)}
            >
              <span className="lobby-type-icon">{info.icon}</span>
              <span className="lobby-type-name">{info.name}</span>
              <span className="lobby-type-players">{info.players}</span>
            </button>
          ))}
        </div>

        {/* Player count slider (poker only) */}
        {isPoker && (
          <div className="lobby-player-count">
            <label className="form-label">Number of seats: {maxPlayers}</label>
            <input
              type="range"
              className="lobby-slider"
              min={3}
              max={7}
              value={maxPlayers}
              onChange={(e) => setMaxPlayers(parseInt(e.target.value, 10))}
            />
            <div className="lobby-slider-labels">
              <span>3</span><span>4</span><span>5</span><span>6</span><span>7</span>
            </div>
          </div>
        )}

        {/* Create buttons */}
        <div className="lobby-create-buttons">
          <button
            className="btn btn-primary btn-lg lobby-create-btn"
            onClick={() => handleCreate(false)}
            disabled={creating}
          >
            <span className="lobby-btn-icon">👥</span>
            <div>
              <div className="lobby-btn-title">Play vs Humans</div>
              <div className="lobby-btn-desc">
                {isPoker
                  ? `Create a lobby for ${maxPlayers - 1} more players`
                  : isMahjong
                    ? 'Create a lobby for 3 more players'
                    : 'Create a lobby and wait for an opponent'}
              </div>
            </div>
          </button>
          <button
            className="btn btn-secondary btn-lg lobby-create-btn"
            onClick={() => handleCreate(true, 'random')}
            disabled={creating}
          >
            <span className="lobby-btn-icon">🎲</span>
            <div>
              <div className="lobby-btn-title">Play vs Random Bots</div>
              <div className="lobby-btn-desc">
                Instant game against random-move AIs
              </div>
            </div>
          </button>
          <button
            className="btn btn-lg lobby-create-btn lobby-btn-hf"
            onClick={() => handleCreate(true, HF_BOT_TYPE[gameType] || 'random')}
            disabled={creating}
          >
            <span className="lobby-btn-icon">🧠</span>
            <div>
              <div className="lobby-btn-title">
                Play vs {HF_BOT_LABEL[gameType] || 'AI'} Bot
              </div>
              <div className="lobby-btn-desc">
                HuggingFace-powered intelligent agent
              </div>
            </div>
          </button>
        </div>
      </div>

      {/* ── Open games list ── */}
      <div className="lobby-open-section">
        <h2 className="lobby-section-title">
          Open Lobbies
          <span className="badge badge-accent" style={{ marginLeft: '0.5rem' }}>
            {openGames.length}
          </span>
        </h2>

        {openGames.length === 0 ? (
          <div className="lobby-empty card">
            <span className="lobby-empty-icon">🕐</span>
            <p>No open games right now. Create one above!</p>
          </div>
        ) : (
          <div className="lobby-game-list">
            {openGames.map((game) => {
              const creator = game.players[0];
              const isOwn = creator?.user_id === user?.id;
              const typeInfo = GAME_TYPE_INFO[game.game_type] || {};
              const slotsUsed = game.players.length;
              const slotsTotal = game.max_seats || 2;
              return (
                <div key={game.game_id} className="card card-hover lobby-game-card">
                  <div className="lobby-game-info">
                    <span className="lobby-game-type">
                      {typeInfo.icon || '🎮'} {game.game_type}
                    </span>
                    <span className="lobby-game-creator">
                      Created by <strong>{creator?.username || '?'}</strong>
                    </span>
                    <span className="badge badge-accent font-mono">
                      {slotsUsed}/{slotsTotal} players
                    </span>
                  </div>
                  <div className="lobby-game-actions">
                    {isOwn ? (
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => navigate(`/game/${game.game_id}`)}
                      >
                        Rejoin
                      </button>
                    ) : (
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={() => handleJoin(game.game_id)}
                        disabled={loading}
                      >
                        Join
                      </button>
                    )}
                    {isOwn && (
                      <>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleAddAi(game.game_id, 'random')}
                          disabled={loading}
                          title="Add a random-move bot"
                        >
                          + 🎲 Bot
                        </button>
                        <button
                          className="btn btn-sm lobby-btn-hf-sm"
                          onClick={() =>
                            handleAddAi(game.game_id, HF_BOT_TYPE[game.game_type] || 'random')
                          }
                          disabled={loading}
                          title="Add a HuggingFace AI bot"
                        >
                          + 🧠 AI
                        </button>
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
