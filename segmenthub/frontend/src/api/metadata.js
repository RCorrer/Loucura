import { useApi } from '@shared/hooks/useApi';
import { useCallback, useMemo } from 'react';

const BASE_URL = '/api/metadata';

export const useMetadataApi = () => {
  const { request, loading, error } = useApi();

  const listarTemas = useCallback(() => request(`${BASE_URL}/temas`), [request]);
  const listarTemasCompletos = useCallback(() => request(`${BASE_URL}/temas-completos`), [request]);
  const listarCampos = useCallback((tema) => request(`${BASE_URL}/temas/${tema}/caracteristicas`), [request]);
  const listarPublicos = useCallback(() => request(`${BASE_URL}/publicos`), [request]);
  const listarCamposEmUso = useCallback(() => request(`${BASE_URL}/caracteristicas-em-uso`), [request]);
  const obterCampo = useCallback((id) => request(`${BASE_URL}/caracteristicas/${id}`), [request]);

  // FX-04: Funções admin removidas (duplicadas em metadataAdmin.js)

  return useMemo(() => ({
    listarTemas,
    listarTemasCompletos,
    listarCampos,
    listarPublicos,
    listarCamposEmUso,
    obterCampo,
    loading,
    error,
  }), [listarTemas, listarTemasCompletos, listarCampos, listarPublicos, listarCamposEmUso, obterCampo, loading, error]);
};