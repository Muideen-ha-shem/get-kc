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
      <h1 className="text-xl font-display font-semibold mb-4 text-ink">Audit Logs</h1>

      <div className="flex gap-2 mb-4">
        <input
          value={workspaceId}
          onChange={(e) => setWorkspaceId(e.target.value)}
          placeholder="Filter by workspace id (optional)"
          className="border border-ink/10 rounded-xl px-3 py-2 text-sm flex-1 bg-paper text-ink outline-none focus:border-gold-400"
        />
        <button onClick={load} className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-paper transition hover:bg-ink-soft">Filter</button>
      </div>

      <table className="w-full bg-white border border-ink/10 rounded-2xl text-sm">
        <thead>
          <tr className="text-left text-ink/50 border-b border-ink/10">
            <th className="px-4 py-2 font-medium">Action</th>
            <th className="px-4 py-2 font-medium">Actor</th>
            <th className="px-4 py-2 font-medium">Workspace</th>
            <th className="px-4 py-2 font-medium">When</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr key={e.id} className="border-b border-ink/10 last:border-0 text-ink">
              <td className="px-4 py-2">{e.action}</td>
              <td className="px-4 py-2 text-ink/50">{e.actor_auth_user_id}</td>
              <td className="px-4 py-2 text-ink/50">{e.workspace_id ?? '—'}</td>
              <td className="px-4 py-2 text-ink/50">{e.created_at?.slice(0, 19).replace('T', ' ') ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {entries.length === 0 && <p className="text-sm text-ink/40 mt-4">No audit entries yet.</p>}
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
