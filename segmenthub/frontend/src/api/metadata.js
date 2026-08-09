import { useApi } from '@shared/hooks/useApi';

const BASE_URL = '/api/metadata';

export const useMetadataApi = () => {
  const { request, loading, error } = useApi();

  const listarTemas = () => request(`${BASE_URL}/temas`);
  const listarCampos = (tema) => request(`${BASE_URL}/temas/${tema}/caracteristicas`);
  const obterCampo = (id) => request(`${BASE_URL}/caracteristicas/${id}`);
  const listarPublicos = () => request(`${BASE_URL}/publicos`);
  const listarCamposEmUso = () => request(`${BASE_URL}/caracteristicas-em-uso`);

  return {
    listarTemas,
    listarCampos,
    obterCampo,
    listarPublicos,
    listarCamposEmUso,
    loading,
    error,
  };
};