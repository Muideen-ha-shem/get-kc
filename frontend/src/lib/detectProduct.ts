import type { Solution } from '../solutions';

export type ProductHeaderInfo = {
  solution: Solution;
  stats: string[];
};

const COMPANY_STAT_REGEX = /\b\d[\d,]*\+?\s*(?:companies|customers|businesses|users|organi[sz]ations)\b/i;
const RATING_STAT_REGEX = /\b\d\.\d\s?(?:★|stars?|\/\s?5|rating)\b/i;
const SCALE_STAT_REGEX = /\b\d[\d,]*(?:\.\d+)?[KMB]\+?[ \t]+[A-Za-z][A-Za-z ]{0,24}/;

/**
 * Detects whether a response is describing a whole catalog solution (not
 * just mentioning it in passing) and, if so, returns the real catalog entry
 * plus any concrete stats actually present in the response text — never
 * fabricated. Generic against the `solutions` catalog, so it needs no
 * per-product code when a new Ha-Shem solution is added.
 */
export function detectProductHeader(content: string, solutions: Solution[]): ProductHeaderInfo | null {
  const trimmed = content.trim();
  if (trimmed.length < 250) return null;

  const lead = trimmed.slice(0, 160);
  const solution = solutions.find((s) => new RegExp(`\\b${escapeRegExp(s.name)}\\b`, 'i').test(lead));
  if (!solution) return null;

  const stats: string[] = [];
  const companyMatch = trimmed.match(COMPANY_STAT_REGEX);
  if (companyMatch) stats.push(titleCase(companyMatch[0]));
  const ratingMatch = trimmed.match(RATING_STAT_REGEX);
  if (ratingMatch) stats.push(ratingMatch[0].trim());
  if (stats.length < 2) {
    const scaleMatch = trimmed.match(SCALE_STAT_REGEX);
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
