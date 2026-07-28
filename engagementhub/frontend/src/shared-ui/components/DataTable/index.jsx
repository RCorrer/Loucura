import React from 'react';
import { DataGrid } from '@mui/x-data-grid';
import { Box } from '@mui/material';

export default function DataTable({ rows, columns, loading, onRowClick, pageSize = 10 }) {
  return (
    <Box sx={{ height: 400, width: '100%' }}>
      <DataGrid
        rows={rows}
        columns={columns}
        loading={loading}
        onRowClick={onRowClick}
        initialState={{ pagination: { paginationModel: { pageSize } } }}
        pageSizeOptions={[5, 10, 25, 50]}
        disableRowSelectionOnClick
      />
    </Box>
  );
}
