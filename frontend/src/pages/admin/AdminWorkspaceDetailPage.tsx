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
  WorkspaceSettings,
} from './adminTypes';

type Tab = 'branding' | 'settings' | 'products' | 'flags' | 'apikey' | 'analytics';

const TABS: Tab[] = ['branding', 'settings', 'products', 'flags', 'apikey', 'analytics'];

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
