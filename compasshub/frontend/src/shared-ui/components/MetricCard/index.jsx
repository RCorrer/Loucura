import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';

export default function MetricCard({ 
  title, 
  value, 
  icon, 
  subtitle, 
  color = 'primary' 
}) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="subtitle2" color="textSecondary">{title}</Typography>
          {icon && <Box sx={{ color: `${color}.main` }}>{icon}</Box>}
        </Box>
        <Typography variant="h5" sx={{ mt: 1, fontWeight: 600 }}>
          {value ?? '-'}
        </Typography>
        {subtitle && <Typography variant="caption" color="textSecondary">{subtitle}</Typography>}
      </CardContent>
    </Card>
  );
}