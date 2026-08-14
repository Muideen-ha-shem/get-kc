import { FormEvent, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Calendar, GitCompare, LifeBuoy, MessageSquare, Star, ThumbsDown, ThumbsUp } from 'lucide-react';
import { apiJson } from '../../lib/apiClient';
import { ConfirmDeleteModal } from '../../components/ConfirmDeleteModal';
import { MetricCard } from '../../components/MetricCard';
import { CARD, DANGER_BUTTON, INPUT_CLASS, PRIMARY_BUTTON, SECONDARY_BUTTON } from '../../lib/uiClassNames';
import { AdminLayout } from './AdminLayout';
import type {
  FeatureFlag,
  WorkspaceAdmin,
  WorkspaceAnalytics,
  WorkspaceProduct,
  WorkspaceReport,
  WorkspaceSettings,
} from './adminTypes';

type Tab = 'branding' | 'settings' | 'products' | 'flags' | 'apikey' | 'analytics' | 'report' | 'operations';

const TABS: Tab[] = ['branding', 'settings', 'products', 'flags', 'apikey', 'analytics', 'report', 'operations'];

function BrandingTab({ workspace, onSaved }: { workspace: WorkspaceAdmin; onSaved: (w: WorkspaceAdmin) => void }) {
  const [logo, setLogo] = useState(workspace.logo ?? '');
  const [primaryColor, setPrimaryColor] = useState(workspace.primary_color ?? '#2563eb');
  const [welcomeMessage, setWelcomeMessage] = useState(workspace.welcome_message ?? '');

  async function submit(event: FormEvent) {
    event.preventDefault();
    const updated = await apiJson<WorkspaceAdmin>(`/admin/workspaces/${workspace.id}/branding`, {
      method: 'PATCH',
      body: JSON.stringify({ logo: logo || null, primary_color: primaryColor, welcome_message: welcomeMessage || null }),
    });
    onSaved(updated);
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-3 max-w-md">
      <label className="text-sm text-ink">
        Logo URL
        <input value={logo} onChange={(e) => setLogo(e.target.value)} className={INPUT_CLASS} />
      </label>
      <label className="text-sm text-ink">
        Primary color
        <input type="color" value={primaryColor} onChange={(e) => setPrimaryColor(e.target.value)} className={`${INPUT_CLASS} h-10`} />
      </label>
      <label className="text-sm text-ink">
        Welcome message
        <input value={welcomeMessage} onChange={(e) => setWelcomeMessage(e.target.value)} className={INPUT_CLASS} />
      </label>
      <button type="submit" className={`${PRIMARY_BUTTON} self-start`}>
        Save Branding
      </button>
    </form>
  );
}

