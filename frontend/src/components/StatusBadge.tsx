import { ReactNode } from 'react';

export type BadgeTone = 'success' | 'warning' | 'danger' | 'neutral' | 'gold';

const TONE_CLASS: Record<BadgeTone, string> = {
  success: 'bg-green-100 text-green-700',
  warning: 'bg-gold-100 text-gold-700',
  danger: 'bg-red-100 text-red-700',
  neutral: 'bg-ink/10 text-ink/50',
  gold: 'bg-gold-50 text-gold-700',
};

/**
 * Generalizes the ad hoc status-color maps that used to be re-declared per
 * page (invitation status, workspace active/suspended/archived, agent
 * status, feature-flag state, etc) into one small component.
 */
export function StatusBadge({ tone, children }: { tone: BadgeTone; children: ReactNode }) {
  return (
    <span className={`inline-block rounded-full px-2 py-1 text-xs font-medium ${TONE_CLASS[tone]}`}>{children}</span>
  );
}
