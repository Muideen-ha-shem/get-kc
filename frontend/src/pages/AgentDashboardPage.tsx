import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bell, Clock, LogOut, PanelLeft, PanelLeftClose } from 'lucide-react';
import { HavisIQMark } from '../components/HavisIQMark';
import { PageContainer } from '../components/PageContainer';
import { Select } from '../components/Select';
import { apiJson } from '../lib/apiClient';
import { useAuth } from '../lib/authContext';
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
  resolution_rate: number | null;
  avg_first_response_minutes: number | null;
};

type WorkSession = {
  id: string;
  agent_id: string;
  work_date: string;
  clock_in_at: string;
  clock_out_at: string | null;
  total_work_seconds: number | null;
};

type AuxEvent = {
  id: string;
  agent_id: string;
  aux_type: string;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
  reason: string | null;
};

type AttendanceMe = {
  session: WorkSession | null;
  aux: AuxEvent | null;
  today_aux_history: AuxEvent[];
};

type PerformanceTargets = {
  resolution_rate: number | null;
  response_minutes: number | null;
  resolution_minutes: number | null;
  csat: number | null;
};

const AUX_TYPES = [
  { value: 'meeting', label: 'Meeting' },
  { value: 'training', label: 'Training' },
  { value: 'admin_work', label: 'Admin Work' },
  { value: 'customer_follow_up', label: 'Customer Follow-up' },
  { value: 'technical_issue', label: 'Technical Issue' },
  { value: 'break', label: 'Break' },
  { value: 'lunch', label: 'Lunch' },
];

function formatDuration(seconds: number): string {
  const clamped = Math.max(0, seconds);
  const h = Math.floor(clamped / 3600);
  const m = Math.floor((clamped % 3600) / 60);
  const s = Math.floor(clamped % 60);
  const pad = (n: number) => n.toString().padStart(2, '0');
  return `${pad(h)}:${pad(m)}:${pad(s)}`;
}

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

function KpiCard({
  label,
  value,
  sub,
  target,
  met,
}: {
  label: string;
  value: string | number;
  sub?: string;
  target?: string;
  met?: boolean;
}) {
  return (
    <div className="bg-white border border-ink/10 rounded-2xl p-3">
      <p className="text-xs text-ink/50 uppercase">{label}</p>
      <p className="text-lg font-display text-ink">{value}</p>
      {sub ? <p className="text-xs text-ink/40">{sub}</p> : null}
      {target ? (
        <p className={`text-xs mt-0.5 ${met ? 'text-green-600' : met === false ? 'text-red-600' : 'text-ink/40'}`}>
          {met === true ? '✓ ' : met === false ? '✗ ' : ''}Target: {target}
        </p>
      ) : null}
    </div>
  );
}

