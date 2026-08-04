import { FormEvent, useEffect, useState } from 'react';
import { apiJson } from '../../lib/apiClient';
import { AdminGuard } from './AdminGuard';
import { AdminLayout } from './AdminLayout';
import type { AdminUser } from './adminTypes';

function AdminUsersContent() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [roleWorkspaceId, setRoleWorkspaceId] = useState('');
  const [roleDepartment, setRoleDepartment] = useState('General');

  function load() {
    apiJson<AdminUser[]>('/admin/users')
      .then((data) => {
        setUsers(data);
        setError(null);
      })
      .catch(() => setError('Unable to list users — check SUPABASE_SERVICE_ROLE_KEY is configured.'));
  }

  useEffect(load, []);

  async function suspend(userId: string) {
    await apiJson(`/admin/users/${userId}/suspend`, { method: 'POST' });
    load();
  }

  async function reactivate(userId: string) {
    await apiJson(`/admin/users/${userId}/reactivate`, { method: 'POST' });
    load();
  }

  async function resetPassword(userId: string, email: string) {
    await apiJson(`/admin/users/${userId}/reset-password?email=${encodeURIComponent(email)}`, { method: 'POST' });
    alert('Password reset email sent.');
  }

  async function assignAgent(event: FormEvent, userId: string, email: string | null, fullName: string | null) {
    event.preventDefault();
    if (!roleWorkspaceId.trim()) {
      alert('Enter a workspace id first.');
      return;
    }
    await apiJson(`/admin/users/${userId}/roles`, {
      method: 'POST',
      body: JSON.stringify({
        role: 'agent', workspace_id: roleWorkspaceId, department: roleDepartment,
        name: fullName ?? email ?? 'Agent', email: email ?? '',
      }),
    });
    alert('Agent role assigned.');
  }

  async function assignAdmin(userId: string) {
    await apiJson(`/admin/users/${userId}/roles`, { method: 'POST', body: JSON.stringify({ role: 'admin' }) });
    alert('Super admin role assigned.');
  }

  return (
    <div>
      <h1 className="text-xl font-semibold mb-4">Users</h1>

      {error && <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-3 mb-4">{error}</p>}

      <div className="bg-white border rounded p-3 mb-4 flex gap-2 items-end">
        <label className="text-xs">
          Workspace id (for agent assignment)
          <input value={roleWorkspaceId} onChange={(e) => setRoleWorkspaceId(e.target.value)} className="block border rounded px-2 py-1 mt-1 text-sm" />
        </label>
        <label className="text-xs">
          Department
          <select value={roleDepartment} onChange={(e) => setRoleDepartment(e.target.value)} className="block border rounded px-2 py-1 mt-1 text-sm">
            {['Support', 'Sales', 'Solution Architect', 'Customer Success', 'General', 'Implementation', 'Training', 'Finance'].map(
              (d) => (
                <option key={d} value={d}>{d}</option>
              ),
            )}
          </select>
        </label>
      </div>

      <div className="bg-white border rounded divide-y">
        {users.map((u) => (
          <div key={u.id} className="flex items-center justify-between px-4 py-3">
            <div>
              <p className="text-sm font-medium">{u.full_name ?? '—'}</p>
              <p className="text-xs text-gray-500">{u.email}</p>
            </div>
            <div className="flex gap-2">
              <button onClick={() => suspend(u.id)} className="text-xs bg-gray-200 rounded px-2 py-1">Suspend</button>
              <button onClick={() => reactivate(u.id)} className="text-xs bg-green-100 text-green-700 rounded px-2 py-1">Reactivate</button>
              <button onClick={() => resetPassword(u.id, u.email ?? '')} className="text-xs bg-gray-200 rounded px-2 py-1">Reset Password</button>
              <form onSubmit={(e) => assignAgent(e, u.id, u.email, u.full_name)} className="inline">
                <button type="submit" className="text-xs bg-blue-100 text-blue-700 rounded px-2 py-1">Make Agent</button>
              </form>
              <button onClick={() => assignAdmin(u.id)} className="text-xs bg-purple-100 text-purple-700 rounded px-2 py-1">
                Make Admin
              </button>
            </div>
          </div>
        ))}
        {users.length === 0 && !error && <p className="px-4 py-3 text-sm text-gray-400">No users.</p>}
      </div>
    </div>
  );
}

export function AdminUsersPage() {
  return (
    <AdminGuard>
      <AdminLayout>
        <AdminUsersContent />
      </AdminLayout>
    </AdminGuard>
  );
}
