import React, { useState, useEffect } from 'react';
import { List, ListItemButton, ListItemText, Collapse, CircularProgress, Typography, Box } from '@mui/material';
import { ExpandLess, ExpandMore } from '@mui/icons-material';
import { useMetadataApi } from '../api/metadata';

export default function TemaMenu({ onSelectCampo }) {
  const { listarTemas, listarCampos, loading } = useMetadataApi();
  const [temas, setTemas] = useState([]);
  const [camposPorTema, setCamposPorTema] = useState({});
  const [expanded, setExpanded] = useState({});
  const [loaded, setLoaded] = useState(false); // flag para evitar recarga

  useEffect(() => {
    if (loaded) return; // já carregou, não recarrega

    const carregarTudo = async () => {
      try {
        const temasResponse = await listarTemas();
        const temasData = temasResponse.data || [];
        setTemas(temasData);

        const promises = temasData.map((tema) =>
          listarCampos(tema.tema).then((response) => ({
            tema: tema.tema,
            campos: response.data || [],
          }))
        );
        const resultados = await Promise.all(promises);
        const map = {};
        resultados.forEach(({ tema, campos }) => {
          map[tema] = campos;
        });
        setCamposPorTema(map);
        setLoaded(true);
      } catch (err) {
        console.error('Erro ao carregar temas/campos:', err);
      }
    };
    carregarTudo();
  }, [listarTemas, listarCampos, loaded]);

  const handleToggle = (tema) => {
    setExpanded((prev) => ({ ...prev, [tema]: !prev[tema] }));
  };

  if (loading && temas.length === 0) {
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
      {temas.map((tema) => {
        const campos = camposPorTema[tema.tema] || [];
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