import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageHeader } from '@shared';
import {
  Box,
  Button,
  Paper,
  Typography,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import TimelineIcon from '@mui/icons-material/Timeline';
import CommentIcon from '@mui/icons-material/Comment';
import { useSegmentacoesApi } from '../api/segmentacoes';
import Timeline from '../components/Timeline';
import Comentarios from '../components/Comentarios';

/**
 * TimelineSegmentacao — S1-FRONT-06
 *
 * Página com duas abas:
 * - Timeline: linha do tempo unificada (GET /timeline)
 * - Comentários: thread aninhada (GET/POST /comentarios, PUT /comentarios/{id})
 *
 * Rota: /segmentacoes/:id/timeline
 */
export default function TimelineSegmentacao() {
  const { id } = useParams();
  const navigate = useNavigate();
  const {
    buscar,
    obterTimeline,
    listarComentarios,
    criarComentario,
    editarComentario,
  } = useSegmentacoesApi();

  const [segNome, setSegNome] = useState('');
  const [tab, setTab] = useState(0);
  const [timelineItems, setTimelineItems] = useState([]);
  const [comentarios, setComentarios] = useState([]);
  const [loadingTimeline, setLoadingTimeline] = useState(true);
  const [loadingComentarios, setLoadingComentarios] = useState(true);
  const [erro, setErro] = useState(null);

  // Carrega dados iniciais
  useEffect(() => {
    carregarTudo();
  }, [id]);

  const carregarTudo = async () => {
    try {
      const seg = await buscar(id);
      setSegNome(seg.nome || '');
    } catch (err) {
      // non-blocking
    }
    carregarTimeline();
    carregarComentarios();
  };

  const carregarTimeline = async () => {
    setLoadingTimeline(true);
    try {
      const data = await obterTimeline(id);
      setTimelineItems(Array.isArray(data) ? data : data?.data || []);
    } catch (err) {
      setErro(err?.message || 'Erro ao carregar timeline');
    } finally {
      setLoadingTimeline(false);
    }
  };

  const carregarComentarios = async () => {
    setLoadingComentarios(true);
    try {
      const data = await listarComentarios(id);
      setComentarios(Array.isArray(data) ? data : data?.data || []);
    } catch (err) {
      setErro(err?.message || 'Erro ao carregar comentários');
    } finally {
      setLoadingComentarios(false);
    }
  };

  const handleCriarComentario = async (payload) => {
    return criarComentario(id, payload);
  };

  const handleEditarComentario = async (comentarioId, payload) => {
    return editarComentario(comentarioId, payload);
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <PageHeader
        title={`Timeline: ${segNome}`}
        subtitle="Histórico unificado e comentários"
      >
        <Button
          variant="outlined"
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate(`/segmentacoes/${id}`)}
        >
          Voltar ao Detalhe
        </Button>
      </PageHeader>

      {erro && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErro(null)}>{erro}</Alert>
      )}

      {/* Abas */}
      <Paper sx={{ mb: 2 }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)}>
          <Tab icon={<TimelineIcon />} label="Timeline" iconPosition="start" />
          <Tab
            icon={<CommentIcon />}
            label={`Comentários (${comentarios.length})`}
            iconPosition="start"
          />
        </Tabs>
      </Paper>

      {/* Conteúdo */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {tab === 0 && (
          <Paper sx={{ p: 2 }}>
            <Timeline items={timelineItems} loading={loadingTimeline} />
          </Paper>
        )}

        {tab === 1 && (
          <Paper sx={{ p: 2 }}>
            <Comentarios
              segId={id}
              comentarios={comentarios}
              loading={loadingComentarios}
              onCriar={handleCriarComentario}
              onEditar={handleEditarComentario}
              onReload={carregarComentarios}
            />
          </Paper>
        )}
      </Box>
    </Box>
  );
}
