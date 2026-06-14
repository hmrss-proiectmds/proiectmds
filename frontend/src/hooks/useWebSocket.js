/**
 * useWebSocket — reusable hook for game/spectate WebSocket connections.
 *
 * Usage:
 *   const { lastMessage, send, readyState } = useWebSocket(url, { onMessage, onClose });
 *
 * The hook automatically reconnects on unexpected disconnects (up to maxRetries).
 */

import { useEffect, useRef, useState, useCallback } from 'react';

const WS_STATES = { CONNECTING: 0, OPEN: 1, CLOSING: 2, CLOSED: 3 };

export function useWebSocket(url, { onMessage, onClose, onOpen, enabled = true } = {}) {
  const wsRef = useRef(null);
  const retryRef = useRef(0);
  const maxRetries = 5;
  const retryDelayMs = 2000;
  const [readyState, setReadyState] = useState(WS_STATES.CLOSED);

  const onMessageRef = useRef(onMessage);
  const onCloseRef = useRef(onClose);
  const onOpenRef = useRef(onOpen);
  useEffect(() => { onMessageRef.current = onMessage; }, [onMessage]);
  useEffect(() => { onCloseRef.current = onClose; }, [onClose]);
  useEffect(() => { onOpenRef.current = onOpen; }, [onOpen]);

  const connectRef = useRef(null);

  const connect = useCallback(() => {
    if (!url || !enabled) return;

    const ws = new WebSocket(url);
    wsRef.current = ws;
    setReadyState(WS_STATES.CONNECTING);

    ws.onopen = () => {
      retryRef.current = 0;
      setReadyState(WS_STATES.OPEN);
      onOpenRef.current?.();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessageRef.current?.(data);
      } catch {
        onMessageRef.current?.(event.data);
      }
    };

    ws.onclose = (event) => {
      setReadyState(WS_STATES.CLOSED);
      onCloseRef.current?.(event);

      // Reconnect on unexpected close (not intentional closes like 4001/4003/4004)
      const intentional = [4001, 4003, 4004].includes(event.code) || event.code === 1000;
      if (!intentional && retryRef.current < maxRetries) {
        retryRef.current += 1;
        setTimeout(() => {
          connectRef.current?.();
        }, retryDelayMs * retryRef.current);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [url, enabled]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    connect();
    return () => {
      const ws = wsRef.current;
      if (ws) {
        ws.onclose = null; // prevent reconnect on intentional unmount
        ws.close(1000, 'component unmounted');
      }
    };
  }, [connect]);

  const send = useCallback((data) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WS_STATES.OPEN) {
      ws.send(typeof data === 'string' ? data : JSON.stringify(data));
    }
  }, []);

  return { send, readyState, isConnected: readyState === WS_STATES.OPEN };
}
