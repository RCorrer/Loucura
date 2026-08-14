import { useApi } from '@shared/hooks/useApi';
import { useCallback } from 'react';

const BASE_URL = '/api/notificacoes';

/**
 * Hook para operações adicionais de notificações
 * (complementa useNotifications do shared-ui com operações específicas do S1).
 *
 * GET /api/notificacoes           -> lista (query: lida=true/false)
 * PUT /api/notificacoes/{id}/lida -> marca como lida
 */
export const useNotificacoesApi = () => {
  const { request, loading, error } = useApi();

  const listar = useCallback(
    (filtros = {}) => {
      const params = new URLSearchParams(filtros).toString();
      return request(`${BASE_URL}${params ? `?${params}` : ''}`);
    },
    [request]
  );

  const marcarLida = useCallback(
    (notifId) => request(`${BASE_URL}/${notifId}/lida`, { method: 'PUT' }),
    [request]
  );

  return { listar, marcarLida, loading, error };
};
