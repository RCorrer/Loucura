import { useApi } from '@shared/hooks/useApi';
import { useCallback } from 'react';

const BASE_URL = '/api/segmentacoes';

export const useSegmentacoesApi = () => {
  const { request, loading, error } = useApi();

  const listar = useCallback((filtros = {}) => {
    const params = new URLSearchParams(filtros).toString();
    return request(`${BASE_URL}?${params}`);
  }, [request]);

  const buscar = useCallback((id) => request(`${BASE_URL}/${id}`), [request]);

  const criar = useCallback((dados) => request(BASE_URL, { method: 'POST', body: JSON.stringify(dados) }), [request]);

  const atualizar = useCallback((id, dados) => request(`${BASE_URL}/${id}`, { method: 'PUT', body: JSON.stringify(dados) }), [request]);

  const arquivar = useCallback((id) => request(`${BASE_URL}/${id}`, { method: 'DELETE' }), [request]);

  const clonar = useCallback((id, dados) => request(`${BASE_URL}/${id}/clonar`, { method: 'POST', body: JSON.stringify(dados) }), [request]);

  const aprovar = useCallback((id, checklist) => request(`${BASE_URL}/${id}/aprovar`, { method: 'POST', body: JSON.stringify(checklist) }), [request]);

  const ativar = useCallback((id) => request(`${BASE_URL}/${id}/ativar`, { method: 'POST' }), [request]);

  const pausar = useCallback((id) => request(`${BASE_URL}/${id}/pausar`, { method: 'POST' }), [request]);

  const reativar = useCallback((id) => request(`${BASE_URL}/${id}/reativar`, { method: 'POST' }), [request]);

  const encerrar = useCallback((id) => request(`${BASE_URL}/${id}/encerrar`, { method: 'POST' }), [request]);

  const executar = useCallback((id) => request(`${BASE_URL}/${id}/executar`, { method: 'POST' }), [request]);

  // S1-FRONT-04: Destino e Vigência
  const buscarDestinos = useCallback((id) => request(`${BASE_URL}/${id}/destinos`), [request]);

  const atualizarDestinos = useCallback(
    (id, destinos) => request(`${BASE_URL}/${id}/destinos`, { method: 'PUT', body: JSON.stringify(destinos) }),
    [request]
  );

  const atualizarVigencia = useCallback(
    (id, dados) => request(`${BASE_URL}/${id}/vigencia`, { method: 'PUT', body: JSON.stringify(dados) }),
    [request]
  );

  return {
    listar,
    buscar,
    criar,
    atualizar,
    arquivar,
    clonar,
    aprovar,
    ativar,
    pausar,
    reativar,
    encerrar,
    executar,
    buscarDestinos,
    atualizarDestinos,
    atualizarVigencia,
    loading,
    error,
  };
};