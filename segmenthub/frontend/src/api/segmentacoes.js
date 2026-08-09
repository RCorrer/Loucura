import { useApi } from '@shared/hooks/useApi';

const BASE_URL = '/api/segmentacoes';

export const useSegmentacoesApi = () => {
  const { request, loading, error } = useApi();

  const listar = (filtros = {}) => {
    const params = new URLSearchParams(filtros).toString();
    return request(`${BASE_URL}?${params}`);
  };

  const buscar = (id) => request(`${BASE_URL}/${id}`);
  const criar = (dados) => request(BASE_URL, { method: 'POST', body: JSON.stringify(dados) });
  const atualizar = (id, dados) => request(`${BASE_URL}/${id}`, { method: 'PUT', body: JSON.stringify(dados) });
  const arquivar = (id) => request(`${BASE_URL}/${id}`, { method: 'DELETE' });
  const clonar = (id, dados) => request(`${BASE_URL}/${id}/clonar`, { method: 'POST', body: JSON.stringify(dados) });

  const aprovar = (id, checklist) => request(`${BASE_URL}/${id}/aprovar`, { method: 'POST', body: JSON.stringify(checklist) });
  const ativar = (id) => request(`${BASE_URL}/${id}/ativar`, { method: 'POST' });
  const pausar = (id) => request(`${BASE_URL}/${id}/pausar`, { method: 'POST' });
  const reativar = (id) => request(`${BASE_URL}/${id}/reativar`, { method: 'POST' });
  const encerrar = (id) => request(`${BASE_URL}/${id}/encerrar`, { method: 'POST' });
  const executar = (id) => request(`${BASE_URL}/${id}/executar`, { method: 'POST' });

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
    loading,
    error,
  };
};