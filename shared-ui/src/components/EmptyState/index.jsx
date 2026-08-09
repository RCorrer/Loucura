import React from 'react';
import { Box, Typography, Button } from '@mui/material';

export default function EmptyState({ 
  title = 'Nenhum dado encontrado', 
  description, 
  icon, 
  actionText, 
  onAction 
}) {
  return (
    <Box sx={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center', 
      py: 8, 
      px: 2 
    }}>
      {icon && <Box sx={{ fontSize: 64, mb: 2 }}>{icon}</Box>}
      <Typography variant="h6" gutterBottom>{title}</Typography>
      {description && <Typography color="textSecondary" align="center">{description}</Typography>}
      {actionText && onAction && (
        <Button variant="contained" onClick={onAction} sx={{ mt: 3 }}>
          {actionText}
        </Button>
      )}
    </Box>
  );
}