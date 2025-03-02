import React, { useState, useRef, useEffect } from 'react';
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
} from '@mui/material';
import {
  Close as CloseIcon,
  Send as SendIcon,
  ContentCopy as CopyIcon,
  Check as CheckIcon,
} from '@mui/icons-material';
import apiService from '@/services/api';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  xml?: string;
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
  const [xmlPreview, setXmlPreview] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Reset copied state after 2 seconds
  useEffect(() => {
    if (copied) {
      const timer = setTimeout(() => setCopied(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [copied]);

  // Load existing chat session if process ID is provided
  useEffect(() => {
    if (processId) {
      loadChatSessions();
    }
  }, [processId]);

  const loadChatSessions = async () => {
    if (!processId) return;

    try {
      const response = await apiService.listChatSessions(processId);

      if (response.data && response.data.length > 0) {
        // Use the most recent session
        const mostRecentSession = response.data[0];
        if (mostRecentSession) {
          setSessionId(mostRecentSession.id);

          // Load messages for this session
          const messagesResponse = await apiService.getChatMessages(
            mostRecentSession.id
          );
          if (messagesResponse.data && messagesResponse.data.length > 0) {
            const formattedMessages = messagesResponse.data.map((msg) => ({
              id: msg.id,
              role: msg.role as 'user' | 'assistant' | 'system',
              content: msg.content,
              timestamp: new Date(msg.createdAt),
              xml: msg.xmlContent,
            }));

            setMessages(formattedMessages);
          }
        }
      }
    } catch (error) {
      console.error('Error loading chat sessions:', error);
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    // Add user message
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
      // Get current XML if modeler is available
      let currentXml = '';
      if (modeler) {
        const { xml } = await modeler.saveXML({ format: true });
        currentXml = xml;
      }

      // Prepare messages for API
      const apiMessages = messages
        .filter((m) => m.role !== 'system')
        .concat(userMessage)
        .map((m) => ({
          role: m.role,
          content: m.content,
        }));

      // Send message to LLM service
      const response = await apiService.sendChatMessage({
        messages: apiMessages,
        processId,
        currentXml,
        sessionId: sessionId || undefined,
      });

      // Update session ID if provided in response
      if (response?.sessionId) {
        setSessionId(response.sessionId);
      }

      // Add assistant message
      const assistantMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: response.message,
        timestamp: new Date(),
        xml: response.xml,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // If XML is provided, set it for preview
      if (response.xml) {
        setXmlPreview(response.xml);
        setCurrentTab(1); // Switch to XML tab
      }
    } catch (error) {
      console.error('Error sending message:', error);
      // Add error message
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant',
          content: 'Sorry, an error occurred. Please try again.',
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleApplyXml = () => {
    if (xmlPreview && onApplyXml) {
      onApplyXml(xmlPreview);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'system',
          content: 'XML changes have been applied to the diagram.',
          timestamp: new Date(),
        },
      ]);
      setXmlPreview(null);
      setCurrentTab(0); // Switch back to chat
    }
  };

  const handleCopyXml = () => {
    if (xmlPreview) {
      navigator.clipboard.writeText(xmlPreview);
      setCopied(true);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  // Render message content with markdown and code highlighting
  const renderMessageContent = (message: Message) => {
    // Simple markdown-like rendering (could use a proper markdown library)
    const content = message.content.split('```').map((part, i) => {
      if (i % 2 === 1) {
        // This is a code block
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
        // Regular text
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
        <Typography variant="h6">Process Assistant</Typography>
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
        {xmlPreview && <Tab label="XML Preview" />}
      </Tabs>

      {currentTab === 0 ? (
        // Chat tab
        <>
          {/* Messages container */}
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

          {/* Input area */}
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
        // XML Preview tab
        <Box
          sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', p: 2 }}
        >
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6">XML Preview</Typography>
            <Box>
              <Tooltip title={copied ? 'Copied!' : 'Copy XML'}>
                <IconButton onClick={handleCopyXml}>
                  {copied ? <CheckIcon color="success" /> : <CopyIcon />}
                </IconButton>
              </Tooltip>
            </Box>
          </Box>

          <Box
            sx={{
              flexGrow: 1,
              overflow: 'auto',
              mb: 2,
              bgcolor: 'grey.900',
              color: 'grey.100',
              p: 2,
              borderRadius: 1,
              fontFamily: 'monospace',
              whiteSpace: 'pre-wrap',
            }}
          >
            {xmlPreview || ''}
          </Box>

          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
            <Button variant="outlined" onClick={() => setCurrentTab(0)}>
              Back to Chat
            </Button>
            <Button
              variant="contained"
              color="primary"
              onClick={handleApplyXml}
              disabled={!xmlPreview}
            >
              Apply Changes
            </Button>
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default ChatPanel;
