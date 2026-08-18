import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import RuleNode from './RuleNode';

/**
 * RuleBuilder — Interface principal para construir regras de inclusão.
 *
 * Agora usa estrutura recursiva (RuleNode).
 * O value é uma árvore: { operator: 'AND'|'OR', rules: [...] }
 * Cada rules[] pode conter:
 *   - RegraFolha: { campo_id, op, value }
 *   - RegraNo: { operator, rules: [...] }
 *
 * Para retrocompatibilidade, também aceita array de grupos (legado)
 * e converte automaticamente em árvore.
 *
 * Props:
 *   - value: RegraNo | array (legado)
 *   - onChange: (RegraNo) => void
 *   - operadores: lista de operadores
 *   - label: título
 *   - interGroupOperator: usado apenas se value for array legado
 *   - onInterGroupOperatorChange: não mais necessário (mantido para compat)
 *   - catalogoCampos: array de campos do catálogo
 */
export default function RuleBuilder({
  value,
  onChange,
  operadores,
  label = 'Inclusão',
  interGroupOperator = 'OR',
  onInterGroupOperatorChange,
  catalogoCampos = [],
}) {
  // Normalizar: se value é array legado, converter para árvore
  const normalizeToTree = (val) => {
    if (!val) return { operator: 'AND', rules: [{ campo_id: '', op: '', value: '' }] };
    // Já é uma árvore válida (tem operator + rules no topo)
    if (val.operator && Array.isArray(val.rules)) return val;
    // Array legado de grupos [{operator, rules}, ...]
    if (Array.isArray(val)) {
      if (val.length === 0) return { operator: 'AND', rules: [{ campo_id: '', op: '', value: '' }] };
      if (val.length === 1) return val[0];
      return { operator: interGroupOperator || 'OR', rules: val };
    }
    return { operator: 'AND', rules: [{ campo_id: '', op: '', value: '' }] };
  };

  const tree = normalizeToTree(value);

  const handleChange = (updatedTree) => {
    onChange(updatedTree);
    // Se existe o callback legado, manter sincronizado
    if (onInterGroupOperatorChange && updatedTree.operator !== interGroupOperator) {
      onInterGroupOperatorChange(updatedTree.operator);
    }
  };

  return (
    <Paper sx={{ p: 2, mb: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6">{label}</Typography>
        <Typography variant="caption" color="text.secondary">
          Clique nos chips para alternar AND/OR • Use "Sub-grupo" para aninhar
        </Typography>
      </Box>
      <RuleNode
        node={tree}
        onChange={handleChange}
        onRemove={null}
        depth={0}
        operadores={operadores}
        catalogoCampos={catalogoCampos}
        variant="inclusao"
      />
    </Paper>
  );
}