import React, { useState, useEffect } from 'react';
import { List, ListItemButton, ListItemText, Collapse, CircularProgress, Typography, Box } from '@mui/material';
import { ExpandLess, ExpandMore } from '@mui/icons-material';
import { useMetadataApi } from '../api/metadata';

export default function TemaMenu({ onSelectCampo }) {
  const { listarTemas, listarCampos, loading } = useMetadataApi();
  const [temas, setTemas] = useState([]);
  const [camposPorTema, setCamposPorTema] = useState({});
  const [expanded, setExpanded] = useState({});
  const [carregandoCampos, setCarregandoCampos] = useState(false);

  // Carrega temas e, em paralelo, os campos de cada tema
  useEffect(() => {
    const carregarTudo = async () => {
      try {
        const responseTemas = await listarTemas();
        const temasData = responseTemas.data || [];
        setTemas(temasData);

        // Pré-carregar campos de todos os temas em paralelo
        setCarregandoCampos(true);
        const promises = temasData.map(tema => listarCampos(tema.tema));
        const resultados = await Promise.all(promises);
        const camposMap = {};
        temasData.forEach((tema, index) => {
          camposMap[tema.tema] = resultados[index].data || [];
        });
        setCamposPorTema(camposMap);
      } catch (err) {
        console.error('Erro ao carregar temas ou campos:', err);
      } finally {
        setCarregandoCampos(false);
      }
    };
    carregarTudo();
  }, [listarTemas, listarCampos]);

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
        {carregandoCampos && <CircularProgress size={16} sx={{ ml: 1 }} />}
      </Typography>
      {temas.map((tema) => (
        <div key={tema.tema}>
          <ListItemButton onClick={() => handleToggle(tema.tema)}>
            <ListItemText primary={tema.tema} secondary={`Ordem: ${tema.tema_ordem}`} />
            {expanded[tema.tema] ? <ExpandLess /> : <ExpandMore />}
          </ListItemButton>
          <Collapse in={expanded[tema.tema]} timeout="auto" unmountOnExit>
            <List component="div" disablePadding>
              {camposPorTema[tema.tema]?.length > 0 ? (
                camposPorTema[tema.tema].map((campo) => (
                  <ListItemButton
                    key={campo.caracteristica_id}
                    sx={{ pl: 4 }}
                    onClick={() => onSelectCampo(campo)}
                  >
                    <ListItemText
                      primary={campo.campo_label}
                      secondary={campo.tipo_dado} // sem cadeado
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
      ))}
    </List>
  );
}