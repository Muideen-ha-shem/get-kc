import { AnimatePresence, motion } from 'framer-motion';
import { FormEvent, useEffect, useState } from 'react';
import { CheckCircle2, X } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

type Status = 'idle' | 'submitting' | 'success' | 'error';

type DemoRequestModalProps = {
  isOpen: boolean;
  onClose: () => void;
  /** Solution id/name this request relates to, if opened from a specific solution card. */
  product?: string;
  /** Human-readable label shown in the modal title, e.g. "SPIDIFY" or "Cybersecurity". */
  productLabel?: string;
};

/**
 * Shared form behind every "Request a demo" / "Contact sales" / "Talk to an
 * expert" call to action across the page — one component, one backend call
 * (POST /demo-request), so every entry point stays in sync automatically.
 */
export function DemoRequestModal({ isOpen, onClose, product, productLabel }: DemoRequestModalProps) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [company, setCompany] = useState('');
  const [useCase, setUseCase] = useState('');
  const [status, setStatus] = useState<Status>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (isOpen) {
      setStatus('idle');
      setErrorMessage('');
    }
  }, [isOpen]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim() || !email.trim() || status === 'submitting') return;

    setStatus('submitting');
    try {
      const response = await fetch(`${API_BASE_URL || 'http://localhost:8000'}/demo-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          company: company.trim() || undefined,
          use_case: useCase.trim() || undefined,
          product: product || undefined,
        }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(typeof data.detail === 'string' ? data.detail : 'We could not submit your request. Please try again.');
      }

      setStatus('success');
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'We could not submit your request. Please try again.');
      setStatus('error');
    }
  };

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
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gold-600">
                  {productLabel ? `About ${productLabel}` : 'Talk to Ha-Shem'}
                </p>
                <h3 className="mt-1 font-display text-xl text-ink">Request a demo</h3>
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

            {status === 'success' ? (
              <div className="flex flex-col items-center gap-3 px-6 py-10 text-center">
                <CheckCircle2 className="text-emerald-500" size={40} />
                <p className="font-display text-lg text-ink">Request received</p>
                <p className="text-sm text-ink/65">
                  Thanks{name ? `, ${name.split(' ')[0]}` : ''} — a member of the Ha-Shem team will reach out shortly.
                </p>
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
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="demo-name" className="text-xs font-medium uppercase tracking-wide text-ink/50">
                    Name
                  </label>
                  <input
                    id="demo-name"
                    required
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    className="rounded-2xl border border-ink/10 bg-paper px-4 py-2.5 text-sm outline-none focus:border-gold-400"
                    placeholder="Your full name"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="demo-email" className="text-xs font-medium uppercase tracking-wide text-ink/50">
                    Work email
                  </label>
                  <input
                    id="demo-email"
                    type="email"
                    required
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="rounded-2xl border border-ink/10 bg-paper px-4 py-2.5 text-sm outline-none focus:border-gold-400"
                    placeholder="you@company.com"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="demo-company" className="text-xs font-medium uppercase tracking-wide text-ink/50">
                    Company
                  </label>
                  <input
                    id="demo-company"
                    value={company}
                    onChange={(event) => setCompany(event.target.value)}
                    className="rounded-2xl border border-ink/10 bg-paper px-4 py-2.5 text-sm outline-none focus:border-gold-400"
                    placeholder="Your company"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="demo-use-case" className="text-xs font-medium uppercase tracking-wide text-ink/50">
                    What are you trying to solve?
                  </label>
                  <textarea
                    id="demo-use-case"
                    value={useCase}
                    onChange={(event) => setUseCase(event.target.value)}
                    className="min-h-24 rounded-2xl border border-ink/10 bg-paper px-4 py-2.5 text-sm outline-none focus:border-gold-400"
                    placeholder="Tell us a little about your business need"
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
                  {status === 'submitting' ? 'Sending...' : 'Send request'}
                </button>
              </form>
            )}
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
