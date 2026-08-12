import { AnimatePresence, motion } from 'framer-motion';
import { FormEvent, useEffect, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { DANGER_BUTTON, INPUT_CLASS, SECONDARY_BUTTON } from '../lib/uiClassNames';

type ConfirmDeleteModalProps = {
  isOpen: boolean;
  onClose: () => void;
  /** The exact text the user must type to enable the confirm button — e.g. the workspace's name. */
  resourceLabel: string;
  /** e.g. "workspace" — used in the body copy. */
  resourceType: string;
  onConfirm: () => Promise<void>;
};

/**
 * Reusable type-to-confirm gate for irreversible deletes. Overlay/backdrop
 * structure mirrors DemoRequestModal/CompareSolutionsModal so every modal
 * in the app shares the same shell.
 */
export function ConfirmDeleteModal({ isOpen, onClose, resourceLabel, resourceType, onConfirm }: ConfirmDeleteModalProps) {
  const [typedValue, setTypedValue] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (isOpen) {
      setTypedValue('');
      setIsDeleting(false);
      setErrorMessage('');
    }
  }, [isOpen]);

  const matches = typedValue === resourceLabel;

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!matches || isDeleting) return;
    setIsDeleting(true);
    setErrorMessage('');
    try {
      await onConfirm();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to delete. Please try again.');
      setIsDeleting(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[90] flex items-center justify-center bg-ink/50 p-4 backdrop-blur-sm"
          onClick={isDeleting ? undefined : onClose}
        >
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.98 }}
            className="w-full max-w-md overflow-hidden rounded-[1.75rem] bg-white shadow-[0_30px_90px_rgba(20,23,29,0.35)]"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-start justify-between border-b border-ink/10 px-6 py-5">
              <div className="flex items-start gap-3">
                <span className="mt-0.5 rounded-full bg-red-50 p-2 text-red-600">
                  <AlertTriangle size={18} />
                </span>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.28em] text-red-600">Permanent action</p>
                  <h3 className="mt-1 font-display text-xl text-ink">Delete this {resourceType}</h3>
                </div>
              </div>
              <button
                type="button"
                onClick={onClose}
                disabled={isDeleting}
                className="rounded-full p-1.5 text-ink/50 transition hover:bg-paper hover:text-ink disabled:opacity-40"
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-4 px-6 py-6">
              <p className="text-sm text-ink/70">
                This will permanently delete <strong className="text-ink">{resourceLabel}</strong> and every piece of
                data associated with it — conversations, customers, documents, and more. This cannot be undone.
              </p>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="confirm-delete-input" className="text-xs font-medium uppercase tracking-wide text-ink/50">
                  Type <span className="font-semibold text-ink">{resourceLabel}</span> to confirm
                </label>
                <input
                  id="confirm-delete-input"
                  value={typedValue}
                  onChange={(event) => setTypedValue(event.target.value)}
                  className={INPUT_CLASS}
                  autoComplete="off"
                  autoFocus
                />
              </div>

              {errorMessage ? <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{errorMessage}</p> : null}

              <div className="flex justify-end gap-2">
                <button type="button" onClick={onClose} disabled={isDeleting} className={SECONDARY_BUTTON}>
                  Cancel
                </button>
                <button type="submit" disabled={!matches || isDeleting} className={DANGER_BUTTON}>
                  {isDeleting ? 'Deleting...' : `Permanently delete`}
                </button>
              </div>
            </form>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
