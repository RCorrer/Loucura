import React from 'react';
import { DataGrid } from '@mui/x-data-grid';
import { ptBR } from '@mui/x-data-grid/locales';
import { Box } from '@mui/material';

export default function DataTable({
  rows,
  columns,
  loading,
  onRowClick,
  pageSize = 10,
  pagination = true,
  hideFooterPagination = false,
  getRowId,
  rowCount,
  paginationModel,
  onPaginationModelChange,
  ...props
}) {
  return (
    <Box sx={{ height: '100%', width: '100%' }}>
      <DataGrid
        rows={rows}
        columns={columns}
        rowCount={rowCount}
        loading={loading}
        onRowClick={onRowClick}
        pagination={pagination}
        hideFooterPagination={hideFooterPagination}
        getRowId={getRowId}
        paginationModel={paginationModel}
        onPaginationModelChange={onPaginationModelChange}
        paginationMode="server"   // <-- ESSENCIAL
        pageSizeOptions={[5, 10, 25, 50]}
        disableRowSelectionOnClick
        localeText={ptBR.components.MuiDataGrid.defaultProps.localeText}
        {...props}
      />
    </Box>
  );
}