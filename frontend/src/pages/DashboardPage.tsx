import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Bell,
  Check,
  GitCompare,
  LifeBuoy,
  LogOut,
  MessageSquarePlus,
  PanelLeft,
  PanelLeftClose,
  Pencil,
  Search,
  SendHorizonal,
  Star,
  Trash2,
  User as UserIcon,
} from 'lucide-react';
import { HavisIQMark } from '../components/HavisIQMark';
import { MessageContent } from '../components/message/MessageContent';
import { MessageActions } from '../components/message/MessageActions';
import { SourceChips } from '../components/message/SourceChips';
import { isSourceRequest } from '../lib/sourceRequest';
import { CompareSolutionsModal } from '../components/CompareSolutionsModal';
import { DemoRequestModal } from '../components/DemoRequestModal';
import { ConversationStartState } from '../components/ConversationStartState';
import { PageContainer } from '../components/PageContainer';
import { StatusBadge, type BadgeTone } from '../components/StatusBadge';
import { useAuth } from '../lib/authContext';
import { apiJson } from '../lib/apiClient';
import { useSolutions } from '../lib/useSolutions';
import { getSessionId } from '../lib/sessionId';
import { downloadMarkdown, messagesToMarkdown } from '../lib/exportConversation';
import { useSidebarCollapse } from '../lib/useSidebarCollapse';
import { INPUT_CLASS, PRIMARY_BUTTON, SECONDARY_BUTTON } from '../lib/uiClassNames';
import type { Solution } from '../solutions';

type ConversationSummary = {
  id: string;
  title: string;
  created_at: string | null;
  updated_at: string | null;
};

type ConversationMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations: string[];
  metadata: Record<string, unknown>;
  created_at: string | null;
  escalationSuggested?: boolean;
};

type ConversationDetail = {
  conversation: ConversationSummary;
  messages: ConversationMessage[];
};

type EscalationStatus = 'waiting' | 'assigned' | 'active' | 'waiting_for_customer' | 'resolved' | 'closed';

type CustomerEscalationMessage = {
  id: string;
  sender_type: 'agent' | 'customer';
  content: string;
  created_at: string | null;
};

type CustomerEscalation = {
  id: string;
  conversation_id: string | null;
  status: EscalationStatus;
  assigned_agent_name: string | null;
  department: string | null;
  created_at: string | null;
  assigned_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  messages?: CustomerEscalationMessage[] | null;
};

const ESCALATION_STATUS_TONE: Record<EscalationStatus, BadgeTone> = {
  waiting: 'neutral',
  assigned: 'gold',
  active: 'gold',
  waiting_for_customer: 'warning',
  resolved: 'success',
  closed: 'success',
};

const ESCALATION_STATUS_LABEL: Record<EscalationStatus, string> = {
  waiting: 'Waiting for an agent',
  assigned: 'Agent assigned',
  active: 'In progress',
  waiting_for_customer: 'Waiting on you',
  resolved: 'Resolved',
  closed: 'Closed',
};

const ESCALATION_POLL_INTERVAL_MS = 2500;

const TITLE_MAX_LEN = 60;

// Mirrors ConversationService._title_from_message on the backend (same
// 60-char truncation, break on the last whole word) so a conversation's
// title reads consistently regardless of which code path derived it.
function titleFromMessage(message: string): string {
  const collapsed = message.trim().split(/\s+/).join(' ');
  if (collapsed.length <= TITLE_MAX_LEN) return collapsed || 'New conversation';
  const truncated = collapsed.slice(0, TITLE_MAX_LEN);
  const lastSpace = truncated.lastIndexOf(' ');
  return `${lastSpace > 0 ? truncated.slice(0, lastSpace) : truncated}…`;
}

type Section = 'conversations' | 'recommendations' | 'comparisons' | 'profile' | 'notifications';

const SECTIONS: { id: Section; label: string }[] = [
  { id: 'conversations', label: 'Conversations' },
  { id: 'recommendations', label: 'Saved Recommendations' },
  { id: 'comparisons', label: 'Saved Comparisons' },
  { id: 'profile', label: 'Profile' },
  { id: 'notifications', label: 'Notifications' },
];

