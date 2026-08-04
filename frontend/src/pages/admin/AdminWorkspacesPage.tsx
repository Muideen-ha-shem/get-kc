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
        <h1 className="text-xl font-semibold">Workspaces</h1>
        <Link to="/admin/workspaces/new" className="bg-blue-600 text-white rounded px-4 py-2 text-sm">
          + New Workspace
        </Link>
      </div>

      <table className="w-full bg-white border rounded text-sm">
        <thead>
          <tr className="text-left text-gray-500 border-b">
            <th className="px-4 py-2 font-medium">Name</th>
            <th className="px-4 py-2 font-medium">Slug</th>
            <th className="px-4 py-2 font-medium">Host</th>
            <th className="px-4 py-2 font-medium">Status</th>
            <th className="px-4 py-2 font-medium">Created</th>
          </tr>
        </thead>
        <tbody>
          {workspaces.map((w) => (
            <tr key={w.id} className="border-b last:border-0 hover:bg-gray-50">
              <td className="px-4 py-2">
                <Link to={`/admin/workspaces/${w.id}`} className="text-blue-600 hover:underline">
                  {w.name}
                </Link>
              </td>
              <td className="px-4 py-2 text-gray-500">{w.slug}</td>
              <td className="px-4 py-2 text-gray-500">{w.host ?? '—'}</td>
              <td className="px-4 py-2">
                {w.deleted_at ? 'Deleted' : w.archived_at ? 'Archived' : w.is_active ? 'Active' : 'Suspended'}
              </td>
              <td className="px-4 py-2 text-gray-500">{w.created_at?.slice(0, 10) ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {workspaces.length === 0 && <p className="text-sm text-gray-400 mt-4">No workspaces yet.</p>}
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
