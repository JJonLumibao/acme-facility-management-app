import { useEffect, useRef, useState } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Fab from '@mui/material/Fab';
import Drawer from '@mui/material/Drawer';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Tooltip from '@mui/material/Tooltip';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useTheme } from '@mui/material/styles';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import CloseIcon from '@mui/icons-material/Close';
import SendIcon from '@mui/icons-material/Send';
import { askAssistant, getAssistantSuggestions } from '../../services/assistantService';
import { ApiError } from '../../services/apiClient';
import type { AssistantLink } from '../../types';
import '../../styles/assistant.css';

const MAX_LENGTH = 500;

interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  text: string;
  links?: AssistantLink[];
  suggestions?: string[];
  isError?: boolean;
}

/** Floating "Ask" button + side panel for asking questions about incidents, locations and workload. */
export default function AssistantPanel() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [starters, setStarters] = useState<string[]>([]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const nextId = useRef(1);
  const listEnd = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Load role-specific starter questions the first time the panel opens.
  useEffect(() => {
    if (open && starters.length === 0) {
      getAssistantSuggestions()
        .then((data) => setStarters(data.suggestions))
        .catch(() => setStarters([]));
    }
  }, [open, starters.length]);

  useEffect(() => {
    listEnd.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, isSending]);

  const addMessage = (message: Omit<ChatMessage, 'id'>) =>
    setMessages((prev) => [...prev, { ...message, id: nextId.current++ }]);

  const send = async (text: string) => {
    const question = text.trim().slice(0, MAX_LENGTH);
    if (!question || isSending) return;

    addMessage({ role: 'user', text: question });
    setInput('');
    setIsSending(true);
    try {
      const reply = await askAssistant(question);
      addMessage({
        role: 'assistant',
        text: reply.answer,
        links: reply.links,
        suggestions: reply.suggestions,
      });
    } catch (err) {
      addMessage({
        role: 'assistant',
        text: err instanceof ApiError ? err.message : 'Sorry, I could not answer that right now.',
        isError: true,
      });
    } finally {
      setIsSending(false);
      inputRef.current?.focus();
    }
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    send(input);
  };

  // Enter sends; Shift+Enter adds a new line.
  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      send(input);
    }
  };

  const suggestionChips = (questions: string[]) => (
    <div className="assistant-suggestions">
      {questions.map((question) => (
        <Chip key={question} label={question} size="small" variant="outlined" onClick={() => send(question)} disabled={isSending} />
      ))}
    </div>
  );

  return (
    <>
      {!open && (
        <Tooltip title="Ask about your incidents" placement="left">
          <Fab color="primary" aria-label="Open assistant" className="assistant-fab" onClick={() => setOpen(true)}>
            <AutoAwesomeIcon />
          </Fab>
        </Tooltip>
      )}

      <Drawer
        anchor="right"
        open={open}
        onClose={() => setOpen(false)}
        slotProps={{ paper: { className: 'assistant-drawer', sx: { width: isMobile ? '100%' : 400 } } }}
      >
        <Box className="assistant-header">
          <AutoAwesomeIcon color="primary" />
          <Box sx={{ flex: 1 }}>
            <Typography variant="subtitle1" component="h2" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
              Ask ACME
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Answers use live incident data you have access to
            </Typography>
          </Box>
          <IconButton aria-label="Close assistant" onClick={() => setOpen(false)}>
            <CloseIcon />
          </IconButton>
        </Box>

        <div className="assistant-messages" aria-live="polite">
          {messages.length === 0 && (
            <div className="assistant-bubble assistant-bubble-bot">
              <Typography variant="body2">
                Hi! Ask me about open incidents, hotspots, response times and more. Try:
              </Typography>
              {suggestionChips(starters)}
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`assistant-bubble ${message.role === 'user' ? 'assistant-bubble-user' : 'assistant-bubble-bot'}${
                message.isError ? ' assistant-bubble-error' : ''
              }`}
            >
              <Typography variant="body2" className="assistant-text">
                {message.text}
              </Typography>
              {message.links && message.links.length > 0 && (
                <div className="assistant-links">
                  {message.links.map((link) => (
                    <Button key={link.to} size="small" component={RouterLink} to={link.to} onClick={() => setOpen(false)}>
                      {link.label}
                    </Button>
                  ))}
                </div>
              )}
              {message.suggestions && message.suggestions.length > 0 && suggestionChips(message.suggestions)}
            </div>
          ))}

          {isSending && (
            <div className="assistant-bubble assistant-bubble-bot" aria-label="Assistant is typing">
              <span className="assistant-typing">
                <span />
                <span />
                <span />
              </span>
            </div>
          )}
          <div ref={listEnd} />
        </div>

        <form className="assistant-input" onSubmit={handleSubmit}>
          <TextField
            inputRef={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value.slice(0, MAX_LENGTH))}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question…"
            size="small"
            fullWidth
            multiline
            maxRows={3}
            autoFocus
            slotProps={{ htmlInput: { 'aria-label': 'Your question', maxLength: MAX_LENGTH } }}
          />
          <IconButton type="submit" color="primary" aria-label="Send question" disabled={isSending || !input.trim()}>
            <SendIcon />
          </IconButton>
        </form>
      </Drawer>
    </>
  );
}
