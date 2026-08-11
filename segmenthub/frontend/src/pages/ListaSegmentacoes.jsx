import React, { useState, useEffect, useCallback } from 'react';
import { PageHeader, DataTable, StatusBadge, EmptyState } from '@shared';
import { Box, Chip, TextField, MenuItem, Button, IconButton, Tooltip, InputAdornment, Alert } from '@mui/material';
import { useSegmentacoesApi } from '../api/segmentacoes';
import { useNavigate } from 'react-router-dom';
import AddIcon from '@mui/icons-material/Add';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import VisibilityIcon from '@mui/icons-material/Visibility';
import EditIcon from '@mui/icons-material/Edit';
import SearchIcon from '@mui/icons-material/Search';

export default function ListaSegmentacoes() {
  const navigate = useNavigate();
  const { listar, clonar, loading, error } = useSegmentacoesApi();

  const [segmentacoes, setSegmentacoes] = useState([]);
  const [filtros, setFiltros] = useState({ page: 1, size: 10, status: '' });
  const [buscaInput, setBuscaInput] = useState('');
  const [buscaAtiva, setBuscaAtiva] = useState('');
  const [meta, setMeta] = useState({ page: 1, size: 10, total: 0, total_pages: 0 });
  const [errorMessage, setErrorMessage] = useState(null);

  const carregar = useCallback(async () => {
    try {
      const response = await listar({
        ...filtros,
        busca: buscaAtiva,
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
  }, [listar, filtros, buscaAtiva]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  useEffect(() => {
    setFiltros((prev) => ({ ...prev, page: 1 }));
  }, [buscaAtiva]);

  const handleBuscar = () => {
    setBuscaAtiva(buscaInput);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleBuscar();
    }
  };

  const handleLimparBusca = () => {
    setBuscaInput('');
    setBuscaAtiva('');
    setFiltros((prev) => ({ ...prev, status: '', page: 1 }));
    setErrorMessage(null);
  };

  const handleFiltroChange = (key, value) => {
    setFiltros((prev) => ({ ...prev, [key]: value, page: 1 }));
  };

  const handlePaginationModelChange = (model) => {
    setFiltros((prev) => ({
      ...prev,
      page: model.page + 1,
      size: model.pageSize,
    }));
  };

  const handleClone = async (id) => {
    try {
      setErrorMessage(null);
      const response = await clonar(id, { owner: 'admin' });
      
      console.log('Clone response:', response);
      
      if (response && response.seg_id) {
        await carregar();
        navigate(`/segmentacoes/${response.seg_id}`);
      } else {
        console.error('Resposta inválida:', response);
        setErrorMessage(`Erro ao clonar: resposta inválida da API. Resposta: ${JSON.stringify(response)}`);
      }
    } catch (err) {
      console.error('Erro ao clonar:', err);
      const errorMsg = err.message || 'Erro desconhecido';
      setErrorMessage(`Erro ao clonar segmentação: ${errorMsg}`);
    }
  };

  const handleVisualizar = (id) => {
    navigate(`/segmentacoes/${id}`);
  };

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
      width: 200,
      renderCell: (params) => (
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          <Tooltip title="Visualizar">
            <IconButton size="small" onClick={() => handleVisualizar(params.row.seg_id)}>
              <VisibilityIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Editar">
            <IconButton size="small" onClick={() => navigate(`/segmentacoes/${params.row.seg_id}/editar`)}>
              <EditIcon fontSize="small" />
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

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <PageHeader
        title="Segmentações"
        subtitle="Gerencie suas segmentações de clientes"
      >
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate('/segmentacoes/nova')}
        >
          Nova Segmentação
        </Button>
      </PageHeader>

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

      {errorMessage && (
        <Alert severity="error" onClose={() => setErrorMessage(null)} sx={{ mb: 2 }}>
          {errorMessage}
        </Alert>
      )}

      {error ? (
        <Alert severity="error">Erro ao carregar: {error}</Alert>
      ) : segmentacoes.length === 0 && !loading ? (
        <EmptyState
          title="Nenhuma segmentação encontrada"
          description="Crie sua primeira segmentação clicando em 'Nova Segmentação'"
          actionText="Criar Segmentação"
          onAction={() => navigate('/segmentacoes/nova')}
        />
      ) : (
        <Box sx={{ 
          flex: 1, 
          minHeight: 400,  // Altura mínima para evitar colapso no loading
          height: '100%' 
        }}>
          <DataTable
            key={`page-${meta.page}-${meta.size}`}
            rows={segmentacoes}
            columns={columns}
            loading={loading}
            pagination={meta.total_pages > 1}
            hideFooterPagination={meta.total_pages <= 1}
            rowCount={meta.total}
            paginationModel={{ page: meta.page - 1, pageSize: meta.size }}
            onPaginationModelChange={handlePaginationModelChange}
            getRowId={(row) => row.seg_id}
          />
        </Box>
      )}
    </Box>
  );
}