export function DashboardPage() {
  const { user, signOut } = useAuth();
  const { solutions } = useSolutions();
  const [section, setSection] = useState<Section>('conversations');
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [selected, setSelected] = useState<ConversationDetail | null>(null);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [compareModal, setCompareModal] = useState<{ open: boolean; productIds?: string[] }>({ open: false });
  const [demoModal, setDemoModal] = useState<{ open: boolean; solution?: Solution }>({ open: false });
  const [unreadCount, setUnreadCount] = useState(0);
  const [isPlatformAdmin, setIsPlatformAdmin] = useState(false);
  const [isSupportAgent, setIsSupportAgent] = useState(false);
  const [adminWorkspaces, setAdminWorkspaces] = useState<{ id: string; slug: string; name: string }[]>([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useSidebarCollapse('havisiq-dashboard-sidebar-collapsed');
  const [escalation, setEscalation] = useState<CustomerEscalation | null>(null);
  const [escalationInput, setEscalationInput] = useState('');
  const [isEscalating, setIsEscalating] = useState(false);

  const loadConversations = (search?: string) => {
    setIsLoadingList(true);
    const query = search ? `?search=${encodeURIComponent(search)}` : '';
    apiJson<ConversationSummary[]>(`/conversations${query}`)
      .then(setConversations)
      .catch(() => setConversations([]))
      .finally(() => setIsLoadingList(false));
  };

  useEffect(() => {
    loadConversations();
    apiJson<{ count: number }>('/notifications/unread-count')
      .then((r) => setUnreadCount(r.count))
      .catch(() => setUnreadCount(0));
    // Cheap 403-probes (same pattern as AdminGuard/AgentDashboardPage) so the
    // sidebar can surface Admin/Agent links only to users who actually have
    // those roles, instead of leaving those routes reachable only by typing
    // the URL directly.
    apiJson('/admin/me')
      .then(() => setIsPlatformAdmin(true))
      .catch(() => setIsPlatformAdmin(false));
    apiJson('/agents/me')
      .then(() => setIsSupportAgent(true))
      .catch(() => setIsSupportAgent(false));
    // A workspace_admin (e.g. someone who self-signed-up their own
    // organization, Phase 28) is scoped to specific workspace(s), not a
    // platform-wide role, so it can't use the same true/false 403-probe
    // as isPlatformAdmin/isSupportAgent above — this always succeeds and
    // just returns whichever workspace(s), if any, the user administers.
    apiJson<{ workspaces: { id: string; slug: string; name: string }[] }>('/workspace-admins/me')
      .then((r) => setAdminWorkspaces(r.workspaces))
      .catch(() => setAdminWorkspaces([]));
  }, []);

  // Debounce search-as-you-type so every keystroke doesn't fire a request.
  useEffect(() => {
    const handle = window.setTimeout(() => loadConversations(searchTerm || undefined), 300);
    return () => window.clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchTerm]);

  const openConversation = async (id: string) => {
    setEscalation(null);
    const detail = await apiJson<ConversationDetail>(`/conversations/${id}`);
    setSelected(detail);
    setSection('conversations');
    apiJson<CustomerEscalation | null>(`/chat/conversations/${id}/escalation`)
      .then(setEscalation)
      .catch(() => setEscalation(null));
  };

  const startNewConversation = async (initialMessage?: string) => {
    const trimmedInitial = initialMessage?.trim();
    const row = await apiJson<ConversationSummary>('/conversations', {
      method: 'POST',
      body: JSON.stringify({ first_message: trimmedInitial || null }),
    });
    setConversations((prev) => [row, ...prev]);
    setSelected({ conversation: row, messages: [] });
    setEscalation(null);
    setSection('conversations');
    if (trimmedInitial) {
      await sendMessage(row.id, trimmedInitial);
    }
  };

  const deleteConversation = async (id: string) => {
    await apiJson(`/conversations/${id}`, { method: 'DELETE' });
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (selected?.conversation.id === id) setSelected(null);
  };

  const submitRename = async (id: string) => {
    const title = renameValue.trim();
    setRenamingId(null);
    if (!title) return;
    const row = await apiJson<ConversationSummary>(`/conversations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    });
    setConversations((prev) => prev.map((c) => (c.id === id ? row : c)));
    setSelected((prev) => (prev && prev.conversation.id === id ? { ...prev, conversation: row } : prev));
  };

  // Shared by the bottom "continue this conversation" form and the
  // centered start-state input (ConversationStartState) — both funnel
  // through the same /chat call and optimistic-update logic, keyed by an
  // explicit conversationId rather than reading `selected` from closure,
  // since the start-state flow calls this immediately after creating a
  // brand-new conversation, before that setSelected() has flushed.
  const sendMessage = async (conversationId: string, text: string) => {
    setIsSending(true);

    // A conversation created via the plain "New conversation" sidebar
    // button (no first_message passed) keeps the literal "New
    // conversation" placeholder title until its first message is sent —
    // rename it here so the sidebar reads as something meaningful without
    // requiring a manual rename. Conversations started with an initial
    // message (ConversationStartState) already get a derived title from
    // the backend at creation time, so this only fires for the gap case.
    const shouldAutoTitle =
      selected?.conversation.id === conversationId &&
      selected.messages.length === 0 &&
      selected.conversation.title === 'New conversation';
    if (shouldAutoTitle) {
      apiJson<ConversationSummary>(`/conversations/${conversationId}`, {
        method: 'PATCH',
        body: JSON.stringify({ title: titleFromMessage(text) }),
      })
        .then((row) => {
          setConversations((prev) => prev.map((c) => (c.id === conversationId ? row : c)));
          setSelected((prev) => (prev && prev.conversation.id === conversationId ? { ...prev, conversation: row } : prev));
        })
        .catch(() => {});
    }

    const optimisticUser: ConversationMessage = {
      id: `local-${Date.now()}`,
      role: 'user',
      content: text,
      citations: [],
      metadata: {},
      created_at: null,
    };
    setSelected((prev) =>
      prev && prev.conversation.id === conversationId ? { ...prev, messages: [...prev.messages, optimisticUser] } : prev
    );

    try {
      const response = await apiJson<{
        answer: string;
        sources: string[];
        session_id: string | null;
        escalation_recommended?: boolean;
      }>('/chat', {
        method: 'POST',
        body: JSON.stringify({
          message: text,
          session_id: getSessionId(),
          conversation_id: conversationId,
        }),
      });

      const assistantMessage: ConversationMessage = {
        id: `local-${Date.now() + 1}`,
        role: 'assistant',
        content: response.answer,
        citations: response.sources || [],
        metadata: {},
        created_at: null,
        escalationSuggested: Boolean(response.escalation_recommended),
      };
      setSelected((prev) =>
        prev && prev.conversation.id === conversationId ? { ...prev, messages: [...prev.messages, assistantMessage] } : prev
      );
      setConversations((prev) =>
        prev.map((c) => (c.id === conversationId ? { ...c, updated_at: new Date().toISOString() } : c))
      );
    } finally {
      setIsSending(false);
    }
  };

  const handleSend = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isSending || !selected) return;
    setInput('');
    await sendMessage(selected.conversation.id, trimmed);
  };

  const requestHumanEscalation = async (question?: string) => {
    if (!selected || isEscalating) return;
    setIsEscalating(true);
    try {
      const lastUserMessage = [...selected.messages].reverse().find((m) => m.role === 'user')?.content;
      const result = await apiJson<CustomerEscalation>('/chat/escalate', {
        method: 'POST',
        body: JSON.stringify({
          conversation_id: selected.conversation.id,
          question: question || lastUserMessage || "I'd like to talk to a human.",
        }),
      });
      setEscalation(result);
    } finally {
      setIsEscalating(false);
    }
  };

  const handleSendEscalationMessage = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = escalationInput.trim();
    if (!trimmed || !escalation) return;
    setEscalationInput('');
    const optimistic: CustomerEscalationMessage = { id: `local-${Date.now()}`, sender_type: 'customer', content: trimmed, created_at: null };
    setEscalation((prev) => (prev ? { ...prev, messages: [...(prev.messages ?? []), optimistic] } : prev));
    await apiJson(`/agent/escalations/${escalation.id}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content: trimmed }),
    });
    const refreshed = await apiJson<CustomerEscalation>(`/chat/escalations/${escalation.id}`);
    setEscalation(refreshed);
  };

  // Poll the open escalation thread while it's live, mirroring
  // AgentDashboardPage's poll pattern — stops once resolved/closed so a
  // finished thread doesn't keep getting hammered.
  useEffect(() => {
    if (!escalation || escalation.status === 'resolved' || escalation.status === 'closed') return;
    const escalationId = escalation.id;
    const interval = window.setInterval(() => {
      apiJson<CustomerEscalation>(`/chat/escalations/${escalationId}`)
        .then(setEscalation)
        .catch(() => {});
    }, ESCALATION_POLL_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [escalation?.id, escalation?.status]);

  const handleExport = () => {
    if (!selected || selected.messages.length === 0) return;
    const markdown = messagesToMarkdown(
      selected.conversation.title,
      selected.messages.map((m) => ({ role: m.role, content: m.content, sources: m.citations }))
    );
    downloadMarkdown(`${selected.conversation.title.slice(0, 40)}.md`, markdown);
  };

  return (
    <div className="relative flex h-screen overflow-hidden bg-paper text-ink">
      {sidebarCollapsed ? (
        <button
          onClick={() => setSidebarCollapsed(false)}
          className="absolute left-3 top-3 z-10 rounded-full border border-ink/10 bg-white p-2 text-ink/60 shadow-sm transition hover:text-ink"
          aria-label="Show sidebar"
        >
          <PanelLeft size={16} />
        </button>
      ) : null}
      <aside
        className={`sticky top-0 flex h-screen shrink-0 flex-col gap-6 overflow-hidden border-r border-ink/10 bg-white/70 py-6 transition-[width] duration-200 ${
          sidebarCollapsed ? 'w-0 px-0 border-r-0' : 'w-72 px-5'
        }`}
      >
        <div className="flex items-center justify-between gap-2">
          <Link to="/" className="flex items-center gap-3 min-w-0">
            <HavisIQMark size={36} />
            <div className="min-w-0">
              <p className="font-display text-base tracking-tight">HavisIQ</p>
              <p className="text-[10px] uppercase tracking-[0.28em] text-ink/50">Customer Dashboard</p>
            </div>
          </Link>
          <div className="flex shrink-0 items-center gap-1">
            <button
              onClick={() => setSection('notifications')}
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
            <button
              onClick={() => setSidebarCollapsed(true)}
              className="rounded-full p-1.5 text-ink/50 transition hover:bg-paper hover:text-ink"
              aria-label="Hide sidebar"
            >
              <PanelLeftClose size={18} />
            </button>
          </div>
        </div>

        <nav className="flex flex-col gap-1 text-sm font-medium text-ink/70">
          {SECTIONS.map((item) => (
            <button
              key={item.id}
              onClick={() => setSection(item.id)}
              className={`flex items-center justify-between rounded-xl px-3 py-2 text-left transition ${
                section === item.id ? 'bg-ink text-paper' : 'hover:bg-paper'
              }`}
            >
              {item.label}
              {item.id === 'notifications' && unreadCount > 0 ? (
                <span
                  className={`rounded-full px-1.5 py-0.5 text-[10px] font-bold ${
                    section === item.id ? 'bg-white/20 text-paper' : 'bg-gold-100 text-gold-700'
                  }`}
                >
                  {unreadCount}
                </span>
              ) : null}
            </button>
          ))}
        </nav>

        {section === 'conversations' ? (
          <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-hidden">
            <button
              onClick={startNewConversation}
              className="flex items-center gap-2 rounded-xl border border-ink/10 px-3 py-2 text-sm font-semibold text-ink transition hover:bg-paper"
            >
              <MessageSquarePlus size={16} /> New conversation
            </button>
            <div className="relative">
              <Search size={13} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink/30" />
              <input
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search conversations..."
                aria-label="Search conversations"
                className="w-full rounded-xl border border-ink/10 bg-white py-2 pl-8 pr-3 text-xs outline-none focus:border-gold-400"
              />
            </div>
            <div className="flex-1 space-y-1 overflow-y-auto">
              {isLoadingList ? <SkeletonRows count={4} /> : null}
              {!isLoadingList && conversations.length === 0 ? (
                <p className="px-2 py-3 text-xs text-ink/40">
                  {searchTerm ? `No conversations match "${searchTerm}".` : 'No conversations yet.'}
                </p>
              ) : null}
              {conversations.map((c) => (
                <div
                  key={c.id}
                  className={`group flex items-center gap-1 rounded-xl px-2 py-2 text-sm transition ${
                    selected?.conversation.id === c.id ? 'bg-gold-100' : 'hover:bg-paper'
                  }`}
                >
                  {renamingId === c.id ? (
                    <input
                      autoFocus
                      value={renameValue}
                      onChange={(e) => setRenameValue(e.target.value)}
                      onBlur={() => submitRename(c.id)}
                      onKeyDown={(e) => e.key === 'Enter' && submitRename(c.id)}
                      className="flex-1 rounded-lg border border-ink/10 bg-white px-2 py-1 text-sm outline-none"
                    />
                  ) : (
                    <button onClick={() => openConversation(c.id)} className="flex-1 truncate text-left">
                      {c.title}
                    </button>
                  )}
                  <button
                    onClick={() => {
                      setRenamingId(c.id);
                      setRenameValue(c.title);
                    }}
                    className="hidden rounded p-1 text-ink/40 hover:text-ink group-hover:block"
                    aria-label={`Rename ${c.title}`}
                  >
                    <Pencil size={13} />
                  </button>
                  <button
                    onClick={() => deleteConversation(c.id)}
                    className="hidden rounded p-1 text-ink/40 hover:text-red-600 group-hover:block"
                    aria-label={`Delete ${c.title}`}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {isPlatformAdmin || isSupportAgent || adminWorkspaces.length > 0 ? (
          <div className="flex flex-col gap-1 border-t border-ink/10 pt-3 text-sm font-medium text-ink/70">
            {isPlatformAdmin ? (
              <Link to="/admin" className="rounded-xl px-3 py-2 transition hover:bg-paper hover:text-ink">
                Admin Dashboard
              </Link>
            ) : null}
            {isSupportAgent ? (
              <Link to="/agent" className="rounded-xl px-3 py-2 transition hover:bg-paper hover:text-ink">
                Agent Dashboard
              </Link>
            ) : null}
            {adminWorkspaces.map((workspace) => (
              <Link
                key={workspace.id}
                to={`/admin/workspaces/${workspace.id}`}
                className="rounded-xl px-3 py-2 transition hover:bg-paper hover:text-ink"
              >
                {workspace.name} (Admin)
              </Link>
            ))}
          </div>
        ) : null}

        <div className="mt-auto flex items-center gap-2.5 border-t border-ink/10 pt-4 text-sm">
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-ink text-xs font-semibold uppercase text-paper"
            aria-hidden="true"
          >
            {(user?.full_name || user?.email || '?').slice(0, 1)}
          </div>
          <div className="min-w-0 flex-1 truncate">
            <p className="truncate font-medium">{user?.full_name || user?.email}</p>
            <p className="truncate text-xs text-ink/50">{user?.email}</p>
          </div>
          <button onClick={() => signOut()} className="shrink-0 rounded-lg p-2 text-ink/50 hover:bg-paper hover:text-ink" aria-label="Sign out">
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto p-8">
        <PageContainer className={section === 'conversations' ? 'flex h-full flex-col' : ''}>
        {section === 'conversations' ? (
          selected ? (
            <div className="flex h-full flex-col">
              <div className="mb-4 flex items-center justify-between gap-3">
                <h2 className="font-display text-xl">{selected.conversation.title}</h2>
                <div className="flex shrink-0 items-center gap-2">
                  {!escalation || escalation.status === 'resolved' || escalation.status === 'closed' ? (
                    <button
                      onClick={() => requestHumanEscalation()}
                      disabled={isEscalating}
                      className={`flex items-center gap-1.5 ${SECONDARY_BUTTON} disabled:cursor-not-allowed disabled:opacity-50`}
                    >
                      <LifeBuoy size={13} /> {isEscalating ? 'Requesting…' : 'Talk to a human'}
                    </button>
                  ) : null}
                  {selected.messages.length > 0 ? (
                    <button
                      onClick={handleExport}
                      className="rounded-full border border-ink/15 px-3 py-1.5 text-xs font-semibold text-ink transition hover:border-gold-400 hover:text-gold-700"
                    >
                      Export
                    </button>
                  ) : null}
                </div>
              </div>
              <div className="flex-1 space-y-4 overflow-y-auto">
                <div className="max-h-[50vh] space-y-4 overflow-y-auto rounded-2xl border border-ink/10 bg-white p-5">
                  {selected.messages.length === 0 ? (
                    <p className="text-sm text-ink/50">Ask HavisIQ anything to continue this conversation.</p>
                  ) : null}
                  {selected.messages.map((m) => {
                    const precedingQuestion =
                      m.role === 'assistant'
                        ? selected.messages[selected.messages.indexOf(m) - 1]?.content ?? ''
                        : '';
                    return (
                      <div key={m.id} className={m.role === 'user' ? 'text-right' : 'text-left'}>
                        <div
                          className={`inline-block max-w-2xl rounded-2xl px-4 py-2.5 text-sm ${
                            m.role === 'user' ? 'bg-ink text-paper' : 'bg-paper text-ink'
                          }`}
                        >
                          {m.role === 'assistant' ? (
                            <MessageContent content={m.content} solutions={solutions} />
                          ) : (
                            m.content
                          )}
                          {m.role === 'assistant' && m.citations.length > 0 && isSourceRequest(precedingQuestion) ? (
                            <div className="mt-1"><SourceChips sources={m.citations} /></div>
                          ) : null}
                        </div>
                        {m.role === 'assistant' ? (
                          <div className="flex justify-start">
                            <MessageActions
                              question={precedingQuestion}
                              answer={m.content}
                              conversationId={selected.conversation.id}
                            />
                          </div>
                        ) : null}
                        {m.role === 'assistant' && m.escalationSuggested && !escalation ? (
                          <div className="mt-2 flex flex-wrap items-center gap-2 rounded-xl border border-gold-200 bg-gold-50 px-3 py-2 text-xs text-gold-700">
                            <span>Would you like to talk to a human about this?</span>
                            <button
                              onClick={() => requestHumanEscalation(precedingQuestion || m.content)}
                              className="font-semibold underline"
                            >
                              Talk to a human
                            </button>
                          </div>
                        ) : null}
                      </div>
                    );
                  })}
                </div>

                {escalation ? (
                  <div className="rounded-2xl border border-ink/10 bg-white p-5">
                    <div className="mb-3 flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 text-ink">
                        <LifeBuoy size={16} className="text-gold-600" />
                        <h3 className="font-display text-base">
                          {escalation.assigned_agent_name
                            ? `Talking with ${escalation.assigned_agent_name}`
                            : 'Waiting for an agent…'}
                        </h3>
                      </div>
                      <StatusBadge tone={ESCALATION_STATUS_TONE[escalation.status]}>
                        {ESCALATION_STATUS_LABEL[escalation.status]}
                      </StatusBadge>
                    </div>
                    <div className="max-h-72 space-y-3 overflow-y-auto">
                      {(escalation.messages ?? []).length === 0 ? (
                        <p className="text-sm text-ink/50">A member of our support team will join shortly.</p>
                      ) : null}
                      {(escalation.messages ?? []).map((m) => (
                        <div key={m.id} className={m.sender_type === 'customer' ? 'text-right' : 'text-left'}>
                          <span
                            className={`inline-block max-w-md rounded-2xl px-4 py-2 text-sm ${
                              m.sender_type === 'customer' ? 'bg-ink text-paper' : 'bg-paper text-ink'
                            }`}
                          >
                            {m.content}
                          </span>
                        </div>
                      ))}
                    </div>
                    {escalation.status !== 'resolved' && escalation.status !== 'closed' ? (
                      <form onSubmit={handleSendEscalationMessage} className="mt-3 flex items-center gap-2">
                        <input
                          value={escalationInput}
                          onChange={(e) => setEscalationInput(e.target.value)}
                          placeholder="Message the agent..."
                          className={`flex-1 ${INPUT_CLASS} mt-0`}
                        />
                        <button type="submit" className={PRIMARY_BUTTON}>Send</button>
                      </form>
                    ) : null}
                  </div>
                ) : null}
              </div>
              <form onSubmit={handleSend} className="mt-4 flex items-center gap-2">
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Continue this conversation..."
                  className="flex-1 rounded-full border border-ink/10 bg-white px-4 py-3 text-sm outline-none focus:border-gold-400"
                />
                <button
                  type="submit"
                  disabled={isSending}
                  className="rounded-full bg-ink p-3 text-paper disabled:opacity-60"
                  aria-label="Send"
                >
                  <SendHorizonal size={16} />
                </button>
              </form>
            </div>
          ) : (
            <ConversationStartState
              userName={user?.full_name}
              isSending={isSending}
              onSubmit={(message) => startNewConversation(message)}
              onOpenCompare={() => setCompareModal({ open: true })}
              onGoToSavedRecommendations={() => setSection('recommendations')}
            />
          )
        ) : null}

        {section === 'recommendations' ? <SavedRecommendationsSection /> : null}

        {section === 'comparisons' ? (
          <SavedComparisonsSection onOpen={(productIds) => setCompareModal({ open: true, productIds })} />
        ) : null}

        {section === 'profile' ? <ProfileSection /> : null}

        {section === 'notifications' ? (
          <NotificationsSection onUnreadCountChange={setUnreadCount} />
        ) : null}
        </PageContainer>
      </main>

      <CompareSolutionsModal
        isOpen={compareModal.open}
        onClose={() => setCompareModal({ open: false })}
        solutions={solutions}
        initialSelectedIds={compareModal.productIds}
        onRequestDemo={(solution) => setDemoModal({ open: true, solution })}
      />
      <DemoRequestModal
        isOpen={demoModal.open}
        onClose={() => setDemoModal({ open: false })}
        product={demoModal.solution?.id}
        productLabel={demoModal.solution?.name}
      />
    </div>
  );
}

function SkeletonRows({ count }: { count: number }) {
  return (
    <div className="space-y-1.5" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="h-9 animate-pulse rounded-xl bg-ink/5" />
      ))}
    </div>
  );
}

function SkeletonCards({ count }: { count: number }) {
  return (
    <div className="max-w-2xl space-y-3" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="h-16 animate-pulse rounded-2xl bg-ink/5" />
      ))}
    </div>
  );
}

