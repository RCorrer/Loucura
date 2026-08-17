import React, { useState, useEffect } from 'react';
import { PageHeader } from '@shared';
import {
  Box,
  Paper,
  Typography,
  CircularProgress,
  Alert,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip,
  IconButton,
  Switch,
  Drawer,
  Button,
  Divider,
  Tabs,
  Tab,
  FormControlLabel,
  Snackbar,
} from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
import HistoryIcon from '@mui/icons-material/History';
import SearchIcon from '@mui/icons-material/Search';
// CheckCircleIcon e BlockIcon removidos — S2/S3 agora usam Switch inline
import { useMetadataAdminApi } from '../api/metadataAdmin';

/**
 * AdminCatalogo — S1-FRONT-10 (adendo)
 *
 * Página admin de governança do catálogo de características.
 * Rota: /admin/catalogo
 *
 * Funcionalidades:
 * - Tabela paginável de campos com filtros (tema, sistema, status, busca)
 * - Toggle ativo/inativo (PUT /status)
 * - Drawer de detalhe + edição de flags (PUT /flags)
 * - Histórico de governança (aba no drawer + trilha geral)
 */
export default function AdminCatalogo() {
  const {
    listarCampos,
    obterCampo,
    atualizarFlags,
    atualizarStatus,
    listarHistorico,
    listarHistoricoCampo,
  } = useMetadataAdminApi();

  // Filtros
  const [filtros, setFiltros] = useState({ tema: '', sistema: '', status: '', busca: '' });
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(50);

  // Dados
  const [campos, setCampos] = useState([]);
  const [totalCampos, setTotalCampos] = useState(0);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);

  // Drawer detalhe
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detalhe, setDetalhe] = useState(null);
  const [historicoCampo, setHistoricoCampo] = useState([]);
  const [loadingDetalhe, setLoadingDetalhe] = useState(false);
  const [drawerTab, setDrawerTab] = useState(0);

  // Histórico geral (tab principal)
  const [tabPrincipal, setTabPrincipal] = useState(0); // 0=campos, 1=histórico
  const [historicoGeral, setHistoricoGeral] = useState([]);
  const [loadingHistorico, setLoadingHistorico] = useState(false);

  // Flags editáveis
  const [editFlags, setEditFlags] = useState({});
  const [salvandoFlags, setSalvandoFlags] = useState(false);

  const [snackbar, setSnackbar] = useState({ open: false, message: '' });

  // Carrega campos
  useEffect(() => {
    carregarCampos();
  }, [page, rowsPerPage]);

  const carregarCampos = async () => {
    setLoading(true);
    setErro(null);
    try {
      const data = await listarCampos({
        ...filtros,
        page: page + 1,
        size: rowsPerPage,
      });
      if (Array.isArray(data)) {
        setCampos(data);
        setTotalCampos(data.length >= rowsPerPage ? (page + 2) * rowsPerPage : (page * rowsPerPage) + data.length);
      } else {
        setCampos(data?.data || data?.items || []);
        setTotalCampos(data?.total || data?.data?.length || 0);
      }
    } catch (err) {
      setErro(err?.message || 'Erro ao carregar campos');
    } finally {
      setLoading(false);
    }
  };

  const handleFiltrar = () => {
    setPage(0);
    carregarCampos();
  };

  // Toggle status
  const handleToggleStatus = async (campo) => {
    try {
      await atualizarStatus(campo.caracteristica_id, !campo.ativo);
      setSnackbar({ open: true, message: `Campo ${!campo.ativo ? 'ativado' : 'desativado'}` });
      carregarCampos();
    } catch (err) {
      setSnackbar({ open: true, message: err?.message || 'Erro ao alterar status' });
    }
  };

  // Abrir detalhe
  const abrirDetalhe = async (caracteristicaId) => {
    setDrawerOpen(true);
    setLoadingDetalhe(true);
    setDrawerTab(0);
    try {
      const [det, hist] = await Promise.all([
        obterCampo(caracteristicaId),
        listarHistoricoCampo(caracteristicaId),
      ]);
      setDetalhe(det);
      setEditFlags({
        usavel_em_visao360: det.usavel_em_visao360 || false,
        usavel_em_peca: det.usavel_em_peca || false,
        bloco_visao360: det.bloco_visao360 || '',
      });
      setHistoricoCampo(Array.isArray(hist) ? hist : hist?.data || []);
    } catch (err) {
      setSnackbar({ open: true, message: err?.message || 'Erro ao carregar detalhe' });
    } finally {
      setLoadingDetalhe(false);
    }
  };

  // Salvar flags
  const handleSalvarFlags = async () => {
    if (!detalhe) return;
    setSalvandoFlags(true);
    try {
      await atualizarFlags(detalhe.caracteristica_id, editFlags);
      setSnackbar({ open: true, message: 'Flags atualizadas com sucesso' });
      carregarCampos();
      // Refresh detalhe
      const det = await obterCampo(detalhe.caracteristica_id);
      setDetalhe(det);
    } catch (err) {
      setSnackbar({ open: true, message: err?.message || 'Erro ao salvar flags' });
    } finally {
      setSalvandoFlags(false);
    }
  };

  // Histórico geral
  const carregarHistoricoGeral = async () => {
    setLoadingHistorico(true);
    try {
      const data = await listarHistorico({ page: 1, size: 50 });
      setHistoricoGeral(Array.isArray(data) ? data : data?.data || []);
    } catch (err) {
      setSnackbar({ open: true, message: err?.message || 'Erro ao carregar histórico' });
    } finally {
      setLoadingHistorico(false);
    }
  };

  useEffect(() => {
    if (tabPrincipal === 1 && historicoGeral.length === 0) {
      carregarHistoricoGeral();
    }
  }, [tabPrincipal]);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <PageHeader
        title="Admin Catálogo"
        subtitle="Governança de características de segmentação"
      />

      {erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}

      {/* Tabs principais */}
      <Paper sx={{ mb: 2 }}>
        <Tabs value={tabPrincipal} onChange={(_, v) => setTabPrincipal(v)}>
          <Tab label="Campos" />
          <Tab icon={<HistoryIcon />} label="Histórico Geral" iconPosition="start" />
        </Tabs>
      </Paper>

      {/* ============ ABA CAMPOS ============ */}
      {tabPrincipal === 0 && (
        <>
          {/* Filtros */}
          <Paper sx={{ p: 2, mb: 2 }}>
            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} sm={3}>
                <TextField
                  label="Busca"
                  size="small"
                  fullWidth
                  value={filtros.busca}
                  onChange={(e) => setFiltros({ ...filtros, busca: e.target.value })}
                  onKeyDown={(e) => e.key === 'Enter' && handleFiltrar()}
                />
              </Grid>
              <Grid item xs={6} sm={2}>
                <FormControl size="small" fullWidth>
                  <InputLabel>Tema</InputLabel>
                  <Select
                    value={filtros.tema}
                    label="Tema"
                    onChange={(e) => setFiltros({ ...filtros, tema: e.target.value })}
                  >
                    <MenuItem value="">Todos</MenuItem>
                    <MenuItem value="cadastral">Cadastral</MenuItem>
                    <MenuItem value="financeiro">Financeiro</MenuItem>
                    <MenuItem value="comportamental">Comportamental</MenuItem>
                    <MenuItem value="digital">Digital</MenuItem>
                    <MenuItem value="credito">Crédito</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={6} sm={2}>
                <FormControl size="small" fullWidth>
                  <InputLabel>Sistema</InputLabel>
                  <Select
                    value={filtros.sistema}
                    label="Sistema"
                    onChange={(e) => setFiltros({ ...filtros, sistema: e.target.value })}
                  >
                    <MenuItem value="">Todos</MenuItem>
                    <MenuItem value="s2">S2 (Visão 360)</MenuItem>
                    <MenuItem value="s3">S3 (Peça/Engajamento)</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={6} sm={2}>
                <FormControl size="small" fullWidth>
                  <InputLabel>Status</InputLabel>
                  <Select
                    value={filtros.status}
                    label="Status"
                    onChange={(e) => setFiltros({ ...filtros, status: e.target.value })}
                  >
                    <MenuItem value="">Todos</MenuItem>
                    <MenuItem value="ativo">Ativo</MenuItem>
                    <MenuItem value="inativo">Inativo</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={6} sm={2}>
                <Button
                  variant="contained"
                  startIcon={<SearchIcon />}
                  onClick={handleFiltrar}
                  fullWidth
                >
                  Filtrar
                </Button>
              </Grid>
            </Grid>
          </Paper>

          {/* Tabela */}
          <Paper sx={{ flex: 1, overflow: 'auto' }}>
            {loading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress /></Box>
            ) : (
              <>
                <TableContainer>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell>Ativo</TableCell>
                        <TableCell>Label</TableCell>
                        <TableCell>Tema</TableCell>
                        <TableCell>Tipo</TableCell>
                        <TableCell>Sensibilidade</TableCell>
                        <TableCell align="center">S2</TableCell>
                        <TableCell align="center">S3</TableCell>
                        <TableCell>Bloco 360</TableCell>
                        <TableCell align="center">Ações</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {campos.map((campo) => (
                        <TableRow key={campo.caracteristica_id} hover>
                          <TableCell>
                            <Switch
                              size="small"
                              checked={campo.ativo}
                              onChange={() => handleToggleStatus(campo)}
                              color={campo.ativo ? 'success' : 'default'}
                            />
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" fontWeight="medium">
                              {campo.campo_label}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip label={campo.tema} size="small" variant="outlined" />
                          </TableCell>
                          <TableCell>{campo.tipo_dado}</TableCell>
                          <TableCell>
                            <Chip
                              label={campo.sensibilidade}
                              size="small"
                              color={campo.sensibilidade === 'alta' ? 'error' : campo.sensibilidade === 'media' ? 'warning' : 'default'}
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell align="center">
                            <Switch
                              size="small"
                              checked={campo.usavel_em_visao360}
                              onChange={() => handleToggleFlag(campo, 'usavel_em_visao360')}
                              color="info"
                            />
                          </TableCell>
                          <TableCell align="center">
                            <Switch
                              size="small"
                              checked={campo.usavel_em_peca}
                              onChange={() => handleToggleFlag(campo, 'usavel_em_peca')}
                              color="success"
                            />
                          </TableCell>
                          <TableCell>
                            <Typography variant="caption">{campo.bloco_visao360 || '-'}</Typography>
                          </TableCell>
                          <TableCell align="center">
                            <IconButton size="small" onClick={() => abrirDetalhe(campo.caracteristica_id)}>
                              <VisibilityIcon fontSize="small" />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                      {campos.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={9} align="center">
                            <Typography variant="body2" color="text.secondary">Nenhum campo encontrado</Typography>
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
                <TablePagination
                  component="div"
                  count={totalCampos}
                  page={page}
                  onPageChange={(_, p) => setPage(p)}
                  rowsPerPage={rowsPerPage}
                  onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value)); setPage(0); }}
                  rowsPerPageOptions={[25, 50, 100]}
                  labelRowsPerPage="Linhas:"
                />
              </>
            )}
          </Paper>
        </>
      )}

      {/* ============ ABA HISTÓRICO GERAL ============ */}
      {tabPrincipal === 1 && (
        <Paper sx={{ flex: 1, overflow: 'auto', p: 2 }}>
          {loadingHistorico ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress /></Box>
          ) : historicoGeral.length > 0 ? (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Data</TableCell>
                    <TableCell>Campo</TableCell>
                    <TableCell>Ação</TableCell>
                    <TableCell>Flag</TableCell>
                    <TableCell>De</TableCell>
                    <TableCell>Para</TableCell>
                    <TableCell>Usuário</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {historicoGeral.map((h) => (
                    <TableRow key={h.hist_id}>
                      <TableCell>
                        <Typography variant="caption">
                          {h.alterado_em ? new Date(h.alterado_em).toLocaleString('pt-BR') : '-'}
                        </Typography>
                      </TableCell>
                      <TableCell>{h.campo_label || h.caracteristica_id?.slice(0, 12)}</TableCell>
                      <TableCell>
                        <Chip label={h.acao} size="small" color={
                          h.acao === 'liberou' ? 'success' : h.acao === 'retirou' ? 'error' : 'info'
                        } variant="outlined" />
                      </TableCell>
                      <TableCell>{h.flag_alterada}</TableCell>
                      <TableCell><Typography variant="caption">{h.valor_anterior || '-'}</Typography></TableCell>
                      <TableCell><Typography variant="caption" fontWeight="bold">{h.valor_novo}</Typography></TableCell>
                      <TableCell>{h.alterado_por}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Typography variant="body2" color="text.secondary" align="center">Nenhum histórico registrado</Typography>
          )}
        </Paper>
      )}

      {/* ============ DRAWER DE DETALHE ============ */}
      <Drawer
        anchor="right"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        PaperProps={{ sx: { width: 420, p: 3 } }}
      >
        {loadingDetalhe ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress /></Box>
        ) : detalhe ? (
          <Box>
            <Typography variant="h6" gutterBottom>{detalhe.campo_label}</Typography>
            <Chip label={detalhe.ativo ? 'Ativo' : 'Inativo'} color={detalhe.ativo ? 'success' : 'default'} size="small" sx={{ mb: 2 }} />

            <Tabs value={drawerTab} onChange={(_, v) => setDrawerTab(v)} sx={{ mb: 2 }}>
              <Tab label="Detalhe & Flags" />
              <Tab label="Histórico" />
            </Tabs>

            {drawerTab === 0 && (
              <Box>
                {/* Metadados */}
                <Grid container spacing={1} sx={{ mb: 2 }}>
                  <Grid item xs={6}><Typography variant="caption" color="text.secondary">Tema</Typography><Typography variant="body2">{detalhe.tema}</Typography></Grid>
                  <Grid item xs={6}><Typography variant="caption" color="text.secondary">Tipo</Typography><Typography variant="body2">{detalhe.tipo_dado}</Typography></Grid>
                  <Grid item xs={6}><Typography variant="caption" color="text.secondary">Sensibilidade</Typography><Typography variant="body2">{detalhe.sensibilidade}</Typography></Grid>
                  <Grid item xs={6}><Typography variant="caption" color="text.secondary">Tabela</Typography><Typography variant="body2" fontFamily="monospace" fontSize="0.7rem">{detalhe.tabela_fisica}</Typography></Grid>
                  <Grid item xs={6}><Typography variant="caption" color="text.secondary">Campo físico</Typography><Typography variant="body2" fontFamily="monospace">{detalhe.campo_fisico}</Typography></Grid>
                  <Grid item xs={6}><Typography variant="caption" color="text.secondary">Operadores</Typography><Typography variant="body2">{detalhe.operadores?.join(', ')}</Typography></Grid>
                  {detalhe.descricao && (
                    <Grid item xs={12}><Typography variant="caption" color="text.secondary">Descrição</Typography><Typography variant="body2">{detalhe.descricao}</Typography></Grid>
                  )}
                </Grid>

                <Divider sx={{ my: 2 }} />

                {/* Edição de Flags */}
                <Typography variant="subtitle2" gutterBottom>Flags de Governança</Typography>

                <FormControlLabel
                  control={
                    <Switch
                      checked={editFlags.usavel_em_visao360}
                      onChange={(e) => setEditFlags({ ...editFlags, usavel_em_visao360: e.target.checked })}
                    />
                  }
                  label="Usável no S2 (Visão 360)"
                />

                <FormControlLabel
                  control={
                    <Switch
                      checked={editFlags.usavel_em_peca}
                      onChange={(e) => setEditFlags({ ...editFlags, usavel_em_peca: e.target.checked })}
                    />
                  }
                  label="Usável no S3 (Peças/Engajamento)"
                />

                <TextField
                  label="Bloco Visão 360"
                  size="small"
                  fullWidth
                  value={editFlags.bloco_visao360}
                  onChange={(e) => setEditFlags({ ...editFlags, bloco_visao360: e.target.value })}
                  sx={{ mt: 2 }}
                  helperText="Ex: dados_pessoais, financeiro, comportamental"
                />

                <Button
                  variant="contained"
                  onClick={handleSalvarFlags}
                  disabled={salvandoFlags}
                  sx={{ mt: 2 }}
                  fullWidth
                >
                  {salvandoFlags ? <CircularProgress size={20} /> : 'Salvar Flags'}
                </Button>
              </Box>
            )}

            {drawerTab === 1 && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>Histórico de Alterações</Typography>
                {historicoCampo.length > 0 ? (
                  historicoCampo.map((h) => (
                    <Paper key={h.hist_id} variant="outlined" sx={{ p: 1.5, mb: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Chip label={h.acao} size="small" color={
                          h.acao === 'liberou' ? 'success' : h.acao === 'retirou' ? 'error' : 'info'
                        } />
                        <Typography variant="caption" color="text.secondary">
                          {h.alterado_em ? new Date(h.alterado_em).toLocaleString('pt-BR') : ''}
                        </Typography>
                      </Box>
                      <Typography variant="body2">
                        <strong>{h.flag_alterada}</strong>: {h.valor_anterior || '(vazio)'} → {h.valor_novo}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        por {h.alterado_por}
                      </Typography>
                    </Paper>
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary">Nenhuma alteração registrada</Typography>
                )}
              </Box>
            )}
          </Box>
        ) : null}
      </Drawer>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        message={snackbar.message}
      />
    </Box>
  );
}
