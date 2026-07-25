import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import type { Solution } from '../solutions';

type CompareSolutionsModalProps = {
  isOpen: boolean;
  onClose: () => void;
  solutions: Solution[];
  onRequestDemo: (solution: Solution) => void;
};

export function CompareSolutionsModal({ isOpen, onClose, solutions, onRequestDemo }: CompareSolutionsModalProps) {
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
            className="max-h-[85vh] w-full max-w-4xl overflow-hidden rounded-[1.75rem] bg-white shadow-[0_30px_90px_rgba(20,23,29,0.35)]"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-start justify-between border-b border-ink/10 px-6 py-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gold-600">Solution catalog</p>
                <h3 className="mt-1 font-display text-xl text-ink">Compare Ha-Shem solutions</h3>
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

            <div className="max-h-[calc(85vh-84px)] overflow-y-auto p-6">
              <div className="grid gap-4 sm:grid-cols-2">
                {solutions.map((solution) => (
                  <div key={solution.id} className="flex flex-col gap-3 rounded-[1.25rem] border border-ink/10 bg-paper p-5">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-display text-lg text-ink">{solution.name}</p>
                      <span
                        className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${
                          solution.status === 'live' ? 'bg-emerald-100 text-emerald-700' : 'bg-gold-100 text-gold-700'
                        }`}
                      >
                        {solution.status === 'live' ? 'Live solution' : 'Ha-Shem Advisory'}
                      </span>
                    </div>
                    <p className="text-xs font-medium uppercase tracking-wide text-ink/40">{solution.category}</p>
                    <p className="text-sm leading-6 text-ink/65">{solution.description}</p>
                    <ul className="flex flex-wrap gap-1.5">
                      {solution.highlights.map((highlight) => (
                        <li key={highlight} className="rounded-full bg-white px-2.5 py-1 text-xs text-ink/70 ring-1 ring-ink/10">
                          {highlight}
                        </li>
                      ))}
                    </ul>
                    <button
                      type="button"
                      onClick={() => onRequestDemo(solution)}
                      className="mt-1 self-start rounded-full border border-ink/15 px-4 py-2 text-xs font-semibold text-ink transition hover:border-gold-400 hover:text-gold-700"
                    >
                      Request demo
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
