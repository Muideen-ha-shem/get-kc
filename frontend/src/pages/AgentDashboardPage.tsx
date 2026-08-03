import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { HavisIQMark } from '../components/HavisIQMark';
import { apiJson } from '../lib/apiClient';

type AgentStatus = 'available' | 'away' | 'offline';

type SupportAgent = {
  id: string;
  workspace_id: string;
  name: string;
  email: string;
  department: string;
  status: AgentStatus;
};

type EscalationSummary = {
  customer: string;
  workspace: string;
  intent: string[];
  sentiment: string;
  products: string[];
  problem: string;
  actions_already_taken: { label: string; action_type: string }[];
  suggested_resolution: { product: string; reason: string }[];
};

type EscalationMessage = {
  id: string;
  sender_type: 'agent' | 'customer';
  content: string;
  created_at: string | null;
};

type EscalationNote = {
  id: string;
  author_agent_id: string | null;
  content: string;
  created_at: string | null;
};

type EscalationStatus = 'waiting' | 'assigned' | 'active' | 'waiting_for_customer' | 'resolved' | 'closed';

const STATUS_LABELS: Record<EscalationStatus, string> = {
  waiting: 'New',
  assigned: 'Assigned',
  active: 'In Progress',
  waiting_for_customer: 'Waiting for Customer',
  resolved: 'Resolved',
  closed: 'Closed',
};

type Escalation = {
  id: string;
  status: EscalationStatus;
  trigger_reason: string;
  department: string | null;
  assigned_agent_name: string | null;
  summary: EscalationSummary | null;
  messages?: EscalationMessage[] | null;
  notes?: EscalationNote[] | null;
};

type DashboardStats = {
  status: AgentStatus;
  department: string;
  current_workload: number;
  resolved_today: number;
  average_resolution_minutes: number | null;
};

const POLL_INTERVAL_MS = 5000;
const OPEN_CONVERSATION_POLL_INTERVAL_MS = 2500;