function SettingsTab({ workspaceId }: { workspaceId: string }) {
  const [settings, setSettings] = useState<WorkspaceSettings | null>(null);

  useEffect(() => {
    apiJson<WorkspaceSettings>(`/admin/workspaces/${workspaceId}/settings`).then(setSettings).catch(() => {});
  }, [workspaceId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!settings) return;
    const updated = await apiJson<WorkspaceSettings>(`/admin/workspaces/${workspaceId}/settings`, {
      method: 'PATCH',
      body: JSON.stringify({
        ai_enabled: settings.ai_enabled,
        live_search_enabled: settings.live_search_enabled,
        human_escalation_enabled: settings.human_escalation_enabled,
        chat_enabled: settings.chat_enabled,
        offline_mode: settings.offline_mode,
        auto_assignment_enabled: settings.auto_assignment_enabled,
        greeting_message: settings.greeting_message,
        company_name: settings.company_name,
        footer_text: settings.footer_text,
        target_resolution_rate: settings.target_resolution_rate,
        target_response_minutes: settings.target_response_minutes,
        target_resolution_minutes: settings.target_resolution_minutes,
        target_csat: settings.target_csat,
      }),
    });
    setSettings(updated);
  }

  if (!settings) return <p className="text-sm text-ink/40">Loading…</p>;

  const toggle = (key: keyof WorkspaceSettings) => (
    <label className="flex items-center gap-2 text-sm text-ink">
      <input
        type="checkbox"
        checked={Boolean(settings[key])}
        onChange={(e) => setSettings({ ...settings, [key]: e.target.checked })}
        className="accent-gold-500"
      />
      {key.replace(/_/g, ' ')}
    </label>
  );

  const numberField = (
    key: 'target_resolution_rate' | 'target_response_minutes' | 'target_resolution_minutes' | 'target_csat',
    label: string,
    step = 1,
  ) => (
    <label className="text-sm text-ink">
      {label}
      <input
        type="number"
        step={step}
        value={settings[key] ?? ''}
        onChange={(e) => setSettings({ ...settings, [key]: e.target.value === '' ? null : Number(e.target.value) })}
        className={INPUT_CLASS}
        placeholder="Not configured"
      />
    </label>
  );

  return (
    <form onSubmit={submit} className="flex flex-col gap-3 max-w-md">
      {toggle('ai_enabled')}
      {toggle('live_search_enabled')}
      {toggle('human_escalation_enabled')}
      {toggle('chat_enabled')}
      {toggle('offline_mode')}
      {toggle('auto_assignment_enabled')}
      <label className="text-sm text-ink">
        Greeting message
        <input
          value={settings.greeting_message ?? ''}
          onChange={(e) => setSettings({ ...settings, greeting_message: e.target.value })}
          className={INPUT_CLASS}
        />
      </label>
      <label className="text-sm text-ink">
        Company name
        <input
          value={settings.company_name ?? ''}
          onChange={(e) => setSettings({ ...settings, company_name: e.target.value })}
          className={INPUT_CLASS}
        />
      </label>
      <label className="text-sm text-ink">
        Footer text
        <input
          value={settings.footer_text ?? ''}
          onChange={(e) => setSettings({ ...settings, footer_text: e.target.value })}
          className={INPUT_CLASS}
        />
      </label>
      <p className="text-xs font-semibold text-ink/50 uppercase mt-2">Performance Targets</p>
      <p className="text-xs text-ink/40 -mt-2">Leave blank to skip a target — agents and reports never invent a benchmark.</p>
      {numberField('target_resolution_rate', 'Target resolution rate (0–1)', 0.01)}
      {numberField('target_response_minutes', 'Target first response (minutes)')}
      {numberField('target_resolution_minutes', 'Target resolution time (minutes)')}
      {numberField('target_csat', 'Target CSAT', 0.1)}
      <button type="submit" className={`${PRIMARY_BUTTON} self-start`}>
        Save Settings
      </button>
    </form>
  );
}

function ProductsTab({ workspaceId }: { workspaceId: string }) {
  const [products, setProducts] = useState<WorkspaceProduct[]>([]);
  const [newProductId, setNewProductId] = useState('');

  function load() {
    apiJson<WorkspaceProduct[]>(`/admin/workspaces/${workspaceId}/products`).then(setProducts).catch(() => {});
  }

  useEffect(load, [workspaceId]);

  async function toggle(productId: string, enabled: boolean) {
    await apiJson(`/admin/workspaces/${workspaceId}/products`, {
      method: 'PATCH',
      body: JSON.stringify({ products: [{ product_id: productId, enabled }] }),
    });
    load();
  }

  async function addProduct(event: FormEvent) {
    event.preventDefault();
    if (!newProductId.trim()) return;
    await toggle(newProductId.trim(), true);
    setNewProductId('');
  }

  return (
    <div className="max-w-md">
      <div className={`${CARD} divide-y divide-ink/10 mb-4`}>
        {products.map((p) => (
          <div key={p.product_id} className="flex items-center justify-between px-4 py-2">
            <span className="text-sm text-ink">{p.product_id}</span>
            <input type="checkbox" checked={p.enabled} onChange={(e) => toggle(p.product_id, e.target.checked)} className="accent-gold-500" />
          </div>
        ))}
        {products.length === 0 && <p className="px-4 py-2 text-sm text-ink/40">No products configured yet.</p>}
      </div>
      <form onSubmit={addProduct} className="flex gap-2">
        <input
          value={newProductId}
          onChange={(e) => setNewProductId(e.target.value)}
          placeholder="Product id (e.g. SPIDIFY)"
          className="flex-1 border border-ink/10 rounded-xl px-3 py-2 text-sm bg-paper text-ink outline-none focus:border-gold-400"
        />
        <button type="submit" className={PRIMARY_BUTTON}>
          Add
        </button>
      </form>
    </div>
  );
}

