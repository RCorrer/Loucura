/**
 * TableSkeleton — FX-14
 *
 * Skeleton loader reutilizável para tabelas e grids.
 * Substitui CircularProgress central por algo visualmente informativo.
 */
import React from 'react';
import { Box, Skeleton, Paper } from '@mui/material';

/**
 * TableSkeleton — simula uma tabela sendo carregada
 * @param {number} rows — número de linhas skeleton (default: 5)
 * @param {number} cols — número de colunas (default: 5)
 * @param {boolean} withHeader — mostra header skeleton (default: true)
 * @param {boolean} withCards — mostra cards métrica no topo (default: false)
 * @param {number} cardCount — quantos cards (default: 4)
 */
export default function TableSkeleton({
  rows = 5,
  cols = 5,
  withHeader = true,
  withCards = false,
  cardCount = 4,
}) {
  return (
    <Box>
      {/* Cards skeleton */}
      {withCards && (
        <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
          {Array.from({ length: cardCount }).map((_, i) => (
            <Paper key={i} sx={{ p: 2, flex: 1, textAlign: 'center' }}>
              <Skeleton variant="text" width="60%" sx={{ mx: 'auto', mb: 1 }} />
              <Skeleton variant="rectangular" height={32} width="40%" sx={{ mx: 'auto' }} />
            </Paper>
          ))}
        </Box>
      )}

      {/* Header skeleton */}
      {withHeader && (
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          {Array.from({ length: Math.min(cols, 3) }).map((_, i) => (
            <Skeleton key={i} variant="rounded" width={i === 0 ? 200 : 120} height={36} />
          ))}
        </Box>
      )}

      {/* Table skeleton */}
      <Paper sx={{ overflow: 'hidden' }}>
        {/* Header row */}
        <Box sx={{ display: 'flex', gap: 1, p: 1.5, bgcolor: 'action.hover' }}>
          {Array.from({ length: cols }).map((_, i) => (
            <Skeleton key={i} variant="text" sx={{ flex: i === 1 ? 2 : 1 }} />
          ))}
        </Box>
        {/* Data rows */}
        {Array.from({ length: rows }).map((_, rowIdx) => (
          <Box key={rowIdx} sx={{ display: 'flex', gap: 1, p: 1.5, borderTop: '1px solid', borderColor: 'divider' }}>
            {Array.from({ length: cols }).map((_, colIdx) => (
              <Skeleton
                key={colIdx}
                variant="text"
                sx={{ flex: colIdx === 1 ? 2 : 1 }}
                animation="wave"
              />
            ))}
          </Box>
        ))}
      </Paper>
    </Box>
  );
}
