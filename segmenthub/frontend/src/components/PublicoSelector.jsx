import React, { useState, useEffect } from 'react';
import { FormControl, InputLabel, Select, MenuItem, FormHelperText, CircularProgress } from '@mui/material';
import { useMetadataApi } from '../api/metadata';

export default function PublicoSelector({ value, onChange, error, helperText }) {
  const { listarPublicos, loading } = useMetadataApi();
  const [publicos, setPublicos] = useState([]);

  useEffect(() => {
    const carregar = async () => {
      try {
        const response = await listarPublicos();
        setPublicos(response.data || []);
      } catch (err) {
        console.error('Erro ao carregar públicos:', err);
      }
    };
    carregar();
  }, []);

  return (
    <FormControl fullWidth error={!!error}>
      <InputLabel id="publico-select-label">Público Base</InputLabel>
      <Select
        labelId="publico-select-label"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        label="Público Base"
        disabled={loading}
      >
        <MenuItem value="">
          <em>Selecione um público</em>
        </MenuItem>
        {publicos.map((pub) => (
          <MenuItem key={pub.publico_id} value={pub.publico_id}>
            {pub.nome} {pub.descricao && `- ${pub.descricao}`}
          </MenuItem>
        ))}
      </Select>
      {loading && <CircularProgress size={20} sx={{ ml: 2 }} />}
      {helperText && <FormHelperText>{helperText}</FormHelperText>}
    </FormControl>
  );
}