import React, { useState, useEffect } from 'react';
import { PageHeader, DataTable, StatusBadge, LoadingState, EmptyState } from '@shared';
import { Box, Chip, TextField, MenuItem, Button, IconButton, Tooltip, InputAdornment } from '@mui/material';
import { useSegmentacoesApi } from '../api/segmentacoes';
import { useNavigate } from 'react-router-dom';
import AddIcon from '@mui/icons-material/Add';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import VisibilityIcon from '@mui/icons-material/Visibility';
import SearchIcon from '@mui/icons-material/Search';

export default function ListaSegmentacoes() {
  const navigate = useNavigate();
  const { listar, clonar, loading, error } = useSegmentacoesApi();

  const [segmentacoes, setSegmentacoes] = useState([]);
  const [filtros, setFiltros] = useState({ page: 1, size: 10, status: '' });

  // Estados da busca
  const [buscaInput, setBuscaInput] = useState('');   // valor digitado
  const [buscaAtiva, setBuscaAtiva] = useState('');   // valor que será usado na requisição (só atualiza no Enter)

  const [meta, setMeta] = useState({ page: 1, size: 10, total: 0, total_pages: 0 });

  // ============================================================
  // 1. CARREGAR LISTA (usa buscaAtiva)
  // ============================================================
  const carregar = async () => {
    try {
      const response = await listar({
        ...filtros,
        busca: buscaAtiva, // usa o valor confirmado
      });
      const rowsWithId = (response.data || []).map(row => ({
        ...row,
        id: row.seg_id,
      }));
      setSegmentacoes(rowsWithId);
      setMeta(response.meta || { page: 1, size: 10, total: 0, total_pages: 0 });
    } catch (err) {
      console.error('Erro ao carregar segmentações:', err);
    }
  };

  // Carrega quando página, status ou busca ativa mudam
  useEffect(() => {
    carregar();
  }, [filtros.page, filtros.size, filtros.status, buscaAtiva]);

  // Resetar página quando a busca ativa mudar
  useEffect(() => {
    setFiltros((prev) => ({ ...prev, page: 1 }));
  }, [buscaAtiva]);

  // ============================================================
  // 2. SUBMETER BUSCA (Enter ou clique no ícone)
  // ============================================================
  const handleBuscar = () => {
    setBuscaAtiva(buscaInput); // atualiza a busca ativa → dispara requisição
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleBuscar();
    }
  };

  // ============================================================
  // 3. LIMPAR BUSCA
  // ============================================================
  const handleLimparBusca = () => {
    setBuscaInput('');
    setBuscaAtiva(''); // limpa a busca ativa → volta a listar todos
  };

  // ============================================================
  // 4. AÇÕES
  // ============================================================
  const handleFiltroChange = (key, value) => {
    setFiltros((prev) => ({ ...prev, [key]: value, page: 1 }));
  };

  const handlePageChange = (newPage) => {
    setFiltros((prev) => ({ ...prev, page: newPage }));
  };

  const handleClone = async (id) => {
    try {
      const response = await clonar(id, { owner: 'admin' });
      await carregar();
      if (response && response.seg_id) {
        navigate(`/segmentacoes/${response.seg_id}`);
      }
    } catch (err) {
      console.error('Erro ao clonar:', err);
    }
  };

  const handleVisualizar = (id) => {
    navigate(`/segmentacoes/${id}`);
  };

  // ============================================================
  // 5. COLUNAS
  // ============================================================
  const columns = [
    { field: 'seg_codigo', headerName: 'Código', width: 150 },
    { field: 'nome', headerName: 'Nome', width: 200 },
    {
      field: 'status',
      headerName: 'Status',
      width: 130,
      renderCell: (params) => (
        <StatusBadge status={params.value} customLabel={params.value?.toUpperCase()} />
      ),
    },
    {
      field: 'objetivo',
      headerName: 'Objetivo',
      width: 150,
      renderCell: (params) => <Chip label={params.value} size="small" />,
    },
    { field: 'owner', headerName: 'Owner', width: 130 },
    { field: 'criado_em', headerName: 'Criado em', width: 180 },
    {
      field: 'actions',
      headerName: 'Ações',
      width: 150,
      renderCell: (params) => (
        <Box>
          <Tooltip title="Visualizar">
            <IconButton size="small" onClick={() => handleVisualizar(params.row.seg_id)}>
              <VisibilityIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Clonar">
            <IconButton size="small" onClick={() => handleClone(params.row.seg_id)}>
              <ContentCopyIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      ),
    },
  ];

  // ============================================================
  // 6. RENDER
  // ============================================================
  if (loading && segmentacoes.length === 0) return <LoadingState />;
  if (error) return <div>Erro ao carregar: {error}</div>;

  return (
    <>
      <PageHeader
        title="Segmentações"
        subtitle="Gerencie suas segmentações de clientes"
        breadcrumbs={[{ label: 'Segmentações', href: '/segmentacoes' }]}
      >
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate('/segmentacoes/nova')}
        >
          Nova Segmentação
        </Button>
      </PageHeader>

      {/* Filtros */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <TextField
          label="Buscar"
          size="small"
          value={buscaInput}
          onChange={(e) => setBuscaInput(e.target.value)}
          onKeyDown={handleKeyDown}
          sx={{ minWidth: 200 }}
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <IconButton onClick={handleBuscar} size="small">
                  <SearchIcon />
                </IconButton>
              </InputAdornment>
            ),
          }}
        />
        <TextField
          select
          label="Status"
          size="small"
          value={filtros.status}
          onChange={(e) => handleFiltroChange('status', e.target.value)}
          sx={{ minWidth: 150 }}
        >
          <MenuItem value="">Todos</MenuItem>
          <MenuItem value="rascunho">Rascunho</MenuItem>
          <MenuItem value="em_aprovacao">Em Aprovação</MenuItem>
          <MenuItem value="aprovada">Aprovada</MenuItem>
          <MenuItem value="ativa">Ativa</MenuItem>
          <MenuItem value="pausada">Pausada</MenuItem>
          <MenuItem value="encerrada">Encerrada</MenuItem>
          <MenuItem value="arquivada">Arquivada</MenuItem>
        </TextField>
        <Button variant="outlined" onClick={handleLimparBusca}>
          Limpar
        </Button>
      </Box>

      {/* Tabela */}
      {segmentacoes.length === 0 ? (
        <EmptyState
          title="Nenhuma segmentação encontrada"
          description="Crie sua primeira segmentação clicando em 'Nova Segmentação'"
          actionText="Criar Segmentação"
          onAction={() => navigate('/segmentacoes/nova')}
        />
      ) : (
        <DataTable
          rows={segmentacoes}
          columns={columns}
          loading={loading}
          pagination
          page={meta.page}
          pageSize={meta.size}
          total={meta.total}
          onPageChange={handlePageChange}
        />
      )}
    </>
  );
}