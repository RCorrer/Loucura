import { useApi } from '@shared/hooks/useApi';
import { useCallback } from 'react';

const BASE_URL = '/api/chat';

/**
 * Hook para consumir o endpoint de chat (Agent Framework + MCP).
 *
 * POST /api/chat  -> envia mensagem e recebe resposta do agente
 */
export const useChatApi = () => {
  const { request, loading, error } = useApi();

  const enviarMensagem = useCallback(
    (payload) => request(BASE_URL, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
    [request]
  );

  return { enviarMensagem, loading, error };
};
