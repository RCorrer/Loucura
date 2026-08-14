import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Avatar,
  Chip,
  IconButton,
  Divider,
  CircularProgress,
  Alert,
  Collapse,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import ReplyIcon from '@mui/icons-material/Reply';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import EditIcon from '@mui/icons-material/Edit';

/**
 * Comentarios — S1-FRONT-06
 *
 * Thread aninhada de comentários com menções (@), tipos e marcar resolvido.
 *
 * Props:
 *   - segId: string
 *   - comentarios: array (thread do backend, pode ter respondendo_a para aninhamento)
 *   - loading: bool
 *   - onCriar: (payload) => Promise (POST /comentarios)
 *   - onEditar: (comentario_id, payload) => Promise (PUT /comentarios/{id})
 *   - onReload: () => void
 */
export default function Comentarios({
  segId,
  comentarios = [],
  loading = false,
  onCriar,
  onEditar,
  onReload,
}) {
  const [novoTexto, setNovoTexto] = useState('');
  const [respondendoA, setRespondendoA] = useState(null);
  const [editandoId, setEditandoId] = useState(null);
  const [editTexto, setEditTexto] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState(null);

  // Extrai menções (@usuario) do texto
  const extrairMencoes = (texto) => {
    const regex = /@([\w.]+)/g;
    const mencoes = [];
    let match;
    while ((match = regex.exec(texto)) !== null) {
      mencoes.push(match[1]);
    }
    return mencoes;
  };

  const handleEnviar = async () => {
    if (!novoTexto.trim()) return;
    setEnviando(true);
    setErro(null);
    try {
      const mencoes = extrairMencoes(novoTexto);
      await onCriar({
        texto: novoTexto.trim(),
        tipo: 'geral',
        respondendo_a: respondendoA,
        mencoes: mencoes.length > 0 ? mencoes : undefined,
      });
      setNovoTexto('');
      setRespondendoA(null);
      onReload?.();
    } catch (err) {
      setErro(err?.message || 'Erro ao enviar comentário');
    } finally {
      setEnviando(false);
    }
  };

  const handleResolver = async (comentarioId, resolvidoAtual) => {
    try {
      await onEditar(comentarioId, { resolvido: !resolvidoAtual });
      onReload?.();
    } catch (err) {
      setErro(err?.message || 'Erro ao marcar resolvido');
    }
  };

  const handleSalvarEdicao = async (comentarioId) => {
    if (!editTexto.trim()) return;
    try {
      await onEditar(comentarioId, { texto: editTexto.trim() });
      setEditandoId(null);
      setEditTexto('');
      onReload?.();
    } catch (err) {
      setErro(err?.message || 'Erro ao editar comentário');
    }
  };

  // Organiza comentários em árvore (raiz + respostas)
  const raiz = comentarios.filter((c) => !c.respondendo_a);
  const respostasMap = {};
  comentarios.forEach((c) => {
    if (c.respondendo_a) {
      if (!respostasMap[c.respondendo_a]) respostasMap[c.respondendo_a] = [];
      respostasMap[c.respondendo_a].push(c);
    }
  });

  // Renderiza um comentário individual
  const renderComentario = (comment, depth = 0) => {
    const respostas = respostasMap[comment.comentario_id] || [];
    const isResolvido = comment.resolvido;
    const isEditando = editandoId === comment.comentario_id;

    return (
      <Box key={comment.comentario_id} sx={{ ml: depth * 3, mb: 1.5 }}>
        <Paper
          variant="outlined"
          sx={{
            p: 1.5,
            opacity: isResolvido ? 0.6 : 1,
            borderLeft: depth > 0 ? '3px solid' : 'none',
            borderLeftColor: depth > 0 ? 'primary.light' : 'transparent',
          }}
        >
          {/* Header */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
            <Avatar sx={{ width: 24, height: 24, fontSize: '0.75rem' }}>
              {(comment.autor || '?')[0].toUpperCase()}
            </Avatar>
            <Typography variant="caption" fontWeight="bold">
              {comment.autor || 'Anônimo'}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {comment.criado_em
                ? new Date(comment.criado_em).toLocaleString('pt-BR', {
                    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
                  })
                : ''}
            </Typography>
            {comment.tipo && comment.tipo !== 'geral' && (
              <Chip label={comment.tipo} size="small" variant="outlined" sx={{ height: 18, fontSize: '0.65rem' }} />
            )}
            {isResolvido && (
              <Chip label="Resolvido" size="small" color="success" sx={{ height: 18, fontSize: '0.65rem' }} />
            )}
          </Box>

          {/* Corpo */}
          {isEditando ? (
            <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
              <TextField
                size="small"
                fullWidth
                value={editTexto}
                onChange={(e) => setEditTexto(e.target.value)}
                autoFocus
              />
              <Button size="small" onClick={() => handleSalvarEdicao(comment.comentario_id)}>Salvar</Button>
              <Button size="small" onClick={() => setEditandoId(null)}>Cancelar</Button>
            </Box>
          ) : (
            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
              {highlightMencoes(comment.texto || '')}
            </Typography>
          )}

          {/* Ações */}
          {!isEditando && (
            <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5 }}>
              <IconButton
                size="small"
                onClick={() => { setRespondendoA(comment.comentario_id); }}
                title="Responder"
              >
                <ReplyIcon fontSize="small" />
              </IconButton>
              <IconButton
                size="small"
                onClick={() => handleResolver(comment.comentario_id, isResolvido)}
                title={isResolvido ? 'Reabrir' : 'Marcar resolvido'}
              >
                {isResolvido
                  ? <CheckCircleIcon fontSize="small" color="success" />
                  : <CheckCircleOutlineIcon fontSize="small" />
                }
              </IconButton>
              <IconButton
                size="small"
                onClick={() => { setEditandoId(comment.comentario_id); setEditTexto(comment.texto || ''); }}
                title="Editar"
              >
                <EditIcon fontSize="small" />
              </IconButton>
            </Box>
          )}
        </Paper>

        {/* Respostas aninhadas */}
        {respostas.map((r) => renderComentario(r, depth + 1))}
      </Box>
    );
  };

  // Destaca menções no texto
  const highlightMencoes = (texto) => {
    const parts = texto.split(/(@[\w.]+)/g);
    return parts.map((part, i) =>
      part.startsWith('@') ? (
        <Typography key={i} component="span" variant="body2" color="primary" fontWeight="bold">
          {part}
        </Typography>
      ) : (
        <React.Fragment key={i}>{part}</React.Fragment>
      )
    );
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  return (
    <Box>
      {erro && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErro(null)}>{erro}</Alert>
      )}

      {/* Lista de comentários */}
      {raiz.length > 0 ? (
        raiz.map((c) => renderComentario(c))
      ) : (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2, textAlign: 'center' }}>
          Nenhum comentário ainda. Seja o primeiro!
        </Typography>
      )}

      <Divider sx={{ my: 2 }} />

      {/* Novo comentário */}
      {respondendoA && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <ReplyIcon fontSize="small" color="primary" />
          <Typography variant="caption" color="primary">
            Respondendo a comentário
          </Typography>
          <Button size="small" onClick={() => setRespondendoA(null)}>Cancelar</Button>
        </Box>
      )}

      <Box sx={{ display: 'flex', gap: 1 }}>
        <TextField
          fullWidth
          size="small"
          placeholder="Escreva um comentário... Use @usuario para mencionar"
          value={novoTexto}
          onChange={(e) => setNovoTexto(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleEnviar(); } }}
          multiline
          maxRows={4}
          disabled={enviando}
        />
        <Button
          variant="contained"
          onClick={handleEnviar}
          disabled={!novoTexto.trim() || enviando}
          startIcon={enviando ? <CircularProgress size={16} /> : <SendIcon />}
          sx={{ minWidth: 100 }}
        >
          Enviar
        </Button>
      </Box>
    </Box>
  );
}
