import React from 'react';
import { Box, Typography, Breadcrumbs, Link } from '@mui/material';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';

export default function PageHeader({ title, subtitle, breadcrumbs }) {
  return (
    <Box sx={{ mb: 3 }}>
      {breadcrumbs && (
        <Breadcrumbs separator={<NavigateNextIcon fontSize="small" />} sx={{ mb: 1 }}>
          {breadcrumbs.map((item, idx) => (
            <Link key={idx} color={idx === breadcrumbs.length - 1 ? 'textPrimary' : 'inherit'} href={item.href} underline="hover">
              {item.label}
            </Link>
          ))}
        </Breadcrumbs>
      )}
      <Typography variant="h4" component="h1">{title}</Typography>
      {subtitle && <Typography variant="subtitle1" color="textSecondary">{subtitle}</Typography>}
    </Box>
  );
}
