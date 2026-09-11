/**
 * AppBreadcrumbs — FX-13
 *
 * Breadcrumbs automáticos baseados na rota atual.
 * Mapeamento de segmentos de URL para labels legíveis.
 */
import React from 'react';
import { useLocation, Link as RouterLink } from 'react-router-dom';
import { Breadcrumbs, Link, Typography } from '@mui/material';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import HomeIcon from '@mui/icons-material/Home';

const ROUTE_LABELS = {
  segmentacoes: 'Segmentações',
  nova: 'Nova',
  editar: 'Editar',
  timeline: 'Timeline',
  validar: 'Validar',
  saude: 'Dashboard de Saúde',
  admin: 'Admin',
  catalogo: 'Catálogo',
  chat: 'Chat',
};

// Detecta UUIDs (segmentos com 8+ chars hex/hífen)
const isUuid = (s) => /^[0-9a-f]{8,}(-[0-9a-f]+)*$/i.test(s);

export default function AppBreadcrumbs({ segName }) {
  const location = useLocation();
  const segments = location.pathname.split('/').filter(Boolean);

  if (segments.length <= 1) return null; // Não mostrar na home/lista

  const crumbs = [];
  let path = '';

  segments.forEach((seg, idx) => {
    path += `/${seg}`;
    const isLast = idx === segments.length - 1;
    let label;

    if (isUuid(seg)) {
      label = segName || `${seg.slice(0, 8)}...`;
    } else {
      label = ROUTE_LABELS[seg] || seg.charAt(0).toUpperCase() + seg.slice(1);
    }

    crumbs.push({ label, path, isLast });
  });

  return (
    <Breadcrumbs
      separator={<NavigateNextIcon fontSize="small" />}
      sx={{ mb: 1.5 }}
      aria-label="breadcrumb"
    >
      <Link
        component={RouterLink}
        to="/segmentacoes"
        sx={{ display: 'flex', alignItems: 'center', gap: 0.3 }}
        color="inherit"
        underline="hover"
      >
        <HomeIcon fontSize="small" /> Início
      </Link>
      {crumbs.map(({ label, path: p, isLast }) =>
        isLast ? (
          <Typography key={p} variant="body2" color="text.primary" fontWeight="medium">
            {label}
          </Typography>
        ) : (
          <Link key={p} component={RouterLink} to={p} color="inherit" underline="hover" variant="body2">
            {label}
          </Link>
        )
      )}
    </Breadcrumbs>
  );
}
