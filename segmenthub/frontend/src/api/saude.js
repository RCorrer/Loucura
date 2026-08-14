import { useApi } from '@shared/hooks/useApi';
import { useCallback } from 'react';

const BASE_URL = '/api/saude';

/**
 * Hook para consumir endpoints de saúde (S1-BACK-09).
 *
 * GET /api/saude               -> dashboard consolidado
 * GET /api/saude/{seg_id}      -> saúde detalhada
 * GET /api/saude/{seg_id}/overlap -> sobreposições
 */
export const useSaudeApi = () => {
  const { request, loading, error } = useApi();

  const obterDashboard = useCallback(() => request(BASE_URL), [request]);

  const obterDetalhe = useCallback((segId) => request(`${BASE_URL}/${segId}`), [request]);

  const obterOverlap = useCallback((segId) => request(`${BASE_URL}/${segId}/overlap`), [request]);

  return { obterDashboard, obterDetalhe, obterOverlap, loading, error };
};