export function AgentDashboardPage() {
  const { signOut } = useAuth();
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
  const [attendance, setAttendance] = useState<AttendanceMe | null>(null);
  const [targets, setTargets] = useState<PerformanceTargets | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const [actionError, setActionError] = useState<string | null>(null);

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

  useEffect(() => {
    if (!agent) return;
    apiJson<PerformanceTargets>('/agents/targets').then(setTargets).catch(() => setTargets(null));
  }, [agent]);

  useEffect(() => {
    if (!agent) return;
    const poll = () => apiJson<AttendanceMe>('/agents/attendance/me').then(setAttendance).catch(() => {});
    poll();
    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [agent]);

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

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

  // A stale draft/question from the previous conversation must never
  // carry over — Ask AI answers a conversation's content, not the agent's
  // desk, so switching escalations clears it.
  useEffect(() => {
    setCopilotQuestion('');
    setCopilotAnswer(null);
  }, [openEscalation?.id]);

  async function clockIn() {
    try {
      const session = await apiJson<WorkSession>('/agents/clock-in', { method: 'POST' });
      setAttendance((prev) => ({ session, aux: null, today_aux_history: prev?.today_aux_history ?? [] }));
      setActionError(null);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Failed to clock in.');
    }
  }

  async function clockOut() {
    try {
      await apiJson<WorkSession>('/agents/clock-out', { method: 'POST' });
      setAttendance({ session: null, aux: null, today_aux_history: [] });
      setActionError(null);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Failed to clock out.');
    }
  }

  async function changeAux(auxType: string) {
    try {
      if (auxType === '') {
        const aux = await apiJson<AuxEvent>('/agents/aux/end', { method: 'POST' });
        setAttendance((prev) => (prev ? { ...prev, aux: null, today_aux_history: [...prev.today_aux_history.filter((e) => e.id !== aux.id), aux] } : prev));
      } else {
        const aux = await apiJson<AuxEvent>('/agents/aux/start', {
          method: 'POST',
          body: JSON.stringify({ aux_type: auxType }),
        });
        setAttendance((prev) => (prev ? { ...prev, aux } : prev));
      }
      setActionError(null);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Failed to update status.');
    }
  }

  async function acceptEscalation(escalationId: string) {
    try {
      await apiJson('/agent/accept', { method: 'POST', body: JSON.stringify({ escalation_id: escalationId }) });
      const detail = await apiJson<Escalation>(`/agent/escalations/${escalationId}`);
      setOpenEscalation(detail);
      setActionError(null);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Failed to accept escalation.');
    }
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
          <Link to="/" aria-label="Back to HavisIQ" className="transition hover:opacity-70">
            <HavisIQMark />
          </Link>
          <button
            onClick={() => setSection('queue')}
            className="font-display font-semibold text-ink"
          >
            Agent Dashboard
          </button>
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
          {attendance?.session ? (
            <>
              <span
                className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
                  attendance.aux ? 'bg-gold-50 text-gold-700' : 'bg-green-50 text-green-700'
                }`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${attendance.aux ? 'bg-gold-500' : 'bg-green-500'}`} />
                {attendance.aux ? AUX_TYPES.find((t) => t.value === attendance.aux?.aux_type)?.label ?? attendance.aux.aux_type : 'Available'}
              </span>
              <span className="flex items-center gap-1.5 text-xs text-ink/50" title="Session duration">
                <Clock size={13} />
                {formatDuration(Math.floor((now - new Date(attendance.session.clock_in_at).getTime()) / 1000))}
              </span>
              <div className="w-40">
                <Select value={attendance.aux?.aux_type ?? ''} onChange={(e) => changeAux(e.target.value)}>
                  <option value="">Available</option>
                  {AUX_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </Select>
              </div>
              <button onClick={clockOut} className={SECONDARY_BUTTON}>
                Clock Out
              </button>
            </>
          ) : (
            <>
              <span className="flex items-center gap-1.5 rounded-full bg-ink/5 px-2.5 py-1 text-xs font-medium text-ink/50">
                <span className="h-1.5 w-1.5 rounded-full bg-ink/30" />
                Clocked out
              </span>
              <button onClick={clockIn} className={PRIMARY_BUTTON}>
                Clock In
              </button>
            </>
          )}
          <button
            onClick={() => signOut()}
            className="rounded-full p-1.5 text-ink/50 transition hover:bg-paper hover:text-ink"
            aria-label="Sign out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </header>

      {actionError ? (
        <div className="flex items-center justify-between px-6 py-2 border-b border-red-200 bg-red-50 text-sm text-red-700">
          <span>{actionError}</span>
          <button onClick={() => setActionError(null)} className="text-xs font-semibold hover:underline">
            Dismiss
          </button>
        </div>
      ) : null}

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
                  {attendance?.session
                    ? attendance.aux
                      ? AUX_TYPES.find((t) => t.value === attendance.aux?.aux_type)?.label ?? attendance.aux.aux_type
                      : 'Available'
                    : 'Clocked out'}
                </dd>
              </dl>
              {stats ? (
                <div className="grid grid-cols-2 gap-3">
                  <KpiCard
                    label="Current status"
                    value={
                      attendance?.session
                        ? attendance.aux
                          ? AUX_TYPES.find((t) => t.value === attendance.aux?.aux_type)?.label ?? attendance.aux.aux_type
                          : 'Available'
                        : 'Clocked out'
                    }
                    sub={
                      attendance?.session
                        ? formatDuration(
                            Math.floor(
                              (now - new Date(attendance.aux?.started_at ?? attendance.session.clock_in_at).getTime()) / 1000,
                            ),
                          )
                        : undefined
                    }
                  />
                  <KpiCard label="Active conversations" value={myConversations.length} />
                  <KpiCard label="Queue" value={queue.length} />
                  <KpiCard label="Resolved today" value={stats.resolved_today} />
                  <KpiCard
                    label="Resolution rate"
                    value={stats.resolution_rate != null ? `${Math.round(stats.resolution_rate * 100)}%` : '—'}
                    target={targets?.resolution_rate != null ? `${Math.round(targets.resolution_rate * 100)}%` : undefined}
                    met={
                      targets?.resolution_rate != null && stats.resolution_rate != null
                        ? stats.resolution_rate >= targets.resolution_rate
                        : undefined
                    }
                  />
                  <KpiCard
                    label="Avg first response"
                    value={stats.avg_first_response_minutes != null ? `${Math.round(stats.avg_first_response_minutes)}m` : '—'}
                    target={targets?.response_minutes != null ? `${Math.round(targets.response_minutes)}m` : undefined}
                    met={
                      targets?.response_minutes != null && stats.avg_first_response_minutes != null
                        ? stats.avg_first_response_minutes <= targets.response_minutes
                        : undefined
                    }
                  />
                  <KpiCard
                    label="Avg resolution time"
                    value={stats.average_resolution_minutes != null ? `${Math.round(stats.average_resolution_minutes)}m` : '—'}
                    target={targets?.resolution_minutes != null ? `${Math.round(targets.resolution_minutes)}m` : undefined}
                    met={
                      targets?.resolution_minutes != null && stats.average_resolution_minutes != null
                        ? stats.average_resolution_minutes <= targets.resolution_minutes
                        : undefined
                    }
                  />
                </div>
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
