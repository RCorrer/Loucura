import React from 'react';
import {
  Box,
  Button,
  Chip,
  IconButton,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tooltip,
  Typography,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import { splitAtConnector, flattenTree } from '../utils/splitAtConnector';
import { tokens } from '../shared-ui/theme/tokens';

const DEFAULT_OPS = [
  '=', '!=', '>', '<', '>=', '<=',                     // Comparação numérica
  'between', 'in', 'not_in',                          // Ranges e listas
  'contains', 'not_contains',                         // Texto: contém
  'starts_with', 'ends_with',                         // Texto: começa/termina com
  'not_starts_with', 'not_ends_with',                 // Texto: negação
  'is_null', 'is_not_null'                            // Nulidade
];

const OPERATOR_COLORS = {
  AND: { border: tokens.feedback.info, bg: '#EDF4FB', chip: 'info' },
  OR: { border: tokens.feedback.warning, bg: tokens.surface.warm1, chip: 'warning' },
};

/**
 * isLeaf — verifica se o item é uma regra folha (campo_id + op + value)
 */
function isLeaf(item) {
  return item && 'campo_id' in item;
}

/**
 * LeafRow — renderiza uma regra individual (campo + operador + valor)
 */
function LeafRow({ rule, onChange, onRemove, operadores, catalogoCampos }) {
  const ops = operadores || DEFAULT_OPS;

  const handleChange = (field, value) => {
    onChange({ ...rule, [field]: value });
  };

  // Resolve nome legível do campo
  const campoInfo = catalogoCampos?.find((c) => c.campo_id === rule.campo_id);

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, pl: 1 }}>
      <TextField
        size="small"
        label="Campo"
        value={rule.campo_id || ''}
        onChange={(e) => handleChange('campo_id', e.target.value)}
        sx={{ flex: 2 }}
        helperText={campoInfo?.descricao || ''}
      />
      <FormControl size="small" sx={{ flex: 1, minWidth: 100 }}>
        <InputLabel>Op</InputLabel>
        <Select
          value={rule.op || ''}
          onChange={(e) => handleChange('op', e.target.value)}
          label="Op"
        >
          {ops.map((op) => (
            <MenuItem key={op} value={op}>{op}</MenuItem>
          ))}
        </Select>
      </FormControl>
      {rule.op !== 'is_null' && rule.op !== 'is_not_null' && (
        <TextField
          size="small"
          label="Valor"
          value={rule.value ?? ''}
          onChange={(e) => handleChange('value', e.target.value)}
          sx={{ flex: 1 }}
          placeholder={rule.op === 'between' ? 'min,max' : rule.op === 'in' || rule.op === 'not_in' ? 'a,b,c' : ''}
        />
      )}
      <Tooltip title="Remover regra">
        <IconButton size="small" onClick={onRemove} color="error">
          <DeleteIcon fontSize="small" />
        </IconButton>
      </Tooltip>
    </Box>
  );
}

/**
 * RuleNode — Componente recursivo.
 *
 * Renderiza um nó da árvore de regras.
 * Um nó tem: { operator: 'AND'|'OR', rules: [...] }
 * Cada item em rules pode ser:
 *   - RegraFolha: { campo_id, op, value }
 *   - RegraNo: { operator, rules: [...] }  (sub-grupo recursivo)
 *
 * Props:
 *   - node: { operator, rules } — o nó atual
 *   - onChange: (updatedNode) => void
 *   - onRemove: () => void (null para root)
 *   - depth: nível de aninhamento (0 = root)
 *   - operadores: lista de operadores disponíveis
 *   - catalogoCampos: lista de campos para autocomplete/helper
 *   - variant: 'inclusao' | 'exclusao' (afeta UX)
 */
