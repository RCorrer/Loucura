import React from 'react';
import { Box, Button, Select, MenuItem, FormControl, InputLabel, Paper } from '@mui/material';
import RuleRow from './RuleRow';

export default function RuleGroup({ group, index, onUpdate, onRemove, operadores = [] }) {
  // Se operadores estiver vazio, use uma lista padrão
  const ops = operadores.length > 0 ? operadores : ['=', '!=', '>', '<', '>=', '<=', 'between', 'in', 'not_in', 'is_null', 'is_not_null'];

  const handleAddRule = () => {
    const newRules = [...group.rules, { campo_id: '', op: '', value: '' }];
    onUpdate(index, { ...group, rules: newRules });
  };

  const handleUpdateRule = (ruleIndex, updatedRule) => {
    const newRules = [...group.rules];
    newRules[ruleIndex] = updatedRule;
    onUpdate(index, { ...group, rules: newRules });
  };

  const handleRemoveRule = (ruleIndex) => {
    const newRules = group.rules.filter((_, i) => i !== ruleIndex);
    onUpdate(index, { ...group, rules: newRules });
  };

  return (
    <Paper sx={{ p: 2, mb: 2, border: '1px solid #e0e0e0' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
        <FormControl size="small" sx={{ minWidth: 100 }}>
          <InputLabel>Operador</InputLabel>
          <Select
            value={group.operator || 'AND'}
            onChange={(e) => onUpdate(index, { ...group, operator: e.target.value })}
            label="Operador"
          >
            <MenuItem value="AND">AND</MenuItem>
            <MenuItem value="OR">OR</MenuItem>
          </Select>
        </FormControl>
        <Button variant="outlined" size="small" onClick={handleAddRule}>
          + Adicionar Regra
        </Button>
        {index > 0 && (
          <Button variant="outlined" size="small" color="error" onClick={() => onRemove(index)}>
            Remover Grupo
          </Button>
        )}
      </Box>

      {group.rules.map((rule, ruleIndex) => (
        <RuleRow
          key={ruleIndex}
          rule={rule}
          index={ruleIndex}
          onUpdate={handleUpdateRule}
          onRemove={handleRemoveRule}
          operadores={ops}  // ← passando a lista com fallback
        />
      ))}
    </Paper>
  );
}