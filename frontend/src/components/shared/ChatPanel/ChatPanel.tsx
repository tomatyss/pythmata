import React, { useState, useRef, useEffect, useCallback } from 'react';
import BpmnModeler from 'bpmn-js/lib/Modeler';
import {
  Box,
  Typography,
  IconButton,
  TextField,
  Button,
  Paper,
  CircularProgress,
  Tabs,
  Tab,
  Tooltip,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  Divider,
} from '@mui/material';
import {
  Close as CloseIcon,
  Send as SendIcon,
  ContentCopy as CopyIcon,
  Check as CheckIcon,
  History as HistoryIcon,
  Add as AddIcon,
  Wifi as WifiIcon,
  WifiOff as WifiOffIcon,
} from '@mui/icons-material';
import apiService from '@/services/api';
import websocketService, { ConnectionState } from '@/services/websocket';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  xml?: string;
}

interface ChatSession {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
}

interface ChatPanelProps {
  processId?: string;
  modeler?: BpmnModeler;
  onClose: () => void;
  onApplyXml?: (xml: string) => void;
}

/**
 * ChatPanel component for interacting with LLM for BPMN assistance
 *
 * Provides a chat interface for getting help with process design,
 * generating XML, and modifying existing diagrams.
 *
 * @param props Component properties
 * @returns ChatPanel component
 */
