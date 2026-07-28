import React from 'react';
import { Chip } from '@mui/material';
import { tokens } from '../../theme/tokens';

const statusMap = {
  ativo: { color: tokens.feedback.success, label: 'Ativo' },
  inativo: { color: tokens.neutral.gray50, label: 'Inativo' },
  rascunho: { color: tokens.neutral.gray70, label: 'Rascunho' },
  aprovado: { color: tokens.feedback.success, label: 'Aprovado' },
  reprovado: { color: tokens.feedback.error, label: 'Reprovado' },
  concluido: { color: tokens.feedback.info, label: 'Concluído' },
  erro: { color: tokens.feedback.error, label: 'Erro' },
  pendente: { color: tokens.feedback.warning, label: 'Pendente' },
};

export default function StatusBadge({ status, customLabel }) {
  const config = statusMap[status?.toLowerCase()] || { color: tokens.neutral.gray50, label: status || 'Desconhecido' };
  return (
    <Chip
      label={customLabel || config.label}
      sx={{
        backgroundColor: config.color,
        color: '#FFFFFF',
        fontWeight: 600,
        fontSize: '0.75rem',
        height: 24,
        '& .MuiChip-label': { px: 1 },
      }}
    />
  );
}
