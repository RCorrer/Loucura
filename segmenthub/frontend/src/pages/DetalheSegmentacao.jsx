import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageHeader } from '@shared';
import {
  Box,
  Button,
  Paper,
  Typography,
  CircularProgress,
  Alert,
  Chip,
  Grid,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Snackbar,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DescriptionIcon from '@mui/icons-material/Description';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import StopIcon from '@mui/icons-material/Stop';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import SendIcon from '@mui/icons-material/Send';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import PersonIcon from '@mui/icons-material/Person';
import CampaignIcon from '@mui/icons-material/Campaign';
import { useSegmentacoesApi } from '../api/segmentacoes';
import ValidationModal from '../components/ValidationModal';

const STATUS_COLORS = {
  rascunho: 'default',
  em_aprovacao: 'warning',
  aprovada: 'info',
  ativa: 'success',
  pausada: 'warning',
  encerrada: 'error',
  arquivada: 'default',
};

/**
 * DetalheSegmentacao — S1-FRONT-05
 *
 * Página de detalhe read-only consolidado.
 * Rota: /segmentacoes/:id
 *
 * Mostra: metadados, status, regras (resumo), destinos, vigência,
 * últimas execuções, versões. Ações de ciclo de vida.
 */
export default function DetalheSegmentacao() {
  const { id } = useParams();
  const navigate = useNavigate();
  const {
    buscar,
    buscarDestinos,
    listarExecucoes,
    listarVersoes,
    ativar,
    pausar,
    reativar,
    encerrar,
    executar,
    enviarAprovacao,
    loading,
  } = useSegmentacoesApi();

  const [seg, setSeg] = useState(null);
  const [destinos, setDestinos] = useState([]);
  const [execucoes, setExecucoes] = useState([]);
  const [versoes, setVersoes] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '' });
  const [validationOpen, setValidationOpen] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState(null);

  const carregar = async () => {
    setCarregando(true);
    setErro(null);
    try {
      const [segData, destData, execData, versData] = await Promise.all([
        buscar(id),
        buscarDestinos(id),
        listarExecucoes(id),
        listarVersoes(id),
      ]);
      setSeg(segData);
      setDestinos(destData || []);
      setExecucoes(Array.isArray(execData) ? execData : execData?.data || []);
      setVersoes(Array.isArray(versData) ? versData : versData?.data || []);
    } catch (err) {
      setErro(err?.message || 'Erro ao carregar segmentação');
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => { carregar(); }, [id]);

  // Ações de ciclo de vida
  const executarAcao = async (acao, label) => {
    try {
      await acao(id);
      setSnackbar({ open: true, message: `${label} realizado com sucesso` });
      carregar(); // reload
    } catch (err) {
      setSnackbar({ open: true, message: err?.message || `Erro ao ${label.toLowerCase()}` });
    }
    setMenuAnchor(null);
  };

  // Loading
  if (carregando) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (erro) {
    return <Alert severity="error">{erro}</Alert>;
  }

  if (!seg) return null;

  const renderRegrasResumo = () => {
    const regras = seg.regras_json;
    if (!regras) return 'Não definidas';
    const countRules = (no) => {
      if (!no?.rules) return 0;
      return no.rules.reduce((acc, r) => acc + (r.rules ? countRules(r) : 1), 0);
    };
    const inc = countRules(regras.inclusao);
    const exc = countRules(regras.exclusao);
    return `${inc} regra(s) de inclusão${exc > 0 ? `, ${exc} de exclusão` : ''}`;
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <PageHeader
        title={seg.nome}
        subtitle={`${seg.seg_codigo} • ${seg.objetivo}`}
      >
        <Button
          variant="outlined"
          startIcon={<EditIcon />}
          onClick={() => navigate(`/segmentacoes/${id}/editar`)}
          sx={{ mr: 1 }}
        >
          Editar
        </Button>
        <Button
          variant="outlined"
          startIcon={<DescriptionIcon />}
          onClick={() => navigate(`/segmentacoes/${id}/documentacao`)}
          sx={{ mr: 1 }}
        >
          Documentação
        </Button>

        {/* Ações de ciclo */}
        {seg.status === 'rascunho' && (
          <Button
            variant="contained"
            startIcon={<SendIcon />}
            onClick={() => executarAcao(enviarAprovacao, 'Envio para aprovação')}
          >
            Enviar p/ Aprovação
          </Button>
        )}
        {seg.status === 'em_aprovacao' && (
          <Button
            variant="contained"
            startIcon={<CheckCircleIcon />}
            onClick={() => setValidationOpen(true)}
            color="success"
          >
            Validar e Aprovar
          </Button>
        )}
        {seg.status === 'ativa' && (
          <>
            <Button
              variant="outlined"
              startIcon={<PlayArrowIcon />}
              onClick={() => executarAcao(executar, 'Execução')}
              sx={{ mr: 1 }}
            >
              Executar
            </Button>
            <Button
              variant="outlined"
              startIcon={<MoreVertIcon />}
              onClick={(e) => setMenuAnchor(e.currentTarget)}
            >
              Ações
            </Button>
            <Menu anchorEl={menuAnchor} open={!!menuAnchor} onClose={() => setMenuAnchor(null)}>
              <MenuItem onClick={() => executarAcao(pausar, 'Pausa')}>
                <ListItemIcon><PauseIcon /></ListItemIcon>
                <ListItemText>Pausar</ListItemText>
              </MenuItem>
              <MenuItem onClick={() => executarAcao(encerrar, 'Encerramento')}>
                <ListItemIcon><StopIcon /></ListItemIcon>
                <ListItemText>Encerrar</ListItemText>
              </MenuItem>
            </Menu>
          </>
        )}
        {seg.status === 'pausada' && (
          <Button
            variant="contained"
            startIcon={<RestartAltIcon />}
            onClick={() => executarAcao(reativar, 'Reativação')}
          >
            Reativar
          </Button>
        )}
      </PageHeader>

      {/* Cards */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        <Grid container spacing={2} sx={{ mb: 3 }}>
          {/* Status */}
          <Grid item xs={12} sm={4}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="caption" color="text.secondary">Status</Typography>
              <Box sx={{ mt: 1 }}>
                <Chip label={seg.status} color={STATUS_COLORS[seg.status] || 'default'} />
              </Box>
            </Paper>
          </Grid>
          {/* Versão */}
          <Grid item xs={12} sm={4}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="caption" color="text.secondary">Versão Atual</Typography>
              <Typography variant="h5">{seg.versao_atual}</Typography>
            </Paper>
          </Grid>
          {/* Público */}
          <Grid item xs={12} sm={4}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="caption" color="text.secondary">Regras</Typography>
              <Typography variant="body1">{renderRegrasResumo()}</Typography>
            </Paper>
          </Grid>
        </Grid>

        {/* Destinos */}
        <Paper sx={{ p: 2, mb: 2 }}>
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Destinos</Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            {destinos.length > 0 ? destinos.map((d) => (
              <Chip
                key={d.destino}
                icon={d.destino === 'sistema2' ? <PersonIcon /> : <CampaignIcon />}
                label={d.destino === 'sistema2' ? 'Atendimento Humano' : 'Digital'}
                color={d.habilitado ? (d.destino === 'sistema2' ? 'info' : 'success') : 'default'}
                variant={d.habilitado ? 'filled' : 'outlined'}
              />
            )) : (
              <Typography variant="body2" color="text.secondary">Nenhum destino configurado</Typography>
            )}
          </Box>
        </Paper>

        {/* Vigência */}
        <Paper sx={{ p: 2, mb: 2 }}>
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Vigência</Typography>
          <Grid container spacing={2}>
            <Grid item xs={4}>
              <Typography variant="caption" color="text.secondary">Início</Typography>
              <Typography variant="body2">{seg.vigencia_inicio || 'Não definido'}</Typography>
            </Grid>
            <Grid item xs={4}>
              <Typography variant="caption" color="text.secondary">Fim</Typography>
              <Typography variant="body2">{seg.vigencia_fim || 'Sem data fim'}</Typography>
            </Grid>
            <Grid item xs={4}>
              <Typography variant="caption" color="text.secondary">Recorrência</Typography>
              <Typography variant="body2">{seg.recorrencia || 'once (estático)'}</Typography>
            </Grid>
          </Grid>
        </Paper>

        {/* Últimas execuções */}
        <Paper sx={{ p: 2, mb: 2 }}>
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
            Últimas Execuções
          </Typography>
          {execucoes.length > 0 ? (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>ID</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Clientes</TableCell>
                    <TableCell>Data</TableCell>
                    <TableCell>Origem</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {execucoes.slice(0, 5).map((exec) => (
                    <TableRow key={exec.exec_id}>
                      <TableCell>
                        <Typography variant="caption" fontFamily="monospace">
                          {exec.exec_id?.slice(-12) || '-'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={exec.status}
                          size="small"
                          color={exec.status === 'sucesso' ? 'success' : exec.status === 'erro' ? 'error' : 'default'}
                        />
                      </TableCell>
                      <TableCell>{exec.qtd_clientes?.toLocaleString('pt-BR') || '-'}</TableCell>
                      <TableCell>{exec.executado_em || exec.criado_em || '-'}</TableCell>
                      <TableCell>{exec.origem_execucao || '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Typography variant="body2" color="text.secondary">Nenhuma execução registrada</Typography>
          )}
        </Paper>

        {/* Versões */}
        <Paper sx={{ p: 2, mb: 2 }}>
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
            Versões
          </Typography>
          {versoes.length > 0 ? (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Versão</TableCell>
                    <TableCell>Motivo</TableCell>
                    <TableCell>Alterado por</TableCell>
                    <TableCell>Data</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {versoes.slice(0, 5).map((v) => (
                    <TableRow key={v.versao}>
                      <TableCell><Chip label={`v${v.versao}`} size="small" /></TableCell>
                      <TableCell>{v.motivo || v.nota_versao || '-'}</TableCell>
                      <TableCell>{v.alterado_por || v.criado_por || '-'}</TableCell>
                      <TableCell>{v.alterado_em || v.criado_em || '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Typography variant="body2" color="text.secondary">Apenas versão atual</Typography>
          )}
        </Paper>

        {/* Metadados */}
        <Paper sx={{ p: 2, mb: 2 }}>
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Metadados</Typography>
          <Grid container spacing={2}>
            <Grid item xs={6} sm={3}>
              <Typography variant="caption" color="text.secondary">Owner</Typography>
              <Typography variant="body2">{seg.owner}</Typography>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Typography variant="caption" color="text.secondary">Área</Typography>
              <Typography variant="body2">{seg.area_responsavel || '-'}</Typography>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Typography variant="caption" color="text.secondary">Criado em</Typography>
              <Typography variant="body2">{seg.criado_em || '-'}</Typography>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Typography variant="caption" color="text.secondary">Atualizado em</Typography>
              <Typography variant="body2">{seg.atualizado_em || '-'}</Typography>
            </Grid>
            {seg.seg_tags?.length > 0 && (
              <Grid item xs={12}>
                <Typography variant="caption" color="text.secondary">Tags</Typography>
                <Box sx={{ mt: 0.5, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                  {seg.seg_tags.map((tag) => (
                    <Chip key={tag} label={tag} size="small" variant="outlined" />
                  ))}
                </Box>
              </Grid>
            )}
          </Grid>
        </Paper>
      </Box>

      {/* Modal de Validação */}
      <ValidationModal
        open={validationOpen}
        onClose={() => setValidationOpen(false)}
        segId={id}
        segData={{ ...seg, destinos }}
        onAprovado={carregar}
      />

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
