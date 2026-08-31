import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageHeader } from '@shared';
import {
  Box,
  Button,
  TextField,
  Paper,
  Typography,
  CircularProgress,
  Alert,
  Chip,
  Divider,
  MenuItem,
  Snackbar,
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { useSegmentacoesApi } from '../api/segmentacoes';
import DestinoSelector from '../components/DestinoSelector';
import VigenciaAgendamento from '../components/VigenciaAgendamento';

/**
 * DocumentacaoSegmentacao — S1-FRONT-04
 *
 * Página para editar documentação/metadados, destino e vigência de uma segmentação.
 * Rota: /segmentacoes/:id/documentacao
 *
 * APIs:
 *  - GET /api/segmentacoes/{id} (carrega dados)
 *  - PUT /api/segmentacoes/{id} (salva documentação/metadados)
 *  - GET/PUT /api/segmentacoes/{id}/destinos
 *  - PUT /api/segmentacoes/{id}/vigencia
 */
export default function DocumentacaoSegmentacao() {
  const { id } = useParams();
  const navigate = useNavigate();
  const {
    buscar,
    atualizar,
    buscarDestinos,
    atualizarDestinos,
    atualizarVigencia,
    loading,
  } = useSegmentacoesApi();

  // Estado principal
  const [dadosDoc, setDadosDoc] = useState({
    nome: '',
    descricao: '',
    objetivo: '',
    owner: '',
    area_responsavel: '',
  });

  const [destinos, setDestinos] = useState([
    { destino: 'sistema2', habilitado: false },
    { destino: 'sistema3', habilitado: false },
  ]);

  const [vigencia, setVigencia] = useState({
    vigencia_inicio: '',
    vigencia_fim: '',
    recorrencia: 'once',
    agendamento_cron: '',
  });


  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [segStatus, setSegStatus] = useState('');

  // Carrega dados ao montar
  useEffect(() => {
    const carregar = async () => {
      setCarregando(true);
      setErro(null);
      try {
        // Carrega segmentação completa
        const seg = await buscar(id);
        setDadosDoc({
          nome: seg.nome || '',
          descricao: seg.descricao || '',
          objetivo: seg.objetivo || '',
          owner: seg.owner || '',
          area_responsavel: seg.area_responsavel || '',
        });
        setSegStatus(seg.status || '');

        // Vigência (vem no detalhe)
        setVigencia({
          vigencia_inicio: seg.vigencia_inicio ? seg.vigencia_inicio.slice(0, 16) : '',
          vigencia_fim: seg.vigencia_fim ? seg.vigencia_fim.slice(0, 16) : '',
          recorrencia: seg.recorrencia || 'once',
          agendamento_cron: seg.agendamento_cron || '',
        });

        // Carrega destinos
        const dest = await buscarDestinos(id);
        if (dest && dest.length > 0) {
          setDestinos(dest);
        }
      } catch (err) {
        setErro('Erro ao carregar segmentação: ' + (err?.message || ''));
      } finally {
        setCarregando(false);
      }
    };
    carregar();
  }, [id]);

  // Handlers
  const handleDocChange = (field, value) => {
    setDadosDoc((prev) => ({ ...prev, [field]: value }));
  };



  // Salvar tudo
  const handleSalvar = async () => {
    setSalvando(true);
    setErro(null);

    try {
      // 1. Salva documentação/metadados via PUT /segmentacoes/{id}
      await atualizar(id, {
        nome: dadosDoc.nome,
        descricao: dadosDoc.descricao,
        objetivo: dadosDoc.objetivo,
        owner: dadosDoc.owner,
        area_responsavel: dadosDoc.area_responsavel,
      });

      // 2. Salva destinos via PUT /segmentacoes/{id}/destinos
      await atualizarDestinos(id, destinos);

      // 3. Salva vigência via PUT /segmentacoes/{id}/vigencia
      await atualizarVigencia(id, {
        vigencia_inicio: vigencia.vigencia_inicio || null,
        vigencia_fim: vigencia.vigencia_fim || null,
        recorrencia: vigencia.recorrencia,
        agendamento_cron: vigencia.recorrencia === 'custom' ? vigencia.agendamento_cron : null,
      });

      setSnackbar({ open: true, message: 'Documentação salva com sucesso!', severity: 'success' });
    } catch (err) {
      const msg = err?.message || err?.detail || 'Erro ao salvar';
      setErro(msg);
      setSnackbar({ open: true, message: msg, severity: 'error' });
    } finally {
      setSalvando(false);
    }
  };

  // Loading
  if (carregando) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <PageHeader
        title={`Documentação: ${dadosDoc.nome}`}
        subtitle="Metadados, destino e vigência da segmentação"
      >
        <Button
          variant="outlined"
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate(`/segmentacoes/${id}`)}
          sx={{ mr: 1 }}
        >
          Voltar
        </Button>
        <Button
          variant="contained"
          startIcon={salvando ? <CircularProgress size={18} /> : <SaveIcon />}
          onClick={handleSalvar}
          disabled={salvando}
        >
          Salvar Tudo
        </Button>
      </PageHeader>

      {erro && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErro(null)}>
          {erro}
        </Alert>
      )}

      {segStatus && (
        <Box sx={{ mb: 2 }}>
          <Chip label={`Status: ${segStatus}`} size="small" variant="outlined" />
        </Box>
      )}

      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {/* Seção 1: Metadados e Documentação */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Metadados
          </Typography>

          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mb: 2 }}>
            <TextField
              label="Nome"
              value={dadosDoc.nome}
              onChange={(e) => handleDocChange('nome', e.target.value)}
              required
              fullWidth
            />
            <TextField
              label="Objetivo"
              value={dadosDoc.objetivo}
              onChange={(e) => handleDocChange('objetivo', e.target.value)}
              select
              fullWidth
            >
              <MenuItem value="AQUISICAO">Aquisição</MenuItem>
              <MenuItem value="RENTABILIZACAO">Rentabilização</MenuItem>
              <MenuItem value="RETENCAO">Retenção</MenuItem>
              <MenuItem value="ENGAJAMENTO">Engajamento</MenuItem>
              <MenuItem value="COBRANCA">Cobrança</MenuItem>
            </TextField>
            <TextField
              label="Owner"
              value={dadosDoc.owner}
              onChange={(e) => handleDocChange('owner', e.target.value)}
              fullWidth
            />
            <TextField
              label="Área Responsável"
              value={dadosDoc.area_responsavel}
              onChange={(e) => handleDocChange('area_responsavel', e.target.value)}
              fullWidth
            />
          </Box>
        </Paper>

        {/* Seção 2: Destino */}
        <Box sx={{ mb: 3 }}>
          <DestinoSelector
            value={destinos}
            onChange={setDestinos}
          />
        </Box>

        {/* Seção 3: Vigência e Agendamento */}
        <Box sx={{ mb: 3 }}>
          <VigenciaAgendamento
            value={vigencia}
            onChange={setVigencia}
          />
        </Box>
      </Box>

      {/* Snackbar de feedback */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        message={snackbar.message}
      />
    </Box>
  );
}
