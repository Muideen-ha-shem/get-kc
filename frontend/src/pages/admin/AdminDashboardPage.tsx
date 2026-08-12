import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiJson } from '../../lib/apiClient';
import { StatusBadge, type BadgeTone } from '../../components/StatusBadge';
import { CARD, PRIMARY_BUTTON } from '../../lib/uiClassNames';
import { AdminGuard } from './AdminGuard';
import { AdminLayout } from './AdminLayout';
import type { PlatformDashboard, WorkspaceAdmin } from './adminTypes';

function workspaceStatusTone(w: WorkspaceAdmin): BadgeTone {
  if (w.deleted_at) return 'danger';
  if (w.is_active) return 'success';
  return 'neutral';
}

function workspaceStatusLabel(w: WorkspaceAdmin): string {
  if (w.deleted_at) return 'Deleted';
  if (w.archived_at) return 'Archived';
  return w.is_active ? 'Active' : 'Suspended';
}

function AdminDashboardContent() {
  const [stats, setStats] = useState<PlatformDashboard | null>(null);
  const [workspaces, setWorkspaces] = useState<WorkspaceAdmin[]>([]);

  useEffect(() => {
    apiJson<PlatformDashboard>('/admin/dashboard').then(setStats).catch(() => {});
    apiJson<WorkspaceAdmin[]>('/admin/workspaces').then(setWorkspaces).catch(() => {});
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-display font-semibold text-ink">Dashboard</h1>
        <Link to="/admin/workspaces/new" className={PRIMARY_BUTTON}>
          + New Workspace
        </Link>
      </div>

      {stats && (
        <div className="grid grid-cols-5 gap-4 mb-8">
          {[
            ['Total Workspaces', stats.total_workspace_count],
            ['Active Workspaces', stats.active_workspace_count],
            ['Total Conversations', stats.total_conversation_count],
            ['Human Escalations', stats.total_escalation_count],
            ['Total Agents', stats.total_agent_count],
          ].map(([label, value]) => (
            <div key={label as string} className={`${CARD} p-4`}>
              <p className="text-xs text-ink/50 uppercase">{label}</p>
              <p className="text-2xl font-display font-semibold mt-1 text-ink">{value}</p>
            </div>
          ))}
        </div>
      )}

      <h2 className="text-sm font-semibold text-ink/50 uppercase mb-2">Workspaces</h2>
      <div className={`${CARD} divide-y divide-ink/10`}>
        {workspaces.map((w) => (
          <Link
            key={w.id}
            to={`/admin/workspaces/${w.id}`}
            className="flex items-center justify-between px-4 py-3 transition hover:bg-paper"
          >
            <div>
              <p className="text-sm font-medium text-ink">{w.name}</p>
              <p className="text-xs text-ink/50">{w.slug}</p>
            </div>
            <StatusBadge tone={workspaceStatusTone(w)}>{workspaceStatusLabel(w)}</StatusBadge>
          </Link>
        ))}
        {workspaces.length === 0 && <p className="px-4 py-3 text-sm text-ink/40">No workspaces yet.</p>}
      </div>
    </div>
  );
}

export function AdminDashboardPage() {
  return (
    <AdminGuard>
      <AdminLayout>
        <AdminDashboardContent />
      </AdminLayout>
    </AdminGuard>
  );
}
