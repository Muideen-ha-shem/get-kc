import { motion } from 'framer-motion';
import { FormEvent, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiJson } from '../../lib/apiClient';
import { useAuth, type AuthSessionResponse } from '../../lib/authContext';

type Plan = 'free' | 'starter' | 'pro';

const PLANS: { id: Plan; label: string; blurb: string }[] = [
  { id: 'free', label: 'Free', blurb: 'Get started, no cost.' },
  { id: 'starter', label: 'Starter', blurb: 'For small growing teams.' },
  { id: 'pro', label: 'Pro', blurb: 'For established organizations.' },
];

function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-');
}

type OrgSignupResponse = AuthSessionResponse & {
  workspace: { id: string; slug: string; name: string };
  api_key: string;
};

export function OrgSignupPage() {
  const navigate = useNavigate();
  const { applySession } = useAuth();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [orgName, setOrgName] = useState('');
  const [slug, setSlug] = useState('');
  const [slugTouched, setSlugTouched] = useState(false);
  const [plan, setPlan] = useState<Plan>('free');
  const [slugAvailable, setSlugAvailable] = useState<boolean | null>(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [status, setStatus] = useState<'idle' | 'submitting' | 'error' | 'done'>('idle');
  const [result, setResult] = useState<OrgSignupResponse | null>(null);

  useEffect(() => {
    if (!slugTouched) setSlug(slugify(orgName));
  }, [orgName, slugTouched]);

  useEffect(() => {
    if (!slug) {
      setSlugAvailable(null);
      return;
    }
    const handle = window.setTimeout(() => {
      apiJson<{ available: boolean }>(`/org-signup/slug-available?slug=${encodeURIComponent(slug)}`)
        .then((r) => setSlugAvailable(r.available))
        .catch(() => setSlugAvailable(null));
    }, 300);
    return () => window.clearTimeout(handle);
  }, [slug]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (status === 'submitting') return;
    setErrorMessage('');
    setStatus('submitting');
    try {
      const response = await apiJson<OrgSignupResponse>('/org-signup', {
        method: 'POST',
        body: JSON.stringify({
          full_name: fullName, email, password, org_name: orgName, slug, plan,
        }),
      });
      applySession(response);
      setResult(response);
      setStatus('done');
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Something went wrong. Please try again.');
      setStatus('error');
    }
  };

  if (status === 'done' && result) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-paper p-4">
        <motion.div
          initial={{ opacity: 0, y: 16, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          className="w-full max-w-lg overflow-hidden rounded-[1.75rem] bg-white shadow-[0_30px_90px_rgba(20,23,29,0.35)]"
        >
          <div className="border-b border-ink/10 px-6 py-5">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gold-600">HavisIQ</p>
            <h3 className="mt-1 font-display text-xl text-ink">{result.workspace.name} is ready</h3>
          </div>
          <div className="px-6 py-6">
            <p className="text-sm text-ink/65 mb-3">
              Add this to your site — the API key below is shown once, here, and never again.
            </p>
            <pre className="bg-gray-900 text-gray-100 text-xs rounded-2xl p-4 overflow-x-auto whitespace-pre-wrap">
{`<script src="https://cdn.havisiq.com/sdk.js"></script>
<script>
  HavisIQ.init({ apiKey: "${result.api_key}" });
</script>`}
            </pre>
            <p className="text-xs text-yellow-700 bg-yellow-50 border border-yellow-200 rounded-xl p-2 mt-3">
              API key: <code>{result.api_key}</code> — save this now, it won't be shown again.
            </p>
            <button
              onClick={() => navigate(`/admin/workspaces/${result.workspace.id}`)}
              className="mt-4 w-full rounded-full bg-ink px-5 py-3 text-sm font-semibold text-paper transition hover:bg-ink-soft"
            >
              Go to your workspace
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper p-4">
      <motion.div
        initial={{ opacity: 0, y: 16, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        className="w-full max-w-lg overflow-hidden rounded-[1.75rem] bg-white shadow-[0_30px_90px_rgba(20,23,29,0.35)]"
      >
        <div className="border-b border-ink/10 px-6 py-5">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gold-600">HavisIQ</p>
          <h3 className="mt-1 font-display text-xl text-ink">Create your organization</h3>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 px-6 py-6">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="signup-name" className="text-xs font-medium uppercase tracking-wide text-ink/50">
              Your name
            </label>
            <input
              id="signup-name"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="rounded-2xl border border-ink/10 bg-paper px-4 py-2.5 text-sm outline-none focus:border-gold-400"
              placeholder="Ada Lovelace"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="signup-email" className="text-xs font-medium uppercase tracking-wide text-ink/50">
              Work email
            </label>
            <input
              id="signup-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-2xl border border-ink/10 bg-paper px-4 py-2.5 text-sm outline-none focus:border-gold-400"
              placeholder="ada@yourcompany.com"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="signup-password" className="text-xs font-medium uppercase tracking-wide text-ink/50">
              Password
            </label>
            <input
              id="signup-password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-2xl border border-ink/10 bg-paper px-4 py-2.5 text-sm outline-none focus:border-gold-400"
              placeholder="At least 8 characters"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="signup-org" className="text-xs font-medium uppercase tracking-wide text-ink/50">
              Organization name
            </label>
            <input
              id="signup-org"
              required
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              className="rounded-2xl border border-ink/10 bg-paper px-4 py-2.5 text-sm outline-none focus:border-gold-400"
              placeholder="Your Company Ltd"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="signup-slug" className="text-xs font-medium uppercase tracking-wide text-ink/50">
              Workspace URL
            </label>
            <input
              id="signup-slug"
              required
              value={slug}
              onChange={(e) => {
                setSlugTouched(true);
                setSlug(slugify(e.target.value));
              }}
              className="rounded-2xl border border-ink/10 bg-paper px-4 py-2.5 text-sm outline-none focus:border-gold-400"
              placeholder="your-company"
            />
            {slugAvailable === false && <p className="text-xs text-red-600">That workspace URL is already taken.</p>}
            {slugAvailable === true && <p className="text-xs text-emerald-600">Available.</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <p className="text-xs font-medium uppercase tracking-wide text-ink/50">Plan</p>
            <div className="grid grid-cols-3 gap-2">
              {PLANS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setPlan(p.id)}
                  className={`rounded-2xl border px-3 py-3 text-left transition ${
                    plan === p.id ? 'border-gold-400 bg-gold-50' : 'border-ink/10 bg-paper hover:bg-white'
                  }`}
                >
                  <p className="text-sm font-semibold text-ink">{p.label}</p>
                  <p className="text-[11px] text-ink/50">{p.blurb}</p>
                </button>
              ))}
            </div>
          </div>

          {status === 'error' ? (
            <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{errorMessage}</p>
          ) : null}

          <button
            type="submit"
            disabled={status === 'submitting' || slugAvailable === false}
            className="mt-1 rounded-full bg-ink px-5 py-3 text-sm font-semibold text-paper transition hover:bg-ink-soft disabled:cursor-not-allowed disabled:opacity-60"
          >
            {status === 'submitting' ? 'Creating your workspace...' : 'Create organization'}
          </button>

          <p className="text-center text-xs text-ink/50">
            Already have an account?{' '}
            <Link to="/" className="font-semibold text-ink hover:underline">
              Back to HavisIQ
            </Link>
          </p>
        </form>
      </motion.div>
    </div>
  );
}
