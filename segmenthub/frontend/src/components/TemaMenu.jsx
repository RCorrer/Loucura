import React, { useState, useEffect } from 'react';
import { List, ListItemButton, ListItemText, Collapse, CircularProgress, Typography, Box } from '@mui/material';
import { ExpandLess, ExpandMore } from '@mui/icons-material';
import { useMetadataApi } from '../api/metadata';

export default function TemaMenu({ onSelectCampo }) {
  const { listarTemasCompletos, loading } = useMetadataApi();
  const [temasCompletos, setTemasCompletos] = useState([]);
  const [expanded, setExpanded] = useState({});
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (loaded) return;

    const carregarTudo = async () => {
      try {
        const response = await listarTemasCompletos();
        setTemasCompletos(response.data || []);
        setLoaded(true);
      } catch (err) {
        console.error('Erro ao carregar temas/campos:', err);
      }
    };
    carregarTudo();
  }, [listarTemasCompletos, loaded]);

  const handleToggle = (tema) => {
    setExpanded((prev) => ({ ...prev, [tema]: !prev[tema] }));
  };

  if (loading && temasCompletos.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <List component="nav" sx={{ width: '100%', bgcolor: 'background.paper' }}>
      <Typography variant="subtitle2" sx={{ px: 2, py: 1, color: 'text.secondary' }}>
        Temas e Campos
      </Typography>
      {temasCompletos.map((tema) => {
        const campos = tema.campos || [];
        const isExpanded = expanded[tema.tema];
        return (
          <div key={tema.tema}>
            <ListItemButton onClick={() => handleToggle(tema.tema)}>
              <ListItemText primary={tema.tema} secondary={`Ordem: ${tema.tema_ordem}`} />
              {isExpanded ? <ExpandLess /> : <ExpandMore />}
            </ListItemButton>
            <Collapse in={isExpanded} timeout="auto" unmountOnExit>
              <List component="div" disablePadding>
                {campos.length > 0 ? (
                  campos.map((campo) => (
                    <ListItemButton
                      key={campo.caracteristica_id}
                      sx={{ pl: 4 }}
                      onClick={() => onSelectCampo(campo)}
                    >
                      <ListItemText
                        primary={campo.campo_label}
                        secondary={campo.tipo_dado}
                      />
                    </ListItemButton>
                  ))
                ) : (
                  <Typography variant="body2" sx={{ pl: 4, py: 1, color: 'text.secondary' }}>
                    Nenhum campo disponível
                  </Typography>
                )}
              </List>
            </Collapse>
          </div>
        );
      })}
    </List>
  );
}