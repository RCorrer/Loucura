import React from 'react';
import {
  Box,
  Typography,
  Chip,
  Paper,
  CircularProgress,
} from '@mui/material';
import TimelineIcon from '@mui/icons-material/Timeline';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import HistoryIcon from '@mui/icons-material/History';
import CommentIcon from '@mui/icons-material/Comment';

const TIPO_CONFIG = {
  estado: { icon: <SwapHorizIcon fontSize="small" />, color: '#1565C0', label: 'Transição' },
  execucao: { icon: <PlayArrowIcon fontSize="small" />, color: '#2E7D32', label: 'Execução' },
  versao: { icon: <HistoryIcon fontSize="small" />, color: '#B26A00', label: 'Versão' },
  comentario: { icon: <CommentIcon fontSize="small" />, color: '#6A1B9A', label: 'Comentário' },
};

/**
 * Timeline — S1-FRONT-06
 *
 * Linha do tempo unificada com 4 fontes:
 * - estados (transições de status)
 * - execuções
 * - versões
 * - comentários
 *
 * Props:
 *   - items: array de {tipo, data, descricao, autor?, detalhes?}
 *     (já ordenado pelo back via GET /timeline)
 *   - loading: bool
 */
export default function Timeline({ items = [], loading = false }) {
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (items.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <TimelineIcon sx={{ fontSize: 48, color: 'text.disabled' }} />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Nenhum evento registrado ainda.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ position: 'relative', pl: 4 }}>
      {/* Linha vertical */}
      <Box
        sx={{
          position: 'absolute',
          left: 15,
          top: 0,
          bottom: 0,
          width: 2,
          bgcolor: 'divider',
        }}
      />

      {items.map((item, index) => {
        const config = TIPO_CONFIG[item.tipo] || TIPO_CONFIG.estado;
        const dataFormatada = item.data
          ? new Date(item.data).toLocaleString('pt-BR', {
              day: '2-digit', month: '2-digit', year: 'numeric',
              hour: '2-digit', minute: '2-digit',
            })
          : '';

        return (
          <Box key={index} sx={{ position: 'relative', mb: 2 }}>
            {/* Dot */}
            <Box
              sx={{
                position: 'absolute',
                left: -25,
                top: 8,
                width: 24,
                height: 24,
                borderRadius: '50%',
                bgcolor: config.color,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                zIndex: 1,
              }}
            >
              {config.icon}
            </Box>

            {/* Card */}
            <Paper variant="outlined" sx={{ p: 1.5, ml: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <Chip
                  label={config.label}
                  size="small"
                  sx={{ bgcolor: config.color, color: 'white', fontSize: '0.7rem', height: 20 }}
                />
                <Typography variant="caption" color="text.secondary">
                  {dataFormatada}
                </Typography>
                {item.autor && (
                  <Typography variant="caption" color="text.secondary">
                    • {item.autor}
                  </Typography>
                )}
              </Box>
              <Typography variant="body2">
                {item.descricao || item.mensagem || item.texto || '-'}
              </Typography>
              {item.detalhes && (
                <Typography variant="caption" color="text.secondary">
                  {typeof item.detalhes === 'string' ? item.detalhes : JSON.stringify(item.detalhes)}
                </Typography>
              )}
            </Paper>
          </Box>
        );
      })}
    </Box>
  );
}
