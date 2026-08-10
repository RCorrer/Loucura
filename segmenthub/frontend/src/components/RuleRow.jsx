import React from 'react';
import { Box, TextField, Select, MenuItem, IconButton, FormControl, InputLabel } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';

const DEFAULT_OPERADORES = ['=', '!=', '>', '<', '>=', '<=', 'between', 'in', 'not_in', 'is_null', 'is_not_null'];

export default function RuleRow({ rule, index, onUpdate, onRemove, operadores = DEFAULT_OPERADORES }) {
  const handleChange = (field, value) => {
    onUpdate(index, { ...rule, [field]: value });
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
      <TextField
        size="small"
        label="Campo"
        value={rule.campo_id || ''}
        onChange={(e) => handleChange('campo_id', e.target.value)}
        sx={{ flex: 2 }}
      />
      <FormControl size="small" sx={{ flex: 1 }}>
        <InputLabel>Operador</InputLabel>
        <Select
          value={rule.op || ''}
          onChange={(e) => handleChange('op', e.target.value)}
          label="Operador"
        >
          {operadores.map((op) => (
            <MenuItem key={op} value={op}>
              {op}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <TextField
        size="small"
        label="Valor"
        value={rule.value || ''}
        onChange={(e) => handleChange('value', e.target.value)}
        sx={{ flex: 1 }}
      />
      <IconButton size="small" onClick={() => onRemove(index)} color="error">
        <DeleteIcon fontSize="small" />
      </IconButton>
    </Box>
  );
}