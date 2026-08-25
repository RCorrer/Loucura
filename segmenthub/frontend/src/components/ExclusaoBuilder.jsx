import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import RuleNode from './RuleNode';
import { tokens } from '../shared-ui/theme/tokens';

/**
 * ExclusaoBuilder — Mesmo engine recursivo do RuleBuilder, com visual de exclusão.
 *
 * Props (mesmas do RuleBuilder, retrocompatível):
 *   - value: RegraNo | array (legado)
 *   - onChange: (RegraNo) => void
 *   - operadores: lista de operadores
 *   - interGroupOperator: usado apenas se value for array legado
 *   - onInterGroupOperatorChange: mantido para compat
 *   - catalogoCampos: array de campos do catálogo
 */
export default function ExclusaoBuilder({
  value,
  onChange,
  operadores,
  interGroupOperator = 'OR',
  onInterGroupOperatorChange,
  catalogoCampos = [],
}) {
  // Normalizar: se value é array legado, converter para árvore
  const normalizeToTree = (val) => {
    if (!val) return { operator: 'OR', rules: [] };
    if (val.operator && Array.isArray(val.rules)) return val;
    if (Array.isArray(val)) {
      if (val.length === 0) return { operator: 'OR', rules: [] };
      if (val.length === 1) return val[0];
      return { operator: interGroupOperator || 'OR', rules: val };
    }
    return { operator: 'OR', rules: [] };
  };

  const tree = normalizeToTree(value);

  const handleChange = (updatedTree) => {
    onChange(updatedTree);
    if (onInterGroupOperatorChange && updatedTree.operator !== interGroupOperator) {
      onInterGroupOperatorChange(updatedTree.operator);
    }
  };

  return (
    <Paper sx={{ p: 2, mb: 3, border: `1px dashed ${tokens.feedback.error}` }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6" sx={{ color: tokens.feedback.error }}>
          Exclusão (opcional)
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Clientes que atendem estas regras serão removidos
        </Typography>
      </Box>
      <RuleNode
        node={tree}
        onChange={handleChange}
        onRemove={null}
        depth={0}
        operadores={operadores}
        catalogoCampos={catalogoCampos}
        variant="exclusao"
      />
    </Paper>
  );
}