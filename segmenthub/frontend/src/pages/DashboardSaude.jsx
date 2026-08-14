import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '@shared';
import {
  Box,
  Paper,
  Typography,
  CircularProgress,
  Alert,
  Grid,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  LinearProgress,
  Tooltip,
  Link,
} from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import { useSaudeApi } from '../api/saude';

const STATUS_ICON = {
  verde: <CheckCircleIcon fontSize="small" sx={{ color: '#2E7D32' }} />,
  amarelo: <WarningIcon fontSize="small" sx={{ color: '#B26A00' }} />,
  vermelho: <ErrorIcon fontSize="small" sx={{ color: '#B00020' }} />,
};

const STATUS_COLOR = {
  verde: '#2E7D32',
  amarelo: '#B26A00',
  vermelho: '#B00020',
};

/**
 * DashboardSaude — S1-FRONT-07
 *
 * Dashboard consolidado de saúde das segmentações.
 * Rota: /saude
 *
 * APIs:
 *  - GET /api/saude (dashboard)
 *  - GET /api/saude/{seg_id} (detalhe)
 *  - GET /api/saude/{seg_id}/overlap
 */
export default function DashboardSaude() {
  const navigate = useNavigate();
  const { obterDashboard, obterDetalhe, obterOverlap } = useSaudeApi();

  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);

  // Dialog de detalhe
  const [detalheOpen, setDetalheOpen] = useState(false);
  const [detalheData, setDetalheData] = useState(null);
  const [overlapData, setOverlapData] = useState([]);
  const [loadingDetalhe, setLoadingDetalhe] = useState(false);

  useEffect(() => {
    carregarDashboard();
  }, []);

  const carregarDashboard = async () => {
    setLoading(true);
    setErro(null);
    try {
      const data = await obterDashboard();
      setDashboard(data);
    } catch (err) {
      setErro(err?.message || 'Erro ao carregar dashboard de saúde');
    } finally {
      setLoading(false);
    }
  };

  const abrirDetalhe = async (segId) => {
    setDetalheOpen(true);
    setLoadingDetalhe(true);
    setDetalheData(null);
    setOverlapData([]);
    try {
      const [det, ovlp] = await Promise.all([
        obterDetalhe(segId),
        obterOverlap(segId).catch(() => ({ overlaps: [] })),
      ]);
      setDetalheData(det);
      setOverlapData(ovlp?.overlaps || []);
    } catch (err) {
      setErro(err?.message || 'Erro ao carregar detalhe');
    } finally {
      setLoadingDetalhe(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (erro && !dashboard) {
    return <Alert severity="error">{erro}</Alert>;
  }

  const detalhes = dashboard?.detalhes || [];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <PageHeader
        title="Dashboard de Saúde"
        subtitle={`Última atualização: ${dashboard?.ultima_atualizacao
          ? new Date(dashboard.ultima_atualizacao).toLocaleString('pt-BR')
          : 'N/A'}`}
      />

      {erro && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErro(null)}>{erro}</Alert>}

      {/* Métricas consolidadas */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} sm={3}>
          <Paper sx={{ p: 2, textAlign: 'center', borderTop: '4px solid #2E7D32' }}>
            <Typography variant="h4" sx={{ color: '#2E7D32' }}>{dashboard?.verde || 0}</Typography>
            <Typography variant="caption">Saudáveis</Typography>
          </Paper>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Paper sx={{ p: 2, textAlign: 'center', borderTop: '4px solid #B26A00' }}>
            <Typography variant="h4" sx={{ color: '#B26A00' }}>{dashboard?.amarelo || 0}</Typography>
            <Typography variant="caption">Atenção</Typography>
          </Paper>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Paper sx={{ p: 2, textAlign: 'center', borderTop: '4px solid #B00020' }}>
            <Typography variant="h4" sx={{ color: '#B00020' }}>{dashboard?.vermelho || 0}</Typography>
            <Typography variant="caption">Críticas</Typography>
          </Paper>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Paper sx={{ p: 2, textAlign: 'center', borderTop: '4px solid #9E9E9E' }}>
            <Typography variant="h4" color="text.secondary">{dashboard?.sem_dados || 0}</Typography>
            <Typography variant="caption">Sem dados</Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Tabela de segmentações */}
      <Paper sx={{ flex: 1, overflow: 'auto' }}>
        <TableContainer>
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>Status</TableCell>
                <TableCell>Segmentação</TableCell>
                <TableCell align="right">Público Atual</TableCell>
                <TableCell align="right">Variação %</TableCell>
                <TableCell align="right">Taxa Sucesso</TableCell>
                <TableCell align="right">Tempo Médio</TableCell>
                <TableCell align="center">Ações</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {detalhes.length > 0 ? detalhes.map((item) => (
                <TableRow
                  key={item.seg_id}
                  hover
                  sx={{ cursor: 'pointer' }}
                  onClick={() => abrirDetalhe(item.seg_id)}
                >
                  <TableCell>
                    <Tooltip title={item.health_status || 'sem dados'}>
                      {STATUS_ICON[item.health_status] || <HelpOutlineIcon fontSize="small" color="disabled" />}
                    </Tooltip>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {item.seg_id?.slice(0, 16)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    {item.publico_atual?.toLocaleString('pt-BR') || '-'}
                  </TableCell>
                  <TableCell align="right">
                    {item.variacao_publico_pct !== null && item.variacao_publico_pct !== undefined ? (
                      <Chip
                        label={`${item.variacao_publico_pct > 0 ? '+' : ''}${item.variacao_publico_pct.toFixed(1)}%`}
                        size="small"
                        color={Math.abs(item.variacao_publico_pct) > 20 ? 'warning' : 'default'}
                        variant="outlined"
                      />
                    ) : '-'}
                  </TableCell>
                  <TableCell align="right">
                    {item.taxa_sucesso_exec !== null && item.taxa_sucesso_exec !== undefined
                      ? `${(item.taxa_sucesso_exec * 100).toFixed(0)}%`
                      : '-'}
                  </TableCell>
                  <TableCell align="right">
                    {item.tempo_medio_exec_seg
                      ? `${item.tempo_medio_exec_seg}s`
                      : '-'}
                  </TableCell>
                  <TableCell align="center">
                    <IconButton size="small" onClick={(e) => { e.stopPropagation(); abrirDetalhe(item.seg_id); }}>
                      <VisibilityIcon fontSize="small" />
                    </IconButton>
                    <IconButton size="small" onClick={(e) => { e.stopPropagation(); navigate(`/segmentacoes/${item.seg_id}`); }}>
                      <OpenInNewIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              )) : (
                <TableRow>
                  <TableCell colSpan={7} align="center">
                    <Typography variant="body2" color="text.secondary">Nenhuma segmentação com dados de saúde</Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Dialog de detalhe */}
      <Dialog open={detalheOpen} onClose={() => setDetalheOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Detalhe de Saúde</DialogTitle>
        <DialogContent dividers>
          {loadingDetalhe ? (
            <Box sx={{ py: 3, textAlign: 'center' }}><CircularProgress /></Box>
          ) : detalheData ? (
            <Box>
              {/* Status */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                {STATUS_ICON[detalheData.health_status] || <HelpOutlineIcon />}
                <Typography variant="h6">
                  {detalheData.health_status?.toUpperCase() || 'SEM DADOS'}
                </Typography>
              </Box>

              {/* Métricas */}
              <Grid container spacing={2} sx={{ mb: 2 }}>
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">Público Atual</Typography>
                  <Typography variant="h6">{detalheData.publico_atual?.toLocaleString('pt-BR') || '-'}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">Variação</Typography>
                  <Typography variant="h6">
                    {detalheData.variacao_publico_pct !== null ? `${detalheData.variacao_publico_pct?.toFixed(1)}%` : '-'}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">Taxa Sucesso Exec</Typography>
                  <Typography variant="h6">
                    {detalheData.taxa_sucesso_exec !== null ? `${(detalheData.taxa_sucesso_exec * 100).toFixed(0)}%` : '-'}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">Tempo Médio</Typography>
                  <Typography variant="h6">{detalheData.tempo_medio_exec_seg ? `${detalheData.tempo_medio_exec_seg}s` : '-'}</Typography>
                </Grid>
              </Grid>

              {/* Alertas */}
              {detalheData.alertas_json && Object.keys(detalheData.alertas_json).length > 0 && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>Alertas</Typography>
                  {Object.entries(detalheData.alertas_json).map(([key, val]) => (
                    <Alert key={key} severity="warning" sx={{ mb: 1 }}>
                      <strong>{key}:</strong> {typeof val === 'string' ? val : JSON.stringify(val)}
                    </Alert>
                  ))}
                </Box>
              )}

              {/* Link Job */}
              {detalheData.job_run_url && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>Link do Job</Typography>
                  <Link href={detalheData.job_run_url} target="_blank" rel="noopener">
                    Abrir última execução do Job <OpenInNewIcon fontSize="small" sx={{ verticalAlign: 'middle' }} />
                  </Link>
                </Box>
              )}

              {/* Overlap */}
              {overlapData.length > 0 && (
                <Box>
                  <Typography variant="subtitle2" gutterBottom>Sobreposições (Fadiga)</Typography>
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Segmento B</TableCell>
                          <TableCell align="right">Clientes em Comum</TableCell>
                          <TableCell align="right">% sobre A</TableCell>
                          <TableCell align="right">% sobre B</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {overlapData.map((o, i) => (
                          <TableRow key={i}>
                            <TableCell>
                              <Typography variant="caption" fontFamily="monospace">
                                {o.seg_id_b?.slice(0, 12)}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">{o.clientes_em_comum?.toLocaleString('pt-BR')}</TableCell>
                            <TableCell align="right">
                              <Chip
                                label={`${o.pct_sobre_a?.toFixed(1)}%`}
                                size="small"
                                color={o.pct_sobre_a > 80 ? 'error' : o.pct_sobre_a > 50 ? 'warning' : 'default'}
                                variant="outlined"
                              />
                            </TableCell>
                            <TableCell align="right">{o.pct_sobre_b?.toFixed(1)}%</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Box>
              )}
            </Box>
          ) : (
            <Typography color="text.secondary">Sem dados disponíveis</Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetalheOpen(false)}>Fechar</Button>
          {detalheData && (
            <Button onClick={() => navigate(`/segmentacoes/${detalheData.seg_id}`)} variant="outlined">
              Abrir Segmentação
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
}
