import { useEffect, useState } from 'react';
import { apiJson } from '../../lib/apiClient';
import { Select } from '../../components/Select';
import { CARD, INPUT_CLASS, PRIMARY_BUTTON, SECONDARY_BUTTON } from '../../lib/uiClassNames';
import { AdminGuard } from './AdminGuard';
import { AdminLayout } from './AdminLayout';
import type { AuditLogEntry } from './adminTypes';

const ACTION_OPTIONS = [
  'workspace.created', 'workspace.suspended', 'workspace.reactivated', 'workspace.archived',
  'workspace.deleted', 'workspace.hard_deleted', 'workspace.branding_changed',
  'workspace.apikey_regenerated', 'workspace.flags_changed',
];

function AdminAuditContent() {
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [workspaceId, setWorkspaceId] = useState('');
  const [actorId, setActorId] = useState('');
  const [action, setAction] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  function load() {
    const params = new URLSearchParams();
    if (workspaceId.trim()) params.set('workspace_id', workspaceId.trim());
    if (actorId.trim()) params.set('actor_auth_user_id', actorId.trim());
    if (action) params.set('action', action);
    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);
    const query = params.toString() ? `?${params.toString()}` : '';
    apiJson<AuditLogEntry[]>(`/admin/audit${query}`).then(setEntries).catch(() => {});
  }

  function clearFilters() {
    setWorkspaceId('');
    setActorId('');
    setAction('');
    setStartDate('');
    setEndDate('');
  }

  useEffect(load, []);

  return (
    <div>
      <h1 className="text-xl font-display font-semibold mb-4 text-ink">Audit Logs</h1>

      <div className={`${CARD} p-4 mb-4 flex flex-wrap gap-3 items-end`}>
        <label className="text-xs text-ink">
          Workspace id
          <input
            value={workspaceId}
            onChange={(e) => setWorkspaceId(e.target.value)}
            placeholder="Any workspace"
            className={INPUT_CLASS}
          />
        </label>
        <label className="text-xs text-ink">
          Actor id
          <input
            value={actorId}
            onChange={(e) => setActorId(e.target.value)}
            placeholder="Any actor"
            className={INPUT_CLASS}
          />
        </label>
        <label className="text-xs text-ink w-48">
          Action
          <Select value={action} onChange={(e) => setAction(e.target.value)} className="mt-1">
            <option value="">All actions</option>
            {ACTION_OPTIONS.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </Select>
        </label>
        <label className="text-xs text-ink">
          From
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className={INPUT_CLASS} />
        </label>
        <label className="text-xs text-ink">
          To
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className={INPUT_CLASS} />
        </label>
        <button onClick={load} className={PRIMARY_BUTTON}>Filter</button>
        <button onClick={() => { clearFilters(); load(); }} className={SECONDARY_BUTTON}>
          Clear filters
        </button>
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
