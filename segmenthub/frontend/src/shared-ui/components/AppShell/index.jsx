import React from 'react';
import { Box, AppBar, Toolbar, Typography, IconButton, Drawer, List, ListItemButton, ListItemIcon, ListItemText, Divider } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import { tokens } from '../../theme/tokens';

const drawerWidth = 260;

export default function AppShell({ children, title, menuItems, user, headerActions }) {
  const [mobileOpen, setMobileOpen] = React.useState(false);

  const handleDrawerToggle = () => setMobileOpen(!mobileOpen);

  const drawer = (
    <Box>
      <Box sx={{ p: 2, borderBottom: '1px solid #EDEDED' }}>
        <Typography variant="h6" sx={{ color: tokens.brand.primary }}>
          {title}
        </Typography>
      </Box>
      <List>
        {menuItems.map((item, index) => {
          // Se for um divisor, renderiza <Divider />
          if (item.divider) {
            return <Divider key={`divider-${index}`} />;
          }
          return (
            <ListItemButton
              key={item.text}
              onClick={item.onClick}
              selected={item.active || false}
              sx={{
                '&.Mui-selected': {
                  backgroundColor: tokens.brand.primary,
                  color: '#fff',
                  '& .MuiListItemIcon-root': {
                    color: '#fff',
                  },
                },
                '&:hover': {
                  backgroundColor: tokens.brand.primary + '20',
                },
              }}
            >
              <ListItemIcon sx={{ color: item.active ? '#fff' : 'inherit' }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          );
        })}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <AppBar position="fixed" sx={{ zIndex: 1200, backgroundColor: tokens.brand.primary }}>
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap sx={{ flexGrow: 1 }}>
            {title}
          </Typography>
          {user && <Typography variant="body2">{user}</Typography>}
        </Toolbar>
      </AppBar>
      <Box component="nav" sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{ display: { xs: 'block', sm: 'none' } }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              width: drawerWidth,
              boxSizing: 'border-box',
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          p: 3,
          mt: 8,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          height: 'calc(100vh - 64px)',
          overflow: 'hidden',
        }}
      >
        {children}
      </Box>
    </Box>
  );
}