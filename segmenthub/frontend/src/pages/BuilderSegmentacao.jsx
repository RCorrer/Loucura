import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { PageHeader } from '@shared';
import {
  Box,
  Button,
  TextField,
  CircularProgress,
  Alert,
  Stepper,
  Step,
  StepLabel,
  Paper,
  MenuItem,
  Typography,
  Divider,
} from '@mui/material';
import { useSegmentacoesApi } from '../api/segmentacoes';
import { tokens } from '../shared-ui/theme/tokens';
import PublicoSelector from '../components/PublicoSelector';
import TemaMenu from '../components/TemaMenu';
import RuleBuilder from '../components/RuleBuilder';
import ExclusaoBuilder from '../components/ExclusaoBuilder';
import EstimativaBadge from '../components/EstimativaBadge';
import DestinoSelector from '../components/DestinoSelector';
import VigenciaAgendamento from '../components/VigenciaAgendamento';

const STEPS = ['Público', 'Regras de Inclusão', 'Regras de Exclusão', 'Destino & Vigência', 'Metadados'];

export default function BuilderSegmentacao() {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEdit = !!id;

  const { buscar, criar, atualizar, buscarDestinos, atualizarDestinos, atualizarVigencia, loading: apiLoading } = useSegmentacoesApi();

  const [dadosBasicos, setDadosBasicos] = useState({
    nome: '',
    descricao: '',
    objetivo: '',
    owner: '',
    area_responsavel: '',
    email_contato: '',
    seg_tags: [],
    resumo: '',
    objetivo_negocio: '',
    publico_alvo_descricao: '',
    observacoes: '',
    documentacao_md: '',
    tipo: 'direta',
  });

  const [publicoSelecionado, setPublicoSelecionado] = useState('');
  // Árvore recursiva de regras (formato RegraNo: { operator, rules })
  const [regrasInclusao, setRegrasInclusao] = useState(
    { operator: 'AND', rules: [{ campo_id: '', op: '', value: '' }] }
  );
  const [regrasExclusao, setRegrasExclusao] = useState(
    { operator: 'OR', rules: [] }
  );

  // Compat legado (não mais usados, mantidos para evitar breaking)
  const [interGroupOpInclusao, setInterGroupOpInclusao] = useState('OR');
  const [interGroupOpExclusao, setInterGroupOpExclusao] = useState('OR');

  const [carregandoDados, setCarregandoDados] = useState(false);
  const [carregandoMetadata, setCarregandoMetadata] = useState(true);
  const [error, setError] = useState(null);
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    if (isEdit) {
      const carregarSegmentacao = async () => {
        setCarregandoDados(true);
        setError(null);
        try {
          const data = await buscar(id);
          setDadosBasicos({
            nome: data.nome || '',
            descricao: data.descricao || '',
            objetivo: data.objetivo || '',
            owner: data.owner || '',  // vazio → backend auto-fill com OBO user
            area_responsavel: data.area_responsavel || '',
            email_contato: data.email_contato || '',
            seg_tags: data.seg_tags || [],
            resumo: data.resumo || '',
            objetivo_negocio: data.objetivo_negocio || '',
            publico_alvo_descricao: data.publico_alvo_descricao || '',
            observacoes: data.observacoes || '',
            documentacao_md: data.documentacao_md || '',
            tipo: data.tipo || 'direta',
          });
          setPublicoSelecionado(data.publico_base_id || '');

          // Carregar destinos e vigência
          try {
            const destData = await buscarDestinos(id);
            if (destData && Array.isArray(destData) && destData.length > 0) {
              setDestinos(destData);
            }
          } catch (e) { /* sem destinos ainda */ }

          // Vigência vem da própria segmentação
          setVigencia({
            vigencia_inicio: data.vigencia_inicio || '',
            vigencia_fim: data.vigencia_fim || '',
            recorrencia: data.recorrencia || 'once',
            agendamento_cron: data.agendamento_cron || '',
          });

          if (data.regras_json) {
            const inclusao = data.regras_json.inclusao;
            const exclusao = data.regras_json.exclusao;

            // Carregar árvore diretamente (formato recursivo RegraNo)
            if (inclusao && inclusao.operator && Array.isArray(inclusao.rules)) {
              setRegrasInclusao(inclusao);
            } else {
              setRegrasInclusao({ operator: 'AND', rules: [{ campo_id: '', op: '', value: '' }] });
            }

            if (exclusao && exclusao.operator && Array.isArray(exclusao.rules)) {
              setRegrasExclusao(exclusao);
            } else {
              setRegrasExclusao({ operator: 'OR', rules: [] });
            }
          }
        } catch (err) {
          console.error(err);
          setError('Erro ao carregar segmentação');
        } finally {
          setCarregandoDados(false);
          setCarregandoMetadata(false);
        }
      };
      carregarSegmentacao();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isEdit, id]);

  // State para destino e vigência
  const [destinos, setDestinos] = useState([
    { destino: 'sistema2', habilitado: false },
    { destino: 'sistema3', habilitado: false },
  ]);
  const [vigencia, setVigencia] = useState({
    vigencia_inicio: '',
    vigencia_fim: '',
    recorrencia: 'once',
    agendamento_cron: '',
  });

  // ✅ Reseta estado ao mudar de edição para criação
  useEffect(() => {
    if (!isEdit) {
      setDadosBasicos({
        nome: '',
        descricao: '',
        objetivo: '',
        owner: '',  // vazio → backend auto-fill com OBO user
        area_responsavel: '',
        email_contato: '',
        seg_tags: [],
        resumo: '',
        objetivo_negocio: '',
        publico_alvo_descricao: '',
        observacoes: '',
        documentacao_md: '',
        tipo: 'direta',
      });
      setPublicoSelecionado('');
      setRegrasInclusao({ operator: 'AND', rules: [{ campo_id: '', op: '', value: '' }] });
      setRegrasExclusao({ operator: 'OR', rules: [] });
      setInterGroupOpInclusao('OR');
      setInterGroupOpExclusao('OR');
      setDestinos([
        { destino: 'sistema2', habilitado: false },
        { destino: 'sistema3', habilitado: false },
      ]);
      setVigencia({ vigencia_inicio: '', vigencia_fim: '', recorrencia: 'once', agendamento_cron: '' });
      setActiveStep(0);
      setError(null);
      setCarregandoMetadata(true);
    }
  }, [isEdit]);

  // Adiciona campo no root da árvore (catálogo → click)
  const handleSelectCampoInclusao = (campo) => {
    setRegrasInclusao((prev) => ({
      ...prev,
      rules: [...prev.rules, { campo_id: campo.caracteristica_id, op: campo.operadores?.[0] || '=', value: '' }],
    }));
    if (activeStep < 1) setActiveStep(1);
  };

  const handleSelectCampoExclusao = (campo) => {
    setRegrasExclusao((prev) => ({
      ...prev,
      rules: [...prev.rules, { campo_id: campo.caracteristica_id, op: campo.operadores?.[0] || '=', value: '' }],
    }));
    if (activeStep < 2) setActiveStep(2);
  };

  const handleSalvar = async () => {
    if (!dadosBasicos.nome) {
      setError('O nome é obrigatório');
      return;
    }
    if (!dadosBasicos.objetivo) {
      setError('Selecione um objetivo');
      return;
    }
    if (!publicoSelecionado) {
      setError('Selecione um público-base');
      return;
    }
    // --- Helpers para limpar/preparar a árvore recursiva ---

    const regraTemValor = (rule) => {
      if (rule.op === 'is_null' || rule.op === 'is_not_null') return true;
      return rule.value !== '' && rule.value !== null && rule.value !== undefined;
    };

    const coerceValue = (value, op) => {
      if (op === 'is_null' || op === 'is_not_null') return null;
      if (typeof value === 'string' && value !== '' && !isNaN(Number(value))) return Number(value);
      if (typeof value === 'string' && (value.toLowerCase() === 'true' || value.toLowerCase() === 'false')) {
        return value.toLowerCase() === 'true';
      }
      // Suporte a listas (in, not_in, between): "a,b,c" -> [a,b,c]
      if (typeof value === 'string' && (op === 'in' || op === 'not_in' || op === 'between')) {
        const parts = value.split(',').map(v => v.trim()).filter(Boolean);
        return parts.map(p => (!isNaN(Number(p)) ? Number(p) : p));
      }
      return value;
    };

    // Limpa a árvore recursivamente: remove folhas incompletas e sub-nós vazios
    const cleanTree = (node) => {
      if (!node || !node.rules) return null;
      const cleanedRules = node.rules
        .map((item) => {
          // Folha
          if ('campo_id' in item) {
            if (!item.campo_id || !item.op || !regraTemValor(item)) return null;
            return { campo_id: item.campo_id, op: item.op, value: coerceValue(item.value, item.op) };
          }
          // Sub-nó recursivo
          return cleanTree(item);
        })
        .filter(Boolean);

      if (cleanedRules.length === 0) return null;
      return { operator: node.operator || 'AND', rules: cleanedRules };
    };

    // Verifica se existe pelo menos 1 folha válida na árvore
    const temFolhaValida = (node) => {
      if (!node || !node.rules) return false;
      return node.rules.some((item) => {
        if ('campo_id' in item) return item.campo_id && item.op && regraTemValor(item);
        return temFolhaValida(item);
      });
    };

    if (!temFolhaValida(regrasInclusao)) {
      setError('Adicione pelo menos uma regra de inclusão válida');
      return;
    }

    const inclusaoNo = cleanTree(regrasInclusao);
    const exclusaoNo = cleanTree(regrasExclusao);

    if (!inclusaoNo) {
      setError('Adicione pelo menos uma regra de inclusão válida');
      return;
    }

    // Payload alinhado ao SegmentacaoCreateDTO/UpdateDTO do backend
    // (destinos e vigência são enviados via endpoints separados)
    const payload = {
      ...dadosBasicos,
      // Se owner vazio, backend auto-preenche com o usuário OBO
      owner: dadosBasicos.owner || '',
      publico_base_id: publicoSelecionado,
      regras_json: {
        publico_base: publicoSelecionado,
        inclusao: inclusaoNo,
        exclusao: exclusaoNo,
      },
    };

    try {
      let segId;
      if (isEdit) {
        await atualizar(id, payload);
        segId = id;
      } else {
        const response = await criar(payload);
        segId = response.seg_id;
      }

      // Persiste destinos e vigência via endpoints dedicados
      // (SegmentacaoCreateDTO não tem esses campos — precisam de chamadas separadas)
      try {
        await atualizarDestinos(segId, destinos);
      } catch (e) {
        console.warn('Aviso: falha ao salvar destinos', e);
      }

      const vigenciaDados = {
        vigencia_inicio: vigencia.vigencia_inicio || null,
        vigencia_fim: vigencia.vigencia_fim || null,
        recorrencia: vigencia.recorrencia || 'once',
        agendamento_cron: vigencia.agendamento_cron || null,
      };
      try {
        await atualizarVigencia(segId, vigenciaDados);
      } catch (e) {
        console.warn('Aviso: falha ao salvar vigência', e);
      }

      navigate(`/segmentacoes/${segId}`);
    } catch (err) {
      setError('Erro ao salvar segmentação: ' + (err.message || ''));
      console.error(err);
    }
  };

  const handleVoltar = () => {
    navigate('/segmentacoes');
  };

  // ✅ Loading apenas na edição
  if (carregandoDados && isEdit) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <PageHeader
        title={isEdit ? 'Editar Segmentação' : 'Nova Segmentação'}
        subtitle={isEdit ? 'Edite os detalhes da segmentação' : 'Crie uma nova segmentação no-code'}
      >
        <Button variant="outlined" onClick={handleVoltar} sx={{ mr: 1 }}>
          Cancelar
        </Button>
        <Button variant="contained" onClick={handleSalvar} disabled={apiLoading}>
          {apiLoading ? <CircularProgress size={24} /> : 'Salvar'}
        </Button>
      </PageHeader>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Stepper activeStep={activeStep} sx={{ mb: 2 }}>
        {STEPS.map((label, index) => (
          <Step key={label} completed={activeStep > index}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      {/* S1-FRONT-03: Estimativa em tempo real */}
      <Box sx={{ mb: 2 }}>
        <EstimativaBadge
          publicoBase={publicoSelecionado}
          regrasInclusao={regrasInclusao}
          regrasExclusao={regrasExclusao}
          interGroupOpInclusao={interGroupOpInclusao}
          interGroupOpExclusao={interGroupOpExclusao}
        />
      </Box>

      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {activeStep === 0 && (
          <Paper sx={{ p: 3 }}>
            <PublicoSelector
              value={publicoSelecionado}
              onChange={setPublicoSelecionado}
              onLoadComplete={() => setCarregandoMetadata(false)}
            />
            <Box sx={{ mt: 3, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
              <TextField
                label="Nome da Segmentação"
                value={dadosBasicos.nome}
                onChange={(e) => setDadosBasicos({ ...dadosBasicos, nome: e.target.value })}
                required
                fullWidth
              />
              <TextField
                label="Objetivo"
                value={dadosBasicos.objetivo}
                onChange={(e) => setDadosBasicos({ ...dadosBasicos, objetivo: e.target.value })}
                select
                fullWidth
              >
                <MenuItem value="AQUISICAO">Aquisição</MenuItem>
                <MenuItem value="RENTABILIZACAO">Rentabilização</MenuItem>
                <MenuItem value="RETENCAO">Retenção</MenuItem>
                <MenuItem value="ENGAJAMENTO">Engajamento</MenuItem>
                <MenuItem value="COBRANCA">Cobrança</MenuItem>
              </TextField>
              <TextField
                label="Descrição"
                value={dadosBasicos.descricao}
                onChange={(e) => setDadosBasicos({ ...dadosBasicos, descricao: e.target.value })}
                fullWidth
                multiline
                rows={2}
              />
              <TextField
                label="Owner (responsável)"
                value={dadosBasicos.owner}
                onChange={(e) => setDadosBasicos({ ...dadosBasicos, owner: e.target.value })}
                fullWidth
                helperText="Deixe vazio para usar seu email automaticamente"
              />
              <TextField
                label="Área Responsável"
                value={dadosBasicos.area_responsavel}
                onChange={(e) => setDadosBasicos({ ...dadosBasicos, area_responsavel: e.target.value })}
                fullWidth
              />
            </Box>
          </Paper>
        )}

        {activeStep === 1 && (
          <Paper sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ display: 'flex', gap: 3, flex: 1, minHeight: 0 }}>
              <Box sx={{ flex: '1 1 40%', overflow: 'auto' }}>
                <TemaMenu onSelectCampo={handleSelectCampoInclusao} />
              </Box>
              <Box sx={{ flex: '1 1 60%', overflow: 'auto' }}>
                <RuleBuilder
                  value={regrasInclusao}
                  onChange={setRegrasInclusao}
                  interGroupOperator={interGroupOpInclusao}
                  onInterGroupOperatorChange={setInterGroupOpInclusao}
                />
              </Box>
            </Box>
          </Paper>
        )}

        {activeStep === 2 && (
          <Paper sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ display: 'flex', gap: 3, flex: 1, minHeight: 0 }}>
              <Box sx={{ flex: '1 1 40%', overflow: 'auto' }}>
                <TemaMenu onSelectCampo={handleSelectCampoExclusao} />
              </Box>
              <Box sx={{ flex: '1 1 60%', overflow: 'auto' }}>
                <ExclusaoBuilder
                  value={regrasExclusao}
                  onChange={setRegrasExclusao}
                  interGroupOperator={interGroupOpExclusao}
                  onInterGroupOperatorChange={setInterGroupOpExclusao}
                />
              </Box>
            </Box>
          </Paper>
        )}

        {activeStep === 3 && (
          <Paper sx={{ p: 3, overflow: 'auto' }}>
            <Typography variant="h6" gutterBottom>
              Destino & Vigência
            </Typography>
            <Divider sx={{ mb: 3 }} />

            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2 }}>
              Para quem esta segmentação será entregue?
            </Typography>
            <DestinoSelector value={destinos} onChange={setDestinos} />

            <Divider sx={{ my: 3 }} />

            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2 }}>
              Quando e com qual frequência?
            </Typography>
            <VigenciaAgendamento value={vigencia} onChange={setVigencia} />
          </Paper>
        )}

        {activeStep === 4 && (
          <Paper sx={{ p: 3, overflow: 'auto' }}>
            <Typography variant="h6" gutterBottom>
              Metadados e Documentação
            </Typography>
            <Divider sx={{ mb: 3 }} />
            
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2 }}>
              Informações Básicas
            </Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mb: 3 }}>
              <TextField
                label="Tipo"
                value={dadosBasicos.tipo}
                onChange={(e) => setDadosBasicos({ ...dadosBasicos, tipo: e.target.value })}
                select
                fullWidth
              >
                <MenuItem value="direta">Direta</MenuItem>
                <MenuItem value="composta">Composta</MenuItem>
              </TextField>
              <TextField
                label="Email de Contato"
                value={dadosBasicos.email_contato}
                onChange={(e) => setDadosBasicos({ ...dadosBasicos, email_contato: e.target.value })}
                type="email"
                fullWidth
              />
            </Box>

            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2 }}>
              Tags e Categorização
            </Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr', gap: 2, mb: 3 }}>
              <TextField
                label="Tags (separadas por vírgula)"
                value={dadosBasicos.seg_tags.join(', ')}
                onChange={(e) => setDadosBasicos({ 
                  ...dadosBasicos, 
                  seg_tags: e.target.value.split(',').map(t => t.trim()).filter(t => t) 
                })}
                fullWidth
                helperText="Ex: marketing, cliente-novo, campanha-2024"
              />
            </Box>

            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2 }}>
              Descrições Detalhadas
            </Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mb: 3 }}>
              <TextField
                label="Resumo"
                value={dadosBasicos.resumo}
                onChange={(e) => setDadosBasicos({ ...dadosBasicos, resumo: e.target.value })}
                fullWidth
                multiline
                rows={2}
              />
              <TextField
                label="Objetivo de Negócio"
                value={dadosBasicos.objetivo_negocio}
                onChange={(e) => setDadosBasicos({ ...dadosBasicos, objetivo_negocio: e.target.value })}
                fullWidth
                multiline
                rows={2}
              />
              <TextField
                label="Descrição do Público-Alvo"
                value={dadosBasicos.publico_alvo_descricao}
                onChange={(e) => setDadosBasicos({ ...dadosBasicos, publico_alvo_descricao: e.target.value })}
                fullWidth
                multiline
                rows={2}
                sx={{ gridColumn: 'span 2' }}
              />
            </Box>

            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2 }}>
              Notas e Documentação
            </Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr', gap: 2 }}>
              <TextField
                label="Observações"
                value={dadosBasicos.observacoes}
                onChange={(e) => setDadosBasicos({ ...dadosBasicos, observacoes: e.target.value })}
                fullWidth
                multiline
                rows={3}
              />
              <TextField
                label="Documentação (Markdown)"
                value={dadosBasicos.documentacao_md}
                onChange={(e) => setDadosBasicos({ ...dadosBasicos, documentacao_md: e.target.value })}
                fullWidth
                multiline
                rows={6}
                helperText="Use Markdown para documentação técnica detalhada"
              />
            </Box>
          </Paper>
        )}
      </Box>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2, pt: 2, borderTop: `1px solid ${tokens.neutral.gray10}` }}>
        <Button
          variant="outlined"
          onClick={() => setActiveStep((prev) => Math.max(prev - 1, 0))}
          disabled={activeStep === 0}
        >
          Voltar
        </Button>
        <Button
          variant="contained"
          onClick={() => setActiveStep((prev) => Math.min(prev + 1, STEPS.length - 1))}
          disabled={activeStep === STEPS.length - 1}
        >
          Avançar
        </Button>
      </Box>
    </Box>
  );
}