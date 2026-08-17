import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
} from '@mui/material';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';

const SEVERITY_CONFIG = {
  warning: { icon: WarningAmberIcon, color: 'warning.main', confirmColor: 'warning' },
  error: { icon: ErrorOutlineIcon, color: 'error.main', confirmColor: 'error' },
  info: { icon: InfoOutlinedIcon, color: 'info.main', confirmColor: 'primary' },
};

/**
 * ConfirmDialog — Componente reutilizável de confirmação.
 *
 * Props:
 *   - open: bool
 *   - onClose: () => void
 *   - onConfirm: () => void
 *   - title: string
 *   - message: string (ou ReactNode)
 *   - severity: 'warning' | 'error' | 'info' (default: 'warning')
 *   - confirmText: string (default: 'Confirmar')
 *   - cancelText: string (default: 'Cancelar')
 *   - loading: bool (default: false)
 */
export default function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title = 'Confirmar ação',
  message = 'Tem certeza que deseja continuar?',
  severity = 'warning',
  confirmText = 'Confirmar',
  cancelText = 'Cancelar',
  loading = false,
}) {
  const config = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.warning;
  const Icon = config.icon;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Icon sx={{ color: config.color }} />
        {title}
      </DialogTitle>
      <DialogContent>
        <Typography variant="body1" color="text.secondary">
          {message}
        </Typography>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={loading}>
          {cancelText}
        </Button>
        <Button
          variant="contained"
          color={config.confirmColor}
          onClick={onConfirm}
          disabled={loading}
        >
          {loading ? 'Processando...' : confirmText}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
