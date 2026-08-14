import { useState, useCallback } from 'react';

export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const request = useCallback(async (url, options = {}) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(url, {
        ...options,
        headers: { 'Content-Type': 'application/json', ...options.headers },
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        const detail = errData.detail;
        const msg = typeof detail === 'string'
          ? detail
          : typeof detail === 'object' && detail !== null
            ? (detail.erros || detail.message || JSON.stringify(detail))
            : `Erro ${response.status}`;
        const error = new Error(msg);
        error.status = response.status;
        error.data = errData;
        throw error;
      }
      return await response.json();
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { request, loading, error };
}
