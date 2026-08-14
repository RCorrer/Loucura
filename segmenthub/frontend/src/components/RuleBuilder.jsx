import React from 'react';
import { Box, Button, Typography, Paper, Chip } from '@mui/material';
import RuleGroup from './RuleGroup';

const DEFAULT_OPERADORES = ['=', '!=', '>', '<', '>=', '<=', 'between', 'in', 'not_in', 'is_null', 'is_not_null'];

/**
 * RuleBuilder com suporte a operador inter-grupo (AND/OR entre grupos).
 * Props:
 *   - value: array de grupos [{operator, rules}, ...]
 *   - onChange: callback para atualizar grupos
 *   - interGroupOperator: 'AND' | 'OR' — como os grupos se relacionam entre si
 *   - onInterGroupOperatorChange: callback para trocar o operador inter-grupo
 */
export default function RuleBuilder({
  value,
  onChange,
  operadores = DEFAULT_OPERADORES,
  label = 'Inclusão',
  interGroupOperator = 'OR',
  onInterGroupOperatorChange,
}) {
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

  const toggleInterGroupOperator = () => {
    if (onInterGroupOperatorChange) {
      onInterGroupOperatorChange(interGroupOperator === 'AND' ? 'OR' : 'AND');
    }
  };

  return (
    <Paper sx={{ p: 2, mb: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6">
          {label}
        </Typography>
        {value.length > 1 && (
          <Typography variant="caption" color="textSecondary">
            Grupos conectados por: <strong>{interGroupOperator}</strong>
          </Typography>
        )}
      </Box>
      {value.length === 0 ? (
        <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
          Nenhuma regra definida. Clique em "Adicionar Grupo" para começar.
        </Typography>
      ) : (
        value.map((group, index) => (
          <React.Fragment key={index}>
            <RuleGroup
              group={group}
              index={index}
              onUpdate={handleUpdateGroup}
              onRemove={handleRemoveGroup}
              operadores={operadores}
            />
            {/* Conector inter-grupo entre os cards */}
            {index < value.length - 1 && (
              <Box sx={{ display: 'flex', justifyContent: 'center', my: 1 }}>
                <Chip
                  label={interGroupOperator}
                  color={interGroupOperator === 'OR' ? 'warning' : 'primary'}
                  size="small"
                  onClick={toggleInterGroupOperator}
                  sx={{ cursor: 'pointer', fontWeight: 'bold', minWidth: 50 }}
                  title="Clique para alternar AND/OR entre grupos"
                />
              </Box>
            )}
          </React.Fragment>
        ))
      )}
      <Button variant="contained" onClick={handleAddGroup} size="small">
        + Adicionar Grupo
      </Button>
    </Paper>
  );
}