function FlagsTab({ workspaceId }: { workspaceId: string }) {
  const [flags, setFlags] = useState<FeatureFlag[]>([]);
  const [newFlagKey, setNewFlagKey] = useState('');

  function load() {
    apiJson<FeatureFlag[]>(`/admin/workspaces/${workspaceId}/flags`).then(setFlags).catch(() => {});
  }

  useEffect(load, [workspaceId]);

  async function toggle(flagKey: string, enabled: boolean) {
    await apiJson(`/admin/workspaces/${workspaceId}/flags`, {
      method: 'PATCH',
      body: JSON.stringify({ flags: [{ flag_key: flagKey, enabled }] }),
    });
    load();
  }

  async function addFlag(event: FormEvent) {
    event.preventDefault();
    if (!newFlagKey.trim()) return;
    await toggle(newFlagKey.trim(), true);
    setNewFlagKey('');
  }

  return (
    <div className="max-w-md">
      <div className={`${CARD} divide-y divide-ink/10 mb-4`}>
        {flags.map((f) => (
          <div key={f.flag_key} className="flex items-center justify-between px-4 py-2">
            <span className="text-sm text-ink">{f.flag_key}</span>
            <input type="checkbox" checked={f.enabled} onChange={(e) => toggle(f.flag_key, e.target.checked)} className="accent-gold-500" />
          </div>
        ))}
        {flags.length === 0 && <p className="px-4 py-2 text-sm text-ink/40">No flags configured yet.</p>}
      </div>
      <form onSubmit={addFlag} className="flex gap-2">
        <input
          value={newFlagKey}
          onChange={(e) => setNewFlagKey(e.target.value)}
          placeholder="Flag key (e.g. ai_copilot)"
          className="flex-1 border border-ink/10 rounded-xl px-3 py-2 text-sm bg-paper text-ink outline-none focus:border-gold-400"
        />
        <button type="submit" className={PRIMARY_BUTTON}>
          Add
        </button>
      </form>
    </div>
  );
}

function ApiKeyTab({ workspaceId }: { workspaceId: string }) {
  const [newKey, setNewKey] = useState<string | null>(null);

  async function regenerate() {
    if (!confirm('Regenerate the API key? The old key will stop working immediately.')) return;
    const result = await apiJson<{ api_key: string }>(`/admin/workspaces/${workspaceId}/apikey/regenerate`, {
      method: 'POST',
    });
    setNewKey(result.api_key);
  }

  return (
    <div className="max-w-md">
      <p className="text-sm text-ink/60 mb-3">
        For security, the raw API key is never shown after creation — only at the moment it's generated.
      </p>
      <button onClick={regenerate} className={DANGER_BUTTON}>
        Regenerate API Key
      </button>
      {newKey && (
        <div className="mt-4 text-xs bg-gold-50 border border-gold-200 rounded-2xl p-3">
          <p className="font-semibold text-gold-700 mb-1">New key — copy it now, it won't be shown again:</p>
          <code className="text-ink">{newKey}</code>
          <p className="font-semibold text-gold-700 mt-3 mb-1">Embed snippet:</p>
          <pre className="bg-ink text-paper rounded-xl p-3 overflow-x-auto whitespace-pre-wrap">
{`<script src="https://cdn.havisiq.com/sdk.js"></script>
<script>
  HavisIQ.init({ apiKey: "${newKey}" });
</script>`}
          </pre>
        </div>
      )}
    </div>
  );
}

