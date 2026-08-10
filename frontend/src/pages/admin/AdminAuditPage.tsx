import { useEffect, useState } from 'react';
import { apiJson } from '../../lib/apiClient';
import { AdminGuard } from './AdminGuard';
import { AdminLayout } from './AdminLayout';
import type { AuditLogEntry } from './adminTypes';

function AdminAuditContent() {
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [workspaceId, setWorkspaceId] = useState('');

  function load() {
    const query = workspaceId.trim() ? `?workspace_id=${encodeURIComponent(workspaceId)}` : '';
    apiJson<AuditLogEntry[]>(`/admin/audit${query}`).then(setEntries).catch(() => {});
  }

  useEffect(load, []);

  return (
    <div>
      <h1 className="text-xl font-semibold mb-4">Audit Logs</h1>

      <div className="flex gap-2 mb-4">
        <input
          value={workspaceId}
          onChange={(e) => setWorkspaceId(e.target.value)}
          placeholder="Filter by workspace id (optional)"
          className="border rounded px-3 py-2 text-sm flex-1"
        />
        <button onClick={load} className="bg-blue-600 text-white rounded px-4 py-2 text-sm">Filter</button>
      </div>

      <table className="w-full bg-white border rounded text-sm">
        <thead>
          <tr className="text-left text-gray-500 border-b">
            <th className="px-4 py-2 font-medium">Action</th>
            <th className="px-4 py-2 font-medium">Actor</th>
            <th className="px-4 py-2 font-medium">Workspace</th>
            <th className="px-4 py-2 font-medium">When</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr key={e.id} className="border-b last:border-0">
              <td className="px-4 py-2">{e.action}</td>
              <td className="px-4 py-2 text-gray-500">{e.actor_auth_user_id}</td>
              <td className="px-4 py-2 text-gray-500">{e.workspace_id ?? '—'}</td>
              <td className="px-4 py-2 text-gray-500">{e.created_at?.slice(0, 19).replace('T', ' ') ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {entries.length === 0 && <p className="text-sm text-gray-400 mt-4">No audit entries yet.</p>}
    </div>
  );
}

export function AdminAuditPage() {
  return (
    <AdminGuard>
      <AdminLayout>
        <AdminAuditContent />
      </AdminLayout>
    </AdminGuard>
  );
}
