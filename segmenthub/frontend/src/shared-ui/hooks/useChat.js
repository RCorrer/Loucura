import { useState, useCallback } from 'react';
import { useApi } from './useApi';

export function useChat(endpoint = '/api/chat/mensagem') {
  const { request, loading } = useApi();
  const [messages, setMessages] = useState([]);

  const sendMessage = useCallback(async (content) => {
    const userMsg = { role: 'user', content };
    setMessages(prev => [...prev, userMsg]);

    try {
      const response = await request(endpoint, {
        method: 'POST',
        body: JSON.stringify({ pergunta: content }),
      });
      const assistantMsg = { role: 'assistant', content: response.resposta || response.data || 'Sem resposta' };
      setMessages(prev => [...prev, assistantMsg]);
      return response;
    } catch (err) {
      const errorMsg = { role: 'assistant', content: `Erro: ${err.message}` };
      setMessages(prev => [...prev, errorMsg]);
      throw err;
    }
  }, [request, endpoint]);

  const clearMessages = useCallback(() => setMessages([]), []);

  return { messages, sendMessage, clearMessages, loading };
}
