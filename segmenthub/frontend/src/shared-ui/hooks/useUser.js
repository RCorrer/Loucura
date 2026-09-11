/**
 * useUser — FX-02
 *
 * React Context + hook para identidade do usuário.
 * Chama GET /api/me no mount e distribui {usuario_id, perfil} via context.
 * Usado por AppShell (nome real), route guards (role), e menus condicionais.
 */
import React, { createContext, useContext, useState, useEffect } from 'react';
import { useApi } from './useApi';

const UserContext = createContext({ user: null, loading: true, isAdmin: false, isAnalista: false });

export function UserProvider({ children }) {
  const { request } = useApi();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const data = await request('/api/me');
        setUser(data?.user || null);
      } catch (err) {
        console.warn('[useUser] Falha ao buscar /api/me:', err?.message);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    fetchUser();
  }, []);

  const value = {
    user,
    loading,
    isAdmin: user?.perfil === 'admin',
    isAnalista: user?.perfil === 'analista',
    perfil: user?.perfil || null,
    usuarioId: user?.usuario_id || null,
  };

  return (
    <UserContext.Provider value={value}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}
