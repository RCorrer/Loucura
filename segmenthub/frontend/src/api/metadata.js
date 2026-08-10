import { useApi } from '@shared/hooks/useApi';
import { useCallback, useMemo } from 'react';

const BASE_URL = '/api/metadata';

export const useMetadataApi = () => {
  const { request, loading, error } = useApi();

  const listarTemas = useCallback(() => request(`${BASE_URL}/temas`), [request]);
  const listarCampos = useCallback((tema) => request(`${BASE_URL}/temas/${tema}/campos`), [request]);
  const listarPublicos = useCallback(() => request(`${BASE_URL}/publicos`), [request]);
  const listarCamposEmUso = useCallback(() => request(`${BASE_URL}/campos-em-uso`), [request]);
  const obterCampo = useCallback((id) => request(`${BASE_URL}/campos/${id}`), [request]);

  // Funções admin (se existirem)
  const listarCamposAdmin = useCallback((filtros) => request(`${BASE_URL}/admin/campos?${new URLSearchParams(filtros)}`), [request]);
  const atualizarFlags = useCallback((id, data) => request(`${BASE_URL}/admin/campos/${id}/flags`, { method: 'PUT', body: JSON.stringify(data) }), [request]);
  const atualizarStatus = useCallback((id, data) => request(`${BASE_URL}/admin/campos/${id}/status`, { method: 'PUT', body: JSON.stringify(data) }), [request]);
  const listarHistorico = useCallback((filtros) => request(`${BASE_URL}/admin/historico?${new URLSearchParams(filtros)}`), [request]);

  return useMemo(() => ({
    listarTemas,
    listarCampos,
    listarPublicos,
    listarCamposEmUso,
    obterCampo,
    listarCamposAdmin,
    atualizarFlags,
    atualizarStatus,
    listarHistorico,
    loading,
    error,
  }), [listarTemas, listarCampos, listarPublicos, listarCamposEmUso, obterCampo, listarCamposAdmin, atualizarFlags, atualizarStatus, listarHistorico, loading, error]);
};