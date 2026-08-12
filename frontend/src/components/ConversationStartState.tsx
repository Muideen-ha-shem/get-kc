import { FormEvent, useState } from 'react';
import { GitCompare, SendHorizonal, Star } from 'lucide-react';
import { SECONDARY_BUTTON } from '../lib/uiClassNames';

type ConversationStartStateProps = {
  userName?: string | null;
  isSending: boolean;
  onSubmit: (message: string) => void;
  onOpenCompare: () => void;
  onGoToSavedRecommendations: () => void;
};

const PROMPT_CHIPS = [
  'Find a solution for employee onboarding',
  'What can help with expense tracking?',
  'Recommend something for customer support',
];

/**
 * Centered greeting + input, shown in place of the conversation list when
 * nothing is selected yet — replaces the old plain EmptyState for the
 * conversations section only (other sections keep using EmptyState as-is).
 */
export function ConversationStartState({
  userName,
  isSending,
  onSubmit,
  onOpenCompare,
  onGoToSavedRecommendations,
}: ConversationStartStateProps) {
  const [draft, setDraft] = useState('');
  const firstName = userName?.split(' ')[0];

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || isSending) return;
    setDraft('');
    onSubmit(trimmed);
  };

  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 px-4 text-center">
      <h2 className="font-display text-2xl text-ink">
        {firstName ? `What can HavisIQ help you find, ${firstName}?` : 'What can HavisIQ help you find today?'}
      </h2>

      <form onSubmit={handleSubmit} className="flex w-full max-w-xl items-center gap-2">
        <input
          autoFocus
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask about a product, compare solutions, or describe a business problem..."
          className="flex-1 rounded-full border border-ink/10 bg-white px-5 py-3.5 text-sm outline-none transition-colors focus:border-gold-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold-400/50"
        />
        <button
          type="submit"
          disabled={!draft.trim() || isSending}
          className="shrink-0 rounded-full bg-ink p-3.5 text-paper transition hover:bg-ink-soft disabled:cursor-not-allowed disabled:opacity-50"
          aria-label="Send"
        >
          <SendHorizonal size={16} />
        </button>
      </form>

      <div className="flex flex-wrap items-center justify-center gap-2">
        {PROMPT_CHIPS.map((chip) => (
          <button key={chip} onClick={() => onSubmit(chip)} disabled={isSending} className={SECONDARY_BUTTON}>
            {chip}
          </button>
        ))}
        <button onClick={onOpenCompare} className={`${SECONDARY_BUTTON} flex items-center gap-1.5`}>
          <GitCompare size={13} /> Compare two solutions
        </button>
        <button onClick={onGoToSavedRecommendations} className={`${SECONDARY_BUTTON} flex items-center gap-1.5`}>
          <Star size={13} /> Saved recommendations
        </button>
      </div>
    </div>
  );
}