export default function RuleNode({
  node,
  onChange,
  onRemove,
  depth = 0,
  operadores = DEFAULT_OPS,
  catalogoCampos = [],
  variant = 'inclusao',
}) {
  const colors = OPERATOR_COLORS[node.operator] || OPERATOR_COLORS.AND;
  const isRoot = depth === 0;

  // --- Handlers ---

  const updateRule = (index, updatedItem) => {
    const newRules = [...node.rules];
    newRules[index] = updatedItem;
    onChange({ ...node, rules: newRules });
  };

  const removeRule = (index) => {
    const newRules = node.rules.filter((_, i) => i !== index);
    // Se ficar vazio e não for root, remove o nó inteiro
    if (newRules.length === 0 && !isRoot) {
      onRemove?.();
    } else {
      onChange({ ...node, rules: newRules });
    }
  };

  const addLeaf = () => {
    onChange({
      ...node,
      rules: [...node.rules, { campo_id: '', op: '', value: '' }],
    });
  };

  const addSubGroup = () => {
    const subOp = node.operator === 'AND' ? 'OR' : 'AND';
    onChange({
      ...node,
      rules: [
        ...node.rules,
        { operator: subOp, rules: [{ campo_id: '', op: '', value: '' }] },
      ],
    });
  };

  const toggleOperator = () => {
    onChange({ ...node, operator: node.operator === 'AND' ? 'OR' : 'AND' });
  };

  const handleConnectorClick = (index) => {
    const newOp = node.operator === 'AND' ? 'OR' : 'AND';
    const restructured = splitAtConnector(node, index, newOp);
    // Flatten para remover nós redundantes (1 filho, ou mesmo operator pai/filho)
    const normalized = flattenTree(restructured);
    onChange(normalized);
  };

  // --- Render ---

  return (
    <Box
      sx={{
        borderLeft: `3px solid ${colors.border}`,
        backgroundColor: depth % 2 === 0 ? colors.bg : tokens.surface.canvas,
        borderRadius: 1,
        p: 1.5,
        mb: 1,
        ml: isRoot ? 0 : 1,
        position: 'relative',
      }}
    >
      {/* Header: operator chip + actions */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <Chip
          label={node.operator}
          color={colors.chip}
          size="small"
          onClick={toggleOperator}
          sx={{ cursor: 'pointer', fontWeight: 'bold', minWidth: 50 }}
          title="Clique para alternar AND/OR"
        />
        {!isRoot && depth > 0 && (
          <Typography variant="caption" color="text.secondary">
            Sub-grupo (nível {depth})
          </Typography>
        )}
        <Box sx={{ flex: 1 }} />
        {!isRoot && onRemove && (
          <Tooltip title="Remover este grupo">
            <IconButton size="small" onClick={onRemove} color="error">
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
      </Box>

      {/* Rules list */}
      {node.rules.map((item, index) => (
        <React.Fragment key={index}>
          {isLeaf(item) ? (
            <LeafRow
              rule={item}
              onChange={(updated) => updateRule(index, updated)}
              onRemove={() => removeRule(index)}
              operadores={operadores}
              catalogoCampos={catalogoCampos}
            />
          ) : (
            <RuleNode
              node={item}
              onChange={(updated) => updateRule(index, updated)}
              onRemove={() => removeRule(index)}
              depth={depth + 1}
              operadores={operadores}
              catalogoCampos={catalogoCampos}
              variant={variant}
            />
          )}
          {/* Conector interativo entre siblings — clicável para mudar operator */}
          {index < node.rules.length - 1 && (
            <Box sx={{ display: 'flex', justifyContent: 'center', my: 0.5 }}>
              <Chip
                label={node.operator}
                size="small"
                color={colors.chip}
                onClick={() => handleConnectorClick(index)}
                sx={{
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  fontSize: '0.65rem',
                  height: 20,
                  '&:hover': { opacity: 0.8, transform: 'scale(1.05)' },
                  transition: 'all 0.15s ease',
                }}
                title="Clique para alternar AND/OR entre estas regras"
              />
            </Box>
          )}
        </React.Fragment>
      ))}

      {/* Acções */}
      <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
        <Button
          size="small"
          variant="outlined"
          startIcon={<AddIcon />}
          onClick={addLeaf}
          sx={{ textTransform: 'none', fontSize: '0.75rem' }}
        >
          Regra
        </Button>
        <Button
          size="small"
          variant="outlined"
          startIcon={<AccountTreeIcon />}
          onClick={addSubGroup}
          color="secondary"
          sx={{ textTransform: 'none', fontSize: '0.75rem' }}
        >
          Sub-grupo
        </Button>
      </Box>
    </Box>
  );
}