const ChatPanel: React.FC<ChatPanelProps> = ({
  processId,
  modeler,
  onClose,
  onApplyXml,
}) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        'Hello! I can help you design your BPMN process. You can ask me questions, request XML generation, or get suggestions for your current diagram.',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [currentTab, setCurrentTab] = useState(0);
  const [copied, setCopied] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // WebSocket related state
  const [connectionState, setConnectionState] =
    useState<ConnectionState>('disconnected');
  const [typingUsers, setTypingUsers] = useState<Set<string>>(new Set());
  const [streamingMessage, setStreamingMessage] = useState<Message | null>(
    null
  );
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [isTyping, setIsTyping] = useState(false);

  // WebSocket event handlers
  /**
   * Handles the incoming token data from WebSocket.
   * @param data - Object containing a 'content' string token.
   * @returns void
   */
  const handleToken = useCallback(
    (data: { content: string }) => {
      if (streamingMessage) {
        setStreamingMessage((prev) => {
          if (!prev) return null;
          return {
            ...prev,
            content: prev.content + data.content,
          };
        });
        setMessages((prev) => {
          const newMessages = [...prev];
          const lastMessage = newMessages[newMessages.length - 1];
          if (lastMessage && lastMessage.id === streamingMessage.id) {
            lastMessage.content += data.content;
            return newMessages;
          } else {
            return [
              ...prev,
              {
                ...streamingMessage,
                content: streamingMessage.content + data.content,
              },
            ];
          }
        });
      } else {
        const newMessage: Message = {
          id: `streaming-${Date.now()}`,
          role: 'assistant',
          content: data.content,
          timestamp: new Date(),
        };
        setStreamingMessage(newMessage);
        setMessages((prev) => [...prev, newMessage]);
      }
    },
    [streamingMessage]
  );

  const handleMessageReceived = useCallback(
    (data: { messageId: string; timestamp: string }) => {
      console.warn('Message received by server:', data.messageId);
    },
    []
  );

  const handleMessageComplete = useCallback(
    (data: { messageId: string; timestamp: string; xml?: string }) => {
      setStreamingMessage(null);
      setLoading(false);
      if (data.xml && onApplyXml) {
        onApplyXml(data.xml);
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            role: 'system',
            content: 'Changes have been automatically applied to the diagram.',
            timestamp: new Date(),
          },
        ]);
      }
    },
    [onApplyXml]
  );

  const handleAssistantTyping = useCallback((data: { status: string }) => {
    if (data.status === 'started') {
      setLoading(true);
    }
  }, []);

  const handleTypingIndicator = useCallback(
    (data: { isTyping: boolean; sessionId?: string }) => {
      // Since we don't have clientId in the updated type, we can use sessionId as an identifier
      // or if that's not available, use a default identifier
      const identifier = data.sessionId || 'anonymous-user';

      setTypingUsers((prev) => {
        const newTypingUsers = new Set(prev);
        if (data.isTyping) {
          newTypingUsers.add(identifier);
        } else {
          newTypingUsers.delete(identifier);
        }
        return newTypingUsers;
      });
    },
    []
  );

  const handleClientJoined = useCallback(
    (data: { clientId: string; timestamp: string }) => {
      setMessages((prev) => [
        ...prev,
        {
          id: `join-${Date.now()}`,
          role: 'system',
          content: `Another user joined the chat.`,
          timestamp: new Date(data.timestamp),
        },
      ]);
    },
    []
  );

  const handleClientLeft = useCallback(
    (data: { clientId: string; timestamp: string }) => {
      setMessages((prev) => [
        ...prev,
        {
          id: `leave-${Date.now()}`,
          role: 'system',
          content: `Another user left the chat.`,
          timestamp: new Date(data.timestamp),
        },
      ]);
      setTypingUsers((prev) => {
        const newTypingUsers = new Set(prev);
        newTypingUsers.delete(data.clientId);
        return newTypingUsers;
      });
    },
    []
  );

  const handleNewMessage = useCallback(
    (data: {
      messageId: string;
      role: 'user' | 'assistant' | 'system';
      content: string;
      xml?: string;
      timestamp: string;
    }) => {
      setMessages((prev) => [
        ...prev,
        {
          id: data.messageId,
          role: data.role,
          content: data.content,
          timestamp: new Date(data.timestamp),
          xml: data.xml,
        },
      ]);
      if (data.xml && onApplyXml) {
        onApplyXml(data.xml);
      }
    },
    [onApplyXml]
  );

  const handleError = useCallback((data: { message: string }) => {
    console.error('WebSocket error:', data.message);
    setMessages((prev) => [
      ...prev,
      {
        id: `error-${Date.now()}`,
        role: 'system',
        content: `Error: ${data.message}`,
        timestamp: new Date(),
      },
    ]);
    setLoading(false);
  }, []);

  useEffect(() => {
    websocketService.connect();
    const unsubscribe =
      websocketService.onConnectionStateChange(setConnectionState);

    // Define callbacks
    const tokenCallback = (data: { content: string }) => handleToken(data);
    const messageReceivedCallback = (data: {
      messageId: string;
      timestamp: string;
    }) => handleMessageReceived(data);
    const messageCompleteCallback = (data: {
      messageId: string;
      timestamp: string;
      xml?: string;
    }) => handleMessageComplete(data);
    const assistantTypingCallback = (data: { status: string }) =>
      handleAssistantTyping(data);
    const typingIndicatorCallback = (data: {
      isTyping: boolean;
      sessionId?: string;
    }) => handleTypingIndicator(data);
    const clientJoinedCallback = (data: {
      clientId: string;
      timestamp: string;
    }) => handleClientJoined(data);
    const clientLeftCallback = (data: {
      clientId: string;
      timestamp: string;
    }) => handleClientLeft(data);
    const newMessageCallback = (data: {
      messageId: string;
      role: 'user' | 'assistant' | 'system';
      content: string;
      xml?: string;
      timestamp: string;
    }) => {
      handleNewMessage(data);
    };
    const errorCallback = (data: { message: string }) => handleError(data);

    // Subscribe events with callbacks
    websocketService.subscribe('token', tokenCallback);
    websocketService.subscribe('message_received', messageReceivedCallback);
    websocketService.subscribe('message_complete', messageCompleteCallback);
    websocketService.subscribe('assistant_typing', assistantTypingCallback);
    websocketService.subscribe('typing_indicator', typingIndicatorCallback);
    websocketService.subscribe('client_joined', clientJoinedCallback);
    websocketService.subscribe('client_left', clientLeftCallback);
    websocketService.subscribe('new_message', newMessageCallback);
    websocketService.subscribe('error', errorCallback);

    return () => {
      unsubscribe();
      websocketService.unsubscribe('token', tokenCallback);
      websocketService.unsubscribe('message_received', messageReceivedCallback);
      websocketService.unsubscribe('message_complete', messageCompleteCallback);
      websocketService.unsubscribe('assistant_typing', assistantTypingCallback);
      websocketService.unsubscribe('typing_indicator', typingIndicatorCallback);
      websocketService.unsubscribe('client_joined', clientJoinedCallback);
      websocketService.unsubscribe('client_left', clientLeftCallback);
      websocketService.unsubscribe('new_message', newMessageCallback);
      websocketService.unsubscribe('error', errorCallback);
      websocketService.disconnect();
    };
  }, [
    handleToken,
    handleMessageReceived,
    handleMessageComplete,
    handleAssistantTyping,
    handleTypingIndicator,
    handleClientJoined,
    handleClientLeft,
    handleNewMessage,
    handleError,
  ]);

  useEffect(() => {
    if (sessionId) {
      websocketService.joinSession(sessionId);
    }
  }, [sessionId]);

  useEffect(() => {
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
    if (input.trim() && !isTyping) {
      setIsTyping(true);
      websocketService.sendTypingIndicator(true, sessionId || undefined);
    } else if (!input.trim() && isTyping) {
      setIsTyping(false);
      websocketService.sendTypingIndicator(false, sessionId || undefined);
    } else if (input.trim() && isTyping) {
      typingTimeoutRef.current = setTimeout(() => {
        setIsTyping(false);
        websocketService.sendTypingIndicator(false, sessionId || undefined);
      }, 2000);
    }
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, [input, isTyping, sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (copied) {
      const timer = setTimeout(() => setCopied(false), 2000);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [copied]);

  const loadMessagesForSession = useCallback(
    async (sessionId: string) => {
      console.warn('Loading messages for session:', sessionId);
      setLoadingMessages(true);
      try {
        const messagesResponse = await apiService.getChatMessages(sessionId);
        console.warn('Messages response:', messagesResponse);
        if (messagesResponse && messagesResponse.length > 0) {
          const formattedMessages = messagesResponse.map((msg) => ({
            id: msg.id,
            role: msg.role as 'user' | 'assistant' | 'system',
            content: msg.content,
            timestamp: new Date(msg.createdAt),
            xml: msg.xmlContent,
          }));
          console.warn('Formatted messages:', formattedMessages);
          setMessages(formattedMessages);
        } else {
          console.warn('No messages found, setting default welcome message');
          setMessages([
            {
              id: 'welcome',
              role: 'assistant',
              content:
                'Hello! I can help you design your BPMN process. You can ask me questions, request XML generation, or get suggestions for your current diagram.',
              timestamp: new Date(),
            },
          ]);
        }
      } catch (error) {
        console.error('Error loading chat messages:', error);
        setMessages([
          {
            id: 'error',
            role: 'system',
            content: 'Failed to load chat messages. Please try again.',
            timestamp: new Date(),
          },
        ]);
      } finally {
        setLoadingMessages(false);
      }
    },
    [setMessages, setLoadingMessages]
  );

  const handleSessionSelect = useCallback(
    async (sessionId: string) => {
      setSessionId(sessionId);
      await loadMessagesForSession(sessionId);
      setCurrentTab(0);
    },
    [loadMessagesForSession, setCurrentTab]
  );

  const createNewSession = useCallback(async () => {
    if (!processId) return;
    try {
      const title = `Chat ${new Date().toLocaleString()}`;
      const response = await apiService.createChatSession({
        process_definition_id: processId,
        title,
      });
      if (response) {
        const newSession = {
          id: response.id,
          title: response.title,
          createdAt: new Date(response.createdAt),
          updatedAt: new Date(response.updatedAt),
        };
        setChatSessions((prev) => [newSession, ...prev]);
        setSessionId(newSession.id);
        setMessages([
          {
            id: 'welcome',
            role: 'assistant',
            content:
              'Hello! I can help you design your BPMN process. You can ask me questions, request XML generation, or get suggestions for your current diagram.',
            timestamp: new Date(),
          },
        ]);
        setCurrentTab(0);
      }
    } catch (error) {
      console.error('Error creating new chat session:', error);
    }
  }, [processId, setCurrentTab]);

  const loadChatSessions = useCallback(async () => {
    if (!processId) return;
    console.warn('Loading chat sessions for process:', processId);
    try {
      const response = await apiService.listChatSessions(processId);
      console.warn('Chat sessions response:', response);
      if (response && response.length > 0) {
        const formattedSessions = response.map((session) => ({
          id: session.id,
          title: session.title,
          createdAt: new Date(session.createdAt),
          updatedAt: new Date(session.updatedAt),
        }));
        console.warn('Formatted sessions:', formattedSessions);
        setChatSessions(formattedSessions);
        const mostRecentSession = formattedSessions[0];
        if (mostRecentSession) {
          console.warn('Using most recent session:', mostRecentSession.id);
          setSessionId(mostRecentSession.id);
          await loadMessagesForSession(mostRecentSession.id);
        }
      } else {
        console.warn('No chat sessions found, creating new session');
        setChatSessions([]);
        if (processId) {
          await createNewSession();
        }
      }
    } catch (error) {
      console.error('Error loading chat sessions:', error);
      setChatSessions([]);
    }
  }, [
    processId,
    createNewSession,
    loadMessagesForSession,
    setChatSessions,
    setSessionId,
  ]);

  useEffect(() => {
    if (processId) {
      loadChatSessions();
    }
  }, [processId, loadChatSessions]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    try {
      let currentXml = '';
      if (modeler) {
        const { xml } = await modeler.saveXML({ format: true });
        currentXml = xml;
      }
      websocketService.sendChatMessage(
        input,
        sessionId || undefined,
        processId,
        currentXml
      );
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'system',
          content: 'Error sending message. Please try again.',
          timestamp: new Date(),
        },
      ]);
      setLoading(false);
    }
  };

  const handleCopyXml = (xml: string) => {
    if (xml) {
      navigator.clipboard.writeText(xml);
      setCopied(true);
    }
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const renderMessageContent = (message: Message) => {
    if (message.role === 'assistant' && message.xml) {
      const parts = message.content.split('```');
      const filteredParts: string[] = [];
      let xmlBlockRemoved = false;
      for (let i = 0; i < parts.length; i++) {
        if (i % 2 === 1) {
          const codeBlock = parts[i] || '';
          if (
            codeBlock.startsWith('xml') ||
            codeBlock.trim().startsWith('<?xml') ||
            codeBlock.trim().startsWith('<bpmn:')
          ) {
            xmlBlockRemoved = true;
            continue;
          }
        }
        filteredParts.push(parts[i] || '');
      }
      let filteredContent = filteredParts
        .map((part, i) => {
          if (i > 0 && i < filteredParts.length - 1) {
            return '```' + part + '```';
          }
          return part;
        })
        .join('');
      if (xmlBlockRemoved) {
        filteredContent +=
          '\n\n(XML changes were automatically applied to the diagram)';
      }
      const content = filteredContent.split('```').map((part, i) => {
        if (i % 2 === 1) {
          const [, ...code] = part.split('\n');
          return (
            <Box
              key={i}
              sx={{
                bgcolor: 'grey.900',
                color: 'grey.100',
                p: 1,
                borderRadius: 1,
                fontFamily: 'monospace',
                whiteSpace: 'pre-wrap',
                overflowX: 'auto',
                my: 1,
              }}
            >
              {code.join('\n')}
            </Box>
          );
        } else {
          return (
            <Typography
              key={i}
              variant="body1"
              component="div"
              sx={{ whiteSpace: 'pre-wrap' }}
            >
              {part}
            </Typography>
          );
        }
      });
      return (
        <>
          {content}
          {message.xml && (
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 1 }}>
              <Tooltip title={copied ? 'Copied!' : 'Copy XML'}>
                <IconButton
                  size="small"
                  onClick={() => handleCopyXml(message.xml || '')}
                  sx={{ opacity: 0.7 }}
                >
                  {copied ? (
                    <CheckIcon fontSize="small" color="success" />
                  ) : (
                    <CopyIcon fontSize="small" />
                  )}
                </IconButton>
              </Tooltip>
            </Box>
          )}
        </>
      );
    }
    const content = message.content.split('```').map((part, i) => {
      if (i % 2 === 1) {
        const [, ...code] = part.split('\n');
        return (
          <Box
            key={i}
            sx={{
              bgcolor: 'grey.900',
              color: 'grey.100',
              p: 1,
              borderRadius: 1,
              fontFamily: 'monospace',
              whiteSpace: 'pre-wrap',
              overflowX: 'auto',
              my: 1,
            }}
          >
            {code.join('\n')}
          </Box>
        );
      } else {
        return (
          <Typography
            key={i}
            variant="body1"
            component="div"
            sx={{ whiteSpace: 'pre-wrap' }}
          >
            {part}
          </Typography>
        );
      }
    });
    return <>{content}</>;
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          p: 2,
          borderBottom: '1px solid rgba(0, 0, 0, 0.12)',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Typography variant="h6">Process Assistant</Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', ml: 2 }}>
            {connectionState === 'connected' ? (
              <Tooltip title="Connected">
                <WifiIcon fontSize="small" color="success" sx={{ mr: 1 }} />
              </Tooltip>
            ) : connectionState === 'connecting' ||
              connectionState === 'reconnecting' ? (
              <Tooltip
                title={
                  connectionState === 'connecting'
                    ? 'Connecting...'
                    : 'Reconnecting...'
                }
              >
                <CircularProgress size={16} color="warning" sx={{ mr: 1 }} />
              </Tooltip>
            ) : (
              <Tooltip title="Disconnected">
                <WifiOffIcon fontSize="small" color="error" sx={{ mr: 1 }} />
              </Tooltip>
            )}
            <Typography variant="caption" color="text.secondary">
              {connectionState === 'connected'
                ? 'Connected'
                : connectionState === 'connecting'
                  ? 'Connecting...'
                  : connectionState === 'reconnecting'
                    ? 'Reconnecting...'
                    : 'Disconnected'}
            </Typography>
          </Box>
          {typingUsers.size > 0 && (
            <Typography variant="caption" sx={{ ml: 2, fontStyle: 'italic' }}>
              Someone is typing...
            </Typography>
          )}
        </Box>
        <IconButton onClick={onClose} aria-label="close">
          <CloseIcon />
        </IconButton>
      </Box>
      <Tabs
        value={currentTab}
        onChange={handleTabChange}
        sx={{ borderBottom: '1px solid rgba(0, 0, 0, 0.12)' }}
      >
        <Tab label="Chat" />
        <Tab label="History" icon={<HistoryIcon />} iconPosition="start" />
      </Tabs>
      {currentTab === 0 ? (
        <>
          {loadingMessages && (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
              <CircularProgress size={24} />
            </Box>
          )}
          <Box sx={{ flexGrow: 1, overflow: 'auto', p: 2 }}>
            {messages.map((message) => (
              <Paper
                key={message.id}
                elevation={1}
                sx={{
                  p: 2,
                  mb: 2,
                  maxWidth: '85%',
                  ml: message.role === 'user' ? 'auto' : 0,
                  mr:
                    message.role === 'assistant' || message.role === 'system'
                      ? 'auto'
                      : 0,
                  bgcolor:
                    message.role === 'user'
                      ? 'primary.light'
                      : message.role === 'system'
                        ? 'info.light'
                        : 'background.paper',
                  color:
                    message.role === 'user'
                      ? 'primary.contrastText'
                      : 'text.primary',
                }}
              >
                {renderMessageContent(message)}
                <Typography
                  variant="caption"
                  sx={{
                    display: 'block',
                    mt: 1,
                    textAlign: 'right',
                    opacity: 0.7,
                  }}
                >
                  {message.timestamp.toLocaleTimeString()}
                </Typography>
              </Paper>
            ))}
            <div ref={messagesEndRef} />
          </Box>
          <Box sx={{ p: 2, borderTop: '1px solid rgba(0, 0, 0, 0.12)' }}>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <TextField
                fullWidth
                variant="outlined"
                placeholder="Ask about your process or request XML changes..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) =>
                  e.key === 'Enter' && !e.shiftKey && handleSend()
                }
                multiline
                maxRows={4}
                disabled={loading}
              />
              <Button
                variant="contained"
                color="primary"
                onClick={handleSend}
                disabled={loading || !input.trim()}
                startIcon={
                  loading ? (
                    <CircularProgress size={20} color="inherit" />
                  ) : (
                    <SendIcon />
                  )
                }
              >
                Send
              </Button>
            </Box>
          </Box>
        </>
      ) : (
        <Box
          sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', p: 2 }}
        >
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6">Chat History</Typography>
            <Button
              variant="contained"
              color="primary"
              startIcon={<AddIcon />}
              onClick={createNewSession}
            >
              New Chat
            </Button>
          </Box>
          {chatSessions.length === 0 ? (
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100%',
              }}
            >
              <Typography variant="body1" color="text.secondary">
                No chat sessions found. Start a new chat to begin.
              </Typography>
            </Box>
          ) : (
            <List
              sx={{
                width: '100%',
                bgcolor: 'background.paper',
                overflow: 'auto',
              }}
            >
              {chatSessions.map((session) => (
                <React.Fragment key={session.id}>
                  <ListItem disablePadding>
                    <ListItemButton
                      selected={sessionId === session.id}
                      onClick={() => handleSessionSelect(session.id)}
                    >
                      <ListItemText
                        primary={session.title}
                        secondary={`Created: ${session.createdAt.toLocaleString()}`}
                      />
                    </ListItemButton>
                  </ListItem>
                  <Divider component="li" />
                </React.Fragment>
              ))}
            </List>
          )}
        </Box>
      )}
    </Box>
  );
};

export default ChatPanel;
