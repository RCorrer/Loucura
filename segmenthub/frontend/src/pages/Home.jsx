import React, { useState, useEffect } from 'react';
import { PageHeader } from '@shared';
import { Typography, Box, CircularProgress, Alert, List, ListItem, ListItemText } from '@mui/material';

export default function Home() {
  const [temas, setTemas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/api/metadata/temas')
      .then(res => {
        if (!res.ok) throw new Error('Erro ao carregar temas');
        return res.json();
      })
      .then(data => {
        setTemas(data.data || []);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Bem-vindo ao SegmentHub" />
      <Box sx={{ mt: 2 }}>
        <Typography variant="h6">Temas disponíveis no catálogo:</Typography>
        {loading && <CircularProgress />}
        {error && <Alert severity="error">{error}</Alert>}
        {!loading && !error && (
          <List>
            {temas.map((tema, idx) => (
              <ListItem key={idx}>
                <ListItemText primary={tema.tema} secondary={`Ordem: ${tema.tema_ordem}`} />
              </ListItem>
            ))}
          </List>
        )}
        {!loading && !error && temas.length === 0 && (
          <Typography>Nenhum tema encontrado.</Typography>
        )}
      </Box>
    </>
  );
}