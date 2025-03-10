import { v4 as uuidv4 } from 'uuid';

export type WebSocketMessageType =
  | 'chat_message'
  | 'token'
  | 'message_received'
  | 'message_complete'
  | 'join_session'
  | 'leave_session'
  | 'typing_indicator'
  | 'assistant_typing'
  | 'client_joined'
  | 'client_left'
  | 'new_message'
  | 'error';

export type WebSocketMessageContentMap = {
  chat_message: { content: string };
  token: { messageId: string; timestamp: string };
  message_received: { messageId: string; timestamp: string; xml?: string };
  message_complete: { messageId: string; timestamp: string };
  join_session: { sessionId: string };
  leave_session: { status?: string }; // Allow optional status
  typing_indicator: { isTyping: boolean; sessionId?: string };
  assistant_typing: {
    messageId: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    xml?: string;
    timestamp: string;
  };
  client_joined: { clientId: string; timestamp: string };
  client_left: { clientId: string; timestamp: string };
  new_message: { content: string };
  error: { message: string };
  status: { status: string };
} & {
  [key in WebSocketMessageType]: unknown; // Allow additional types dynamically
};

export interface WebSocketMessage {
  type: WebSocketMessageType;
  content:
    | { content: string }
    | { messageId: string; timestamp: string }
    | { messageId: string; timestamp: string; xml?: string }
    | { status: string }
    | { clientId: string; isTyping: boolean }
    | { clientId: string; timestamp: string }
    | {
        messageId: string;
        role: 'user' | 'assistant' | 'system';
        content: string;
        xml?: string;
        timestamp: string;
      }
    | { message: string };
}

type MessageCallback<T> = (data: T) => void;
type ConnectionStateCallback = (state: ConnectionState) => void;

export type ConnectionState =
  | 'connecting'
  | 'connected'
  | 'disconnected'
  | 'reconnecting';

/**
 * WebSocket service for chat functionality
 *
 * Manages WebSocket connections, message handling, and reconnection logic
 * for real-time chat communication.
 */
class WebSocketService {
  private socket: WebSocket | null = null;
  private clientId: string;
  private messageCallbacks: Map<
    WebSocketMessageType,
    Set<MessageCallback<WebSocketMessageContentMap[WebSocketMessageType]>>
  > = new Map();
  private connectionStateCallbacks: Set<ConnectionStateCallback> = new Set();
  private connectionState: ConnectionState = 'disconnected';
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private manualDisconnect = false;
  private messageQueue: Array<{
    type: WebSocketMessageType;
    content: unknown;
  }> = [];

  constructor() {
    // Generate a unique client ID or retrieve from storage
    this.clientId = localStorage.getItem('chat_client_id') || uuidv4();
    localStorage.setItem('chat_client_id', this.clientId);
  }

