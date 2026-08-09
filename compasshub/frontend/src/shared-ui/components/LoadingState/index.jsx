import React from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';

export default function LoadingState({ message = 'Carregando...' }) {
  return (
    <Box sx={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center', 
      py: 8 
    }}>
      <CircularProgress />
      <Typography variant="body2" color="textSecondary" sx={{ mt: 2 }}>
        {message}
      </Typography>
    </Box>
  );
}