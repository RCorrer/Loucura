import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from '@shared';
import ListaSegmentacoes from './pages/ListaSegmentacoes';
import { useNavigate } from 'react-router-dom';

function App() {
  const navigate = useNavigate();

  const menuItems = [
    { text: 'Segmentações', onClick: () => navigate('/segmentacoes'), icon: 'list' },
    // Futuramente: 'Dashboard de Saúde', 'Admin Catálogo', etc.
  ];

  return (
    <AppShell title="SegmentHub" menuItems={menuItems} user="Analista">
      <Routes>
        <Route path="/" element={<Navigate to="/segmentacoes" replace />} />
        <Route path="/segmentacoes" element={<ListaSegmentacoes />} />
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