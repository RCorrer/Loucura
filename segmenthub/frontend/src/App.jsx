import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AppShell } from '@shared';
import ListAltIcon from '@mui/icons-material/ListAlt';
import AddIcon from '@mui/icons-material/Add';
import HealthAndSafetyIcon from '@mui/icons-material/HealthAndSafety';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import ChatIcon from '@mui/icons-material/Chat';
import { Divider } from '@mui/material';
import BuilderSegmentacao from './pages/BuilderSegmentacao';
import ListaSegmentacoes from './pages/ListaSegmentacoes';
import DocumentacaoSegmentacao from './pages/DocumentacaoSegmentacao';
import DetalheSegmentacao from './pages/DetalheSegmentacao';
import TimelineSegmentacao from './pages/TimelineSegmentacao';
import DashboardSaude from './pages/DashboardSaude';
import NotificacoesPainel from './components/NotificacoesPainel';

function App() {
  const location = useLocation();
  const navigate = useNavigate();

  // Verifica se a rota atual corresponde ao caminho do menu
  const isActive = (path) => location.pathname === path || location.pathname.startsWith(path + '/');

  // Itens do menu com ícones e rota
  const menuItems = [
    {
      text: 'Segmentações',
      icon: <ListAltIcon />,
      path: '/segmentacoes',
      onClick: () => navigate('/segmentacoes'),
    },
    {
      text: 'Nova Segmentação',
      icon: <AddIcon />,
      path: '/segmentacoes/nova',
      onClick: () => navigate('/segmentacoes/nova'),
    },
    { divider: true }, // linha separadora
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

  // Adiciona a propriedade active para destacar o item atual
  const menuItemsWithActive = menuItems.map((item) => {
    if (item.divider) return item;
    return {
      ...item,
      active: isActive(item.path),
    };
  });

  return (
    <AppShell
      title="SegmentHub"
      menuItems={menuItemsWithActive}
      user="Analista"
    >
      <Routes>
        {/* Redirecionamento */}
        <Route path="/" element={<Navigate to="/segmentacoes" replace />} />

        {/* Segmentações */}
        <Route path="/segmentacoes" element={<ListaSegmentacoes />} />
        <Route path="/segmentacoes/nova" element={<BuilderSegmentacao />} />
        <Route path="/segmentacoes/:id/editar" element={<BuilderSegmentacao />} />

        {/* Futuras rotas (placeholders para desenvolvimento) */}
        <Route path="/segmentacoes/:id" element={<div>Detalhe da Segmentação (em breve)</div>} />
        <Route path="/segmentacoes/:id/timeline" element={<div>Timeline (em breve)</div>} />
        <Route path="/segmentacoes/:id/validar" element={<div>Validação (em breve)</div>} />
        <Route path="/segmentacoes/:id/documentacao" element={<div>Documentação (em breve)</div>} />

        {/* Outras seções */}
        <Route path="/saude" element={<div>Dashboard de Saúde (em breve)</div>} />
        <Route path="/admin/catalogo" element={<div>Admin Catálogo (em breve)</div>} />
        <Route path="/chat" element={<div>Chat (em breve)</div>} />
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