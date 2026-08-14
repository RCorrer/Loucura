import { useApi } from '@shared/hooks/useApi';
import { useCallback } from 'react';

const BASE_URL = '/api/estimativa';

/**
 * Hook para consumir o endpoint de estimativa.
 * POST /api/estimativa/preview
 * Request:  { publico_base, inclusao: RegraNo, exclusao: RegraNo|null }
 * Response: { estimativa: int, inclusao: int, exclusao: int, tempo_ms: int }
 */
export const useEstimativaApi = () => {
  const { request, loading, error } = useApi();

  const calcularPreview = useCallback(
    (regrasJson) =>
      request(`${BASE_URL}/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(regrasJson),
      }),
    [request]
  );

  return { calcularPreview, loading, error };
};
