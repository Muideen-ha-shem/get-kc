import { motion } from 'framer-motion';
import { CheckCircle2 } from 'lucide-react';
import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiJson } from '../../lib/apiClient';
import { useAuth, type AuthSessionResponse } from '../../lib/authContext';

function parseRecoveryToken(): string | null {
  const hash = window.location.hash.startsWith('#') ? window.location.hash.slice(1) : window.location.hash;
  const hashParams = new URLSearchParams(hash);
  const queryParams = new URLSearchParams(window.location.search);
  return hashParams.get('access_token') || queryParams.get('access_token');
}

export function AcceptInvitePage() {
  const { applySession } = useAuth();
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [status, setStatus] = useState<'idle' | 'submitting' | 'error' | 'done'>('idle');

  useEffect(() => {
    setAccessToken(parseRecoveryToken());
  }, []);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (status === 'submitting') return;
    setErrorMessage('');

    if (password !== confirmPassword) {
      setErrorMessage('Passwords do not match.');
      setStatus('error');
      return;
    }
    if (!accessToken) {
      setErrorMessage('This invite link is invalid or has expired. Ask your admin to resend it.');
      setStatus('error');
      return;
    }

    setStatus('submitting');
    try {
      const session = await apiJson<AuthSessionResponse>('/org-signup/accept-invite', {
        method: 'POST',
        body: JSON.stringify({ access_token: accessToken, password }),
      });
      applySession(session);
      setStatus('done');
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Something went wrong. Please try again.');
      setStatus('error');
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper p-4">
      <motion.div
        initial={{ opacity: 0, y: 16, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        className="w-full max-w-md overflow-hidden rounded-[1.75rem] bg-white shadow-[0_30px_90px_rgba(20,23,29,0.35)]"
      >
        <div className="border-b border-ink/10 px-6 py-5">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gold-600">HavisIQ</p>
          <h3 className="mt-1 font-display text-xl text-ink">Join your team</h3>
        </div>

        {!accessToken ? (
          <div className="flex flex-col items-center gap-3 px-6 py-10 text-center">
            <p className="text-sm text-ink/65">
              This invite link is invalid or has expired. Ask your admin to send a new one.
            </p>
            <Link to="/" className="mt-2 rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-paper transition hover:bg-ink-soft">
              Back to home
            </Link>
          </div>
        ) : status === 'done' ? (
          <div className="flex flex-col items-center gap-3 px-6 py-10 text-center">
            <CheckCircle2 className="text-emerald-500" size={40} />
            <p className="font-display text-lg text-ink">You're in</p>
            <p className="text-sm text-ink/65">Your account is set up — you can start using HavisIQ now.</p>
            <Link to="/dashboard" className="mt-2 rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-paper transition hover:bg-ink-soft">
              Go to dashboard
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4 px-6 py-6">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="invite-password" className="text-xs font-medium uppercase tracking-wide text-ink/50">
                Set a password
              </label>
              <input
                id="invite-password"
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="rounded-2xl border border-ink/10 bg-paper px-4 py-2.5 text-sm outline-none focus:border-gold-400"
                placeholder="At least 8 characters"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="invite-confirm-password" className="text-xs font-medium uppercase tracking-wide text-ink/50">
                Confirm password
              </label>
              <input
                id="invite-confirm-password"
                type="password"
                required
                minLength={8}
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                className="rounded-2xl border border-ink/10 bg-paper px-4 py-2.5 text-sm outline-none focus:border-gold-400"
                placeholder="Re-enter your password"
              />
            </div>

            {status === 'error' ? (
              <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{errorMessage}</p>
            ) : null}

            <button
              type="submit"
              disabled={status === 'submitting'}
              className="mt-1 rounded-full bg-ink px-5 py-3 text-sm font-semibold text-paper transition hover:bg-ink-soft disabled:cursor-not-allowed disabled:opacity-60"
            >
              {status === 'submitting' ? 'Joining...' : 'Join team'}
            </button>
          </form>
        )}
      </motion.div>
    </div>
  );
}
