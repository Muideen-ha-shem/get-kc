import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiJson } from '../../lib/apiClient';
import { AdminGuard } from './AdminGuard';
import { AdminLayout } from './AdminLayout';
import type { WorkspaceAdmin } from './adminTypes';

type Step = 'details' | 'branding' | 'settings' | 'snippet';

function AdminOnboardingWizardContent() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>('details');
  const [workspace, setWorkspace] = useState<WorkspaceAdmin | null>(null);
  const [apiKey, setApiKey] = useState<string | null>(null);

  const [slug, setSlug] = useState('');
  const [name, setName] = useState('');
  const [host, setHost] = useState('');

  const [logo, setLogo] = useState('');
  const [primaryColor, setPrimaryColor] = useState('#2563eb');
  const [welcomeMessage, setWelcomeMessage] = useState('');

  const [companyName, setCompanyName] = useState('');
  const [aiEnabled, setAiEnabled] = useState(true);
  const [humanEscalationEnabled, setHumanEscalationEnabled] = useState(true);

  async function submitDetails(event: FormEvent) {
    event.preventDefault();
    const result = await apiJson<{ workspace: WorkspaceAdmin; api_key: string }>('/admin/workspaces', {
      method: 'POST',
      body: JSON.stringify({ slug, name, host: host || null }),
    });
    setWorkspace(result.workspace);
    setApiKey(result.api_key);
    setStep('branding');
  }

  async function submitBranding(event: FormEvent) {
    event.preventDefault();
    if (!workspace) return;
    await apiJson(`/admin/workspaces/${workspace.id}/branding`, {
      method: 'PATCH',
      body: JSON.stringify({ logo: logo || null, primary_color: primaryColor, welcome_message: welcomeMessage || null }),
    });
    setStep('settings');
  }

  async function submitSettings(event: FormEvent) {
    event.preventDefault();
    if (!workspace) return;
    await apiJson(`/admin/workspaces/${workspace.id}/settings`, {
      method: 'PATCH',
      body: JSON.stringify({
        company_name: companyName || null,
        ai_enabled: aiEnabled,
        human_escalation_enabled: humanEscalationEnabled,
      }),
    });
    setStep('snippet');
  }

  const snippet = workspace
    ? `<script src="https://cdn.havisiq.com/sdk.js"></script>\n<script>\n  HavisIQ.init({ apiKey: "${apiKey}" });\n</script>`
    : '';

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-semibold mb-6">New Workspace</h1>

      <div className="flex gap-2 mb-6 text-xs">
        {(['details', 'branding', 'settings', 'snippet'] as Step[]).map((s) => (
          <span
            key={s}
            className={`px-2 py-1 rounded-full ${step === s ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500'}`}
          >
            {s}
          </span>
        ))}
      </div>

      {step === 'details' && (
        <form onSubmit={submitDetails} className="bg-white border rounded p-6 flex flex-col gap-3">
          <label className="text-sm">
            Company / Workspace name
            <input value={name} onChange={(e) => setName(e.target.value)} required className="w-full border rounded px-3 py-2 mt-1" />
          </label>
          <label className="text-sm">
            Slug
            <input value={slug} onChange={(e) => setSlug(e.target.value)} required className="w-full border rounded px-3 py-2 mt-1" />
          </label>
          <label className="text-sm">
            Domain / host (optional)
            <input value={host} onChange={(e) => setHost(e.target.value)} className="w-full border rounded px-3 py-2 mt-1" />
          </label>
          <button type="submit" className="bg-blue-600 text-white rounded px-4 py-2 text-sm self-start">
            Create Workspace
          </button>
        </form>
      )}

      {step === 'branding' && (
        <form onSubmit={submitBranding} className="bg-white border rounded p-6 flex flex-col gap-3">
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
            Continue
          </button>
        </form>
      )}

      {step === 'settings' && (
        <form onSubmit={submitSettings} className="bg-white border rounded p-6 flex flex-col gap-3">
          <label className="text-sm">
            Company name (shown in widget footer)
            <input value={companyName} onChange={(e) => setCompanyName(e.target.value)} className="w-full border rounded px-3 py-2 mt-1" />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={aiEnabled} onChange={(e) => setAiEnabled(e.target.checked)} />
            AI enabled
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={humanEscalationEnabled}
              onChange={(e) => setHumanEscalationEnabled(e.target.checked)}
            />
            Human escalation enabled
          </label>
          <button type="submit" className="bg-blue-600 text-white rounded px-4 py-2 text-sm self-start">
            Continue
          </button>
        </form>
      )}

      {step === 'snippet' && workspace && (
        <div className="bg-white border rounded p-6">
          <p className="text-sm text-gray-600 mb-3">
            Ready for embedding. Add this to the site — the API key below is shown once, here, and never again.
          </p>
          <pre className="bg-gray-900 text-gray-100 text-xs rounded p-4 overflow-x-auto whitespace-pre-wrap">{snippet}</pre>
          <p className="text-xs text-yellow-700 bg-yellow-50 border border-yellow-200 rounded p-2 mt-3">
            API key: <code>{apiKey}</code> — save this now, it won't be shown again. Use "Regenerate API Key" on the
            workspace's detail page if it's ever lost.
          </p>
          <button
            onClick={() => navigate(`/admin/workspaces/${workspace.id}`)}
            className="mt-4 bg-blue-600 text-white rounded px-4 py-2 text-sm"
          >
            Go to workspace
          </button>
        </div>
      )}
    </div>
  );
}

export function AdminOnboardingWizardPage() {
  return (
    <AdminGuard>
      <AdminLayout>
        <AdminOnboardingWizardContent />
      </AdminLayout>
    </AdminGuard>
  );
}
