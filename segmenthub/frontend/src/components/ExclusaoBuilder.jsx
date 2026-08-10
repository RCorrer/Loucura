import React from 'react';
import { Box, Button, Typography, Paper } from '@mui/material';
import RuleGroup from './RuleGroup';

const DEFAULT_OPERADORES = ['=', '!=', '>', '<', '>=', '<=', 'between', 'in', 'not_in', 'is_null', 'is_not_null'];

export default function ExclusaoBuilder({ value, onChange, operadores = DEFAULT_OPERADORES }) {
  const handleAddGroup = () => {
    const newGroups = [...value, { operator: 'OR', rules: [{ campo_id: '', op: '', value: '' }] }];
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
    <Paper sx={{ p: 2, mb: 3, border: '1px dashed #d32f2f' }}>
      <Typography variant="h6" sx={{ mb: 2, color: '#d32f2f' }}>
        Exclusão (opcional)
      </Typography>
      <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
        Clientes que atendem a estas regras serão removidos do segmento.
      </Typography>
      {value.map((group, index) => (
        <RuleGroup
          key={index}
          group={group}
          index={index}
          onUpdate={handleUpdateGroup}
          onRemove={handleRemoveGroup}
          operadores={operadores}  // ← passando para o grupo
        />
      ))}
      <Button variant="outlined" color="error" onClick={handleAddGroup} size="small">
        + Adicionar Grupo de Exclusão
      </Button>
    </Paper>
  );
}