import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  CircularProgress,
  Chip,
  Alert,
  Tooltip,
  Divider,
} from '@mui/material';
import PeopleIcon from '@mui/icons-material/People';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import RemoveCircleOutlineIcon from '@mui/icons-material/RemoveCircleOutline';
import TimerIcon from '@mui/icons-material/Timer';
import { useEstimativaApi } from '../api/estimativa';

const DEBOUNCE_MS = 800;

/**
 * EstimativaBadge — S1-FRONT-03
 *
 * Mostra estimativa de público em tempo real dentro do Builder.
 * Dispara POST /api/estimativa/preview com debounce ao alterar regras.
 * Nunca exibe lista de clientes — só contagens agregadas.
 *
 * Props:
 *   - publicoBase: string (publico_id selecionado)
 *   - regrasInclusao: array de grupos [{operator, rules}, ...]
 *   - regrasExclusao: array de grupos [{operator, rules}, ...]
 *   - interGroupOpInclusao: 'AND' | 'OR'
 *   - interGroupOpExclusao: 'AND' | 'OR'
 */
export default function EstimativaBadge({
  publicoBase,
  regrasInclusao,
  regrasExclusao,
  interGroupOpInclusao = 'OR',
  interGroupOpExclusao = 'OR',
}) {
  const { calcularPreview } = useEstimativaApi();

  const [resultado, setResultado] = useState(null);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState(null);
  const debounceRef = useRef(null);
  const abortRef = useRef(null);

  // =============================================
  // Helpers para montar o payload no formato do back
  // (mesma lógica do buildRegraNo do BuilderSegmentacao)
  // =============================================

  const regraTemValor = (rule) => {
    if (rule.op === 'is_null' || rule.op === 'is_not_null') return true;
    return rule.value !== '' && rule.value !== null && rule.value !== undefined;
  };

  const prepararRegras = (rules) =>
    rules
      .filter((r) => r.campo_id && r.op && regraTemValor(r))
      .map((r) => {
        let value = r.value;
        if (typeof value === 'string' && value !== '' && !isNaN(Number(value))) {
          value = Number(value);
        }
        if (
          typeof value === 'string' &&
          (value.toLowerCase() === 'true' || value.toLowerCase() === 'false')
        ) {
          value = value.toLowerCase() === 'true';
        }
        if (r.op === 'is_null' || r.op === 'is_not_null') {
          value = null;
        }
        return { campo_id: r.campo_id, op: r.op, value };
      });

  const buildRegraNo = useCallback((groups, interGroupOp) => {
    const gruposValidos = groups
      .map((group) => ({
        operator: group.operator || 'AND',
        rules: prepararRegras(group.rules || []),
      }))
      .filter((g) => g.rules.length > 0);

    if (gruposValidos.length === 0) return null;
    if (gruposValidos.length === 1) return gruposValidos[0];
    return { operator: interGroupOp, rules: gruposValidos };
  }, []);

  // =============================================
  // Verifica se temos o mínimo para disparar
  // =============================================

  const podEstimar = useCallback(() => {
    if (!publicoBase) return false;
    // Precisa de ao menos 1 regra válida na inclusão
    const temRegra = regrasInclusao.some((group) =>
      (group.rules || []).some((r) => r.campo_id && r.op && regraTemValor(r))
    );
    return temRegra;
  }, [publicoBase, regrasInclusao]);

  // =============================================
  // Dispara estimativa com debounce
  // =============================================

  const dispararEstimativa = useCallback(async () => {
    if (!podEstimar()) {
      setResultado(null);
      setErro(null);
      return;
    }

    const inclusaoNo = buildRegraNo(regrasInclusao, interGroupOpInclusao);
    if (!inclusaoNo) {
      setResultado(null);
      return;
    }

    const exclusaoNo = buildRegraNo(regrasExclusao, interGroupOpExclusao);

    const payload = {
      publico_base: publicoBase,
      inclusao: inclusaoNo,
      exclusao: exclusaoNo,
    };

    setLoading(true);
    setErro(null);

    try {
      const res = await calcularPreview(payload);
      setResultado(res);
    } catch (err) {
      // useApi agora propaga err.status e err.data
      if (err?.status === 422) {
        // Mensagem já vem parseada no err.message pelo useApi
        setErro(err.message || 'Regras inválidas');
      } else {
        setErro(err?.message || 'Erro ao calcular estimativa');
      }
      setResultado(null);
    } finally {
      setLoading(false);
    }
  }, [publicoBase, regrasInclusao, regrasExclusao, interGroupOpInclusao, interGroupOpExclusao, buildRegraNo, podEstimar, calcularPreview]);

  // =============================================
  // Effect com debounce — reage a mudanças nas regras
  // =============================================

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      dispararEstimativa();
    }, DEBOUNCE_MS);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [dispararEstimativa]);

  // =============================================
  // Formatação de números
  // =============================================

  const formatarNumero = (num) => {
    if (num === null || num === undefined) return '—';
    return new Intl.NumberFormat('pt-BR').format(num);
  };

  // =============================================
  // Render
  // =============================================

  // Não renderiza nada se não há público selecionado
  if (!publicoBase) return null;

  return (
    <Paper
      elevation={2}
      sx={{
        p: 2,
        display: 'flex',
        alignItems: 'center',
        gap: 2,
        flexWrap: 'wrap',
        border: '1px solid',
        borderColor: erro ? 'error.light' : resultado ? 'success.light' : 'divider',
        bgcolor: erro ? 'error.50' : 'background.paper',
        transition: 'all 0.3s ease',
      }}
    >
      {/* Ícone principal */}
      <PeopleIcon color={erro ? 'error' : 'primary'} />

      {/* Loading */}
      {loading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CircularProgress size={18} />
          <Typography variant="body2" color="text.secondary">
            Estimando...
          </Typography>
        </Box>
      )}

      {/* Erro de validação */}
      {!loading && erro && (
        <Alert severity="warning" variant="outlined" sx={{ py: 0, flex: 1 }}>
          <Typography variant="body2">{erro}</Typography>
        </Alert>
      )}

      {/* Resultado */}
      {!loading && !erro && resultado && (
        <>
          {/* Estimativa final */}
          <Tooltip title="Público estimado (inclusão − exclusão)">
            <Chip
              icon={<PeopleIcon />}
              label={formatarNumero(resultado.estimativa)}
              color="primary"
              variant="filled"
              sx={{ fontWeight: 'bold', fontSize: '0.95rem' }}
            />
          </Tooltip>

          <Divider orientation="vertical" flexItem />

          {/* Detalhamento */}
          <Tooltip title="Clientes na inclusão">
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <AddCircleOutlineIcon fontSize="small" color="success" />
              <Typography variant="body2" color="text.secondary">
                {formatarNumero(resultado.inclusao)}
              </Typography>
            </Box>
          </Tooltip>

          {resultado.exclusao > 0 && (
            <Tooltip title="Clientes excluídos">
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <RemoveCircleOutlineIcon fontSize="small" color="error" />
                <Typography variant="body2" color="text.secondary">
                  −{formatarNumero(resultado.exclusao)}
                </Typography>
              </Box>
            </Tooltip>
          )}

          {/* Tempo */}
          <Tooltip title="Tempo de cálculo">
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <TimerIcon fontSize="small" sx={{ color: 'text.disabled' }} />
              <Typography variant="caption" color="text.disabled">
                {resultado.tempo_ms < 1000
                  ? `${resultado.tempo_ms}ms`
                  : `${(resultado.tempo_ms / 1000).toFixed(1)}s`}
              </Typography>
            </Box>
          </Tooltip>
        </>
      )}

      {/* Estado inicial (sem resultado, sem erro, sem loading) */}
      {!loading && !erro && !resultado && (
        <Typography variant="body2" color="text.secondary">
          Adicione regras para ver a estimativa de público
        </Typography>
      )}
    </Paper>
  );
}
