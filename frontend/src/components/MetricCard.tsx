import type { LucideIcon } from 'lucide-react';

type MetricCardProps = {
  label: string;
  value: string | number;
  icon: LucideIcon;
  /** Optional short caption under the number, e.g. a timestamp or a unit. */
  caption?: string;
  tone?: 'ink' | 'gold' | 'green' | 'red';
  /** For non-numeric values (e.g. a timestamp) where a huge 3xl number would look wrong. */
  small?: boolean;
};

const TONE_ICON_CLASS: Record<NonNullable<MetricCardProps['tone']>, string> = {
  ink: 'bg-ink/5 text-ink',
  gold: 'bg-gold-50 text-gold-600',
  green: 'bg-green-50 text-green-600',
  red: 'bg-red-50 text-red-600',
};

function formatValue(value: string | number): string {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value.toLocaleString();
  }
  return String(value);
}

/**
 * Standard stat tile used across the admin dashboard, workspace analytics,
 * and knowledge-base dashboards — a labeled icon badge plus a large,
 * thousands-separated number, replacing the old plain [label, value] boxes.
 */
export function MetricCard({ label, value, icon: Icon, caption, tone = 'gold', small = false }: MetricCardProps) {
  return (
    <div className="rounded-2xl border border-ink/10 bg-white p-5 transition hover:border-gold-300/70 hover:shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wide text-ink/50">{label}</p>
        <span className={`rounded-full p-2 ${TONE_ICON_CLASS[tone]}`}>
          <Icon size={15} />
        </span>
      </div>
      <p
        className={`mt-3 font-display font-semibold tabular-nums text-ink ${small ? 'text-base' : 'text-3xl'}`}
      >
        {formatValue(value)}
      </p>
      {caption ? <p className="mt-1 text-xs text-ink/40">{caption}</p> : null}
    </div>
  );
}
