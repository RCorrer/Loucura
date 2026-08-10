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
} from '@mui/material';
import { useSegmentacoesApi } from '../api/segmentacoes';
import { useMetadataApi } from '../api/metadata';

// Componentes que vamos construir em seguida
import PublicoSelector from '../components/PublicoSelector';
import TemaMenu from '../components/TemaMenu';
import RuleBuilder from '../components/RuleBuilder';
import ExclusaoBuilder from '../components/ExclusaoBuilder';

// Estados do builder
const STEPS = ['Público', 'Regras de Inclusão', 'Regras de Exclusão'];

export default function BuilderSegmentacao() {
  const navigate = useNavigate();
  const { id } = useParams(); // se for edição, tem o ID
  const isEdit = !!id;

  // API hooks
  const { buscar, criar, atualizar, loading: apiLoading } = useSegmentacoesApi();
  const { listarPublicos, loading: metaLoading } = useMetadataApi();

  // Estados da segmentação
  const [dadosBasicos, setDadosBasicos] = useState({
    nome: '',
    descricao: '',
    objetivo: '',
    owner: 'admin',
    area_responsavel: '',
    email_contato: '',
  });

  // Estados do builder
  const [publicoSelecionado, setPublicoSelecionado] = useState(null);
  const [regrasInclusao, setRegrasInclusao] = useState({
    operator: 'AND',
    rules: [],
  });
  const [regrasExclusao, setRegrasExclusao] = useState({
    operator: 'OR',
    rules: [],
  });

  // Estado de carregamento da segmentação (se for edição)
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
            setRegrasInclusao(data.regras_json.inclusao || { operator: 'AND', rules: [] });
            setRegrasExclusao(data.regras_json.exclusao || { operator: 'OR', rules: [] });
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
    if (!regrasInclusao.rules || regrasInclusao.rules.length === 0) {
      setError('Adicione pelo menos uma regra de inclusão');
      return;
    }

    const payload = {
      ...dadosBasicos,
      publico_base_id: publicoSelecionado,
      regras_json: {
        publico_base: publicoSelecionado,
        inclusao: regrasInclusao,
        exclusao: regrasExclusao.rules.length > 0 ? regrasExclusao : null,
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

      {/* Stepper para navegar entre os passos */}
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
            {/* Campos básicos podem ficar aqui ou em uma aba separada */}
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
              rules={regrasInclusao}
              onChange={setRegrasInclusao}
            />
          </Paper>
        )}

        {activeStep === 2 && (
          <Paper sx={{ p: 3 }}>
            <ExclusaoBuilder
              rules={regrasExclusao}
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