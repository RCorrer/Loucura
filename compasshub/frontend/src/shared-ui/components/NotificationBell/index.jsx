import React, { useState } from 'react';
import { IconButton, Badge, Menu, MenuItem, Typography, Box } from '@mui/material';
import NotificationsIcon from '@mui/icons-material/Notifications';

export default function NotificationBell({ 
  notifications = [], 
  onMarkAsRead, 
  onOpen 
}) {
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);

  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
    if (onOpen) onOpen();
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const unreadCount = notifications.filter(n => !n.lida).length;

  return (
    <>
      <IconButton onClick={handleClick} size="large">
        <Badge badgeContent={unreadCount} color="error">
          <NotificationsIcon />
        </Badge>
      </IconButton>
      <Menu anchorEl={anchorEl} open={open} onClose={handleClose} PaperProps={{ sx: { width: 360, maxHeight: 400 } }}>
        {notifications.length === 0 ? (
          <MenuItem disabled>Nenhuma notificação</MenuItem>
        ) : (
          notifications.map((notif, idx) => (
            <MenuItem key={notif.notif_id || idx} onClick={() => onMarkAsRead?.(notif.notif_id)}>
              <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                <Typography variant="body2" fontWeight={notif.lida ? 'normal' : 'bold'}>
                  {notif.titulo}
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  {notif.mensagem}
                </Typography>
              </Box>
            </MenuItem>
          ))
        )}
      </Menu>
    </>
  );
}