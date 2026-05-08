import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { api } from '../api/client';
import './GameLobby.css';

export default function GameLobby() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [openGames, setOpenGames] = useState([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

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
        game_type: 'chess',
        vs_ai: vsAi,
        bot_type: botType,
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

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">♟️ Game Lobby</h1>
        <p className="page-subtitle">Create a new game or join an open match</p>
      </div>

      {error && <div className="alert alert-error mb-4">{error}</div>}

      {/* Create game buttons */}
      <div className="lobby-create-section">
        <h2 className="lobby-section-title">Start a New Game</h2>
        <div className="lobby-create-buttons">
          <button
            className="btn btn-primary btn-lg lobby-create-btn"
            onClick={() => handleCreate(false)}
            disabled={creating}
          >
            <span className="lobby-btn-icon">👥</span>
            <div>
              <div className="lobby-btn-title">Play vs Human</div>
              <div className="lobby-btn-desc">Create a game and wait for an opponent</div>
            </div>
          </button>
          <button
            className="btn btn-secondary btn-lg lobby-create-btn"
            onClick={() => handleCreate(true, 'random')}
            disabled={creating}
          >
            <span className="lobby-btn-icon">🎲</span>
            <div>
              <div className="lobby-btn-title">Play vs Random Bot</div>
              <div className="lobby-btn-desc">Instant game against a random-move AI</div>
            </div>
          </button>
          <button
            className="btn btn-lg lobby-create-btn lobby-btn-hf"
            onClick={() => handleCreate(true, 'chessbot')}
            disabled={creating}
          >
            <span className="lobby-btn-icon">🧠</span>
            <div>
              <div className="lobby-btn-title">Play vs ChessBot AI</div>
              <div className="lobby-btn-desc">HuggingFace transformer trained on 750M positions</div>
            </div>
          </button>
        </div>
      </div>

      {/* Open games list */}
      <div className="lobby-open-section">
        <h2 className="lobby-section-title">
          Open Games
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
              return (
                <div key={game.game_id} className="card card-hover lobby-game-card">
                  <div className="lobby-game-info">
                    <span className="lobby-game-type">♟ {game.game_type}</span>
                    <span className="lobby-game-creator">
                      Created by <strong>{creator?.username || '?'}</strong>
                    </span>
                    <span className="badge badge-accent font-mono">
                      {creator?.elo_rating || '?'} ELO
                    </span>
                  </div>
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
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
