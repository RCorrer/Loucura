import React, { useState, useRef, useEffect } from 'react';
import { Box, TextField, IconButton, Paper, Typography, CircularProgress } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import { tokens } from '../../theme/tokens';

export default function ChatPanel({ onSendMessage, messages, loading, placeholder = 'Digite sua pergunta...' }) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });

  useEffect(() => scrollToBottom(), [messages]);

  const handleSend = () => {
    if (!input.trim()) return;
    onSendMessage(input);
    setInput('');
  };

  return (
    <Paper sx={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 400, borderRadius: 2, overflow: 'hidden' }}>
      <Box sx={{ p: 2, borderBottom: '1px solid #EDEDED', bgcolor: tokens.surface.warm1 }}>
        <Typography variant="subtitle1" fontWeight={600}>Assistente</Typography>
      </Box>
      <Box sx={{ flex: 1, overflowY: 'auto', p: 2, bgcolor: tokens.surface.canvas }}>
        {messages.length === 0 && (
          <Typography color="textSecondary" align="center" sx={{ mt: 4 }}>
            Faça uma pergunta para começar.
          </Typography>
        )}
        {messages.map((msg, idx) => (
          <Box key={idx} sx={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start', mb: 2 }}>
            <Paper sx={{ p: 1.5, maxWidth: '80%', bgcolor: msg.role === 'user' ? tokens.brand.primary : '#FFFFFF', color: msg.role === 'user' ? '#FFFFFF' : 'inherit' }}>
              <Typography variant="body2">{msg.content}</Typography>
            </Paper>
          </Box>
        ))}
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2 }}>
            <CircularProgress size={24} />
          </Box>
        )}
        <div ref={messagesEndRef} />
      </Box>
      <Box sx={{ p: 2, borderTop: '1px solid #EDEDED', bgcolor: '#FFFFFF', display: 'flex' }}>
        <TextField
          fullWidth
          size="small"
          placeholder={placeholder}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          disabled={loading}
        />
        <IconButton color="primary" onClick={handleSend} disabled={loading || !input.trim()} sx={{ ml: 1 }}>
          <SendIcon />
        </IconButton>
      </Box>
    </Paper>
  );
}
