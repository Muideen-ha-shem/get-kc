/**
 * Shared className recipes for the post-login (admin/agent/knowledge/team)
 * pages. Extracted from what AdminWorkspaceDetailPage/KnowledgeManagementPage/
 * AdminOnboardingWizardPage/AdminUsersPage each re-declared locally, with
 * focus-visible rings and hover/active micro-interactions added everywhere
 * (previously missing) — no new colors, same ink/paper/gold tokens.
 */

const FOCUS_RING =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold-400/50 focus-visible:ring-offset-2 focus-visible:ring-offset-paper';

export const INPUT_CLASS =
  `w-full border border-ink/10 rounded-xl px-3 py-2 mt-1 bg-paper text-ink text-sm outline-none transition-colors focus:border-gold-400 ${FOCUS_RING}`;

export const PRIMARY_BUTTON =
  `rounded-full bg-ink px-4 py-2 text-sm font-semibold text-paper transition hover:bg-ink-soft hover:-translate-y-0.5 hover:shadow-sm active:translate-y-0 active:shadow-none ${FOCUS_RING}`;

export const SECONDARY_BUTTON =
  `rounded-full border border-ink/15 px-3 py-1 text-xs text-ink transition hover:border-gold-400 hover:text-gold-700 hover:-translate-y-0.5 hover:shadow-sm active:translate-y-0 active:shadow-none ${FOCUS_RING}`;

export const DANGER_BUTTON =
  `rounded-full bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700 hover:-translate-y-0.5 hover:shadow-sm active:translate-y-0 active:shadow-none disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-none ${FOCUS_RING}`;

export const CARD =
  'bg-white border border-ink/10 rounded-2xl transition hover:border-gold-300/70 hover:shadow-sm';
