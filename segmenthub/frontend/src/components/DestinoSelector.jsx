import React from 'react';
import {
  Paper,
  Typography,
  FormGroup,
  FormControlLabel,
  Switch,
  Box,
  Chip,
  Alert,
} from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import CampaignIcon from '@mui/icons-material/Campaign';

/**
 * DestinoSelector — S1-FRONT-04 (FX-15: config extensível)
 *
 * Permite selecionar a natureza da segmentação.
 * FX-15: Sistema de destinos configurado via DESTINOS_CONFIG.
 *        Para adicionar S4, basta incluir um entry.
 *
 * Props:
 *   - value: [{destino: 'sistema2'|'sistema3', habilitado: bool}]
 *   - onChange: (newDestinos) => void
 *   - disabled: bool
 */

const DESTINOS_CONFIG = [
  {
    key: 'sistema2',
    label: 'Atendimento Humano (ClientView 360)',
    description: 'Segmento aparece como ação do gerente na carteira',
    icon: PersonIcon,
    color: 'info',
  },
  {
    key: 'sistema3',
    label: 'Digital (EngagementHub)',
    description: 'Segmento é associado a campanhas e jornadas digitais',
    icon: CampaignIcon,
    color: 'success',
  },
  // FX-15: Adicionar novos sistemas aqui:
  // { key: 'sistema4', label: 'Analytics (DataHub)', description: '...', icon: ..., color: 'secondary' },
];

export default function DestinoSelector({ value = [], onChange, disabled = false }) {
  // FX-15: Lógica genérica baseada em DESTINOS_CONFIG
  const getDestino = (key) => value.find((d) => d.destino === key);
  const isAtivo = (key) => getDestino(key)?.habilitado || false;

  const handleToggle = (sistema, checked) => {
    const novosDestinos = DESTINOS_CONFIG.map(({ key }) => ({
      destino: key,
      habilitado: key === sistema ? checked : isAtivo(key),
    }));
    onChange(novosDestinos);
  };

  const ativos = DESTINOS_CONFIG.filter(({ key }) => isAtivo(key));

  const getNaturezaLabel = () => {
    if (ativos.length === 0) return 'Nenhum destino selecionado';
    if (ativos.length === DESTINOS_CONFIG.length) return 'Mista (Todos)';
    return ativos.map(d => d.label.split(' (')[0]).join(' + ');
  };

  const getNaturezaColor = () => {
    if (ativos.length === 0) return 'default';
    if (ativos.length > 1) return 'primary';
    return ativos[0].color;
  };

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="subtitle1" fontWeight="bold">
          Destino (Natureza)
        </Typography>
        <Chip
          label={getNaturezaLabel()}
          color={getNaturezaColor()}
          size="small"
          variant="outlined"
        />
      </Box>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Define para quais sistemas este segmento será encaminhado.
      </Typography>

      {/* FX-15: Render dinâmico baseado em config */}
      <FormGroup>
        {DESTINOS_CONFIG.map(({ key, label, description, icon: IconComp, color }, idx) => (
          <FormControlLabel
            key={key}
            control={
              <Switch
                checked={isAtivo(key)}
                onChange={(e) => handleToggle(key, e.target.checked)}
                disabled={disabled}
                color={color}
              />
            }
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <IconComp fontSize="small" color={color} />
                <Box>
                  <Typography variant="body2" fontWeight="medium">{label}</Typography>
                  <Typography variant="caption" color="text.secondary">{description}</Typography>
                </Box>
              </Box>
            }
            sx={{ mb: idx < DESTINOS_CONFIG.length - 1 ? 1 : 0 }}
          />
        ))}
      </FormGroup>

      {ativos.length === 0 && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          Selecione ao menos um destino para que o segmento seja utilizado.
        </Alert>
      )}
    </Paper>
  );
}
