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
    resumo: '',
    objetivo_negocio: '',
    publico_alvo_descricao: '',
    observacoes: '',
    documentacao_md: '',
    seg_tags: [],
    owner: '',
    area_responsavel: '',
    email_contato: '',
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

  const [tagsInput, setTagsInput] = useState('');
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
          resumo: seg.resumo || '',
          objetivo_negocio: seg.objetivo_negocio || '',
          publico_alvo_descricao: seg.publico_alvo_descricao || '',
          observacoes: seg.observacoes || '',
          documentacao_md: seg.documentacao_md || '',
          seg_tags: seg.seg_tags || [],
          owner: seg.owner || '',
          area_responsavel: seg.area_responsavel || '',
          email_contato: seg.email_contato || '',
        });
        setSegStatus(seg.status || '');
        setTagsInput((seg.seg_tags || []).join(', '));

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

  const handleTagsChange = (input) => {
    setTagsInput(input);
    const tags = input
      .split(',')
      .map((t) => t.trim())
      .filter((t) => t.length > 0);
    setDadosDoc((prev) => ({ ...prev, seg_tags: tags }));
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
        resumo: dadosDoc.resumo,
        objetivo_negocio: dadosDoc.objetivo_negocio,
        publico_alvo_descricao: dadosDoc.publico_alvo_descricao,
        observacoes: dadosDoc.observacoes,
        documentacao_md: dadosDoc.documentacao_md,
        seg_tags: dadosDoc.seg_tags,
        owner: dadosDoc.owner,
        area_responsavel: dadosDoc.area_responsavel,
        email_contato: dadosDoc.email_contato,
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
            <TextField
              label="E-mail de Contato"
              value={dadosDoc.email_contato}
              onChange={(e) => handleDocChange('email_contato', e.target.value)}
              type="email"
              fullWidth
            />
            <TextField
              label="Tags (separadas por vírgula)"
              value={tagsInput}
              onChange={(e) => handleTagsChange(e.target.value)}
              fullWidth
              helperText={dadosDoc.seg_tags.length > 0 ? `${dadosDoc.seg_tags.length} tag(s)` : ''}
            />
          </Box>

          <TextField
            label="Resumo"
            value={dadosDoc.resumo}
            onChange={(e) => handleDocChange('resumo', e.target.value)}
            fullWidth
            multiline
            rows={2}
            sx={{ mb: 2 }}
          />
          <TextField
            label="Objetivo de Negócio"
            value={dadosDoc.objetivo_negocio}
            onChange={(e) => handleDocChange('objetivo_negocio', e.target.value)}
            fullWidth
            multiline
            rows={2}
            sx={{ mb: 2 }}
            helperText="Descreva o objetivo de negócio que esta segmentação atende"
          />
          <TextField
            label="Descrição do Público-Alvo"
            value={dadosDoc.publico_alvo_descricao}
            onChange={(e) => handleDocChange('publico_alvo_descricao', e.target.value)}
            fullWidth
            multiline
            rows={2}
            sx={{ mb: 2 }}
            helperText="Descreva em linguagem natural quem é o público-alvo"
          />
          <TextField
            label="Observações"
            value={dadosDoc.observacoes}
            onChange={(e) => handleDocChange('observacoes', e.target.value)}
            fullWidth
            multiline
            rows={2}
            sx={{ mb: 2 }}
          />

          <Divider sx={{ my: 2 }} />

          <Typography variant="subtitle1" gutterBottom>
            Documentação (Markdown)
          </Typography>
          <TextField
            value={dadosDoc.documentacao_md}
            onChange={(e) => handleDocChange('documentacao_md', e.target.value)}
            fullWidth
            multiline
            rows={8}
            placeholder="# Documentação da Segmentação\n\nDescreva aqui detalhes adicionais..."
            helperText="Suporta Markdown. Use para documentar critérios, premissas e histórico de decisões."
          />
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
