import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiJson } from '../../lib/apiClient';
import { INPUT_CLASS, PRIMARY_BUTTON, SECONDARY_BUTTON } from '../../lib/uiClassNames';
import { AdminGuard } from './AdminGuard';
import { AdminLayout } from './AdminLayout';
import type { WorkspaceAdmin } from './adminTypes';

type Step = 'details' | 'branding' | 'settings' | 'snippet';

const STEP_ORDER: Step[] = ['details', 'branding', 'settings', 'snippet'];

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
  const [errorMessage, setErrorMessage] = useState('');

  async function submitDetails(event: FormEvent) {
    event.preventDefault();
    setErrorMessage('');
    try {
      const result = await apiJson<{ workspace: WorkspaceAdmin; api_key: string }>('/admin/workspaces', {
        method: 'POST',
        body: JSON.stringify({ slug, name, host: host || null }),
      });
      setWorkspace(result.workspace);
      setApiKey(result.api_key);
      setStep('branding');
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to create workspace.');
    }
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

  function goBack() {
    const index = STEP_ORDER.indexOf(step);
    if (index > 0) setStep(STEP_ORDER[index - 1]);
  }

  const snippet = workspace
    ? `<script src="https://cdn.havisiq.com/sdk.js"></script>\n<script>\n  HavisIQ.init({ apiKey: "${apiKey}" });\n</script>`
    : '';

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-display font-semibold mb-6 text-ink">New Workspace</h1>

      <div className="flex gap-2 mb-6 text-xs">
        {STEP_ORDER.map((s, index) => {
          const isReachable = workspace != null && index <= STEP_ORDER.indexOf(step);
          return (
            <button
              key={s}
              type="button"
              disabled={!isReachable}
              onClick={() => isReachable && setStep(s)}
              className={`px-3 py-1 rounded-full capitalize transition ${
                step === s
                  ? 'bg-ink text-paper'
                  : isReachable
                    ? 'bg-ink/10 text-ink/60 hover:bg-ink/20 cursor-pointer'
                    : 'bg-ink/10 text-ink/50 cursor-not-allowed'
              }`}
            >
              {s}
            </button>
          );
        })}
      </div>

      {step === 'details' && (
        <form onSubmit={submitDetails} className="bg-white border border-ink/10 rounded-2xl p-6 flex flex-col gap-3">
          <label className="text-sm text-ink">
            Company / Workspace name
            <input value={name} onChange={(e) => setName(e.target.value)} required className={INPUT_CLASS} />
          </label>
          <label className="text-sm text-ink">
            Slug
            <input value={slug} onChange={(e) => setSlug(e.target.value)} required className={INPUT_CLASS} />
          </label>
          <label className="text-sm text-ink">
            Domain / host (optional)
            <input value={host} onChange={(e) => setHost(e.target.value)} className={INPUT_CLASS} />
          </label>
          {errorMessage && <p className="text-sm text-red-600">{errorMessage}</p>}
          <button type="submit" className={`${PRIMARY_BUTTON} self-start`}>
            Create Workspace
          </button>
        </form>
      )}

      {step === 'branding' && (
        <form onSubmit={submitBranding} className="bg-white border border-ink/10 rounded-2xl p-6 flex flex-col gap-3">
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
          <div className="flex gap-2">
            <button type="button" onClick={goBack} className={SECONDARY_BUTTON}>
              Back
            </button>
            <button type="submit" className={`${PRIMARY_BUTTON} self-start`}>
              Continue
            </button>
          </div>
        </form>
      )}

      {step === 'settings' && (
        <form onSubmit={submitSettings} className="bg-white border border-ink/10 rounded-2xl p-6 flex flex-col gap-3">
          <label className="text-sm text-ink">
            Company name (shown in widget footer)
            <input value={companyName} onChange={(e) => setCompanyName(e.target.value)} className={INPUT_CLASS} />
          </label>
          <label className="flex items-center gap-2 text-sm text-ink">
            <input type="checkbox" checked={aiEnabled} onChange={(e) => setAiEnabled(e.target.checked)} className="accent-gold-500" />
            AI enabled
          </label>
          <label className="flex items-center gap-2 text-sm text-ink">
            <input
              type="checkbox"
              checked={humanEscalationEnabled}
              onChange={(e) => setHumanEscalationEnabled(e.target.checked)}
              className="accent-gold-500"
            />
            Human escalation enabled
          </label>
          <div className="flex gap-2">
            <button type="button" onClick={goBack} className={SECONDARY_BUTTON}>
              Back
            </button>
            <button type="submit" className={`${PRIMARY_BUTTON} self-start`}>
              Continue
            </button>
          </div>
        </form>
      )}

      {step === 'snippet' && workspace && (
        <div className="bg-white border border-ink/10 rounded-2xl p-6">
          <p className="text-sm text-ink/60 mb-3">
            Ready for embedding. Add this to the site — the API key below is shown once, here, and never again.
          </p>
          <pre className="bg-ink text-paper text-xs rounded-xl p-4 overflow-x-auto whitespace-pre-wrap">{snippet}</pre>
          <p className="text-xs text-gold-700 bg-gold-50 border border-gold-200 rounded-xl p-2 mt-3">
            API key: <code>{apiKey}</code> — save this now, it won't be shown again. Use "Regenerate API Key" on the
            workspace's detail page if it's ever lost.
          </p>
          <div className="mt-4 flex gap-2">
            <button type="button" onClick={goBack} className={SECONDARY_BUTTON}>
              Back
            </button>
            <button
              onClick={() => navigate(`/admin/workspaces/${workspace.id}`)}
              className={PRIMARY_BUTTON}
            >
              Go to workspace
            </button>
          </div>
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
