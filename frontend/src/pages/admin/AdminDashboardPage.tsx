import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bot, Building2, CheckCircle2, LifeBuoy, MessageSquare } from 'lucide-react';
import { apiJson } from '../../lib/apiClient';
import { MetricCard } from '../../components/MetricCard';
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
          <MetricCard label="Total Workspaces" value={stats.total_workspace_count} icon={Building2} tone="gold" />
          <MetricCard label="Active Workspaces" value={stats.active_workspace_count} icon={CheckCircle2} tone="green" />
          <MetricCard label="Total Conversations" value={stats.total_conversation_count} icon={MessageSquare} tone="ink" />
          <MetricCard label="Human Escalations" value={stats.total_escalation_count} icon={LifeBuoy} tone="red" />
          <MetricCard label="Total Agents" value={stats.total_agent_count} icon={Bot} tone="gold" />
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
