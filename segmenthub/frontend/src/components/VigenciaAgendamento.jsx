import React, { useState } from 'react';
import {
  Paper,
  Typography,
  Box,
  TextField,
  MenuItem,
  Alert,
  Chip,
} from '@mui/material';
import ScheduleIcon from '@mui/icons-material/Schedule';

const RECORRENCIAS = [
  { value: 'once', label: 'Estático (execução única)', descricao: 'O segmento é calculado uma vez e não atualiza automaticamente' },
  { value: 'hourly', label: 'A cada hora', descricao: 'Recalcula o público a cada hora' },
  { value: 'daily', label: 'Diário', descricao: 'Recalcula uma vez por dia' },
  { value: 'weekly', label: 'Semanal', descricao: 'Recalcula uma vez por semana' },
  { value: 'monthly', label: 'Mensal', descricao: 'Recalcula uma vez por mês' },
  { value: 'custom', label: 'Personalizado (CRON)', descricao: 'Expressão cron customizada' },
];

/**
 * VigenciaAgendamento — S1-FRONT-04
 *
 * Gerencia vigência (início/fim) e recorrência de execução.
 *
 * Props:
 *   - value: { vigencia_inicio, vigencia_fim, recorrencia, agendamento_cron }
 *   - onChange: (newValue) => void
 *   - disabled: bool
 */
export default function VigenciaAgendamento({ value = {}, onChange, disabled = false }) {
  const [cronError, setCronError] = useState('');

  const handleChange = (field, val) => {
    const updated = { ...value, [field]: val };

    // Se recorrência mudou para algo diferente de custom, limpa cron
    if (field === 'recorrencia' && val !== 'custom') {
      updated.agendamento_cron = null;
      setCronError('');
    }

    onChange(updated);
  };

  const validarCron = (cron) => {
    // Validação básica: 5 campos (minuto hora dia mês dia-semana)
    if (!cron) {
      setCronError('');
      return;
    }
    const parts = cron.trim().split(/\s+/);
    if (parts.length < 5 || parts.length > 6) {
      setCronError('Expressão cron deve ter 5 ou 6 campos (ex: 0 8 * * MON-FRI)');
    } else {
      setCronError('');
    }
  };

  const recorrenciaAtual = RECORRENCIAS.find((r) => r.value === value.recorrencia);

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <ScheduleIcon color="action" />
        <Typography variant="subtitle1" fontWeight="bold">
          Vigência e Agendamento
        </Typography>
        {value.recorrencia === 'once' && (
          <Chip label="Estático" size="small" variant="outlined" />
        )}
      </Box>

      {/* Vigência */}
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mb: 3 }}>
        <TextField
          label="Início da vigência"
          type="datetime-local"
          value={value.vigencia_inicio || ''}
          onChange={(e) => handleChange('vigencia_inicio', e.target.value)}
          InputLabelProps={{ shrink: true }}
          disabled={disabled}
          fullWidth
          helperText="Quando o segmento começa a ser executado"
        />
        <TextField
          label="Fim da vigência (opcional)"
          type="datetime-local"
          value={value.vigencia_fim || ''}
          onChange={(e) => handleChange('vigencia_fim', e.target.value || null)}
          InputLabelProps={{ shrink: true }}
          disabled={disabled}
          fullWidth
          helperText="Quando o segmento é automaticamente encerrado"
        />
      </Box>

      {/* Validação: fim antes do início */}
      {value.vigencia_inicio && value.vigencia_fim && value.vigencia_fim <= value.vigencia_inicio && (
        <Alert severity="error" sx={{ mb: 2 }}>
          O fim da vigência deve ser posterior ao início.
        </Alert>
      )}

      {/* Recorrência */}
      <TextField
        select
        label="Recorrência"
        value={value.recorrencia || 'once'}
        onChange={(e) => handleChange('recorrencia', e.target.value)}
        disabled={disabled}
        fullWidth
        sx={{ mb: 2 }}
        helperText={recorrenciaAtual?.descricao || ''}
      >
        {RECORRENCIAS.map((r) => (
          <MenuItem key={r.value} value={r.value}>
            {r.label}
          </MenuItem>
        ))}
      </TextField>

      {/* Campo CRON (só se custom) */}
      {value.recorrencia === 'custom' && (
        <TextField
          label="Expressão CRON"
          value={value.agendamento_cron || ''}
          onChange={(e) => {
            handleChange('agendamento_cron', e.target.value);
            validarCron(e.target.value);
          }}
          disabled={disabled}
          fullWidth
          placeholder="0 8 * * MON-FRI"
          helperText={cronError || 'Formato: minuto hora dia mês dia-semana (ex: 0 8 * * MON-FRI = toda segunda a sexta às 8h)'}
          error={!!cronError}
        />
      )}

      {/* Info para estático */}
      {value.recorrencia === 'once' && (
        <Alert severity="info" sx={{ mt: 1 }}>
          Segmentação estática: o público é calculado uma vez e não atualiza automaticamente.
          Para recalcular, use a ação “Executar” manualmente.
        </Alert>
      )}
    </Paper>
  );
}
