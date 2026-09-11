/**
 * ErrorBoundary — FX-08
 *
 * Captura erros de renderização em componentes filhos.
 * Sem error boundary, qualquer crash mata a app inteira.
 */
import React from 'react';
import { Box, Typography, Button, Paper, Alert } from '@mui/material';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error('[ErrorBoundary] Caught:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', p: 4 }}>
          <Paper sx={{ p: 4, maxWidth: 500, textAlign: 'center' }}>
            <ErrorOutlineIcon sx={{ fontSize: 64, color: 'error.main', mb: 2 }} />
            <Typography variant="h5" gutterBottom>Algo deu errado</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Ocorreu um erro inesperado nesta página.
            </Typography>
            {this.state.error && (
              <Alert severity="error" sx={{ mb: 2, textAlign: 'left' }}>
                {this.state.error.message || String(this.state.error)}
              </Alert>
            )}
            <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
              <Button variant="contained" onClick={this.handleReset}>
                Tentar novamente
              </Button>
              <Button variant="outlined" onClick={() => window.location.href = '/segmentacoes'}>
                Voltar ao início
              </Button>
            </Box>
          </Paper>
        </Box>
      );
    }

    return this.props.children;
  }
}
