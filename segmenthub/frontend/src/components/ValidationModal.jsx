import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  CircularProgress,
  Alert,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Checkbox,
  FormControlLabel,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch';
import { useSegmentacoesApi } from '../api/segmentacoes';

const CHECKLIST_ITEMS = [
  { key: 'regras_revisadas', label: 'Regras de segmentação revisadas e corretas' },
  { key: 'destino_definido', label: 'Destino (natureza) configurado' },
  { key: 'vigencia_ok', label: 'Vigência e agendamento adequados' },
  { key: 'documentacao_ok', label: 'Documentação preenchida' },
  { key: 'publico_validado', label: 'Estimativa de público verificada' },
];

/**
 * ValidationModal — S1-FRONT-05
 *
 * Modal de validação/aprovação de segmentação.
 * - Dispara POST /validar para obter resumo consolidado
 * - Mostra regras legíveis + estimativa + destino + vigência
 * - Checklist obrigatório para aprovação
 * - Informa que aprovação dispara recálculo imediato (Opção A)
 *
 * Props:
 *   - open: bool
 *   - onClose: () => void
 *   - segId: string
 *   - segData: object (dados da segmentação, incl. destinos e vigência)
 *   - onAprovado: () => void (callback após aprovação bem-sucedida)
 */
export default function ValidationModal({ open, onClose, segId, segData, onAprovado }) {
  const { validar, aprovar } = useSegmentacoesApi();

  const [validacao, setValidacao] = useState(null);
  const [loadingValidar, setLoadingValidar] = useState(false);
  const [loadingAprovar, setLoadingAprovar] = useState(false);
  const [erro, setErro] = useState(null);
  const [checklist, setChecklist] = useState({});

  // Dispara validação ao abrir
  useEffect(() => {
    if (open && segId) {
      executarValidacao();
      // Reset checklist
      const initial = {};
      CHECKLIST_ITEMS.forEach((item) => { initial[item.key] = false; });
      setChecklist(initial);
    }
  }, [open, segId]);

  const executarValidacao = async () => {
    setLoadingValidar(true);
    setErro(null);
    try {
      const result = await validar(segId);
      setValidacao(result);
    } catch (err) {
      setErro(err?.message || 'Erro ao validar segmentação');
    } finally {
      setLoadingValidar(false);
    }
  };

  const handleChecklistChange = (key) => {
    setChecklist((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const todosCheckados = CHECKLIST_ITEMS.every((item) => checklist[item.key]);
  const podeAprovar = validacao?.valido && todosCheckados;

  const handleAprovar = async () => {
    setLoadingAprovar(true);
    setErro(null);
    try {
      await aprovar(segId, { checklist_json: checklist });
      onAprovado?.();
      onClose();
    } catch (err) {
      setErro(err?.message || 'Erro ao aprovar segmentação');
    } finally {
      setLoadingAprovar(false);
    }
  };

  // Helper: renderiza regras de forma legível
  const renderRegrasLegiveis = (regras) => {
    if (!regras) return <Typography variant="body2" color="text.secondary">Sem regras</Typography>;
    const inclusao = regras.inclusao;
    const exclusao = regras.exclusao;
    return (
      <Box>
        <Typography variant="body2"><strong>Público base:</strong> {regras.publico_base}</Typography>
        <Typography variant="body2"><strong>Inclusão:</strong> {renderNo(inclusao)}</Typography>
        {exclusao && (
          <Typography variant="body2"><strong>Exclusão:</strong> {renderNo(exclusao)}</Typography>
        )}
      </Box>
    );
  };

  const renderNo = (no) => {
    if (!no || !no.rules) return 'Nenhuma';
    const parts = no.rules.map((r) => {
      if (r.rules) return `(${renderNo(r)})`; // nested
      return `${r.campo_id} ${r.op} ${r.value ?? ''}`;
    });
    return parts.join(` ${no.operator} `);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <RocketLaunchIcon color="primary" />
        Validação e Aprovação
      </DialogTitle>

      <DialogContent dividers>
        {/* Loading */}
        {loadingValidar && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
            <Typography sx={{ ml: 2 }}>Validando regras...</Typography>
          </Box>
        )}

        {/* Erro */}
        {erro && (
          <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>
        )}

        {/* Resultado da validação */}
        {!loadingValidar && validacao && (
          <Box>
            {/* Status */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              {validacao.valido ? (
                <Chip icon={<CheckCircleIcon />} label="Válida" color="success" />
              ) : (
                <Chip icon={<ErrorIcon />} label="Inválida" color="error" />
              )}
              <Typography variant="body2" color="text.secondary">
                {validacao.mensagem || ''}
              </Typography>
            </Box>

            {/* Erros de validação */}
            {!validacao.valido && validacao.erros && (
              <Alert severity="error" sx={{ mb: 2 }}>
                <Typography variant="subtitle2">Erros encontrados:</Typography>
                {Array.isArray(validacao.erros) ? (
                  <List dense>
                    {validacao.erros.map((e, i) => (
                      <ListItem key={i}>
                        <ListItemIcon><WarningIcon color="error" fontSize="small" /></ListItemIcon>
                        <ListItemText primary={e} />
                      </ListItem>
                    ))}
                  </List>
                ) : (
                  <Typography variant="body2">{validacao.erros}</Typography>
                )}
              </Alert>
            )}

            {/* Resumo consolidado */}
            {validacao.valido && (
              <>
                <Typography variant="subtitle1" gutterBottom fontWeight="bold">
                  Resumo da Segmentação
                </Typography>

                {/* Regras */}
                <Box sx={{ mb: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Typography variant="subtitle2" gutterBottom>Regras</Typography>
                  {segData?.regras_json
                    ? renderRegrasLegiveis(segData.regras_json)
                    : <Typography variant="body2" color="text.secondary">N/A</Typography>
                  }
                </Box>

                {/* Destino */}
                <Box sx={{ mb: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Typography variant="subtitle2" gutterBottom>Destino</Typography>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    {segData?.destinos?.map((d) => (
                      <Chip
                        key={d.destino}
                        label={d.destino === 'sistema2' ? 'Humano (S2)' : 'Digital (S3)'}
                        color={d.habilitado ? (d.destino === 'sistema2' ? 'info' : 'success') : 'default'}
                        variant={d.habilitado ? 'filled' : 'outlined'}
                        size="small"
                      />
                    )) || <Typography variant="body2" color="text.secondary">Não configurado</Typography>}
                  </Box>
                </Box>

                {/* Vigência */}
                <Box sx={{ mb: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Typography variant="subtitle2" gutterBottom>Vigência</Typography>
                  <Typography variant="body2">
                    <strong>Início:</strong> {segData?.vigencia_inicio || 'Não definido'}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Fim:</strong> {segData?.vigencia_fim || 'Sem data fim'}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Recorrência:</strong> {segData?.recorrencia || 'once'}
                  </Typography>
                </Box>

                <Divider sx={{ my: 2 }} />

                {/* Checklist */}
                <Typography variant="subtitle1" gutterBottom fontWeight="bold">
                  Checklist de Aprovação
                </Typography>
                <Box sx={{ mb: 2 }}>
                  {CHECKLIST_ITEMS.map((item) => (
                    <FormControlLabel
                      key={item.key}
                      control={
                        <Checkbox
                          checked={checklist[item.key] || false}
                          onChange={() => handleChecklistChange(item.key)}
                        />
                      }
                      label={item.label}
                      sx={{ display: 'block' }}
                    />
                  ))}
                </Box>

                {/* Aviso de recálculo */}
                <Alert severity="info" icon={<RocketLaunchIcon />}>
                  <Typography variant="body2">
                    <strong>Atenção:</strong> Ao aprovar, um recálculo imediato será disparado
                    (Job seg_exec). O público será materializado em <code>seg_resultado_corrente</code>.
                  </Typography>
                </Alert>
              </>
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={onClose} variant="outlined">
          Cancelar
        </Button>
        <Button
          onClick={handleAprovar}
          variant="contained"
          disabled={!podeAprovar || loadingAprovar}
          startIcon={loadingAprovar ? <CircularProgress size={18} /> : <CheckCircleIcon />}
        >
          Aprovar e Executar
        </Button>
      </DialogActions>
    </Dialog>
  );
}
