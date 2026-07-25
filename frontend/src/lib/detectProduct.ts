import type { Solution } from '../solutions';

export type ProductHeaderInfo = {
  solution: Solution;
  stats: string[];
};

// Require at least 2 digits (or a "+"/comma) so small counts that happen to
// share a keyword with real scale claims — a plan's "5 Users" seat limit,
// say — don't get mistaken for a "trusted by N companies" marketing stat.
const COMPANY_STAT_REGEX = /\b\d{2,}[\d,]*\+?\s*(?:companies|customers|businesses|organi[sz]ations)\b/i;
const RATING_STAT_REGEX = /\b\d\.\d\s?(?:★|stars?|\/\s?5|rating)\b/i;
const SCALE_STAT_REGEX = /\b\d[\d,]*(?:\.\d+)?[KMB]\+[ \t]+[A-Za-z][A-Za-z ]{0,24}/;

// Headline scale/trust claims belong in a response's opening framing, not
// buried mid-document (a pricing table row, a feature aside) — scoping the
// stat search to the lead avoids surfacing an unrelated number as if it
// were the product's marketing stat.
const STAT_SEARCH_WINDOW = 400;

/**
 * Detects whether a response is describing a whole catalog solution (not
 * just mentioning it in passing) and, if so, returns the real catalog entry
 * plus any concrete stats actually present in the response's lead text —
 * never fabricated. Generic against the `solutions` catalog, so it needs no
 * per-product code when a new Ha-Shem solution is added.
 */
export function detectProductHeader(content: string, solutions: Solution[]): ProductHeaderInfo | null {
  const trimmed = content.trim();
  if (trimmed.length < 250) return null;

  const lead = trimmed.slice(0, 160);
  const solution = solutions.find((s) => new RegExp(`\\b${escapeRegExp(s.name)}\\b`, 'i').test(lead));
  if (!solution) return null;

  const statWindow = trimmed.slice(0, STAT_SEARCH_WINDOW);
  const stats: string[] = [];
  const companyMatch = statWindow.match(COMPANY_STAT_REGEX);
  if (companyMatch) stats.push(titleCase(companyMatch[0]));
  const ratingMatch = statWindow.match(RATING_STAT_REGEX);
  if (ratingMatch) stats.push(ratingMatch[0].trim());
  if (stats.length < 2) {
    const scaleMatch = statWindow.match(SCALE_STAT_REGEX);
    if (scaleMatch && !stats.includes(scaleMatch[0])) stats.push(scaleMatch[0].trim());
  }

  return { solution, stats: stats.slice(0, 3) };
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function titleCase(value: string): string {
  return value.replace(/\w\S*/g, (w) => w.charAt(0).toUpperCase() + w.slice(1));
}
