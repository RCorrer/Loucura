import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppShell } from '@shared';
import Home from './pages/Home';

const menuItems = [
  { text: 'Início', icon: null, onClick: () => {} },
  { text: 'Carteira', icon: null, onClick: () => {} },
];

function App() {
  return (
    <BrowserRouter>
      <AppShell title="ClientView 360" menuItems={menuItems} user="Gerente">
        <Routes>
          <Route path="/" element={<Home />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}

export default App;
