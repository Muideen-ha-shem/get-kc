import { AnimatePresence, motion } from 'framer-motion';
import { CheckCircle2, GitCompare, Star, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { Solution } from '../solutions';
import { useAuth } from '../lib/authContext';
import { apiJson } from '../lib/apiClient';

type CompareSolutionsModalProps = {
  isOpen: boolean;
  onClose: () => void;
  solutions: Solution[];
  onRequestDemo: (solution: Solution) => void;
  /** Pre-selects one solution when opened from a card's "Compare" button. */
  initialSelectedId?: string;
  /** Pre-selects multiple solutions — used to reopen a saved comparison from
   * the Customer Dashboard with its full selection already loaded. Takes
   * priority over initialSelectedId when both are given. */
  initialSelectedIds?: string[];
};

export function CompareSolutionsModal({
  isOpen,
  onClose,
  solutions,
  onRequestDemo,
  initialSelectedId,
  initialSelectedIds,
}: CompareSolutionsModalProps) {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const { user } = useAuth();
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle');

  useEffect(() => {
    if (isOpen) {
      setSelectedIds(initialSelectedIds ?? (initialSelectedId ? [initialSelectedId] : []));
      setSaveStatus('idle');
    }
  }, [isOpen, initialSelectedId, initialSelectedIds]);

  const handleSaveComparison = async () => {
    if (saveStatus === 'saving' || selectedIds.length < 2) return;
    setSaveStatus('saving');
    try {
      await apiJson('/saved-comparisons', { method: 'POST', body: JSON.stringify({ product_ids: selectedIds }) });
      setSaveStatus('saved');
    } catch {
      setSaveStatus('idle');
    }
  };

  const toggleSelection = (id: string) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const selectedSolutions = solutions.filter((s) => selectedIds.includes(s.id));
  const isComparing = selectedSolutions.length >= 2;

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
            className="max-h-[85vh] w-full max-w-5xl overflow-hidden rounded-[1.75rem] bg-white shadow-[0_30px_90px_rgba(20,23,29,0.35)]"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-start justify-between border-b border-ink/10 px-6 py-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gold-600">Solution catalog</p>
                <h3 className="mt-1 font-display text-xl text-ink">
                  {isComparing ? `Comparing ${selectedSolutions.length} solutions` : 'Compare Ha-Shem solutions'}
                </h3>
                {!isComparing ? (
                  <p className="mt-1 text-sm text-ink/50">Select two or more to see a side-by-side comparison.</p>
                ) : null}
              </div>
              <div className="flex items-center gap-2">
                {isComparing && user ? (
                  <button
                    type="button"
                    onClick={handleSaveComparison}
                    disabled={saveStatus !== 'idle'}
                    className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                      saveStatus === 'saved'
                        ? 'cursor-default border-emerald-300 bg-emerald-50 text-emerald-700'
                        : 'border-ink/15 text-ink/70 hover:border-gold-400 hover:text-gold-700'
                    }`}
                  >
                    {saveStatus === 'saved' ? <CheckCircle2 size={13} /> : <Star size={13} />}
                    {saveStatus === 'saved'
                      ? 'Comparison saved successfully'
                      : saveStatus === 'saving'
                      ? 'Saving...'
                      : 'Save Comparison'}
                  </button>
                ) : null}
                {selectedIds.length > 0 ? (
                  <button
                    type="button"
                    onClick={() => setSelectedIds([])}
                    className="rounded-full border border-ink/15 px-3 py-1.5 text-xs font-semibold text-ink/60 transition hover:text-ink"
                  >
                    Clear selection
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-full p-1.5 text-ink/50 transition hover:bg-paper hover:text-ink"
                  aria-label="Close"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            <div className="max-h-[calc(85vh-84px)] overflow-y-auto p-6">
              {isComparing ? (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[640px] border-collapse text-left text-sm">
                    <thead>
                      <tr>
                        <th className="w-40 pb-4 pr-4 align-bottom text-xs font-semibold uppercase tracking-wide text-ink/40">
                          &nbsp;
                        </th>
                        {selectedSolutions.map((solution) => (
                          <th key={solution.id} className="pb-4 pr-4 align-bottom">
                            <p className="font-display text-lg text-ink">{solution.name}</p>
                            <span
                              className={`mt-1 inline-block rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${
                                solution.status === 'live' ? 'bg-emerald-100 text-emerald-700' : 'bg-gold-100 text-gold-700'
                              }`}
                            >
                              {solution.status === 'live' ? 'Live solution' : 'Ha-Shem Advisory'}
                            </span>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { label: 'Purpose', render: (s: Solution) => s.description },
                        { label: 'Best For', render: (s: Solution) => s.category },
                        {
                          label: 'Key Features',
                          render: (s: Solution) =>
                            s.highlights.length > 0 ? (
                              <ul className="space-y-1">
                                {s.highlights.map((h) => (
                                  <li key={h} className="flex items-start gap-1.5">
                                    <CheckCircle2 size={13} className="mt-0.5 shrink-0 text-emerald-500" />
                                    {h}
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <span className="text-ink/40">—</span>
                            ),
                        },
                        { label: 'Typical Users', render: (s: Solution) => s.typicalUsers ?? 'Business and operations teams' },
                      ].map((row) => (
                        <tr key={row.label} className="border-t border-ink/10 align-top">
                          <td className="py-4 pr-4 text-xs font-semibold uppercase tracking-wide text-ink/40">{row.label}</td>
                          {selectedSolutions.map((solution) => (
                            <td key={solution.id} className="py-4 pr-4 text-ink/70">
                              {row.render(solution)}
                            </td>
                          ))}
                        </tr>
                      ))}
                      <tr className="border-t border-ink/10">
                        <td className="py-4 pr-4" />
                        {selectedSolutions.map((solution) => (
                          <td key={solution.id} className="py-4 pr-4">
                            <button
                              type="button"
                              onClick={() => onRequestDemo(solution)}
                              className="rounded-full border border-ink/15 px-4 py-2 text-xs font-semibold text-ink transition hover:border-gold-400 hover:text-gold-700"
                            >
                              Request demo
                            </button>
                          </td>
                        ))}
                      </tr>
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2">
                  {solutions.map((solution) => {
                    const selected = selectedIds.includes(solution.id);
                    return (
                      <div
                        key={solution.id}
                        className={`flex flex-col gap-3 rounded-[1.25rem] border p-5 transition ${
                          selected ? 'border-gold-400 bg-gold-50/40 ring-1 ring-gold-300' : 'border-ink/10 bg-paper'
                        }`}
                      >
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
                        <div className="mt-1 flex flex-wrap gap-2">
                          <button
                            type="button"
                            onClick={() => toggleSelection(solution.id)}
                            className={`inline-flex items-center gap-1.5 self-start rounded-full px-4 py-2 text-xs font-semibold transition ${
                              selected
                                ? 'bg-ink text-paper'
                                : 'border border-ink/15 text-ink transition hover:border-gold-400 hover:text-gold-700'
                            }`}
                          >
                            <GitCompare size={13} />
                            {selected ? 'Selected' : 'Select to compare'}
                          </button>
                          <button
                            type="button"
                            onClick={() => onRequestDemo(solution)}
                            className="self-start rounded-full border border-ink/15 px-4 py-2 text-xs font-semibold text-ink transition hover:border-gold-400 hover:text-gold-700"
                          >
                            Request demo
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
