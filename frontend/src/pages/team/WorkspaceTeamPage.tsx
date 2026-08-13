import { FormEvent, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { apiJson } from '../../lib/apiClient';
import { Select } from '../../components/Select';
import { StatusBadge, type BadgeTone } from '../../components/StatusBadge';
import { INPUT_CLASS, PRIMARY_BUTTON } from '../../lib/uiClassNames';
import type { Department, InvitationRole, WorkspaceInvitation } from './teamTypes';

const DEPARTMENTS: Department[] = ['Support', 'Sales', 'Solution Architect', 'Customer Success', 'General'];

const STATUS_TONE: Record<string, BadgeTone> = {
  pending: 'warning',
  accepted: 'success',
  revoked: 'neutral',
};

function WorkspaceTeamContent({ workspaceId }: { workspaceId: string }) {
  const [invitations, setInvitations] = useState<WorkspaceInvitation[]>([]);
  const [forbidden, setForbidden] = useState(false);
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<InvitationRole>('agent');
  const [department, setDepartment] = useState<Department>('General');
  const [errorMessage, setErrorMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);

  function load() {
    apiJson<WorkspaceInvitation[]>(`/workspaces/${workspaceId}/invitations`)
      .then((rows) => {
        setInvitations(rows);
        setForbidden(false);
      })
      .catch(() => setForbidden(true));
  }

  useEffect(load, [workspaceId]);

  async function sendInvite(event: FormEvent) {
    event.preventDefault();
    setErrorMessage('');
    setSubmitting(true);
    try {
      await apiJson(`/workspaces/${workspaceId}/invitations`, {
        method: 'POST',
        body: JSON.stringify({
          email, role, department: role === 'agent' ? department : null,
        }),
      });
      setEmail('');
      load();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to send invite.');
    } finally {
      setSubmitting(false);
    }
  }

  async function revoke(invitationId: string) {
    await apiJson(`/workspaces/${workspaceId}/invitations/${invitationId}`, { method: 'DELETE' });
    load();
  }

  if (forbidden) {
    return (
      <div className="min-h-screen bg-paper p-8 text-center">
        <p className="text-lg font-display text-ink">You don't have admin access to this workspace's team.</p>
        <Link to="/admin" className="text-gold-700 underline hover:text-gold-600">Back to Admin</Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-display font-semibold text-ink">Team</h1>
        <Link to={`/admin/workspaces/${workspaceId}`} className="text-sm text-gold-700 underline hover:text-gold-600">
          Back to workspace
        </Link>
      </div>

      <form onSubmit={sendInvite} className="bg-white border border-ink/10 rounded-2xl p-4 mb-6 flex flex-col gap-3 max-w-md">
        <h2 className="text-sm font-semibold text-ink/50 uppercase">Invite a teammate</h2>
        <label className="text-sm text-ink">
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className={INPUT_CLASS}
          />
        </label>
        <label className="text-sm text-ink">
          Role
          <Select value={role} onChange={(e) => setRole(e.target.value as InvitationRole)} className="mt-1">
            <option value="agent">Support Agent</option>
            <option value="workspace_admin">Workspace Admin</option>
          </Select>
        </label>
        {role === 'agent' && (
          <label className="text-sm text-ink">
            Department
            <Select value={department} onChange={(e) => setDepartment(e.target.value as Department)} className="mt-1">
              {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
            </Select>
          </label>
        )}
        {errorMessage && <p className="text-sm text-red-600">{errorMessage}</p>}
        <button
          type="submit"
          disabled={submitting}
          className={`${PRIMARY_BUTTON} self-start disabled:opacity-50`}
        >
          {submitting ? 'Sending...' : 'Send invite'}
        </button>
      </form>

      <div className="bg-white border border-ink/10 rounded-2xl divide-y divide-ink/10">
        {invitations.map((i) => (
          <div key={i.id} className="flex items-center justify-between px-4 py-3">
            <div>
              <p className="text-sm font-medium text-ink">{i.email}</p>
              <p className="text-xs text-ink/50">
                {i.role === 'workspace_admin' ? 'Workspace Admin' : `Agent · ${i.department ?? 'General'}`}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <StatusBadge tone={STATUS_TONE[i.status] ?? 'neutral'}>{i.status}</StatusBadge>
              {i.status === 'pending' && (
                <button onClick={() => revoke(i.id)} className="rounded-full bg-red-50 text-red-700 border border-red-200 px-3 py-1 text-xs transition hover:bg-red-100">
                  Revoke
                </button>
              )}
            </div>
          </div>
        ))}
        {invitations.length === 0 && <p className="px-4 py-3 text-sm text-ink/40">No invitations yet.</p>}
      </div>
    </div>
  );
}

export function WorkspaceTeamPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  if (!workspaceId) return null;
  return <WorkspaceTeamContent workspaceId={workspaceId} />;
}