type Notification = { id: string; type: string; title: string; body: string | null; is_read: boolean; created_at: string | null };

const NOTIFICATION_ICON: Record<string, string> = {
  demo_request: '📅',
  appointment: '🗓️',
  saved_recommendation: '⭐',
  support_update: '💬',
};

function NotificationsSection({ onUnreadCountChange }: { onUnreadCountChange: (count: number) => void }) {
  const [items, setItems] = useState<Notification[] | null>(null);

  const load = () => {
    apiJson<Notification[]>('/notifications')
      .then(setItems)
      .catch(() => setItems([]));
  };

  useEffect(() => {
    load();
  }, []);

  const markRead = async (id: string) => {
    await apiJson(`/notifications/${id}/read`, { method: 'POST' });
    setItems((prev) => {
      const next = prev ? prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)) : prev;
      onUnreadCountChange(next ? next.filter((n) => !n.is_read).length : 0);
      return next;
    });
  };

  const markAllRead = async () => {
    await apiJson('/notifications/read-all', { method: 'POST' });
    setItems((prev) => (prev ? prev.map((n) => ({ ...n, is_read: true })) : prev));
    onUnreadCountChange(0);
  };

  if (items === null) return <SkeletonCards count={3} />;
  if (items.length === 0) {
    return (
      <EmptyState
        icon={<Bell size={28} />}
        title="Notifications"
        body="Updates on demo requests, appointments, and saved recommendations will show up here."
      />
    );
  }

  const hasUnread = items.some((n) => !n.is_read);

  return (
    <div className="max-w-2xl space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl text-ink">Notifications</h2>
        {hasUnread ? (
          <button onClick={markAllRead} className="flex items-center gap-1 text-xs font-semibold text-ink/60 hover:text-ink">
            <Check size={13} /> Mark all read
          </button>
        ) : null}
      </div>
      {items.map((item) => (
        <button
          key={item.id}
          onClick={() => !item.is_read && markRead(item.id)}
          className={`flex w-full items-start gap-3 rounded-2xl border p-4 text-left transition ${
            item.is_read ? 'border-ink/10 bg-white' : 'border-gold-300 bg-gold-50/60'
          }`}
        >
          <span className="text-lg" aria-hidden="true">{NOTIFICATION_ICON[item.type] ?? '🔔'}</span>
          <div className="min-w-0 flex-1">
            <p className="font-medium text-ink">{item.title}</p>
            {item.body ? <p className="mt-0.5 text-sm text-ink/60">{item.body}</p> : null}
            {item.created_at ? (
              <p className="mt-1 text-xs text-ink/35">{new Date(item.created_at).toLocaleString()}</p>
            ) : null}
          </div>
          {!item.is_read ? <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-gold-500" aria-hidden="true" /> : null}
        </button>
      ))}
    </div>
  );
}

