import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AppShell } from '@shared';
import DashboardIcon from '@mui/icons-material/Dashboard';
import ListAltIcon from '@mui/icons-material/ListAlt';
import HealthAndSafetyIcon from '@mui/icons-material/HealthAndSafety';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import ChatIcon from '@mui/icons-material/Chat';
import { Divider } from '@mui/material';
import BuilderSegmentacao from './pages/BuilderSegmentacao';
import ListaSegmentacoes from './pages/ListaSegmentacoes';

function App() {
  const location = useLocation();
  const navigate = useNavigate();

  // Itens do menu com ícones e rota
  const menuItems = [
    {
      text: 'Segmentações',
      icon: <ListAltIcon />,
      path: '/segmentacoes',
      onClick: () => navigate('/segmentacoes'),
    },
    {
      text: 'Dashboard de Saúde',
      icon: <HealthAndSafetyIcon />,
      path: '/saude',
      onClick: () => navigate('/saude'),
    },
    {
      text: 'Admin Catálogo',
      icon: <AdminPanelSettingsIcon />,
      path: '/admin/catalogo',
      onClick: () => navigate('/admin/catalogo'),
    },
    {
      text: 'Chat',
      icon: <ChatIcon />,
      path: '/chat',
      onClick: () => navigate('/chat'),
    },
  ];

  // Verifica se a rota atual corresponde ao caminho do menu
  const isActive = (path) => location.pathname === path;

  // Envolve os itens em uma estrutura que o AppShell espera
  // (Se o AppShell esperar apenas { text, onClick, icon }, adaptamos)
  const menuItemsWithActive = menuItems.map((item) => ({
    ...item,
    active: isActive(item.path),
  }));

  return (
    <AppShell
      title="SegmentHub"
      menuItems={menuItemsWithActive}
      user="Analista"
    >
      <Routes>
        <Route path="/" element={<Navigate to="/segmentacoes" replace />} />
        <Route path="/segmentacoes" element={<ListaSegmentacoes />} />
        <Route path="/segmentacoes/nova" element={<BuilderSegmentacao />} />
        <Route path="/segmentacoes/:id/editar" element={<BuilderSegmentacao />} />
        {/* Futuras rotas */}
        <Route path="/saude" element={<div>Dashboard de Saúde</div>} />
        <Route path="/admin/catalogo" element={<div>Admin Catálogo</div>} />
        <Route path="/chat" element={<div>Chat</div>} />
      </Routes>
    </AppShell>
  );
}

export default function WrappedApp() {
  return (
    <BrowserRouter>
      <App />
    </BrowserRouter>
  );
}