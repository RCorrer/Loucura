import { useState, useEffect } from 'react';
import { useApi } from './useApi';

export function useNotifications() {
  const { request, loading } = useApi();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchNotifications = async (filter = null) => {
    try {
      const url = filter ? `/api/notificacoes?lida=${filter}` : '/api/notificacoes';
      const data = await request(url);
      setNotifications(data || []);
      setUnreadCount((data || []).filter(n => !n.lida).length);
    } catch (error) {
      console.error('Erro ao buscar notificações:', error);
    }
  };

  const markAsRead = async (notifId) => {
    try {
      await request(`/api/notificacoes/${notifId}/lida`, { method: 'PUT' });
      // Atualiza a lista
      await fetchNotifications();
    } catch (error) {
      console.error('Erro ao marcar como lida:', error);
    }
  };

  const markAllAsRead = async () => {
    const unread = notifications.filter(n => !n.lida);
    await Promise.all(unread.map(notif =>
      request(`/api/notificacoes/${notif.notif_id}/lida`, { method: 'PUT' })
    ));
    await fetchNotifications();
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  return {
    notifications,
    unreadCount,
    loading,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
  };
}