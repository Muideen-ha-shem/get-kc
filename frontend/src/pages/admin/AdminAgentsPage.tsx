import { FormEvent, useEffect, useState } from 'react';
import { apiJson } from '../../lib/apiClient';
import { AdminGuard } from './AdminGuard';
import { AdminLayout } from './AdminLayout';
import type { AgentPerformance, SupportAgent } from './adminTypes';

const DEPARTMENTS = ['Support', 'Sales', 'Solution Architect', 'Customer Success', 'General', 'Implementation', 'Training', 'Finance'];

function AdminAgentsContent() {
  const [workspaceId, setWorkspaceId] = useState('');
  const [agents, setAgents] = useState<SupportAgent[]>([]);
  const [performance, setPerformance] = useState<Record<string, AgentPerformance>>({});

  async function load(event?: FormEvent) {
    event?.preventDefault();
    if (!workspaceId.trim()) return;
    const list = await apiJson<SupportAgent[]>(`/admin/agents?workspace_id=${encodeURIComponent(workspaceId)}`);
    setAgents(list);
    const perfEntries = await Promise.all(
      list.map((a) => apiJson<AgentPerformance>(`/admin/agents/${a.id}/performance`).then((p) => [a.id, p] as const)),
    );
    setPerformance(Object.fromEntries(perfEntries));
  }

  async function removeAgent(agentId: string) {
    if (!confirm('Remove this agent?')) return;
    await apiJson(`/admin/agents/${agentId}`, { method: 'DELETE' });
    load();
  }

  async function changeDepartment(agentId: string, department: string) {
    await apiJson(`/admin/agents/${agentId}/department?department=${encodeURIComponent(department)}`, { method: 'PATCH' });
    load();
  }

  return (
    <div>
      <h1 className="text-xl font-semibold mb-4">Agents</h1>

      <form onSubmit={load} className="flex gap-2 mb-4">
        <input
          value={workspaceId}
          onChange={(e) => setWorkspaceId(e.target.value)}
          placeholder="Workspace id"
          className="border rounded px-3 py-2 text-sm"
        />
        <button type="submit" className="bg-blue-600 text-white rounded px-4 py-2 text-sm">Load</button>
      </form>

      <div className="bg-white border rounded divide-y">
        {agents.map((a) => (
          <div key={a.id} className="flex items-center justify-between px-4 py-3">
            <div>
              <p className="text-sm font-medium">{a.name} <span className="text-gray-400 font-normal">· {a.status}</span></p>
              <p className="text-xs text-gray-500">{a.email}</p>
              {performance[a.id] && (
                <p className="text-xs text-gray-500 mt-1">
                  Active chats: {performance[a.id].active_chats} · Resolved today: {performance[a.id].resolved_today}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <select
                value={a.department}
                onChange={(e) => changeDepartment(a.id, e.target.value)}
                className="text-xs border rounded px-2 py-1"
              >
                {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
              <button onClick={() => removeAgent(a.id)} className="text-xs bg-red-100 text-red-700 rounded px-2 py-1">
                Remove
              </button>
            </div>
          </div>
        ))}
        {agents.length === 0 && <p className="px-4 py-3 text-sm text-gray-400">Enter a workspace id to load its agents.</p>}
      </div>
    </div>
  );
}

export function AdminAgentsPage() {
  return (
    <AdminGuard>
      <AdminLayout>
        <AdminAgentsContent />
      </AdminLayout>
    </AdminGuard>
  );
}
