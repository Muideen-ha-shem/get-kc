import { AnimatePresence, motion } from 'framer-motion';
import { FormEvent, useEffect, useState } from 'react';
import { CheckCircle2, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../lib/authContext';

type Mode = 'sign-in' | 'sign-up' | 'reset';
type Status = 'idle' | 'submitting' | 'error' | 'reset-sent';

type AuthModalProps = {
  isOpen: boolean;
  onClose: () => void;
  initialMode?: Mode;
};

export function AuthModal({ isOpen, onClose, initialMode = 'sign-in' }: AuthModalProps) {
  const { signIn, signUp, requestPasswordReset } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>(initialMode);
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [status, setStatus] = useState<Status>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (isOpen) {
      setMode(initialMode);
      setStatus('idle');
      setErrorMessage('');
      setPassword('');
    }
  }, [isOpen, initialMode]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (status === 'submitting') return;
    setStatus('submitting');
    setErrorMessage('');
    try {
      if (mode === 'sign-in') {
        await signIn(email.trim(), password);
        onClose();
        navigate('/dashboard');
      } else if (mode === 'sign-up') {
        await signUp(email.trim(), password, fullName.trim() || undefined);
        onClose();
        navigate('/dashboard');
      } else {
        await requestPasswordReset(email.trim());
        setStatus('reset-sent');
        return;
      }
      setStatus('idle');
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Something went wrong. Please try again.');
      setStatus('error');
    }
  };

  const title = mode === 'sign-in' ? 'Sign in' : mode === 'sign-up' ? 'Create your account' : 'Reset your password';

  return (
    <AnimatePresence>
      {isOpen ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[80] flex items-center justify-center bg-ink/50 p-4 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.98 }}
            className="w-full max-w-md overflow-hidden rounded-[1.75rem] bg-white shadow-[0_30px_90px_rgba(20,23,29,0.35)]"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-start justify-between border-b border-ink/10 px-6 py-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gold-600">HavisIQ Account</p>
                <h3 className="mt-1 font-display text-xl text-ink">{title}</h3>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="rounded-full p-1.5 text-ink/50 transition hover:bg-paper hover:text-ink"
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>

            {status === 'reset-sent' ? (
              <div className="flex flex-col items-center gap-3 px-6 py-10 text-center">
                <CheckCircle2 className="text-emerald-500" size={40} />
                <p className="font-display text-lg text-ink">Check your email</p>
                <p className="text-sm text-ink/65">We sent a password reset link to {email}.</p>
                <button
                  type="button"
                  onClick={onClose}
                  className="mt-2 rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-paper transition hover:bg-ink-soft"
                >
                  Done
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="flex flex-col gap-4 px-6 py-6">
                {mode === 'sign-up' ? (
                  <div className="flex flex-col gap-1.5">
                    <label htmlFor="auth-name" className="text-xs font-medium uppercase tracking-wide text-ink/50">
                      Full name
                    </label>
                    <input
                      id="auth-name"
                      value={fullName}
                      onChange={(event) => setFullName(event.target.value)}
                      className="rounded-2xl border border-ink/10 bg-paper px-4 py-2.5 text-sm outline-none focus:border-gold-400"
                      placeholder="Your full name"
                    />
                  </div>
                ) : null}

                <div className="flex flex-col gap-1.5">
                  <label htmlFor="auth-email" className="text-xs font-medium uppercase tracking-wide text-ink/50">
                    Email
                  </label>
                  <input
                    id="auth-email"
                    type="email"
                    required
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="rounded-2xl border border-ink/10 bg-paper px-4 py-2.5 text-sm outline-none focus:border-gold-400"
                    placeholder="you@company.com"
                  />
                </div>

                {mode !== 'reset' ? (
                  <div className="flex flex-col gap-1.5">
                    <label htmlFor="auth-password" className="text-xs font-medium uppercase tracking-wide text-ink/50">
                      Password
                    </label>
                    <input
                      id="auth-password"
                      type="password"
                      required
                      minLength={8}
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      className="rounded-2xl border border-ink/10 bg-paper px-4 py-2.5 text-sm outline-none focus:border-gold-400"
                      placeholder="At least 8 characters"
                    />
                  </div>
                ) : null}

                {status === 'error' ? (
                  <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{errorMessage}</p>
                ) : null}

                <button
                  type="submit"
                  disabled={status === 'submitting'}
                  className="mt-1 rounded-full bg-ink px-5 py-3 text-sm font-semibold text-paper transition hover:bg-ink-soft disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {status === 'submitting'
                    ? 'Please wait...'
                    : mode === 'sign-in'
                    ? 'Sign in'
                    : mode === 'sign-up'
                    ? 'Create account'
                    : 'Send reset link'}
                </button>

                <div className="flex items-center justify-between text-xs text-ink/50">
                  {mode === 'sign-in' ? (
                    <>
                      <button type="button" onClick={() => setMode('reset')} className="hover:text-ink">
                        Forgot password?
                      </button>
                      <button type="button" onClick={() => setMode('sign-up')} className="font-semibold hover:text-ink">
                        Create an account
                      </button>
                    </>
                  ) : (
                    <button type="button" onClick={() => setMode('sign-in')} className="font-semibold hover:text-ink">
                      Back to sign in
                    </button>
                  )}
                </div>

                {mode === 'sign-up' ? (
                  <p className="text-center text-xs text-ink/50">
                    Setting up on behalf of a company?{' '}
                    <button
                      type="button"
                      onClick={() => {
                        onClose();
                        navigate('/signup');
                      }}
                      className="font-semibold text-ink hover:underline"
                    >
                      Create an organization instead
                    </button>
                  </p>
                ) : null}
              </form>
            )}
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