type SavedComparison = { id: string; product_ids: string[]; created_at: string | null };

function SavedComparisonsSection({ onOpen }: { onOpen: (productIds: string[]) => void }) {
  const { solutions } = useSolutions();
  const [items, setItems] = useState<SavedComparison[] | null>(null);

  const load = () => {
    apiJson<SavedComparison[]>('/saved-comparisons')
      .then(setItems)
      .catch(() => setItems([]));
  };

  useEffect(() => {
    load();
  }, []);

  const remove = async (id: string) => {
    await apiJson(`/saved-comparisons/${id}`, { method: 'DELETE' });
    setItems((prev) => (prev ? prev.filter((c) => c.id !== id) : prev));
  };

  if (items === null) return <SkeletonCards count={3} />;
  if (items.length === 0) {
    return (
      <EmptyState
        icon={<GitCompare size={28} />}
        title="Saved comparisons"
        body="Solution comparisons you save will show up here."
      />
    );
  }

  const nameFor = (id: string) => solutions.find((s) => s.id === id)?.name || id;

  return (
    <div className="max-w-2xl space-y-3">
      <h2 className="font-display text-xl text-ink">Saved comparisons</h2>
      {items.map((item) => (
        <div key={item.id} className="flex items-center justify-between rounded-2xl border border-ink/10 bg-white p-4">
          <div>
            <p className="font-medium text-ink">{item.product_ids.map(nameFor).join(' vs. ')}</p>
            {item.created_at ? (
              <p className="text-xs text-ink/40">{new Date(item.created_at).toLocaleDateString()}</p>
            ) : null}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onOpen(item.product_ids)}
              className="rounded-full border border-ink/15 px-3 py-1.5 text-xs font-semibold text-ink transition hover:border-gold-400 hover:text-gold-700"
            >
              Open
            </button>
            <button
              onClick={() => remove(item.id)}
              className="rounded-lg p-1.5 text-ink/40 hover:text-red-600"
              aria-label={`Remove comparison of ${item.product_ids.map(nameFor).join(', ')}`}
            >
              <Trash2 size={14} />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

type SavedRecommendation = {
  id: string;
  products: string[];
  question: string;
  recommendation: string;
  created_at: string | null;
};

function SavedRecommendationsSection() {
  const [items, setItems] = useState<SavedRecommendation[] | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    apiJson<SavedRecommendation[]>('/saved-recommendations')
      .then(setItems)
      .catch(() => setItems([]));
  }, []);

  const remove = async (id: string) => {
    await apiJson(`/saved-recommendations/${id}`, { method: 'DELETE' });
    setItems((prev) => (prev ? prev.filter((r) => r.id !== id) : prev));
  };

  if (items === null) return <SkeletonCards count={3} />;
  if (items.length === 0) {
    return (
      <EmptyState
        icon={<Star size={28} />}
        title="Saved recommendations"
        body="Recommendations you save from HavisIQ's advisor will show up here."
      />
    );
  }

  return (
    <div className="max-w-2xl space-y-3">
      <h2 className="font-display text-xl text-ink">Saved recommendations</h2>
      {items.map((item) => {
        const isOpen = expandedId === item.id;
        return (
          <div key={item.id} className="rounded-2xl border border-ink/10 bg-white p-4">
            <div className="flex items-start justify-between gap-3">
              <button
                onClick={() => setExpandedId(isOpen ? null : item.id)}
                className="flex-1 text-left"
                aria-expanded={isOpen}
              >
                <p className="font-medium text-ink">{item.products.join(', ')}</p>
                <p className="mt-0.5 truncate text-xs text-ink/50">{item.question}</p>
              </button>
              <button
                onClick={() => remove(item.id)}
                className="shrink-0 rounded-lg p-1.5 text-ink/40 hover:text-red-600"
                aria-label={`Remove recommendation for ${item.products.join(', ')}`}
              >
                <Trash2 size={14} />
              </button>
            </div>
            {isOpen ? <p className="mt-3 text-sm leading-6 text-ink/70">{item.recommendation}</p> : null}
          </div>
        );
      })}
    </div>
  );
}

function EmptyState({ icon, title, body }: { icon: React.ReactNode; title: string; body?: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 text-center text-ink/50">
      <div className="rounded-full bg-white p-4 shadow-sm">{icon}</div>
      <p className="font-display text-lg text-ink">{title}</p>
      {body ? <p className="max-w-sm text-sm">{body}</p> : null}
    </div>
  );
}

type Profile = {
  id: string;
  email: string;
  full_name: string | null;
  company_name: string | null;
  industry: string | null;
  phone: string | null;
};

function ProfileSection() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved'>('idle');

  useEffect(() => {
    apiJson<Profile>('/profile').then(setProfile);
  }, []);

  if (!profile) {
    return (
      <div className="max-w-md space-y-4" aria-hidden="true">
        <div className="h-6 w-40 animate-pulse rounded bg-ink/5" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-12 animate-pulse rounded-2xl bg-ink/5" />
        ))}
      </div>
    );
  }

  const handleSave = async (event: FormEvent) => {
    event.preventDefault();
    setStatus('saving');
    const updated = await apiJson<Profile>('/profile', {
      method: 'PATCH',
      body: JSON.stringify({
        full_name: profile.full_name,
        company_name: profile.company_name,
        industry: profile.industry,
        phone: profile.phone,
      }),
    });
    setProfile(updated);
    setStatus('saved');
  };

  return (
    <form onSubmit={handleSave} className="max-w-md space-y-4">
      <div className="flex items-center gap-2 text-ink/70">
        <UserIcon size={18} />
        <h2 className="font-display text-xl text-ink">Your profile</h2>
      </div>
      <Field label="Email" value={profile.email} disabled />
      <Field
        label="Full name"
        value={profile.full_name || ''}
        onChange={(v) => setProfile({ ...profile, full_name: v })}
      />
      <Field
        label="Company"
        value={profile.company_name || ''}
        onChange={(v) => setProfile({ ...profile, company_name: v })}
      />
      <Field label="Industry" value={profile.industry || ''} onChange={(v) => setProfile({ ...profile, industry: v })} />
      <Field label="Phone" value={profile.phone || ''} onChange={(v) => setProfile({ ...profile, phone: v })} />
      <button type="submit" className="rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-paper">
        {status === 'saving' ? 'Saving...' : status === 'saved' ? 'Saved' : 'Save changes'}
      </button>
    </form>
  );
}

function Field({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: string;
  onChange?: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium uppercase tracking-wide text-ink/50">{label}</label>
      <input
        value={value}
        disabled={disabled}
        onChange={(e) => onChange?.(e.target.value)}
        className="rounded-2xl border border-ink/10 bg-white px-4 py-2.5 text-sm outline-none focus:border-gold-400 disabled:bg-paper disabled:text-ink/50"
      />
    </div>
  );
}
