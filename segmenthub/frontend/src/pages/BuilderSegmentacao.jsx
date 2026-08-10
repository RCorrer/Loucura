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
  MenuItem, // ✅ ADICIONADO
} from '@mui/material';
import { useSegmentacoesApi } from '../api/segmentacoes';
import { useMetadataApi } from '../api/metadata';

// Componentes auxiliares
import PublicoSelector from '../components/PublicoSelector';
import TemaMenu from '../components/TemaMenu';
import RuleBuilder from '../components/RuleBuilder';
import ExclusaoBuilder from '../components/ExclusaoBuilder';

// Passos do builder
const STEPS = ['Público', 'Regras de Inclusão', 'Regras de Exclusão'];

export default function BuilderSegmentacao() {
  const navigate = useNavigate();
  const { id } = useParams(); // ID da segmentação (se for edição)
  const isEdit = !!id;

  // Hooks de API
  const { buscar, criar, atualizar, loading: apiLoading } = useSegmentacoesApi();
  const { loading: metaLoading } = useMetadataApi();

  // Dados básicos da segmentação
  const [dadosBasicos, setDadosBasicos] = useState({
    nome: '',
    descricao: '',
    objetivo: '',
    owner: 'admin',
    area_responsavel: '',
    email_contato: '',
  });

  // Estados do builder (ajustados para arrays de grupos)
  const [publicoSelecionado, setPublicoSelecionado] = useState(null);
  const [regrasInclusao, setRegrasInclusao] = useState([
    { operator: 'AND', rules: [{ campo_id: '', op: '', value: '' }] }
  ]);
  const [regrasExclusao, setRegrasExclusao] = useState([
    { operator: 'OR', rules: [{ campo_id: '', op: '', value: '' }] }
  ]);

  // Estado de carregamento da edição
  const [carregandoDados, setCarregandoDados] = useState(false);
  const [error, setError] = useState(null);

  // Passo atual do stepper
  const [activeStep, setActiveStep] = useState(0);

  // Carregar dados se for edição
  useEffect(() => {
    if (isEdit) {
      const carregarSegmentacao = async () => {
        setCarregandoDados(true);
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
          setPublicoSelecionado(data.publico_base_id || null);
          if (data.regras_json) {
            // Garantir que sejam arrays, mesmo se vierem como objeto único
            const inclusao = Array.isArray(data.regras_json.inclusao) 
              ? data.regras_json.inclusao 
              : [data.regras_json.inclusao || { operator: 'AND', rules: [] }];
            const exclusao = data.regras_json.exclusao 
              ? (Array.isArray(data.regras_json.exclusao) 
                  ? data.regras_json.exclusao 
                  : [data.regras_json.exclusao])
              : [{ operator: 'OR', rules: [] }];
            setRegrasInclusao(inclusao);
            setRegrasExclusao(exclusao);
          }
        } catch (err) {
          setError('Erro ao carregar segmentação');
          console.error(err);
        } finally {
          setCarregandoDados(false);
        }
      };
      carregarSegmentacao();
    }
  }, [id, buscar]);

  // Função para salvar
  const handleSalvar = async () => {
    // Validações básicas
    if (!dadosBasicos.nome) {
      setError('O nome é obrigatório');
      return;
    }
    if (!publicoSelecionado) {
      setError('Selecione um público-base');
      return;
    }
    // Verifica se há pelo menos uma regra com campo preenchido
    const temRegraValida = regrasInclusao.some(group => 
      group.rules.some(rule => rule.campo_id && rule.op && rule.value !== '')
    );
    if (!temRegraValida) {
      setError('Adicione pelo menos uma regra de inclusão válida');
      return;
    }

    const payload = {
      ...dadosBasicos,
      publico_base_id: publicoSelecionado,
      regras_json: {
        publico_base: publicoSelecionado,
        inclusao: regrasInclusao,
        exclusao: regrasExclusao.some(group => group.rules.some(r => r.campo_id)) ? regrasExclusao : null,
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

  // Loading states
  if (carregandoDados) {
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

      {/* Stepper */}
      <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
        {STEPS.map((label, index) => (
          <Step key={label} completed={activeStep > index}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      {/* Conteúdo do passo atual */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {activeStep === 0 && (
          <Paper sx={{ p: 3 }}>
            <PublicoSelector
              value={publicoSelecionado}
              onChange={setPublicoSelecionado}
              disabled={metaLoading}
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
          <Paper sx={{ p: 3 }}>
            <RuleBuilder
              value={regrasInclusao}
              onChange={setRegrasInclusao}
            />
          </Paper>
        )}

        {activeStep === 2 && (
          <Paper sx={{ p: 3 }}>
            <ExclusaoBuilder
              value={regrasExclusao}
              onChange={setRegrasExclusao}
            />
          </Paper>
        )}
      </Box>

      {/* Navegação entre passos */}
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