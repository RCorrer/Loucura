/**
 * VersionDiffDialog — FX-11
 *
 * Compara duas versões de uma segmentação lado a lado.
 * Mostra diff de dados básicos + regras (inclusao/exclusao).
 * Usa GET /api/segmentacoes/{id}/versoes/{v} para buscar cada versão.
 */
import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  CircularProgress,
  Grid,
  Chip,
  Paper,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Divider,
  Alert,
} from '@mui/material';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import RuleViewer from './RuleViewer';

const CAMPOS_DIFF = [
  { key: 'nome', label: 'Nome' },
  { key: 'descricao', label: 'Descrição' },
  { key: 'objetivo', label: 'Objetivo' },
  { key: 'publico_base_id', label: 'Público Base' },
  { key: 'owner', label: 'Owner' },
  { key: 'area_responsavel', label: 'Área' },
  { key: 'status', label: 'Status' },
];

function DiffRow({ label, valA, valB }) {
  const changed = String(valA ?? '') !== String(valB ?? '');
  return (
    <Grid container spacing={1} sx={{ py: 0.5, bgcolor: changed ? 'warning.light' : 'transparent', borderRadius: 1, px: 1 }}>
      <Grid item xs={3}>
        <Typography variant="caption" color="text.secondary" fontWeight="bold">{label}</Typography>
      </Grid>
      <Grid item xs={4}>
        <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
          {valA ?? '—'}
        </Typography>
      </Grid>
      <Grid item xs={1} sx={{ textAlign: 'center' }}>
        {changed && <Chip label="≠" size="small" color="warning" sx={{ minWidth: 24 }} />}
      </Grid>
      <Grid item xs={4}>
        <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
          {valB ?? '—'}
        </Typography>
      </Grid>
    </Grid>
  );
}

export default function VersionDiffDialog({ open, onClose, segId, versoes = [], obterVersao }) {
  const [versaoA, setVersaoA] = useState(null);
  const [versaoB, setVersaoB] = useState(null);
  const [dadosA, setDadosA] = useState(null);
  const [dadosB, setDadosB] = useState(null);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState(null);

  // Auto-selecionar últimas 2 versões ao abrir
  useEffect(() => {
    if (open && versoes.length >= 2) {
      setVersaoA(versoes[1].versao);
      setVersaoB(versoes[0].versao);
    } else if (open && versoes.length === 1) {
      setVersaoA(versoes[0].versao);
      setVersaoB(versoes[0].versao);
    }
  }, [open, versoes]);

  // Buscar dados das versões selecionadas
  useEffect(() => {
    if (!open || !versaoA || !versaoB || !obterVersao) return;
    const buscar = async () => {
      setLoading(true);
      setErro(null);
      try {
        const [a, b] = await Promise.all([
          obterVersao(segId, versaoA),
          obterVersao(segId, versaoB),
        ]);
        setDadosA(a);
        setDadosB(b);
      } catch (err) {
        setErro(err?.message || 'Erro ao buscar versões');
      } finally {
        setLoading(false);
      }
    };
    buscar();
  }, [open, segId, versaoA, versaoB, obterVersao]);

  const handleClose = () => {
    setDadosA(null);
    setDadosB(null);
    setErro(null);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="lg" fullWidth>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <CompareArrowsIcon /> Comparar Versões
      </DialogTitle>
      <DialogContent dividers>
        {/* Seletores de versão */}
        <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Versão A (anterior)</InputLabel>
            <Select
              value={versaoA || ''}
              label="Versão A (anterior)"
              onChange={(e) => setVersaoA(e.target.value)}
            >
              {versoes.map((v) => (
                <MenuItem key={v.versao} value={v.versao}>
                  v{v.versao} — {v.motivo || v.nota_versao || 'sem motivo'}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <CompareArrowsIcon sx={{ alignSelf: 'center', color: 'text.secondary' }} />
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Versão B (atual)</InputLabel>
            <Select
              value={versaoB || ''}
              label="Versão B (atual)"
              onChange={(e) => setVersaoB(e.target.value)}
            >
              {versoes.map((v) => (
                <MenuItem key={v.versao} value={v.versao}>
                  v{v.versao} — {v.motivo || v.nota_versao || 'sem motivo'}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>

        {erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress /></Box>
        ) : dadosA && dadosB ? (
          <Box>
            {/* Header */}
            <Grid container spacing={1} sx={{ mb: 1 }}>
              <Grid item xs={3} />
              <Grid item xs={4}>
                <Chip label={`v${versaoA}`} size="small" color="default" variant="outlined" />
              </Grid>
              <Grid item xs={1} />
              <Grid item xs={4}>
                <Chip label={`v${versaoB}`} size="small" color="primary" />
              </Grid>
            </Grid>

            <Divider sx={{ mb: 1 }} />

            {/* Campos básicos */}
            {CAMPOS_DIFF.map(({ key, label }) => (
              <DiffRow key={key} label={label} valA={dadosA[key]} valB={dadosB[key]} />
            ))}

            <Divider sx={{ my: 2 }} />

            {/* Regras lado a lado */}
            <Typography variant="subtitle2" gutterBottom>Regras de Segmentação</Typography>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Paper variant="outlined" sx={{ p: 1.5 }}>
                  <Typography variant="caption" color="text.secondary">v{versaoA}</Typography>
                  <RuleViewer regrasJson={dadosA.regras_json} />
                </Paper>
              </Grid>
              <Grid item xs={6}>
                <Paper variant="outlined" sx={{ p: 1.5 }}>
                  <Typography variant="caption" color="text.secondary">v{versaoB}</Typography>
                  <RuleViewer regrasJson={dadosB.regras_json} />
                </Paper>
              </Grid>
            </Grid>
          </Box>
        ) : (
          <Typography color="text.secondary">Selecione duas versões para comparar</Typography>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Fechar</Button>
      </DialogActions>
    </Dialog>
  );
}
