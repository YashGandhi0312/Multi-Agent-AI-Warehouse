// ============================================================
// WebSocket Hook — Real-time simulation state synchronization
// ============================================================

import { useEffect, useRef, useState, useCallback } from 'react';
import type { WarehouseState } from '../types';
import * as api from '../services/api';

const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;

export function useSimulationWebSocket() {
  const [state, setState] = useState<WarehouseState | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchState = useCallback(async () => {
    try {
      const data = await api.getState();
      setState(data as WarehouseState);
    } catch {
      // Backend may be starting up
    }
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        if (reconnectTimerRef.current) {
          clearTimeout(reconnectTimerRef.current);
          reconnectTimerRef.current = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'pong') return;
          setState(data as WarehouseState);
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = () => {
        setConnected(false);
        // Auto-reconnect after 2 seconds
        if (!reconnectTimerRef.current) {
          reconnectTimerRef.current = setTimeout(() => {
            reconnectTimerRef.current = null;
            connect();
          }, 2000);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      // Handled by onclose
    }
  }, []);

  useEffect(() => {
    fetchState();
    connect();
    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
  }, [connect, fetchState]);

  const sendMessage = useCallback((msg: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  return { state, connected, sendMessage, refresh: fetchState };
}

