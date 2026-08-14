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
 * DestinoSelector — S1-FRONT-04
 *
 * Permite selecionar a natureza da segmentação:
 * - sistema2 = Atendimento Humano (ClientView 360)
 * - sistema3 = Digital (EngagementHub)
 * - ambos = os dois habilitados
 *
 * Props:
 *   - value: [{destino: 'sistema2'|'sistema3', habilitado: bool}]
 *   - onChange: (newDestinos) => void
 *   - disabled: bool
 */
export default function DestinoSelector({ value = [], onChange, disabled = false }) {
  const getSistema2 = () => value.find((d) => d.destino === 'sistema2');
  const getSistema3 = () => value.find((d) => d.destino === 'sistema3');

  const isHumanoAtivo = getSistema2()?.habilitado || false;
  const isDigitalAtivo = getSistema3()?.habilitado || false;

  const handleToggle = (sistema, checked) => {
    const novosDestinos = [
      { destino: 'sistema2', habilitado: sistema === 'sistema2' ? checked : isHumanoAtivo },
      { destino: 'sistema3', habilitado: sistema === 'sistema3' ? checked : isDigitalAtivo },
    ];
    onChange(novosDestinos);
  };

  const getNaturezaLabel = () => {
    if (isHumanoAtivo && isDigitalAtivo) return 'Mista (Humano + Digital)';
    if (isHumanoAtivo) return 'Atendimento Humano';
    if (isDigitalAtivo) return 'Digital';
    return 'Nenhum destino selecionado';
  };

  const getNaturezaColor = () => {
    if (isHumanoAtivo && isDigitalAtivo) return 'primary';
    if (isHumanoAtivo) return 'info';
    if (isDigitalAtivo) return 'success';
    return 'default';
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

      <FormGroup>
        <FormControlLabel
          control={
            <Switch
              checked={isHumanoAtivo}
              onChange={(e) => handleToggle('sistema2', e.target.checked)}
              disabled={disabled}
              color="info"
            />
          }
          label={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <PersonIcon fontSize="small" color="info" />
              <Box>
                <Typography variant="body2" fontWeight="medium">
                  Atendimento Humano (ClientView 360)
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Segmento aparece como ação do gerente na carteira
                </Typography>
              </Box>
            </Box>
          }
          sx={{ mb: 1 }}
        />
        <FormControlLabel
          control={
            <Switch
              checked={isDigitalAtivo}
              onChange={(e) => handleToggle('sistema3', e.target.checked)}
              disabled={disabled}
              color="success"
            />
          }
          label={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <CampaignIcon fontSize="small" color="success" />
              <Box>
                <Typography variant="body2" fontWeight="medium">
                  Digital (EngagementHub)
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Segmento é associado a campanhas e jornadas digitais
                </Typography>
              </Box>
            </Box>
          }
        />
      </FormGroup>

      {!isHumanoAtivo && !isDigitalAtivo && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          Selecione ao menos um destino para que o segmento seja utilizado.
        </Alert>
      )}
    </Paper>
  );
}
