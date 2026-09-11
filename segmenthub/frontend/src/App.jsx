import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AppShell } from '@shared';
import { UserProvider, useUser } from '@shared/hooks/useUser';
import ListAltIcon from '@mui/icons-material/ListAlt';
import AddIcon from '@mui/icons-material/Add';
import HealthAndSafetyIcon from '@mui/icons-material/HealthAndSafety';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import ChatIcon from '@mui/icons-material/Chat';
import BuilderSegmentacao from './pages/BuilderSegmentacao';
import ListaSegmentacoes from './pages/ListaSegmentacoes';
import DetalheSegmentacao from './pages/DetalheSegmentacao';
import TimelineSegmentacao from './pages/TimelineSegmentacao';
import DashboardSaude from './pages/DashboardSaude';
import NotificacoesPainel from './components/NotificacoesPainel';
import ChatSegmentacao from './pages/ChatSegmentacao';
import AdminCatalogo from './pages/AdminCatalogo';
import ErrorBoundary from './components/ErrorBoundary';

function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const { usuarioId, perfil, isAdmin, loading: userLoading } = useUser();

  // Verifica se a rota atual corresponde ao caminho do menu
  const isActive = (path) => location.pathname === path || location.pathname.startsWith(path + '/');

  // FX-03: Menu condicional por role — Admin Catálogo só para admin
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
    { divider: true },
    {
      text: 'Dashboard de Saúde',
      icon: <HealthAndSafetyIcon />,
      path: '/saude',
      onClick: () => navigate('/saude'),
    },
    // FX-03: Só admin vê Admin Catálogo
    ...(isAdmin ? [{
      text: 'Admin Catálogo',
      icon: <AdminPanelSettingsIcon />,
      path: '/admin/catalogo',
      onClick: () => navigate('/admin/catalogo'),
    }] : []),
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

  // FX-06: Nome real do usuário + badge do perfil
  const userDisplay = userLoading
    ? 'Carregando...'
    : usuarioId
      ? `${usuarioId.split('@')[0]} (${perfil || 'sem perfil'})`
      : 'Não autenticado';

  return (
    <AppShell
      title="SegmentHub"
      menuItems={menuItemsWithActive}
      user={userDisplay}
      headerActions={<NotificacoesPainel />}
    >
      <Routes>
        {/* Redirecionamento */}
        <Route path="/" element={<Navigate to="/segmentacoes" replace />} />

        {/* Segmentações */}
        <Route path="/segmentacoes" element={<ListaSegmentacoes />} />
        <Route path="/segmentacoes/nova" element={<BuilderSegmentacao />} />
        <Route path="/segmentacoes/:id/editar" element={<BuilderSegmentacao />} />

        {/* Detalhe, Timeline, Validação, Documentação */}
        <Route path="/segmentacoes/:id" element={<DetalheSegmentacao />} />
        <Route path="/segmentacoes/:id/timeline" element={<TimelineSegmentacao />} />
        <Route path="/segmentacoes/:id/validar" element={<DetalheSegmentacao />} />

        {/* Outras seções */}
        <Route path="/saude" element={<DashboardSaude />} />
        <Route path="/admin/catalogo" element={<AdminCatalogo />} />
        <Route path="/chat" element={<ChatSegmentacao />} />
      </Routes>
    </AppShell>
  );
}

export default function WrappedApp() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <UserProvider>
          <App />
        </UserProvider>
      </ErrorBoundary>
    </BrowserRouter>
  );
}