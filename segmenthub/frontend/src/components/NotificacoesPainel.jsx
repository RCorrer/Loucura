import React, { useState, useEffect, useRef } from 'react';
import {
  IconButton,
  Badge,
  Popover,
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Button,
  Chip,
  CircularProgress,
} from '@mui/material';
import NotificationsIcon from '@mui/icons-material/Notifications';
import CommentIcon from '@mui/icons-material/Comment';
import WarningIcon from '@mui/icons-material/Warning';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz';
import AlternateEmailIcon from '@mui/icons-material/AlternateEmail';
import DoneAllIcon from '@mui/icons-material/DoneAll';
import { useNotifications } from '@shared/hooks/useNotifications';

const POLL_INTERVAL_MS = 30000; // 30s

const TIPO_ICON = {
  mencao: <AlternateEmailIcon fontSize="small" color="primary" />,
  saude: <WarningIcon fontSize="small" color="warning" />,
  estado: <SwapHorizIcon fontSize="small" color="info" />,
  comentario: <CommentIcon fontSize="small" color="secondary" />,
};

/**
 * NotificacoesPainel — S1-FRONT-08
 *
 * Sininho global de notificações com painel popover.
 * Usa useNotifications do shared-ui (GET /api/notificacoes, PUT /{id}/lida).
 * Adiciona polling a cada 30s para atualizar badge.
 *
 * Integrar diretamente no App.jsx (shell).
 */
export default function NotificacoesPainel() {
  const {
    notifications,
    unreadCount,
    loading,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
  } = useNotifications();

  const [anchorEl, setAnchorEl] = useState(null);
  const intervalRef = useRef(null);
  const fetchRef = useRef(fetchNotifications);

  // Mantém ref atualizada sem re-disparar effect
  useEffect(() => {
    fetchRef.current = fetchNotifications;
  });

  // Polling estável (dep array vazio — não reseta a cada render)
  useEffect(() => {
    intervalRef.current = setInterval(() => {
      fetchRef.current();
    }, POLL_INTERVAL_MS);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const handleOpen = (event) => {
    setAnchorEl(event.currentTarget);
    fetchNotifications(); // refresh ao abrir
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleMarkRead = async (notifId) => {
    await markAsRead(notifId);
  };

  const handleMarkAllRead = async () => {
    await markAllAsRead();
  };

  const open = Boolean(anchorEl);

  const formatData = (dateStr) => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleString('pt-BR', {
      day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
    });
  };

  return (
    <>
      <IconButton onClick={handleOpen} size="large" sx={{ color: 'inherit' }}>
        <Badge badgeContent={unreadCount} color="error" max={99}>
          <NotificationsIcon />
        </Badge>
      </IconButton>

      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        PaperProps={{ sx: { width: 380, maxHeight: 480 } }}
      >
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', p: 2, pb: 1 }}>
          <Typography variant="subtitle1" fontWeight="bold">
            Notificações
          </Typography>
          {unreadCount > 0 && (
            <Button
              size="small"
              startIcon={<DoneAllIcon />}
              onClick={handleMarkAllRead}
            >
              Marcar todas como lidas
            </Button>
          )}
        </Box>

        <Divider />

        {/* Lista */}
        {loading && notifications.length === 0 ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
            <CircularProgress size={24} />
          </Box>
        ) : notifications.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <NotificationsIcon sx={{ fontSize: 40, color: 'text.disabled' }} />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Nenhuma notificação
            </Typography>
          </Box>
        ) : (
          <List dense sx={{ maxHeight: 360, overflow: 'auto' }}>
            {notifications.map((notif) => (
              <ListItem
                key={notif.notif_id}
                onClick={() => !notif.lida && handleMarkRead(notif.notif_id)}
                sx={{
                  cursor: notif.lida ? 'default' : 'pointer',
                  bgcolor: notif.lida ? 'transparent' : 'action.hover',
                  '&:hover': { bgcolor: 'action.selected' },
                }}
                secondaryAction={
                  !notif.lida && (
                    <Chip label="Nova" size="small" color="error" sx={{ height: 18, fontSize: '0.65rem' }} />
                  )
                }
              >
                <ListItemIcon sx={{ minWidth: 32 }}>
                  {TIPO_ICON[notif.tipo] || TIPO_ICON.estado}
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Typography
                      variant="body2"
                      fontWeight={notif.lida ? 'normal' : 'bold'}
                      noWrap
                    >
                      {notif.titulo || notif.mensagem || 'Notificação'}
                    </Typography>
                  }
                  secondary={
                    <Box component="span" sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="caption" color="text.secondary" noWrap sx={{ maxWidth: 200 }}>
                        {notif.mensagem || ''}
                      </Typography>
                      <Typography variant="caption" color="text.disabled">
                        {formatData(notif.criado_em)}
                      </Typography>
                    </Box>
                  }
                />
              </ListItem>
            ))}
          </List>
        )}
      </Popover>
    </>
  );
}
