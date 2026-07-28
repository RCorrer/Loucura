import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppShell } from '@shared';
import Home from './pages/Home';

const menuItems = [
  { text: 'Início', icon: null, onClick: () => {} },
  { text: 'Campanhas', icon: null, onClick: () => {} },
];

function App() {
  return (
    <BrowserRouter>
      <AppShell title="EngagementHub" menuItems={menuItems} user="Admin">
        <Routes>
          <Route path="/" element={<Home />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}

export default App;
