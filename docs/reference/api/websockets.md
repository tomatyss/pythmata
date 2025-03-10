# WebSocket API

Pythmata provides a WebSocket API for real-time communication between the frontend and backend. This enables features like streaming LLM responses, typing indicators, and multi-client chat sessions.

## Connection

To connect to the WebSocket API, use the following URL:

```
ws://{host}/api/ws/chat/{client_id}
```

Where:
- `{host}` is the hostname of the Pythmata server
- `{client_id}` is a unique identifier for the client (e.g., a UUID)

For secure connections, use `wss://` instead of `ws://`.

## Message Format

All WebSocket messages follow this JSON format:

```json
{
  "type": "message_type",
  "content": {
    // Message-specific content
  }
}
```

## Client-to-Server Messages

These are messages sent from the client to the server.

### Chat Message

Send a chat message to the LLM.

```json
{
  "type": "chat_message",
  "content": {
    "content": "Your message text",
    "sessionId": "optional-session-id",
    "processId": "optional-process-id",
    "currentXml": "optional-bpmn-xml",
    "model": "optional-model-name"
  }
}
```

### Join Session

Join an existing chat session.

```json
{
  "type": "join_session",
  "content": {
    "sessionId": "session-id"
  }
}
```

### Leave Session

Leave the current chat session.

```json
{
  "type": "leave_session",
  "content": {}
}
```

### Typing Indicator

Indicate that the user is typing.

```json
{
  "type": "typing_indicator",
  "content": {
    "isTyping": true,
    "sessionId": "session-id"
  }
}
```

## Server-to-Client Messages

These are messages sent from the server to the client.

### Token

A token from the streaming LLM response.

```json
{
  "type": "token",
  "content": {
    "content": "token-text"
  }
}
```

### Message Received

Acknowledgment that a message was received by the server.

```json
{
  "type": "message_received",
  "content": {
    "messageId": "message-id",
    "timestamp": "ISO-timestamp"
  }
}
```

### Message Complete

Notification that the LLM response is complete.

```json
{
  "type": "message_complete",
  "content": {
    "messageId": "message-id",
    "timestamp": "ISO-timestamp",
    "xml": "optional-bpmn-xml"
  }
}
```

### Assistant Typing

Notification that the assistant is generating a response.

```json
{
  "type": "assistant_typing",
  "content": {
    "status": "started"
  }
}
```

### Typing Indicator

Notification that another user in the session is typing.

```json
{
  "type": "typing_indicator",
  "content": {
    "clientId": "client-id",
    "isTyping": true,
    "timestamp": "ISO-timestamp"
  }
}
```

### Client Joined

Notification that another client has joined the session.

```json
{
  "type": "client_joined",
  "content": {
    "clientId": "client-id",
    "timestamp": "ISO-timestamp"
  }
}
```

### Client Left

Notification that another client has left the session.

```json
{
  "type": "client_left",
  "content": {
    "clientId": "client-id",
    "timestamp": "ISO-timestamp"
  }
}
```

### New Message

Notification of a new message from another client in the session.

```json
{
  "type": "new_message",
  "content": {
    "messageId": "message-id",
    "role": "user|assistant|system",
    "content": "message-content",
    "xml": "optional-bpmn-xml",
    "timestamp": "ISO-timestamp"
  }
}
```

### Error

Notification of an error.

```json
{
  "type": "error",
  "content": {
    "message": "error-message"
  }
}
```

## Example Usage

Here's an example of how to use the WebSocket API in JavaScript:

```javascript
// Generate a unique client ID
const clientId = crypto.randomUUID();

// Connect to the WebSocket
const socket = new WebSocket(`ws://localhost:8000/api/ws/chat/${clientId}`);

// Set up event handlers
socket.onopen = () => {
  console.log('Connected to WebSocket');
  
  // Join a session
  socket.send(JSON.stringify({
    type: 'join_session',
    content: {
      sessionId: 'your-session-id'
    }
  }));
};

socket.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch (message.type) {
    case 'token':
      // Handle streaming token
      console.log('Token:', message.content.content);
      break;
    case 'message_complete':
      // Handle message completion
      console.log('Message complete:', message.content.messageId);
      break;
    // Handle other message types
  }
};

// Send a chat message
function sendMessage(text) {
  socket.send(JSON.stringify({
    type: 'chat_message',
    content: {
      content: text,
      sessionId: 'your-session-id'
    }
  }));
}
```

## Error Handling and Reconnection

Clients should implement reconnection logic to handle temporary disconnections. A common approach is to use exponential backoff:

```javascript
function connect() {
  const socket = new WebSocket(`ws://localhost:8000/api/ws/chat/${clientId}`);
  
  socket.onclose = (event) => {
    console.log('Socket closed, reconnecting...');
    setTimeout(() => {
      connect();
    }, 1000 * Math.min(30, Math.pow(2, reconnectAttempts++)));
  };
  
  // Other event handlers
}
```

## Security Considerations

- WebSocket connections should be authenticated
- Use secure WebSocket connections (wss://) in production
- Implement rate limiting to prevent abuse
