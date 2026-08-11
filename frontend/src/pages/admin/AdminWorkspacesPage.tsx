import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiJson } from '../../lib/apiClient';
import { AdminGuard } from './AdminGuard';
import { AdminLayout } from './AdminLayout';
import type { WorkspaceAdmin } from './adminTypes';

function AdminWorkspacesContent() {
  const [workspaces, setWorkspaces] = useState<WorkspaceAdmin[]>([]);

  useEffect(() => {
    apiJson<WorkspaceAdmin[]>('/admin/workspaces').then(setWorkspaces).catch(() => {});
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-display font-semibold text-ink">Workspaces</h1>
        <Link to="/admin/workspaces/new" className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-paper transition hover:bg-ink-soft">
          + New Workspace
        </Link>
      </div>

      <table className="w-full bg-white border border-ink/10 rounded-2xl text-sm">
        <thead>
          <tr className="text-left text-ink/50 border-b border-ink/10">
            <th className="px-4 py-2 font-medium">Name</th>
            <th className="px-4 py-2 font-medium">Slug</th>
            <th className="px-4 py-2 font-medium">Host</th>
            <th className="px-4 py-2 font-medium">Status</th>
            <th className="px-4 py-2 font-medium">Created</th>
          </tr>
        </thead>
        <tbody>
          {workspaces.map((w) => (
            <tr key={w.id} className="border-b border-ink/10 last:border-0 transition hover:bg-paper">
              <td className="px-4 py-2">
                <Link to={`/admin/workspaces/${w.id}`} className="text-gold-700 hover:underline">
                  {w.name}
                </Link>
              </td>
              <td className="px-4 py-2 text-ink/50">{w.slug}</td>
              <td className="px-4 py-2 text-ink/50">{w.host ?? '—'}</td>
              <td className="px-4 py-2 text-ink">
                {w.deleted_at ? 'Deleted' : w.archived_at ? 'Archived' : w.is_active ? 'Active' : 'Suspended'}
              </td>
              <td className="px-4 py-2 text-ink/50">{w.created_at?.slice(0, 10) ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {workspaces.length === 0 && <p className="text-sm text-ink/40 mt-4">No workspaces yet.</p>}
    </div>
  );
}

export function AdminWorkspacesPage() {
  return (
    <AdminGuard>
      <AdminLayout>
        <AdminWorkspacesContent />
      </AdminLayout>
    </AdminGuard>
  );
}
