import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Bell, PanelLeft, PanelLeftClose } from 'lucide-react';
import { HavisIQMark } from '../components/HavisIQMark';
import { PageContainer } from '../components/PageContainer';
import { Select } from '../components/Select';
import { apiJson } from '../lib/apiClient';
import { INPUT_CLASS, PRIMARY_BUTTON, SECONDARY_BUTTON } from '../lib/uiClassNames';
import { useSidebarCollapse } from '../lib/useSidebarCollapse';

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
  resolution: string | null;
  handoff_recap: string | null;
};

type EscalationMessage = {
  id: string;
  sender_type: 'agent' | 'customer';
  sender_auth_user_id: string;
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

type AgentNotification = {
  id: string;
  type: string;
  title: string;
  body: string | null;
  is_read: boolean;
  created_at: string | null;
};

type CustomerTimeline = {
  profile: { id: string; email: string; full_name: string | null; company_name: string | null; industry: string | null } | null;
  conversations: { id: string; title: string; created_at: string | null; updated_at: string | null }[];
  saved_recommendations: unknown[];
  saved_comparisons: unknown[];
  appointments: { date: string; time: string; status: string }[];
  past_escalations: { id: string; status: string; created_at: string | null }[];
  demo_requests: { product: string | null; created_at: string | null }[];
};

const POLL_INTERVAL_MS = 5000;
const OPEN_CONVERSATION_POLL_INTERVAL_MS = 2500;

type Section = 'queue' | 'profile' | 'notifications';

export function AgentDashboardPage() {
  const [agent, setAgent] = useState<SupportAgent | null>(null);
  const [notAnAgent, setNotAnAgent] = useState(false);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [queue, setQueue] = useState<Escalation[]>([]);
  const [myConversations, setMyConversations] = useState<Escalation[]>([]);
  const [openEscalation, setOpenEscalation] = useState<Escalation | null>(null);
  const [messageInput, setMessageInput] = useState('');
  const [noteInput, setNoteInput] = useState('');
  const [copilotQuestion, setCopilotQuestion] = useState('');
  const [copilotAnswer, setCopilotAnswer] = useState<string | null>(null);
  const [resolutionDraft, setResolutionDraft] = useState('');
  const [timeline, setTimeline] = useState<CustomerTimeline | null>(null);
  const [section, setSection] = useState<Section>('queue');
  const [notifications, setNotifications] = useState<AgentNotification[] | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const [sidebarCollapsed, setSidebarCollapsed] = useSidebarCollapse('havisiq-agent-sidebar-collapsed');

  useEffect(() => {
    apiJson<SupportAgent>('/agents/me')
      .then(setAgent)
      .catch(() => setNotAnAgent(true));
  }, []);

  useEffect(() => {
    if (!agent) return;
    apiJson<{ count: number }>('/notifications/unread-count')
      .then((r) => setUnreadCount(r.count))
      .catch(() => setUnreadCount(0));
  }, [agent]);

  useEffect(() => {
    if (!agent) return;

    const poll = () => {
      apiJson<Escalation[]>('/agent/queue').then(setQueue).catch(() => {});
      apiJson<Escalation[]>('/agent/conversations').then(setMyConversations).catch(() => {});
      apiJson<DashboardStats>('/agent/dashboard/stats').then(setStats).catch(() => {});
      apiJson<{ count: number }>('/notifications/unread-count').then((r) => setUnreadCount(r.count)).catch(() => {});
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

  // Customer Timeline — resolved from the first customer message's
  // sender_auth_user_id (no dedicated field links an escalation straight
  // to a customer identity; a real customer message is the only place
  // that id appears).
  useEffect(() => {
    setTimeline(null);
    const customerAuthUserId = openEscalation?.messages?.find((m) => m.sender_type === 'customer')?.sender_auth_user_id;
    if (!customerAuthUserId) return;
    apiJson<CustomerTimeline>(`/agent/customers/${customerAuthUserId}/timeline`)
      .then(setTimeline)
      .catch(() => setTimeline(null));
  }, [openEscalation?.id, openEscalation?.messages?.length]);

  useEffect(() => {
    setResolutionDraft(openEscalation?.summary?.resolution ?? '');
  }, [openEscalation?.id, openEscalation?.summary?.resolution]);

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
    // Stays open — the agent reviews/edits the AI-drafted resolution
    // summary next, then explicitly closes. Never disappears silently.
    const updated = await apiJson<Escalation>('/agent/resolve', {
      method: 'POST',
      body: JSON.stringify({ escalation_id: escalationId }),
    });
    setOpenEscalation(updated);
  }

  async function closeEscalation(escalationId: string) {
    await apiJson(`/agent/escalations/${escalationId}/close`, {
      method: 'POST',
      body: JSON.stringify({ resolution_summary: resolutionDraft || null }),
    });
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
    setCopilotAnswer(null);
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

  async function askCopilot(event: FormEvent) {
    event.preventDefault();
    if (!openEscalation || !copilotQuestion.trim()) return;
    const result = await apiJson<{ draft: string }>(
      `/agent/escalations/${openEscalation.id}/copilot/suggest-reply`,
      { method: 'POST', body: JSON.stringify({ question: copilotQuestion }) },
    );
    setCopilotAnswer(result.draft);
  }

  async function markNotificationRead(id: string) {
    await apiJson(`/notifications/${id}/read`, { method: 'POST' });
    setNotifications((prev) => {
      const next = prev ? prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)) : prev;
      setUnreadCount(next ? next.filter((n) => !n.is_read).length : 0);
      return next;
    });
  }

  async function markAllNotificationsRead() {
    await apiJson('/notifications/read-all', { method: 'POST' });
    setNotifications((prev) => (prev ? prev.map((n) => ({ ...n, is_read: true })) : prev));
    setUnreadCount(0);
  }

  function openNotifications() {
    setSection('notifications');
    apiJson<AgentNotification[]>('/notifications').then(setNotifications).catch(() => setNotifications([]));
  }

  if (notAnAgent) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center text-center p-8">
        <div>
          <p className="text-lg font-display text-ink">You're not a registered support agent.</p>
          <Link to="/" className="text-gold-700 underline hover:text-gold-600">
            Back to HavisIQ
          </Link>
        </div>
      </div>
    );
  }

  if (!agent) {
    return <div className="min-h-screen bg-paper flex items-center justify-center text-ink/60">Loading…</div>;
  }

  return (
    <div className="min-h-screen bg-paper flex flex-col">
      <header className="flex items-center justify-between px-6 py-4 border-b border-ink/10 bg-white">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSidebarCollapsed((v) => !v)}
            className="rounded-full p-1.5 text-ink/50 transition hover:bg-paper hover:text-ink"
            aria-label={sidebarCollapsed ? 'Show queue sidebar' : 'Hide queue sidebar'}
          >
            {sidebarCollapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
          </button>
          <HavisIQMark />
          <button
            onClick={() => setSection('queue')}
            className="font-display font-semibold text-ink"
          >
            Agent Dashboard
          </button>
          <Link
            to="/dashboard"
            className="ml-2 flex items-center gap-1.5 rounded-full border border-ink/15 px-3 py-1.5 text-xs text-ink transition hover:border-gold-400 hover:text-gold-700"
          >
            <ArrowLeft size={13} /> Back to Dashboard
          </Link>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={openNotifications}
            className="relative rounded-full p-1.5 text-ink/50 transition hover:bg-paper hover:text-ink"
            aria-label={unreadCount > 0 ? `${unreadCount} unread notifications` : 'Notifications'}
          >
            <Bell size={18} />
            {unreadCount > 0 ? (
              <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-gold-500 px-1 text-[9px] font-bold text-ink">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            ) : null}
          </button>
          <button onClick={() => setSection('profile')} className="text-sm text-ink/50 hover:text-ink">
            {agent.name} · {agent.department}
          </button>
          <div className="w-32">
            <Select value={agent.status} onChange={(e) => setStatus(e.target.value as AgentStatus)}>
              <option value="available">Available</option>
              <option value="away">Away</option>
              <option value="offline">Offline</option>
            </Select>
          </div>
        </div>
      </header>

      {stats && (
        <div className="flex gap-6 px-6 py-3 border-b border-ink/10 bg-white text-sm text-ink/60">
          <span>Workload: <strong className="text-ink">{stats.current_workload}</strong></span>
          <span>Resolved today: <strong className="text-ink">{stats.resolved_today}</strong></span>
          <span>
            Avg. resolution:{' '}
            <strong className="text-ink">
              {stats.average_resolution_minutes != null ? `${Math.round(stats.average_resolution_minutes)}m` : '—'}
            </strong>
          </span>
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        <aside
          className={`shrink-0 border-r border-ink/10 bg-white overflow-y-auto overflow-x-hidden transition-[width] duration-200 ${
            sidebarCollapsed ? 'w-0 border-r-0' : 'w-80'
          }`}
        >
          <section className="p-4">
            <h2 className="text-sm font-semibold text-ink/50 uppercase mb-2">My Queue</h2>
            {queue.length === 0 && <p className="text-sm text-ink/40">Nothing waiting.</p>}
            {queue.map((escalation) => (
              <div key={escalation.id} className="border border-ink/10 rounded-xl p-3 mb-2">
                <p className="text-sm font-medium text-ink">{escalation.trigger_reason} · {escalation.department}</p>
                <p className="text-xs text-ink/50">{escalation.summary?.problem}</p>
                <button
                  onClick={() => acceptEscalation(escalation.id)}
                  className="mt-2 rounded-full bg-ink px-3 py-1 text-xs text-paper font-semibold transition hover:bg-ink-soft hover:-translate-y-0.5 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold-400/50 focus-visible:ring-offset-2 focus-visible:ring-offset-paper"
                >
                  Accept
                </button>
              </div>
            ))}
          </section>
          <section className="p-4 border-t border-ink/10">
            <h2 className="text-sm font-semibold text-ink/50 uppercase mb-2">Active Chats</h2>
            {myConversations.length === 0 && <p className="text-sm text-ink/40">None yet.</p>}
            {myConversations.map((escalation) => (
              <button
                key={escalation.id}
                onClick={() => {
                  setOpenEscalation(escalation);
                  setSection('queue');
                }}
                className="w-full text-left border border-ink/10 rounded-xl p-3 mb-2 transition hover:border-gold-400 hover:bg-paper"
              >
                <p className="text-sm font-medium text-ink">{STATUS_LABELS[escalation.status]}</p>
                <p className="text-xs text-ink/50">{escalation.summary?.problem}</p>
              </button>
            ))}
          </section>
        </aside>

        <main className="flex-1 flex flex-col p-6 overflow-y-auto">
          <PageContainer className="flex-1 flex flex-col h-full">
          {section === 'notifications' ? (
            <div className="max-w-2xl space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-xl text-ink">Notifications</h2>
                {notifications?.some((n) => !n.is_read) ? (
                  <button onClick={markAllNotificationsRead} className="text-xs font-semibold text-ink/60 hover:text-ink">
                    Mark all read
                  </button>
                ) : null}
              </div>
              {notifications === null ? (
                <p className="text-sm text-ink/40">Loading…</p>
              ) : notifications.length === 0 ? (
                <p className="text-sm text-ink/40">
                  New escalations, assignments, and customer replies will show up here.
                </p>
              ) : (
                notifications.map((n) => (
                  <button
                    key={n.id}
                    onClick={() => !n.is_read && markNotificationRead(n.id)}
                    className={`flex w-full items-start gap-3 rounded-2xl border p-4 text-left transition ${
                      n.is_read ? 'border-ink/10 bg-white' : 'border-gold-300 bg-gold-50/60'
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-ink">{n.title}</p>
                      {n.body ? <p className="mt-0.5 text-sm text-ink/60">{n.body}</p> : null}
                      {n.created_at ? (
                        <p className="mt-1 text-xs text-ink/35">{new Date(n.created_at).toLocaleString()}</p>
                      ) : null}
                    </div>
                    {!n.is_read ? <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-gold-500" aria-hidden="true" /> : null}
                  </button>
                ))
              )}
            </div>
          ) : section === 'profile' ? (
            <div className="max-w-md space-y-4">
              <h2 className="font-display text-xl text-ink">Your profile</h2>
              <dl className="text-sm grid grid-cols-2 gap-y-3 text-ink bg-white border border-ink/10 rounded-2xl p-4">
                <dt className="text-ink/50">Name</dt>
                <dd>{agent.name}</dd>
                <dt className="text-ink/50">Email</dt>
                <dd>{agent.email}</dd>
                <dt className="text-ink/50">Role</dt>
                <dd>Support Agent</dd>
                <dt className="text-ink/50">Department</dt>
                <dd>{agent.department}</dd>
                <dt className="text-ink/50">Workspace</dt>
                <dd>{agent.workspace_id}</dd>
                <dt className="text-ink/50">Availability</dt>
                <dd>
                  <div className="w-32">
                    <Select value={agent.status} onChange={(e) => setStatus(e.target.value as AgentStatus)}>
                      <option value="available">Available</option>
                      <option value="away">Away</option>
                      <option value="offline">Offline</option>
                    </Select>
                  </div>
                </dd>
              </dl>
              {stats ? (
                <dl className="text-sm grid grid-cols-2 gap-y-3 text-ink bg-white border border-ink/10 rounded-2xl p-4">
                  <dt className="text-ink/50">Current workload</dt>
                  <dd>{stats.current_workload}</dd>
                  <dt className="text-ink/50">Resolved today</dt>
                  <dd>{stats.resolved_today}</dd>
                  <dt className="text-ink/50">Average resolution time</dt>
                  <dd>{stats.average_resolution_minutes != null ? `${Math.round(stats.average_resolution_minutes)}m` : '—'}</dd>
                </dl>
              ) : null}
            </div>
          ) : !openEscalation ? (
            <p className="text-ink/40">Select a conversation to view details.</p>
          ) : (
            <div className="flex flex-col h-full">
              <div className="bg-white border border-ink/10 rounded-2xl p-4 mb-4">
                <div className="flex items-center justify-between mb-2">
                  <h2 className="font-display font-semibold text-ink">Summary — {STATUS_LABELS[openEscalation.status]}</h2>
                  <div className="flex gap-2">
                    {openEscalation.status === 'active' && (
                      <button onClick={() => markWaitingForCustomer(openEscalation.id)} className={SECONDARY_BUTTON}>
                        Waiting on Customer
                      </button>
                    )}
                    {openEscalation.status !== 'resolved' && openEscalation.status !== 'closed' && (
                      <>
                        <button
                          onClick={() => resolveEscalation(openEscalation.id)}
                          className="text-xs rounded-full bg-green-600 text-white px-3 py-1 transition hover:bg-green-700"
                        >
                          Resolve
                        </button>
                        <button
                          onClick={() => rejoinAi(openEscalation.id)}
                          className="text-xs rounded-full bg-ink text-paper px-3 py-1 transition hover:bg-ink-soft"
                        >
                          Hand back to AI
                        </button>
                      </>
                    )}
                  </div>
                </div>
                {openEscalation.summary && (
                  <dl className="text-sm grid grid-cols-2 gap-2 text-ink">
                    <dt className="text-ink/50">Customer</dt>
                    <dd>{openEscalation.summary.customer}</dd>
                    <dt className="text-ink/50">Workspace</dt>
                    <dd>{openEscalation.summary.workspace}</dd>
                    <dt className="text-ink/50">Sentiment</dt>
                    <dd>{openEscalation.summary.sentiment}</dd>
                    <dt className="text-ink/50">Products</dt>
                    <dd>{openEscalation.summary.products.join(', ') || '—'}</dd>
                    <dt className="text-ink/50">Problem</dt>
                    <dd>{openEscalation.summary.problem}</dd>
                  </dl>
                )}
              </div>

              {openEscalation.status === 'resolved' ? (
                <div className="bg-gold-50 border border-gold-200 rounded-2xl p-4 mb-4">
                  <h3 className="text-sm font-semibold text-gold-700 mb-2">Resolution summary (AI-drafted — review before closing)</h3>
                  <textarea
                    value={resolutionDraft}
                    onChange={(e) => setResolutionDraft(e.target.value)}
                    rows={3}
                    className={`w-full ${INPUT_CLASS} mt-0`}
                    placeholder="No draft available — describe what was resolved before closing…"
                  />
                  <button
                    onClick={() => closeEscalation(openEscalation.id)}
                    className="mt-2 text-xs rounded-full bg-ink text-paper px-3 py-1.5 font-semibold transition hover:bg-ink-soft"
                  >
                    Close ticket
                  </button>
                </div>
              ) : null}

              {timeline ? (
                <div className="bg-white border border-ink/10 rounded-2xl p-3 mb-4">
                  <h3 className="text-sm font-semibold text-ink/50 uppercase mb-2">Customer Timeline</h3>
                  <dl className="text-xs grid grid-cols-2 gap-1 text-ink/70 mb-2">
                    <dt className="text-ink/40">Company</dt>
                    <dd>{timeline.profile?.company_name ?? '—'}</dd>
                    <dt className="text-ink/40">Industry</dt>
                    <dd>{timeline.profile?.industry ?? '—'}</dd>
                    <dt className="text-ink/40">Prior conversations</dt>
                    <dd>{timeline.conversations.length}</dd>
                    <dt className="text-ink/40">Prior escalations</dt>
                    <dd>{timeline.past_escalations.length}</dd>
                    <dt className="text-ink/40">Appointments</dt>
                    <dd>{timeline.appointments.length}</dd>
                    <dt className="text-ink/40">Demo requests</dt>
                    <dd>{timeline.demo_requests.length}</dd>
                  </dl>
                </div>
              ) : null}

              <div className="bg-white border border-ink/10 rounded-2xl p-3 mb-4">
                <h3 className="text-sm font-semibold text-ink/50 uppercase mb-2">Internal Notes</h3>
                {(openEscalation.notes ?? []).map((note) => (
                  <p key={note.id} className="text-xs text-ink/60 mb-1">{note.content}</p>
                ))}
                <form onSubmit={addNote} className="flex gap-2 mt-2">
                  <input
                    value={noteInput}
                    onChange={(e) => setNoteInput(e.target.value)}
                    className={`flex-1 ${INPUT_CLASS} mt-0 text-xs`}
                    placeholder="Add an internal note (not visible to the customer)…"
                  />
                  <button type="submit" className={SECONDARY_BUTTON}>Add</button>
                </form>
              </div>

              <div className="flex-1 bg-white border border-ink/10 rounded-2xl p-4 overflow-y-auto mb-4">
                {(openEscalation.messages ?? []).map((m) => (
                  <div key={m.id} className={m.sender_type === 'agent' ? 'text-right mb-2' : 'text-left mb-2'}>
                    <span className="inline-block bg-paper rounded-xl px-3 py-1 text-sm text-ink">{m.content}</span>
                  </div>
                ))}
              </div>

              <div className="bg-white border border-ink/10 rounded-2xl p-3 mb-3">
                <p className="text-xs font-semibold text-ink/50 uppercase mb-2">Ask AI</p>
                <form onSubmit={askCopilot} className="flex gap-2">
                  <input
                    value={copilotQuestion}
                    onChange={(e) => setCopilotQuestion(e.target.value)}
                    className={`flex-1 ${INPUT_CLASS} mt-0 text-sm`}
                    placeholder='e.g. "Summarize this conversation" or "What does our knowledge base say about SPIDIFY?"'
                  />
                  <button type="submit" className={`${SECONDARY_BUTTON} py-2`}>Ask</button>
                </form>
                {copilotAnswer && (
                  <div className="mt-3 rounded-xl bg-gold-50 border border-gold-200 p-3 text-sm">
                    <p className="mb-2 text-ink">{copilotAnswer}</p>
                    <button
                      onClick={() => setMessageInput(copilotAnswer)}
                      className="text-xs rounded-full bg-gold-600 text-white px-3 py-1 transition hover:bg-gold-700"
                    >
                      Use as draft reply
                    </button>
                  </div>
                )}
              </div>

              <form onSubmit={sendMessage} className="flex gap-2">
                <input
                  value={messageInput}
                  onChange={(e) => setMessageInput(e.target.value)}
                  className={`flex-1 ${INPUT_CLASS} mt-0`}
                  placeholder="Type a reply…"
                />
                <button type="submit" className={PRIMARY_BUTTON}>
                  Send
                </button>
              </form>
            </div>
          )}
          </PageContainer>
        </main>
      </div>
    </div>
  );
}