  /**
   * Connect to the WebSocket server
   */
  connect(): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      return;
    }

    this.manualDisconnect = false;
    this.updateConnectionState('connecting');

    // Use the environment variable instead of window.location.host
    const wsUrl = import.meta.env.VITE_WS_URL || '';
    this.socket = new WebSocket(`${wsUrl}/api/ws/chat/${this.clientId}`);

    this.setupEventListeners();
  }

  /**
   * Set up WebSocket event listeners
   */
  private setupEventListeners(): void {
    if (!this.socket) return;

    this.socket.onopen = () => {
      this.updateConnectionState('connected');
      this.reconnectAttempts = 0;

      // Send any queued messages
      this.processMessageQueue();
    };

    this.socket.onclose = () => {
      this.updateConnectionState('disconnected');

      // Attempt to reconnect if not manually disconnected
      if (
        !this.manualDisconnect &&
        this.reconnectAttempts < this.maxReconnectAttempts
      ) {
        this.reconnect();
      }
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage;
        this.handleMessage(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };
  }

  /**
   * Handle incoming WebSocket messages
   *
   * @param message The WebSocket message
   */
  private handleMessage(message: WebSocketMessage): void {
    const callbacks = this.messageCallbacks.get(message.type);
    if (callbacks) {
      callbacks.forEach((callback) => callback(message.content));
    }
  }

  /**
   * Update the connection state and notify subscribers
   *
   * @param state The new connection state
   */
  private updateConnectionState(state: ConnectionState): void {
    this.connectionState = state;
    this.connectionStateCallbacks.forEach((callback) => callback(state));
  }

  /**
   * Attempt to reconnect to the WebSocket server
   * with exponential backoff
   */
  private reconnect(): void {
    const backoff = Math.min(30, Math.pow(2, this.reconnectAttempts));

    this.updateConnectionState('reconnecting');

    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      this.connect();
    }, backoff * 1000);
  }

  /**
   * Process any queued messages
   */
  private processMessageQueue(): void {
    if (this.messageQueue.length > 0 && this.isConnected()) {
      // Process all queued messages
      const queue = [...this.messageQueue];
      this.messageQueue = [];

      queue.forEach((item) => {
        this.send(item.type, item.content);
      });
    }
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    this.manualDisconnect = true;

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }

    this.updateConnectionState('disconnected');
  }

  /**
   * Send a message to the WebSocket server
   *
   * @param type The message type
   * @param content The message content
   */
  send(type: WebSocketMessageType, content: unknown): void {
    if (!this.isConnected()) {
      // Queue message if not connected
      this.messageQueue.push({ type, content });

      // Try to connect if disconnected
      if (this.connectionState === 'disconnected') {
        this.connect();
      }
      return;
    }

    try {
      this.socket?.send(JSON.stringify({ type, content }));
    } catch (error) {
      console.error('Failed to send WebSocket message:', error);
      // Queue the message for retry
      this.messageQueue.push({ type, content });
    }
  }

  /**
   * Subscribe to a specific message type
   *
   * @param type The message type to subscribe to
   * @param callback The callback function to call when a message of this type is received
   */
  subscribe<K extends WebSocketMessageType>(
    type: K,
    callback: MessageCallback<WebSocketMessageContentMap[K]>
  ): void {
    if (!this.messageCallbacks.has(type)) {
      this.messageCallbacks.set(type, new Set());
    }
    this.messageCallbacks.get(type)?.add(callback);
  }

  /**
   * Unsubscribe from a specific message type
   *
   * @param type The message type to unsubscribe from
   * @param callback The callback function to remove
   */
  unsubscribe(
    type: WebSocketMessageType,
    callback: MessageCallback<WebSocketMessage['content']>
  ): void {
    this.messageCallbacks.get(type)?.delete(callback);
  }

  /**
   * Subscribe to connection state changes
   *
   * @param callback The callback function to call when the connection state changes
   * @returns A function to unsubscribe
   */
  onConnectionStateChange(callback: ConnectionStateCallback): () => void {
    this.connectionStateCallbacks.add(callback);

    // Return unsubscribe function
    return () => {
      this.connectionStateCallbacks.delete(callback);
    };
  }

  /**
   * Check if the WebSocket is connected
   *
   * @returns True if connected, false otherwise
   */
  isConnected(): boolean {
    return this.socket !== null && this.socket.readyState === WebSocket.OPEN;
  }

  /**
   * Get the current connection state
   *
   * @returns The current connection state
   */
  getConnectionState(): ConnectionState {
    return this.connectionState;
  }

  /**
   * Get the client ID
   *
   * @returns The client ID
   */
  getClientId(): string {
    return this.clientId;
  }

  /**
   * Join a chat session
   *
   * @param sessionId The session ID to join
   */
  joinSession(sessionId: string): void {
    this.send('join_session', { sessionId });
  }

  /**
   * Leave the current chat session
   */
  leaveSession(): void {
    this.send('leave_session', {});
  }

  /**
   * Send a chat message
   *
   * @param content The message content
   * @param sessionId Optional session ID
   * @param processId Optional process ID
   * @param currentXml Optional current XML
   * @param model Optional model to use
   */
  sendChatMessage(
    content: string,
    sessionId?: string,
    processId?: string,
    currentXml?: string,
    model?: string
  ): void {
    this.send('chat_message', {
      content,
      sessionId,
      processId,
      currentXml,
      model,
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Send a typing indicator
   *
   * @param isTyping Whether the user is typing
   * @param sessionId The session ID
   */
  sendTypingIndicator(isTyping: boolean, sessionId?: string): void {
    if (sessionId) {
      this.send('typing_indicator', {
        isTyping,
        sessionId,
        timestamp: new Date().toISOString(),
      });
    }
  }
}

// Create a singleton instance
const websocketService = new WebSocketService();

export default websocketService;
