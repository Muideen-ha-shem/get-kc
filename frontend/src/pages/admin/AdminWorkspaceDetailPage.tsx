import { FormEvent, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiJson } from '../../lib/apiClient';
import { AdminGuard } from './AdminGuard';
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
      <label className="text-sm">
        Logo URL
        <input value={logo} onChange={(e) => setLogo(e.target.value)} className="w-full border rounded px-3 py-2 mt-1" />
      </label>
      <label className="text-sm">
        Primary color
        <input type="color" value={primaryColor} onChange={(e) => setPrimaryColor(e.target.value)} className="w-full border rounded px-3 py-2 mt-1 h-10" />
      </label>
      <label className="text-sm">
        Welcome message
        <input value={welcomeMessage} onChange={(e) => setWelcomeMessage(e.target.value)} className="w-full border rounded px-3 py-2 mt-1" />
      </label>
      <button type="submit" className="bg-blue-600 text-white rounded px-4 py-2 text-sm self-start">
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

  if (!settings) return <p className="text-sm text-gray-400">Loading…</p>;

  const toggle = (key: keyof WorkspaceSettings) => (
    <label className="flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        checked={Boolean(settings[key])}
        onChange={(e) => setSettings({ ...settings, [key]: e.target.checked })}
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
      <label className="text-sm">
        Greeting message
        <input
          value={settings.greeting_message ?? ''}
          onChange={(e) => setSettings({ ...settings, greeting_message: e.target.value })}
          className="w-full border rounded px-3 py-2 mt-1"
        />
      </label>
      <label className="text-sm">
        Company name
        <input
          value={settings.company_name ?? ''}
          onChange={(e) => setSettings({ ...settings, company_name: e.target.value })}
          className="w-full border rounded px-3 py-2 mt-1"
        />
      </label>
      <label className="text-sm">
        Footer text
        <input
          value={settings.footer_text ?? ''}
          onChange={(e) => setSettings({ ...settings, footer_text: e.target.value })}
          className="w-full border rounded px-3 py-2 mt-1"
        />
      </label>
      <button type="submit" className="bg-blue-600 text-white rounded px-4 py-2 text-sm self-start">
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
      <div className="bg-white border rounded divide-y mb-4">
        {products.map((p) => (
          <div key={p.product_id} className="flex items-center justify-between px-4 py-2">
            <span className="text-sm">{p.product_id}</span>
            <input type="checkbox" checked={p.enabled} onChange={(e) => toggle(p.product_id, e.target.checked)} />
          </div>
        ))}
        {products.length === 0 && <p className="px-4 py-2 text-sm text-gray-400">No products configured yet.</p>}
      </div>
      <form onSubmit={addProduct} className="flex gap-2">
        <input
          value={newProductId}
          onChange={(e) => setNewProductId(e.target.value)}
          placeholder="Product id (e.g. SPIDIFY)"
          className="flex-1 border rounded px-3 py-2 text-sm"
        />
        <button type="submit" className="bg-blue-600 text-white rounded px-4 py-2 text-sm">
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
      <div className="bg-white border rounded divide-y mb-4">
        {flags.map((f) => (
          <div key={f.flag_key} className="flex items-center justify-between px-4 py-2">
            <span className="text-sm">{f.flag_key}</span>
            <input type="checkbox" checked={f.enabled} onChange={(e) => toggle(f.flag_key, e.target.checked)} />
          </div>
        ))}
        {flags.length === 0 && <p className="px-4 py-2 text-sm text-gray-400">No flags configured yet.</p>}
      </div>
      <form onSubmit={addFlag} className="flex gap-2">
        <input
          value={newFlagKey}
          onChange={(e) => setNewFlagKey(e.target.value)}
          placeholder="Flag key (e.g. ai_copilot)"
          className="flex-1 border rounded px-3 py-2 text-sm"
        />
        <button type="submit" className="bg-blue-600 text-white rounded px-4 py-2 text-sm">
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
      <p className="text-sm text-gray-600 mb-3">
        For security, the raw API key is never shown after creation — only at the moment it's generated.
      </p>
      <button onClick={regenerate} className="bg-red-600 text-white rounded px-4 py-2 text-sm">
        Regenerate API Key
      </button>
      {newKey && (
        <div className="mt-4 text-xs bg-yellow-50 border border-yellow-200 rounded p-3">
          <p className="font-semibold text-yellow-700 mb-1">New key — copy it now, it won't be shown again:</p>
          <code>{newKey}</code>
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

  if (!analytics) return <p className="text-sm text-gray-400">Loading…</p>;

  return (
    <div className="grid grid-cols-3 gap-4 max-w-2xl">
      {[
        ['Conversations', analytics.conversation_count],
        ['Escalations', analytics.escalation_count],
        ['Appointments', analytics.appointment_count],
        ['Saved Recommendations', analytics.saved_recommendation_count],
        ['Saved Comparisons', analytics.saved_comparison_count],
        ['Feedback: Helpful', analytics.feedback_helpful_count],
        ['Feedback: Not Helpful', analytics.feedback_not_helpful_count],
      ].map(([label, value]) => (
        <div key={label as string} className="bg-white border rounded p-4">
          <p className="text-xs text-gray-500 uppercase">{label}</p>
          <p className="text-xl font-semibold mt-1">{value}</p>
        </div>
      ))}
      <div className="bg-white border rounded p-4 col-span-3">
        <p className="text-xs text-gray-500 uppercase mb-2">Escalation Status Breakdown</p>
        <div className="flex gap-4 text-sm">
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
  const [workspace, setWorkspace] = useState<WorkspaceAdmin | null>(null);
  const [tab, setTab] = useState<Tab>('branding');

  useEffect(() => {
    if (!workspaceId) return;
    apiJson<WorkspaceAdmin>(`/admin/workspaces/${workspaceId}`).then(setWorkspace).catch(() => {});
  }, [workspaceId]);

  async function lifecycleAction(action: 'suspend' | 'reactivate' | 'archive' | 'delete') {
    if (!workspaceId) return;
    const updated = await apiJson<WorkspaceAdmin>(`/admin/workspaces/${workspaceId}/${action}`, { method: 'POST' });
    setWorkspace(updated);
  }

  if (!workspace || !workspaceId) return <p className="text-sm text-gray-400">Loading…</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-xl font-semibold">{workspace.name}</h1>
          <p className="text-xs text-gray-500">{workspace.slug}</p>
        </div>
        <div className="flex gap-2">
          {workspace.is_active ? (
            <button onClick={() => lifecycleAction('suspend')} className="text-xs bg-gray-200 rounded px-3 py-2">
              Suspend
            </button>
          ) : (
            <button onClick={() => lifecycleAction('reactivate')} className="text-xs bg-green-600 text-white rounded px-3 py-2">
              Reactivate
            </button>
          )}
          <button onClick={() => lifecycleAction('archive')} className="text-xs bg-gray-200 rounded px-3 py-2">
            Archive
          </button>
          <button onClick={() => lifecycleAction('delete')} className="text-xs bg-red-100 text-red-700 rounded px-3 py-2">
            Delete
          </button>
        </div>
      </div>

      <div className="flex gap-2 mb-6 border-b">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-sm capitalize ${tab === t ? 'border-b-2 border-blue-600 text-blue-700 font-medium' : 'text-gray-500'}`}
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
    </div>
  );
}

export function AdminWorkspaceDetailPage() {
  return (
    <AdminGuard>
      <AdminLayout>
        <AdminWorkspaceDetailContent />
      </AdminLayout>
    </AdminGuard>
  );
}
