import { createTheme } from '@mui/material/styles';
import { palette } from './palette';
import { typography } from './typography';
import { tokens } from './tokens';

const theme = createTheme({
  palette,
  typography,
  shape: { borderRadius: tokens.radius.md },
  spacing: (factor) => tokens.spacing * factor,
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          fontWeight: 600,
          borderRadius: tokens.radius.md,
          textTransform: 'none',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: tokens.radius.lg,
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
        },
      },
    },
    MuiDataGrid: {
      styleOverrides: {
        root: {
          border: 'none',
          '& .MuiDataGrid-cell': {
            borderBottom: '1px solid #EDEDED',
          },
        },
      },
    },
  },
});

export default theme;
