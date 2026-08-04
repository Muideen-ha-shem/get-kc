import { ReactNode, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiJson } from '../../lib/apiClient';

/** Wraps every /admin/* page: calls GET /admin/me on mount (a cheap
 * 403-probe) and shows a fallback if the signed-in user isn't a platform
 * admin — mirrors AgentDashboardPage.tsx's notAnAgent pattern exactly. */
export function AdminGuard({ children }: { children: ReactNode }) {
  const [state, setState] = useState<'loading' | 'ok' | 'forbidden'>('loading');

  useEffect(() => {
    apiJson('/admin/me')
      .then(() => setState('ok'))
      .catch(() => setState('forbidden'));
  }, []);

  if (state === 'loading') {
    return <div className="min-h-screen flex items-center justify-center">Loading…</div>;
  }

  if (state === 'forbidden') {
    return (
      <div className="min-h-screen flex items-center justify-center text-center p-8">
        <div>
          <p className="text-lg font-medium">You're not a platform admin.</p>
          <Link to="/" className="text-blue-600 underline">
            Back to HavisIQ
          </Link>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
