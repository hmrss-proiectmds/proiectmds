/**
 * WebSocket manager for live game connections.
 */

export function createGameSocket(gameId, token) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const url = `${protocol}//${host}/api/games/ws/${gameId}?token=${token}`;

  const ws = new WebSocket(url);
  return ws;
}
