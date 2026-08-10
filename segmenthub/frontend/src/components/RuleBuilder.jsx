import React from 'react';
import { Box, Button, Typography, Paper } from '@mui/material';
import RuleGroup from './RuleGroup';

// Lista padrão de operadores
const DEFAULT_OPERADORES = ['=', '!=', '>', '<', '>=', '<=', 'between', 'in', 'not_in', 'is_null', 'is_not_null'];

export default function RuleBuilder({ value, onChange, operadores = DEFAULT_OPERADORES, label = 'Inclusão' }) {
  const handleAddGroup = () => {
    const newGroups = [...value, { operator: 'AND', rules: [{ campo_id: '', op: '', value: '' }] }];
    onChange(newGroups);
  };

  const handleUpdateGroup = (index, updatedGroup) => {
    const newGroups = [...value];
    newGroups[index] = updatedGroup;
    onChange(newGroups);
  };

  const handleRemoveGroup = (index) => {
    const newGroups = value.filter((_, i) => i !== index);
    onChange(newGroups);
  };

  return (
    <Paper sx={{ p: 2, mb: 3 }}>
      <Typography variant="h6" sx={{ mb: 2 }}>
        {label}
      </Typography>
      {value.length === 0 ? (
        <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
          Nenhuma regra definida. Clique em "Adicionar Grupo" para começar.
        </Typography>
      ) : (
        value.map((group, index) => (
          <RuleGroup
            key={index}
            group={group}
            index={index}
            onUpdate={handleUpdateGroup}
            onRemove={handleRemoveGroup}
            operadores={operadores}  // ← passando para o grupo
          />
        ))
      )}
      <Button variant="contained" onClick={handleAddGroup} size="small">
        + Adicionar Grupo
      </Button>
    </Paper>
  );
}