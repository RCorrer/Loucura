import React, { useState, useEffect } from 'react';
import { FormControl, InputLabel, Select, MenuItem, FormHelperText, CircularProgress } from '@mui/material';
import { useMetadataApi } from '../api/metadata';

export default function PublicoSelector({ value, onChange, error, helperText }) {
  const { listarPublicos, loading } = useMetadataApi();
  const [publicos, setPublicos] = useState([]);
  const [carregado, setCarregado] = useState(false);

  useEffect(() => {
    const carregar = async () => {
      try {
        const response = await listarPublicos();
        setPublicos(response.data || []);
      } catch (err) {
        console.error('Erro ao carregar públicos:', err);
      } finally {
        setCarregado(true);
      }
    };
    carregar();
  }, [listarPublicos]);

  return (
    <FormControl fullWidth error={!!error}>
      <InputLabel id="publico-select-label">Público Base</InputLabel>
      <Select
        labelId="publico-select-label"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        label="Público Base"
        disabled={loading || !carregado}
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
      {(loading || !carregado) && <CircularProgress size={20} sx={{ ml: 2, position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)' }} />}
      {helperText && <FormHelperText>{helperText}</FormHelperText>}
    </FormControl>
  );
}