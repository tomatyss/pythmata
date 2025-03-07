import { useEffect, useRef, useState, useCallback } from 'react';

type WebSocketMessageType =
  | 'ACTIVITY_COMPLETED'
  | 'VARIABLE_UPDATED'
  | 'STATUS_CHANGED';

interface ProcessUpdate {
  id: string;
  timestamp: string;
  type: WebSocketMessageType;
  details: Record<string, unknown>;
}

interface WebSocketMessage {
  type: WebSocketMessageType;
  payload: ProcessUpdate;
}

interface UseWebSocketOptions {
  url: string;
  onMessage?: (message: WebSocketMessage) => void;
  onError?: (error: Event) => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
  autoReconnect?: boolean;
}

const useWebSocket = ({
  url,
  onMessage,
  onError,
  reconnectAttempts = 5,
  reconnectInterval = 5000,
  autoReconnect = true,
}: UseWebSocketOptions) => {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectCountRef.current = 0;
      };

      ws.onclose = () => {
        setIsConnected(false);
        if (autoReconnect && reconnectCountRef.current < reconnectAttempts) {
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectCountRef.current += 1;
            connect();
          }, reconnectInterval);
        }
      };

      ws.onerror = (event) => {
        setError('WebSocket connection error');
        onError?.(event);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          if (message.type === 'VARIABLE_UPDATED') {
            // Handle token updates
            // Ensure setUpdates is defined or passed as a parameter
            console.warn(
              'setUpdates is not defined. Please ensure it is passed or declared.'
            );
          } else {
            onMessage?.(message);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      setError('Failed to establish WebSocket connection');
      console.error('WebSocket connection error:', error);
    }
  }, [
    url,
    onMessage,
    onError,
    autoReconnect,
    reconnectAttempts,
    reconnectInterval,
  ]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const send = useCallback(
    (type: WebSocketMessageType, payload: ProcessUpdate) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        setError('WebSocket is not connected');
        return;
      }

      try {
        wsRef.current.send(
          JSON.stringify({
            type,
            payload,
          })
        );
      } catch (error) {
        setError('Failed to send message');
        console.error('Failed to send WebSocket message:', error);
      }
    },
    []
  );

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    error,
    send,
    disconnect,
    reconnect: connect,
  };
};

// Helper hook for process instance updates
export const useProcessUpdates = (instanceId: string) => {
  const [updates, setUpdates] = useState<ProcessUpdate[]>([]);

  const { isConnected, error } = useWebSocket({
    url: `ws://${window.location.host}/api/ws/instances/${instanceId}`,
    onMessage: (message) => {
      switch (message.type) {
        case 'ACTIVITY_COMPLETED':
        case 'VARIABLE_UPDATED':
        case 'STATUS_CHANGED':
          setUpdates((prev) => [...prev, message.payload]);
          break;
        default:
          console.warn(`Unknown message type: ${message.type as string}`);
      }
    },
  });

  return {
    isConnected,
    error,
    updates,
    clearUpdates: () => setUpdates([]),
  };
};

export default useWebSocket;
