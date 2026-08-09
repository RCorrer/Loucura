import { useState, useCallback } from 'react';
import { useApi } from './useApi';

export function useChat(endpoint = '/api/chat/mensagem') {
  const { request, loading } = useApi();
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);

  const sendMessage = useCallback(async (content) => {
    const userMsg = { role: 'user', content, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);

    try {
      const payload = {
        mensagem: content,
        session_id: sessionId,
        historico: messages.map(m => ({ role: m.role, content: m.content }))
      };
      
      const response = await request(endpoint, {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      const assistantMsg = {
        role: 'assistant',
        content: response.resposta || 'Sem resposta',
        regras_json: response.regras_json,
        precisa_confirmacao: response.precisa_confirmacao || false,
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, assistantMsg]);
      if (response.session_id) setSessionId(response.session_id);
      
      return response;
    } catch (err) {
      const errorMsg = {
        role: 'assistant',
        content: `Erro: ${err.message}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMsg]);
      throw err;
    }
  }, [request, endpoint, sessionId, messages]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setSessionId(null);
  }, []);

  return { messages, sendMessage, clearMessages, loading };
}