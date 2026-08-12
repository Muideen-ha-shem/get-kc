import { useEffect, useState } from 'react';

/**
 * Persists sidebar collapse state per-shell (a distinct storageKey per page)
 * so a user's Dashboard vs Admin-portal collapse preference don't fight
 * each other.
 */
export function useSidebarCollapse(storageKey: string) {
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(storageKey) === '1');

  useEffect(() => {
    localStorage.setItem(storageKey, collapsed ? '1' : '0');
  }, [collapsed, storageKey]);

  return [collapsed, setCollapsed] as const;
}
