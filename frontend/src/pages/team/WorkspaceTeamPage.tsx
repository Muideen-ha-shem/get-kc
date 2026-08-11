import { FormEvent, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { apiJson } from '../../lib/apiClient';
import type { Department, InvitationRole, WorkspaceInvitation } from './teamTypes';

const DEPARTMENTS: Department[] = ['Support', 'Sales', 'Solution Architect', 'Customer Success', 'General'];

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-gold-100 text-gold-700',
  accepted: 'bg-green-100 text-green-700',
  revoked: 'bg-ink/10 text-ink/50',
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
            className="w-full border border-ink/10 rounded-xl px-3 py-1.5 mt-1 bg-paper text-ink text-sm outline-none focus:border-gold-400"
          />
        </label>
        <label className="text-sm text-ink">
          Role
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as InvitationRole)}
            className="w-full border border-ink/10 rounded-xl px-3 py-1.5 mt-1 bg-paper text-ink text-sm outline-none focus:border-gold-400"
          >
            <option value="agent">Support Agent</option>
            <option value="workspace_admin">Workspace Admin</option>
          </select>
        </label>
        {role === 'agent' && (
          <label className="text-sm text-ink">
            Department
            <select
              value={department}
              onChange={(e) => setDepartment(e.target.value as Department)}
              className="w-full border border-ink/10 rounded-xl px-3 py-1.5 mt-1 bg-paper text-ink text-sm outline-none focus:border-gold-400"
            >
              {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
        )}
        {errorMessage && <p className="text-sm text-red-600">{errorMessage}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-paper transition hover:bg-ink-soft self-start disabled:opacity-50"
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
              <span className={`text-xs rounded-full px-2 py-1 ${STATUS_STYLES[i.status] ?? ''}`}>
                {i.status}
              </span>
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
