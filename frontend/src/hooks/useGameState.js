import { useState, useEffect, useRef, useCallback } from 'react';
import { createGameSocket } from '../api/websocket';

/**
 * Hook that manages a WebSocket connection to a live game.
 * Returns the current game state and a sendMove function.
 */
export function useGameState(gameId) {
  const [gameState, setGameState] = useState(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!gameId) return;

    const token = localStorage.getItem('access_token');
    if (!token) {
      setError('Not authenticated');
      return;
    }

    const ws = createGameSocket(gameId, token);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'game_state') {
        setGameState(data);
      } else if (data.type === 'error') {
        setError(data.message);
        // Clear error after 3s
        setTimeout(() => setError(null), 3000);
      }
    };

    ws.onclose = (event) => {
      setConnected(false);
      if (event.code !== 1000) {
        setError(event.reason || 'Connection lost');
      }
    };

    ws.onerror = () => {
      setError('WebSocket error');
    };

    return () => {
      ws.close(1000);
      wsRef.current = null;
    };
  }, [gameId]);

  const sendMove = useCallback((moveUci) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'move', move: moveUci }));
    }
  }, []);

  const sendResign = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'resign' }));
    }
  }, []);

  return { gameState, connected, error, sendMove, sendResign };
}
