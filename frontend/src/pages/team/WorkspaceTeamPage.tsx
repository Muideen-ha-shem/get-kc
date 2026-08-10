import { FormEvent, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { apiJson } from '../../lib/apiClient';
import type { Department, InvitationRole, WorkspaceInvitation } from './teamTypes';

const DEPARTMENTS: Department[] = ['Support', 'Sales', 'Solution Architect', 'Customer Success', 'General'];

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-700',
  accepted: 'bg-green-100 text-green-700',
  revoked: 'bg-gray-200 text-gray-500',
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
      <div className="p-8 text-center">
        <p className="text-lg font-medium">You don't have admin access to this workspace's team.</p>
        <Link to="/admin" className="text-blue-600 underline">Back to Admin</Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Team</h1>
        <Link to={`/admin/workspaces/${workspaceId}`} className="text-sm text-blue-600 underline">
          Back to workspace
        </Link>
      </div>

      <form onSubmit={sendInvite} className="bg-white border rounded p-4 mb-6 flex flex-col gap-3 max-w-md">
        <h2 className="text-sm font-semibold text-gray-500 uppercase">Invite a teammate</h2>
        <label className="text-sm">
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full border rounded px-2 py-1 mt-1"
          />
        </label>
        <label className="text-sm">
          Role
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as InvitationRole)}
            className="w-full border rounded px-2 py-1 mt-1"
          >
            <option value="agent">Support Agent</option>
            <option value="workspace_admin">Workspace Admin</option>
          </select>
        </label>
        {role === 'agent' && (
          <label className="text-sm">
            Department
            <select
              value={department}
              onChange={(e) => setDepartment(e.target.value as Department)}
              className="w-full border rounded px-2 py-1 mt-1"
            >
              {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
        )}
        {errorMessage && <p className="text-sm text-red-600">{errorMessage}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="bg-blue-600 text-white rounded px-4 py-2 text-sm self-start disabled:opacity-50"
        >
          {submitting ? 'Sending...' : 'Send invite'}
        </button>
      </form>

      <div className="bg-white border rounded divide-y">
        {invitations.map((i) => (
          <div key={i.id} className="flex items-center justify-between px-4 py-3">
            <div>
              <p className="text-sm font-medium">{i.email}</p>
              <p className="text-xs text-gray-500">
                {i.role === 'workspace_admin' ? 'Workspace Admin' : `Agent · ${i.department ?? 'General'}`}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className={`text-xs rounded-full px-2 py-1 ${STATUS_STYLES[i.status] ?? ''}`}>
                {i.status}
              </span>
              {i.status === 'pending' && (
                <button onClick={() => revoke(i.id)} className="text-xs bg-red-100 text-red-700 rounded px-2 py-1">
                  Revoke
                </button>
              )}
            </div>
          </div>
        ))}
        {invitations.length === 0 && <p className="px-4 py-3 text-sm text-gray-400">No invitations yet.</p>}
      </div>
    </div>
  );
}

export function WorkspaceTeamPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  if (!workspaceId) return null;
  return <WorkspaceTeamContent workspaceId={workspaceId} />;
}
