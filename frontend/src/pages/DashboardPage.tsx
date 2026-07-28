import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Bell,
  GitCompare,
  LogOut,
  MessageSquarePlus,
  Pencil,
  SendHorizonal,
  Star,
  Trash2,
  User as UserIcon,
} from 'lucide-react';
import { HavisIQMark } from '../components/HavisIQMark';
import { MessageContent } from '../components/message/MessageContent';
import { SourceChips } from '../components/message/SourceChips';
import { CompareSolutionsModal } from '../components/CompareSolutionsModal';
import { DemoRequestModal } from '../components/DemoRequestModal';
import { useAuth } from '../lib/authContext';
import { apiJson } from '../lib/apiClient';
import { useSolutions } from '../lib/useSolutions';
import { getSessionId } from '../lib/sessionId';
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
};

type ConversationDetail = {
  conversation: ConversationSummary;
  messages: ConversationMessage[];
};

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
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [compareModal, setCompareModal] = useState<{ open: boolean; productIds?: string[] }>({ open: false });
  const [demoModal, setDemoModal] = useState<{ open: boolean; solution?: Solution }>({ open: false });

  const loadConversations = () => {
    setIsLoadingList(true);
    apiJson<ConversationSummary[]>('/conversations')
      .then(setConversations)
      .catch(() => setConversations([]))
      .finally(() => setIsLoadingList(false));
  };

  useEffect(() => {
    loadConversations();
  }, []);

  const openConversation = async (id: string) => {
    const detail = await apiJson<ConversationDetail>(`/conversations/${id}`);
    setSelected(detail);
    setSection('conversations');
  };

  const startNewConversation = async () => {
    const row = await apiJson<ConversationSummary>('/conversations', {
      method: 'POST',
      body: JSON.stringify({}),
    });
    setConversations((prev) => [row, ...prev]);
    setSelected({ conversation: row, messages: [] });
    setSection('conversations');
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

  const handleSend = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isSending || !selected) return;
    setIsSending(true);
    setInput('');

    const optimisticUser: ConversationMessage = {
      id: `local-${Date.now()}`,
      role: 'user',
      content: trimmed,
      citations: [],
      metadata: {},
      created_at: null,
    };
    setSelected((prev) => (prev ? { ...prev, messages: [...prev.messages, optimisticUser] } : prev));

    try {
      const response = await apiJson<{ answer: string; sources: string[]; session_id: string | null }>('/chat', {
        method: 'POST',
        body: JSON.stringify({
          message: trimmed,
          session_id: getSessionId(),
          conversation_id: selected.conversation.id,
        }),
      });

      const assistantMessage: ConversationMessage = {
        id: `local-${Date.now() + 1}`,
        role: 'assistant',
        content: response.answer,
        citations: response.sources || [],
        metadata: {},
        created_at: null,
      };
      setSelected((prev) => (prev ? { ...prev, messages: [...prev.messages, assistantMessage] } : prev));
      setConversations((prev) =>
        prev.map((c) => (c.id === selected.conversation.id ? { ...c, updated_at: new Date().toISOString() } : c))
      );
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-paper text-ink">
      <aside className="sticky top-0 flex h-screen w-72 shrink-0 flex-col gap-6 border-r border-ink/10 bg-white/70 px-5 py-6">
        <Link to="/" className="flex items-center gap-3">
          <HavisIQMark size={36} />
          <div>
            <p className="font-display text-base tracking-tight">HavisIQ</p>
            <p className="text-[10px] uppercase tracking-[0.28em] text-ink/50">Customer Dashboard</p>
          </div>
        </Link>

        <nav className="flex flex-col gap-1 text-sm font-medium text-ink/70">
          {SECTIONS.map((item) => (
            <button
              key={item.id}
              onClick={() => setSection(item.id)}
              className={`rounded-xl px-3 py-2 text-left transition ${
                section === item.id ? 'bg-ink text-paper' : 'hover:bg-paper'
              }`}
            >
              {item.label}
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
            <div className="flex-1 space-y-1 overflow-y-auto">
              {isLoadingList ? <p className="px-2 py-3 text-xs text-ink/40">Loading...</p> : null}
              {!isLoadingList && conversations.length === 0 ? (
                <p className="px-2 py-3 text-xs text-ink/40">No conversations yet.</p>
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
                    aria-label="Rename"
                  >
                    <Pencil size={13} />
                  </button>
                  <button
                    onClick={() => deleteConversation(c.id)}
                    className="hidden rounded p-1 text-ink/40 hover:text-red-600 group-hover:block"
                    aria-label="Delete"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
            </div>
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
        {section === 'conversations' ? (
          selected ? (
            <div className="flex h-full flex-col">
              <h2 className="mb-4 font-display text-xl">{selected.conversation.title}</h2>
              <div className="flex-1 space-y-4 overflow-y-auto rounded-2xl border border-ink/10 bg-white p-5">
                {selected.messages.length === 0 ? (
                  <p className="text-sm text-ink/50">Ask HavisIQ anything to continue this conversation.</p>
                ) : null}
                {selected.messages.map((m) => (
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
                    </div>
                    {m.role === 'assistant' && m.citations.length > 0 ? (
                      <div className="mt-1"><SourceChips sources={m.citations} /></div>
                    ) : null}
                  </div>
                ))}
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
            <EmptyState icon={<MessageSquarePlus size={28} />} title="Select or start a conversation" />
          )
        ) : null}

        {section === 'recommendations' ? <SavedRecommendationsSection /> : null}

        {section === 'comparisons' ? (
          <SavedComparisonsSection onOpen={(productIds) => setCompareModal({ open: true, productIds })} />
        ) : null}

        {section === 'profile' ? <ProfileSection /> : null}

        {section === 'notifications' ? (
          <EmptyState icon={<Bell size={28} />} title="Notifications" body="Nothing to show yet." />
        ) : null}
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

  if (items === null) return <p className="text-sm text-ink/50">Loading...</p>;
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
              aria-label="Remove"
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

  if (items === null) return <p className="text-sm text-ink/50">Loading...</p>;
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
              <button onClick={() => setExpandedId(isOpen ? null : item.id)} className="flex-1 text-left">
                <p className="font-medium text-ink">{item.products.join(', ')}</p>
                <p className="mt-0.5 truncate text-xs text-ink/50">{item.question}</p>
              </button>
              <button
                onClick={() => remove(item.id)}
                className="shrink-0 rounded-lg p-1.5 text-ink/40 hover:text-red-600"
                aria-label="Remove"
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

  if (!profile) return <p className="text-sm text-ink/50">Loading...</p>;

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