export function AgentDashboardPage() {
  const [agent, setAgent] = useState<SupportAgent | null>(null);
  const [notAnAgent, setNotAnAgent] = useState(false);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [queue, setQueue] = useState<Escalation[]>([]);
  const [myConversations, setMyConversations] = useState<Escalation[]>([]);
  const [openEscalation, setOpenEscalation] = useState<Escalation | null>(null);
  const [messageInput, setMessageInput] = useState('');
  const [noteInput, setNoteInput] = useState('');
  const [copilotDraft, setCopilotDraft] = useState<string | null>(null);

  useEffect(() => {
    apiJson<SupportAgent>('/agents/me')
      .then(setAgent)
      .catch(() => setNotAnAgent(true));
  }, []);

  useEffect(() => {
    if (!agent) return;

    const poll = () => {
      apiJson<Escalation[]>('/agent/queue').then(setQueue).catch(() => {});
      apiJson<Escalation[]>('/agent/conversations').then(setMyConversations).catch(() => {});
      apiJson<DashboardStats>('/agent/dashboard/stats').then(setStats).catch(() => {});
      if (openEscalation) {
        apiJson<Escalation>(`/agent/escalations/${openEscalation.id}`)
          .then(setOpenEscalation)
          .catch(() => {});
      }
    };

    poll();
    const interval = setInterval(poll, openEscalation ? OPEN_CONVERSATION_POLL_INTERVAL_MS : POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [agent, openEscalation?.id]);

  async function setStatus(status: AgentStatus) {
    const updated = await apiJson<SupportAgent>('/agents/status', {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
    setAgent(updated);
  }

  async function acceptEscalation(escalationId: string) {
    await apiJson('/agent/accept', { method: 'POST', body: JSON.stringify({ escalation_id: escalationId }) });
    const detail = await apiJson<Escalation>(`/agent/escalations/${escalationId}`);
    setOpenEscalation(detail);
  }

  async function resolveEscalation(escalationId: string) {
    await apiJson('/agent/resolve', { method: 'POST', body: JSON.stringify({ escalation_id: escalationId }) });
    setOpenEscalation(null);
  }

  async function markWaitingForCustomer(escalationId: string) {
    const updated = await apiJson<Escalation>(`/agent/escalations/${escalationId}/wait-for-customer`, {
      method: 'POST',
    });
    setOpenEscalation(updated);
  }

  async function rejoinAi(escalationId: string) {
    await apiJson(`/agent/escalations/${escalationId}/rejoin-ai`, { method: 'POST' });
    setOpenEscalation(null);
  }

  async function sendMessage(event: FormEvent) {
    event.preventDefault();
    if (!openEscalation || !messageInput.trim()) return;
    await apiJson(`/agent/escalations/${openEscalation.id}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content: messageInput }),
    });
    setMessageInput('');
    setCopilotDraft(null);
    const detail = await apiJson<Escalation>(`/agent/escalations/${openEscalation.id}`);
    setOpenEscalation(detail);
  }

  async function addNote(event: FormEvent) {
    event.preventDefault();
    if (!openEscalation || !noteInput.trim()) return;
    await apiJson(`/agent/escalations/${openEscalation.id}/notes`, {
      method: 'POST',
      body: JSON.stringify({ content: noteInput }),
    });
    setNoteInput('');
    const detail = await apiJson<Escalation>(`/agent/escalations/${openEscalation.id}`);
    setOpenEscalation(detail);
  }

  async function requestCopilotDraft() {
    if (!openEscalation) return;
    const question = openEscalation.summary?.problem ?? '';
    const result = await apiJson<{ draft: string }>(
      `/agent/escalations/${openEscalation.id}/copilot/suggest-reply`,
      { method: 'POST', body: JSON.stringify({ question }) },
    );
    setCopilotDraft(result.draft);
  }

  if (notAnAgent) {
    return (
      <div className="min-h-screen flex items-center justify-center text-center p-8">
        <div>
          <p className="text-lg font-medium">You're not a registered support agent.</p>
          <Link to="/" className="text-blue-600 underline">
            Back to HavisIQ
          </Link>
        </div>
      </div>
    );
  }

  if (!agent) {
    return <div className="min-h-screen flex items-center justify-center">Loading…</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="flex items-center justify-between px-6 py-4 border-b bg-white">
        <div className="flex items-center gap-2">
          <HavisIQMark />
          <span className="font-semibold">Agent Dashboard</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">{agent.name} · {agent.department}</span>
          <select
            value={agent.status}
            onChange={(e) => setStatus(e.target.value as AgentStatus)}
            className="border rounded px-2 py-1 text-sm"
          >
            <option value="available">Available</option>
            <option value="away">Away</option>
            <option value="offline">Offline</option>
          </select>
        </div>
      </header>

      {stats && (
        <div className="flex gap-6 px-6 py-3 border-b bg-white text-sm text-gray-600">
          <span>Workload: <strong className="text-gray-900">{stats.current_workload}</strong></span>
          <span>Resolved today: <strong className="text-gray-900">{stats.resolved_today}</strong></span>
          <span>
            Avg. resolution:{' '}
            <strong className="text-gray-900">
              {stats.average_resolution_minutes != null ? `${Math.round(stats.average_resolution_minutes)}m` : '—'}
            </strong>
          </span>
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        <aside className="w-80 border-r bg-white overflow-y-auto">
          <section className="p-4">
            <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">My Queue</h2>
            {queue.length === 0 && <p className="text-sm text-gray-400">Nothing waiting.</p>}
            {queue.map((escalation) => (
              <div key={escalation.id} className="border rounded p-3 mb-2">
                <p className="text-sm font-medium">{escalation.trigger_reason} · {escalation.department}</p>
                <p className="text-xs text-gray-500">{escalation.summary?.problem}</p>
                <button
                  onClick={() => acceptEscalation(escalation.id)}
                  className="mt-2 text-xs bg-blue-600 text-white rounded px-2 py-1"
                >
                  Accept
                </button>
              </div>
            ))}
          </section>
          <section className="p-4 border-t">
            <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Active Chats</h2>
            {myConversations.length === 0 && <p className="text-sm text-gray-400">None yet.</p>}
            {myConversations.map((escalation) => (
              <button
                key={escalation.id}
                onClick={() => setOpenEscalation(escalation)}
                className="w-full text-left border rounded p-3 mb-2 hover:bg-gray-50"
              >
                <p className="text-sm font-medium">{STATUS_LABELS[escalation.status]}</p>
                <p className="text-xs text-gray-500">{escalation.summary?.problem}</p>
              </button>
            ))}
          </section>
        </aside>

        <main className="flex-1 flex flex-col p-6 overflow-y-auto">
          {!openEscalation ? (
            <p className="text-gray-400">Select a conversation to view details.</p>
          ) : (
            <div className="flex flex-col h-full">
              <div className="bg-white border rounded p-4 mb-4">
                <div className="flex items-center justify-between mb-2">
                  <h2 className="font-semibold">Summary — {STATUS_LABELS[openEscalation.status]}</h2>
                  <div className="flex gap-2">
                    {openEscalation.status === 'active' && (
                      <button
                        onClick={() => markWaitingForCustomer(openEscalation.id)}
                        className="text-xs bg-gray-200 rounded px-2 py-1"
                      >
                        Waiting on Customer
                      </button>
                    )}
                    {openEscalation.status !== 'resolved' && openEscalation.status !== 'closed' && (
                      <>
                        <button
                          onClick={() => resolveEscalation(openEscalation.id)}
                          className="text-xs bg-green-600 text-white rounded px-2 py-1"
                        >
                          Resolve
                        </button>
                        <button
                          onClick={() => rejoinAi(openEscalation.id)}
                          className="text-xs bg-purple-600 text-white rounded px-2 py-1"
                        >
                          Hand back to AI
                        </button>
                      </>
                    )}
                  </div>
                </div>
                {openEscalation.summary && (
                  <dl className="text-sm grid grid-cols-2 gap-2">
                    <dt className="text-gray-500">Customer</dt>
                    <dd>{openEscalation.summary.customer}</dd>
                    <dt className="text-gray-500">Workspace</dt>
                    <dd>{openEscalation.summary.workspace}</dd>
                    <dt className="text-gray-500">Sentiment</dt>
                    <dd>{openEscalation.summary.sentiment}</dd>
                    <dt className="text-gray-500">Products</dt>
                    <dd>{openEscalation.summary.products.join(', ') || '—'}</dd>
                    <dt className="text-gray-500">Problem</dt>
                    <dd>{openEscalation.summary.problem}</dd>
                  </dl>
                )}
              </div>

              <div className="bg-white border rounded p-3 mb-4">
                <h3 className="text-sm font-semibold text-gray-500 uppercase mb-2">Internal Notes</h3>
                {(openEscalation.notes ?? []).map((note) => (
                  <p key={note.id} className="text-xs text-gray-600 mb-1">{note.content}</p>
                ))}
                <form onSubmit={addNote} className="flex gap-2 mt-2">
                  <input
                    value={noteInput}
                    onChange={(e) => setNoteInput(e.target.value)}
                    className="flex-1 border rounded px-2 py-1 text-xs"
                    placeholder="Add an internal note (not visible to the customer)…"
                  />
                  <button type="submit" className="text-xs bg-gray-200 rounded px-2 py-1">Add</button>
                </form>
              </div>

              <div className="flex-1 bg-white border rounded p-4 overflow-y-auto mb-4">
                {(openEscalation.messages ?? []).map((m) => (
                  <div key={m.id} className={m.sender_type === 'agent' ? 'text-right mb-2' : 'text-left mb-2'}>
                    <span className="inline-block bg-gray-100 rounded px-3 py-1 text-sm">{m.content}</span>
                  </div>
                ))}
              </div>

              {copilotDraft && (
                <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mb-3 text-sm">
                  <p className="text-xs font-semibold text-yellow-700 mb-1">Suggested reply (review before sending)</p>
                  <p className="mb-2">{copilotDraft}</p>
                  <button
                    onClick={() => setMessageInput(copilotDraft)}
                    className="text-xs bg-yellow-600 text-white rounded px-2 py-1"
                  >
                    Use as draft
                  </button>
                </div>
              )}

              <form onSubmit={sendMessage} className="flex gap-2">
                <button
                  type="button"
                  onClick={requestCopilotDraft}
                  className="text-xs bg-gray-200 rounded px-3 py-2"
                >
                  Ask Copilot
                </button>
                <input
                  value={messageInput}
                  onChange={(e) => setMessageInput(e.target.value)}
                  className="flex-1 border rounded px-3 py-2 text-sm"
                  placeholder="Type a reply…"
                />
                <button type="submit" className="bg-blue-600 text-white rounded px-4 py-2 text-sm">
                  Send
                </button>
              </form>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
