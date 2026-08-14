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
} from '@mui/material';
import { useSegmentacoesApi } from '../api/segmentacoes';
import PublicoSelector from '../components/PublicoSelector';
import TemaMenu from '../components/TemaMenu';
import RuleBuilder from '../components/RuleBuilder';
import ExclusaoBuilder from '../components/ExclusaoBuilder';

const STEPS = ['Público', 'Regras de Inclusão', 'Regras de Exclusão'];

export default function BuilderSegmentacao() {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEdit = !!id;

  const { buscar, criar, atualizar, loading: apiLoading } = useSegmentacoesApi();

  const [dadosBasicos, setDadosBasicos] = useState({
    nome: '',
    descricao: '',
    objetivo: '',
    owner: 'admin',
    area_responsavel: '',
    email_contato: '',
  });

  const [publicoSelecionado, setPublicoSelecionado] = useState('');
  const [regrasInclusao, setRegrasInclusao] = useState([
    { operator: 'AND', rules: [{ campo_id: '', op: '', value: '' }] }
  ]);
  const [regrasExclusao, setRegrasExclusao] = useState([
    { operator: 'OR', rules: [{ campo_id: '', op: '', value: '' }] }
  ]);

  // Operadores inter-grupo: como os GRUPOS se conectam entre si
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
            owner: data.owner || 'admin',
            area_responsavel: data.area_responsavel || '',
            email_contato: data.email_contato || '',
          });
          setPublicoSelecionado(data.publico_base_id || '');
          if (data.regras_json) {
            const inclusao = data.regras_json.inclusao;
            const exclusao = data.regras_json.exclusao;

            // Se inclusao é um RegraNo com sub-RegraNos (estrutura aninhada),
            // decompor em grupos + inter-group operator
            if (inclusao && inclusao.rules && inclusao.rules.length > 0 && inclusao.rules[0]?.rules) {
              // Estrutura aninhada: {operator: 'OR', rules: [{operator:'AND', rules:[...]}, ...]}
              setInterGroupOpInclusao(inclusao.operator || 'OR');
              setRegrasInclusao(inclusao.rules);
            } else if (inclusao) {
              // Estrutura flat legada: {operator: 'AND', rules: [folha, folha, ...]}
              setRegrasInclusao([inclusao]);
              setInterGroupOpInclusao('OR');
            } else {
              setRegrasInclusao([{ operator: 'AND', rules: [] }]);
            }

            if (exclusao && exclusao.rules && exclusao.rules.length > 0 && exclusao.rules[0]?.rules) {
              setInterGroupOpExclusao(exclusao.operator || 'OR');
              setRegrasExclusao(exclusao.rules);
            } else if (exclusao) {
              setRegrasExclusao([exclusao]);
              setInterGroupOpExclusao('OR');
            } else {
              setRegrasExclusao([{ operator: 'OR', rules: [] }]);
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

  // ✅ Reseta estado ao mudar de edição para criação
  useEffect(() => {
    if (!isEdit) {
      setDadosBasicos({
        nome: '',
        descricao: '',
        objetivo: '',
        owner: 'admin',
        area_responsavel: '',
        email_contato: '',
      });
      setPublicoSelecionado('');
      setRegrasInclusao([{ operator: 'AND', rules: [{ campo_id: '', op: '', value: '' }] }]);
      setRegrasExclusao([{ operator: 'OR', rules: [{ campo_id: '', op: '', value: '' }] }]);
      setInterGroupOpInclusao('OR');
      setInterGroupOpExclusao('OR');
      setActiveStep(0);
      setError(null);
      setCarregandoMetadata(true);
    }
  }, [isEdit]);

  const handleSelectCampoInclusao = (campo) => {
    const lastIndex = regrasInclusao.length - 1;
    const novasRegras = [...regrasInclusao];
    novasRegras[lastIndex].rules.push({
      campo_id: campo.caracteristica_id,
      op: campo.operadores?.[0] || '=',
      value: '',
    });
    setRegrasInclusao(novasRegras);
    if (activeStep < 1) setActiveStep(1);
  };

  const handleSelectCampoExclusao = (campo) => {
    const lastIndex = regrasExclusao.length - 1;
    const novasRegras = [...regrasExclusao];
    novasRegras[lastIndex].rules.push({
      campo_id: campo.caracteristica_id,
      op: campo.operadores?.[0] || '=',
      value: '',
    });
    setRegrasExclusao(novasRegras);
    if (activeStep < 2) setActiveStep(2);
  };

  const handleSalvar = async () => {
    if (!dadosBasicos.nome) {
      setError('O nome é obrigatório');
      return;
    }
    if (!publicoSelecionado) {
      setError('Selecione um público-base');
      return;
    }
    // Helper: verifica se uma regra tem valor preenchido
    const regraTemValor = (rule) => {
      if (rule.op === 'is_null' || rule.op === 'is_not_null') return true;
      // value pode ser 0, false, [] — só rejeita '' e null/undefined
      return rule.value !== '' && rule.value !== null && rule.value !== undefined;
    };

    const temRegraValida = regrasInclusao.some(group =>
      group.rules.some(rule => rule.campo_id && rule.op && regraTemValor(rule))
    );
    if (!temRegraValida) {
      setError('Adicione pelo menos uma regra de inclusão válida');
      return;
    }

    // Filtra regras incompletas e converte value para tipo correto
    const prepararRegras = (rules) =>
      rules
        .filter(r => r.campo_id && r.op && regraTemValor(r))
        .map(r => {
          let value = r.value;
          // Coerce: string numérica -> number (evita enviar "25" ao invés de 25)
          if (typeof value === 'string' && value !== '' && !isNaN(Number(value))) {
            value = Number(value);
          }
          // Coerce: string boolean -> boolean
          if (typeof value === 'string' && (value.toLowerCase() === 'true' || value.toLowerCase() === 'false')) {
            value = value.toLowerCase() === 'true';
          }
          // Operadores sem valor
          if (r.op === 'is_null' || r.op === 'is_not_null') {
            value = null;
          }
          return { campo_id: r.campo_id, op: r.op, value };
        });

    // Monta cada grupo como um RegraNo individual
    const buildRegraNo = (groups, interGroupOp) => {
      const gruposValidos = groups
        .map(group => ({
          operator: group.operator || 'AND',
          rules: prepararRegras(group.rules),
        }))
        .filter(g => g.rules.length > 0);

      if (gruposValidos.length === 0) return null;
      // Se só 1 grupo, envia flat (compatível com legado)
      if (gruposValidos.length === 1) return gruposValidos[0];
      // Múltiplos grupos: wrapper RegraNo com inter-group operator
      return {
        operator: interGroupOp,
        rules: gruposValidos,
      };
    };

    const inclusaoNo = buildRegraNo(regrasInclusao, interGroupOpInclusao);
    const exclusaoNo = buildRegraNo(regrasExclusao, interGroupOpExclusao);

    if (!inclusaoNo) {
      setError('Adicione pelo menos uma regra de inclusão válida');
      return;
    }

    const payload = {
      ...dadosBasicos,
      publico_base_id: publicoSelecionado,
      regras_json: {
        publico_base: publicoSelecionado,
        inclusao: inclusaoNo,
        exclusao: exclusaoNo,
      },
    };

    try {
      let response;
      if (isEdit) {
        response = await atualizar(id, payload);
      } else {
        response = await criar(payload);
      }
      navigate(`/segmentacoes/${response.seg_id || id}`);
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

      <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
        {STEPS.map((label, index) => (
          <Step key={label} completed={activeStep > index}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

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
      </Box>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2, pt: 2, borderTop: '1px solid #e0e0e0' }}>
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