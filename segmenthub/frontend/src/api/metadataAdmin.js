import { useApi } from '@shared/hooks/useApi';
import { useCallback } from 'react';

const BASE_URL = '/api/metadata/admin';

/**
 * Hook para endpoints admin de governança de catálogo (S1-BACK-11).
 *
 * GET  /api/metadata/admin/campos                     -> lista com filtros
 * GET  /api/metadata/admin/campos/{id}                -> detalhe
 * PUT  /api/metadata/admin/campos/{id}/flags          -> atualiza flags (S2/S3/bloco)
 * PUT  /api/metadata/admin/campos/{id}/status         -> ativa/desativa
 * GET  /api/metadata/admin/historico                   -> trilha geral
 * GET  /api/metadata/admin/campos/{id}/historico       -> histórico de um campo
 */
export const useMetadataAdminApi = () => {
  const { request, loading, error } = useApi();

  const listarCampos = useCallback(
    (filtros = {}) => {
      const params = new URLSearchParams(
        Object.entries(filtros).filter(([, v]) => v !== null && v !== undefined && v !== '')
      ).toString();
      return request(`${BASE_URL}/campos${params ? `?${params}` : ''}`);
    },
    [request]
  );

  const obterCampo = useCallback(
    (caracteristicaId) => request(`${BASE_URL}/campos/${caracteristicaId}`),
    [request]
  );

  const atualizarFlags = useCallback(
    (caracteristicaId, flags) =>
      request(`${BASE_URL}/campos/${caracteristicaId}/flags`, {
        method: 'PUT',
        body: JSON.stringify(flags),
      }),
    [request]
  );

  const atualizarStatus = useCallback(
    (caracteristicaId, ativo) =>
      request(`${BASE_URL}/campos/${caracteristicaId}/status`, {
        method: 'PUT',
        body: JSON.stringify({ ativo }),
      }),
    [request]
  );

  const listarHistorico = useCallback(
    (filtros = {}) => {
      const params = new URLSearchParams(
        Object.entries(filtros).filter(([, v]) => v !== null && v !== undefined && v !== '')
      ).toString();
      return request(`${BASE_URL}/historico${params ? `?${params}` : ''}`);
    },
    [request]
  );

  const listarHistoricoCampo = useCallback(
    (caracteristicaId, page = 1) =>
      request(`${BASE_URL}/campos/${caracteristicaId}/historico?page=${page}`),
    [request]
  );

  return {
    listarCampos,
    obterCampo,
    atualizarFlags,
    atualizarStatus,
    listarHistorico,
    listarHistoricoCampo,
    loading,
    error,
  };
};