function AnalyticsTab({ workspaceId }: { workspaceId: string }) {
  const [analytics, setAnalytics] = useState<WorkspaceAnalytics | null>(null);

  useEffect(() => {
    apiJson<WorkspaceAnalytics>(`/admin/workspaces/${workspaceId}/analytics`).then(setAnalytics).catch(() => {});
  }, [workspaceId]);

  if (!analytics) return <p className="text-sm text-ink/40">Loading…</p>;

  return (
    <div className="grid grid-cols-3 gap-4 max-w-2xl">
      <MetricCard label="Conversations" value={analytics.conversation_count} icon={MessageSquare} tone="ink" />
      <MetricCard label="Escalations" value={analytics.escalation_count} icon={LifeBuoy} tone="red" />
      <MetricCard label="Appointments" value={analytics.appointment_count} icon={Calendar} tone="gold" />
      <MetricCard label="Saved Recommendations" value={analytics.saved_recommendation_count} icon={Star} tone="gold" />
      <MetricCard label="Saved Comparisons" value={analytics.saved_comparison_count} icon={GitCompare} tone="ink" />
      <MetricCard label="Feedback: Helpful" value={analytics.feedback_helpful_count} icon={ThumbsUp} tone="green" />
      <MetricCard label="Feedback: Not Helpful" value={analytics.feedback_not_helpful_count} icon={ThumbsDown} tone="red" />
      <div className={`${CARD} p-4 col-span-3`}>
        <p className="text-xs text-ink/50 uppercase mb-2">Escalation Status Breakdown</p>
        <div className="flex gap-4 text-sm text-ink">
          {Object.entries(analytics.escalation_status_breakdown).map(([status, count]) => (
            <span key={status}>
              {status}: <strong>{count}</strong>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function formatMetricLabel(key: string): string {
  return key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ');
}

function ReportTab({ workspaceId }: { workspaceId: string }) {
  const [report, setReport] = useState<WorkspaceReport | null>(null);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);

  useEffect(() => {
    apiJson<WorkspaceReport>(`/admin/workspaces/${workspaceId}/report`).then(setReport).catch(() => {});
  }, [workspaceId]);

  async function askHavisIQ(event: FormEvent) {
    event.preventDefault();
    if (!question.trim() || asking) return;
    setAsking(true);
    try {
      const result = await apiJson<{ answer: string }>(`/admin/workspaces/${workspaceId}/ask`, {
        method: 'POST',
        body: JSON.stringify({ question }),
      });
      setAnswer(result.answer);
    } finally {
      setAsking(false);
    }
  }

  if (!report) return <p className="text-sm text-ink/40">Loading…</p>;

  return (
    <div className="max-w-3xl space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <MetricCard
          label="Resolution Rate"
          value={report.resolution_rate != null ? `${Math.round(report.resolution_rate * 100)}%` : '—'}
          icon={LifeBuoy}
          tone="green"
        />
        <MetricCard
          label="Avg. Resolution Time"
          value={report.average_resolution_minutes != null ? `${Math.round(report.average_resolution_minutes)}m` : '—'}
          icon={Calendar}
          tone="gold"
        />
        <MetricCard
          label="AI-Resolved Rate (est.)"
          value={report.ai_resolved_rate_estimate != null ? `${Math.round(report.ai_resolved_rate_estimate * 100)}%` : '—'}
          icon={MessageSquare}
          tone="ink"
        />
      </div>
      <p className="text-xs text-ink/40">{report.ai_resolved_rate_caveat}</p>

      <div className={`${CARD} p-4`}>
        <p className="text-xs text-ink/50 uppercase mb-2">Agents</p>
        {report.agents.length === 0 ? (
          <p className="text-sm text-ink/40">No agents in this workspace yet.</p>
        ) : (
          <div className="divide-y divide-ink/10">
            {report.agents.map((agent) => (
              <div key={agent.id} className="flex items-center justify-between py-2 text-sm text-ink">
                <span>{agent.name} · {agent.department}</span>
                <span className="text-ink/50">{agent.status} · workload {agent.current_workload}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className={`${CARD} p-4`}>
        <p className="text-xs text-ink/50 uppercase mb-2">Department Activity</p>
        {Object.keys(report.department_activity).length === 0 ? (
          <p className="text-sm text-ink/40">No resolved escalations yet.</p>
        ) : (
          <div className="flex flex-wrap gap-4 text-sm text-ink">
            {Object.entries(report.department_activity).map(([dept, count]) => (
              <span key={dept}>{dept}: <strong>{count}</strong></span>
            ))}
          </div>
        )}
      </div>

      <div className={`${CARD} p-4`}>
        <p className="text-xs text-ink/50 uppercase mb-2">Requested Products</p>
        {Object.keys(report.requested_products).length === 0 ? (
          <p className="text-sm text-ink/40">No saved recommendations yet.</p>
        ) : (
          <div className="flex flex-wrap gap-4 text-sm text-ink">
            {Object.entries(report.requested_products).map(([product, count]) => (
              <span key={product}>{product}: <strong>{count}</strong></span>
            ))}
          </div>
        )}
      </div>

      <div className={`${CARD} p-4`}>
        <p className="text-xs text-ink/50 uppercase mb-2">Knowledge</p>
        <p className="text-sm text-ink/50">{report.knowledge_tracking_note}</p>
      </div>

      <div className={`${CARD} p-4`}>
        <p className="text-sm font-semibold text-ink mb-2">Ask HavisIQ</p>
        <form onSubmit={askHavisIQ} className="flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder='e.g. "How did support perform this week?" or "Which agents are overloaded?"'
            className="flex-1 border border-ink/10 rounded-xl px-3 py-2 text-sm bg-paper text-ink outline-none focus:border-gold-400"
          />
          <button type="submit" className={PRIMARY_BUTTON} disabled={asking}>
            {asking ? 'Asking…' : 'Ask'}
          </button>
        </form>
        {answer ? <p className="mt-3 text-sm text-ink whitespace-pre-wrap">{answer}</p> : null}
      </div>
    </div>
  );
}

function formatAuxLabel(auxType: string): string {
  return auxType.charAt(0).toUpperCase() + auxType.slice(1).replace(/_/g, ' ');
}

function OperationsTab({ workspaceId }: { workspaceId: string }) {
  const [report, setReport] = useState<WorkspaceReport | null>(null);

  useEffect(() => {
    const poll = () => apiJson<WorkspaceReport>(`/admin/workspaces/${workspaceId}/report`).then(setReport).catch(() => {});
    poll();
    const interval = setInterval(poll, 15000);
    return () => clearInterval(interval);
  }, [workspaceId]);

  if (!report) return <p className="text-sm text-ink/40">Loading…</p>;

  const totalAgents = report.agents.length;

  return (
    <div className="max-w-4xl space-y-6">
      <div className="grid grid-cols-4 gap-4">
        <MetricCard label="Scheduled" value={totalAgents} icon={MessageSquare} tone="ink" />
        <MetricCard label="Clocked In" value={report.clocked_in_count} icon={LifeBuoy} tone="green" />
        <MetricCard label="Available" value={report.available_count} icon={Star} tone="gold" />
        <MetricCard label="Avg. First Response" value={report.avg_first_response_minutes != null ? `${Math.round(report.avg_first_response_minutes)}m` : '—'} icon={Calendar} tone="ink" />
      </div>

      <div className={`${CARD} p-4`}>
        <p className="text-xs text-ink/50 uppercase mb-2">AUX Breakdown</p>
        {Object.keys(report.aux_breakdown).length === 0 ? (
          <p className="text-sm text-ink/40">No agents currently in an AUX state.</p>
        ) : (
          <div className="flex flex-wrap gap-4 text-sm text-ink">
            {Object.entries(report.aux_breakdown).map(([auxType, count]) => (
              <span key={auxType}>{formatAuxLabel(auxType)}: <strong>{count}</strong></span>
            ))}
          </div>
        )}
      </div>

      <div className={`${CARD} p-4`}>
        <p className="text-xs text-ink/50 uppercase mb-2">Time by AUX Category</p>
        {Object.keys(report.aux_time_by_category).length === 0 ? (
          <p className="text-sm text-ink/40">No AUX activity right now.</p>
        ) : (
          <div className="flex flex-wrap gap-4 text-sm text-ink">
            {Object.entries(report.aux_time_by_category).map(([category, count]) => (
              <span key={category}>{formatMetricLabel(category)}: <strong>{count}</strong></span>
            ))}
          </div>
        )}
      </div>

      <div className={`${CARD} p-4 overflow-x-auto`}>
        <p className="text-xs text-ink/50 uppercase mb-2">Agents</p>
        {report.agents.length === 0 ? (
          <p className="text-sm text-ink/40">No agents in this workspace yet.</p>
        ) : (
          <table className="w-full text-sm text-ink">
            <thead>
              <tr className="text-left text-ink/50 text-xs uppercase">
                <th className="py-1 pr-4">Agent</th>
                <th className="py-1 pr-4">Clock In</th>
                <th className="py-1 pr-4">AUX</th>
                <th className="py-1 pr-4">Workload</th>
                <th className="py-1 pr-4">Avg. First Response</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink/10">
              {report.agents.map((agent) => (
                <tr key={agent.id}>
                  <td className="py-2 pr-4">{agent.name} · {agent.department}</td>
                  <td className="py-2 pr-4 text-ink/60">
                    {agent.clock_in_at ? new Date(agent.clock_in_at).toLocaleTimeString() : 'Clocked out'}
                  </td>
                  <td className="py-2 pr-4 text-ink/60">{agent.current_aux ? formatAuxLabel(agent.current_aux) : agent.clock_in_at ? 'Available' : '—'}</td>
                  <td className="py-2 pr-4 text-ink/60">{agent.current_workload}</td>
                  <td className="py-2 pr-4 text-ink/60">
                    {agent.avg_first_response_minutes != null ? `${Math.round(agent.avg_first_response_minutes)}m` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className={`${CARD} p-4`}>
        <p className="text-xs text-ink/50 uppercase mb-2">Attendance Adherence</p>
        {report.adherence === null ? (
          <p className="text-sm text-ink/40">{report.adherence_note}</p>
        ) : report.adherence.length === 0 ? (
          <p className="text-sm text-ink/40">No agents clocked in yet today.</p>
        ) : (
          <div className="divide-y divide-ink/10">
            {report.adherence.map((entry) => {
              const agent = report.agents.find((a) => a.id === entry.agent_id);
              return (
                <div key={entry.agent_id} className="flex items-center justify-between py-2 text-sm text-ink">
                  <span>{agent?.name ?? entry.agent_id}</span>
                  <span className={entry.difference_minutes > 5 ? 'text-red-600' : 'text-ink/50'}>
                    Scheduled {entry.scheduled_start} · {entry.difference_minutes > 0 ? '+' : ''}
                    {Math.round(entry.difference_minutes)}m
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function AdminWorkspaceDetailContent() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const [workspace, setWorkspace] = useState<WorkspaceAdmin | null>(null);
  const [tab, setTab] = useState<Tab>('branding');
  const [forbidden, setForbidden] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  // Lifecycle actions (suspend/archive/delete) and the Flags tab stay
  // super-admin-only even after Phase 28 widened the rest of this page to
  // workspace_admins — best-effort probe, not a hard gate (mirrors
  // DashboardPage's isPlatformAdmin probe).
  const [isPlatformAdmin, setIsPlatformAdmin] = useState(false);

  useEffect(() => {
    if (!workspaceId) return;
    apiJson<WorkspaceAdmin>(`/admin/workspaces/${workspaceId}`)
      .then((w) => {
        setWorkspace(w);
        setForbidden(false);
      })
      .catch(() => setForbidden(true));
    apiJson('/admin/me')
      .then(() => setIsPlatformAdmin(true))
      .catch(() => setIsPlatformAdmin(false));
  }, [workspaceId]);

  async function lifecycleAction(action: 'suspend' | 'reactivate' | 'archive') {
    if (!workspaceId) return;
    const updated = await apiJson<WorkspaceAdmin>(`/admin/workspaces/${workspaceId}/${action}`, { method: 'POST' });
    setWorkspace(updated);
  }

  async function hardDeleteWorkspace() {
    if (!workspaceId || !workspace) return;
    await apiJson(`/admin/workspaces/${workspaceId}/hard-delete`, {
      method: 'POST',
      body: JSON.stringify({ confirm_name: workspace.name }),
    });
    navigate('/admin/workspaces');
  }

  if (forbidden) {
    return (
      <div className="min-h-screen bg-paper p-8 text-center">
        <p className="text-lg font-display text-ink">You don't have admin access to this workspace.</p>
        <Link to="/admin" className="text-gold-700 underline hover:text-gold-600">Back to Admin</Link>
      </div>
    );
  }

  if (!workspace || !workspaceId) return <p className="text-sm text-ink/40">Loading…</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-xl font-display font-semibold text-ink">{workspace.name}</h1>
          <p className="text-xs text-ink/50">{workspace.slug}</p>
        </div>
        <div className="flex gap-2">
          <Link
            to={`/admin/workspaces/${workspaceId}/knowledge`}
            className="rounded-full bg-ink px-3 py-2 text-xs font-semibold text-paper transition hover:bg-ink-soft flex items-center"
          >
            Knowledge
          </Link>
          <Link
            to={`/admin/workspaces/${workspaceId}/team`}
            className="rounded-full bg-ink px-3 py-2 text-xs font-semibold text-paper transition hover:bg-ink-soft flex items-center"
          >
            Team
          </Link>
          {isPlatformAdmin ? (
            <>
              {workspace.is_active ? (
                <button onClick={() => lifecycleAction('suspend')} className={SECONDARY_BUTTON}>
                  Suspend
                </button>
              ) : (
                <button onClick={() => lifecycleAction('reactivate')} className="rounded-full bg-green-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-green-700">
                  Reactivate
                </button>
              )}
              <button onClick={() => lifecycleAction('archive')} className={SECONDARY_BUTTON}>
                Archive
              </button>
              <button
                onClick={() => setDeleteModalOpen(true)}
                className="rounded-full bg-red-50 text-red-700 border border-red-200 px-3 py-2 text-xs transition hover:bg-red-100"
              >
                Delete
              </button>
            </>
          ) : null}
        </div>
      </div>

      <div className="flex gap-2 mb-6 border-b border-ink/10">
        {TABS.filter((t) => t !== 'flags' || isPlatformAdmin).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-sm capitalize transition ${
              tab === t ? 'border-b-2 border-gold-500 text-ink font-medium' : 'text-ink/50 hover:text-ink'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'branding' && <BrandingTab workspace={workspace} onSaved={setWorkspace} />}
      {tab === 'settings' && <SettingsTab workspaceId={workspaceId} />}
      {tab === 'products' && <ProductsTab workspaceId={workspaceId} />}
      {tab === 'flags' && <FlagsTab workspaceId={workspaceId} />}
      {tab === 'apikey' && <ApiKeyTab workspaceId={workspaceId} />}
      {tab === 'analytics' && <AnalyticsTab workspaceId={workspaceId} />}
      {tab === 'report' && <ReportTab workspaceId={workspaceId} />}
      {tab === 'operations' && <OperationsTab workspaceId={workspaceId} />}

      <ConfirmDeleteModal
        isOpen={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        resourceLabel={workspace.name}
        resourceType="workspace"
        onConfirm={hardDeleteWorkspace}
      />
    </div>
  );
}

export function AdminWorkspaceDetailPage() {
  return (
    <AdminLayout>
      <AdminWorkspaceDetailContent />
    </AdminLayout>
  );
}
