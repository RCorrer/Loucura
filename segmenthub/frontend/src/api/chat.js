import { useApi } from '@shared/hooks/useApi';
import { useCallback } from 'react';

const BASE_URL = '/api/chat/mensagem';

/**
 * Hook para consumir o endpoint de chat (Agent Framework + MCP).
 * NOTA: Este hook NÃO é usado — a page ChatSegmentacao usa useChat do shared-ui.
 *
 * POST /api/chat/mensagem  -> envia mensagem e recebe resposta do agente
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
