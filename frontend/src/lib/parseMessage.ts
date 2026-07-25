/**
 * Turns the raw markdown-ish text HavisIQ's backend returns into a small
 * set of structured blocks the chat UI can render as premium components
 * (pricing cards, feature cards, a timeline, stat chips, tables) instead of
 * raw Markdown. Every rule here is a generic structural heuristic — pattern
 * matching on Markdown syntax and lightweight cues (currency symbols, "N+"
 * style numbers) — nothing is keyed to SPIDIFY, ZivaAIRA, or any other
 * specific product, so it works unchanged for any future Ha-Shem solution.
 *
 * The parser never throws on malformed/partial input (e.g. text stopped
 * mid-stream by the user): anything it can't confidently classify falls
 * back to a plain paragraph.
 */

export type FeatureItem = { title: string; body: string };
export type StepItem = { title: string; body: string };

export type MessageBlock =
  | { type: 'heading'; text: string }
  | { type: 'paragraph'; text: string }
  | { type: 'stats'; items: string[] }
  | { type: 'steps'; items: StepItem[] }
  | { type: 'features'; items: FeatureItem[] }
  | { type: 'checklist'; items: string[] }
  | { type: 'pricing'; plans: { name: string; price?: string; rows: { label: string; value: string }[] }[] }
  | { type: 'table'; headers: string[]; rows: string[][] };

// Matches "500+", "2M+", "4.9★", "3×", "24/7" — anchored so it only fires at
// the *start* of a short line (used to detect a standalone "stats row"),
// with a non-anchored twin below for inline highlighting inside prose.
const STAT_LINE_START = /^(?:\d[\d,]*(?:\.\d+)?(?:[KMB]\+?|\+|%)?|\d\.\d★|\d+×|24\/7)(?=\s|$)/i;
export const STAT_INLINE_REGEX =
  /\d[\d,]*(?:\.\d+)?(?:[KMB]\+?|\+|%)(?=[\s.,;:!?)]|$)|\d\.\d★|\d+×(?=[\s.,;:!?)]|$)|\b24\/7\b/gi;

const CURRENCY_REGEX = /[₦$€£]|\bNGN\b|\bUSD\b/i;
const PRICE_ROW_LABEL_REGEX = /price|pricing|cost|\/mo\b|\/month\b|per month/i;

const isTableRow = (line: string) => {
  const trimmed = line.trim();
  return trimmed.startsWith('|') || (trimmed.includes('|') && trimmed.split('|').length > 2);
};

const isSeparatorRow = (line: string) => /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(line);

const splitTableRow = (line: string): string[] =>
  line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim());

const isOrderedItem = (line: string) => /^\s*\d+[.)]\s+/.test(line);
const isBulletItem = (line: string) => /^\s*[-*•]\s+/.test(line);
const stripListMarker = (line: string) => line.trim().replace(/^\d+[.)]\s+/, '').replace(/^[-*•]\s+/, '');

const isHeadingLine = (line: string) => {
  const trimmed = line.trim();
  if (/^#{1,6}\s+/.test(trimmed)) return true;
  // A short, single bold line with no trailing sentence punctuation reads as
  // a section header (e.g. "**Key Features**"), not a bolded sentence.
  const boldOnly = trimmed.match(/^\*\*([^*]+)\*\*:?$/);
  return Boolean(boldOnly && boldOnly[1].length < 60);
};

const stripHeadingMarkup = (line: string) =>
  line
    .trim()
    .replace(/^#{1,6}\s+/, '')
    .replace(/^\*\*/, '')
    .replace(/\*\*:?$/, '')
    .trim();

/** Splits a bullet item into a bold title + description when the pattern is
 * clearly "**Title** — description" (or similar separators). */
const splitTitleBody = (text: string): FeatureItem | null => {
  const match = text.match(/^\*\*([^*]+)\*\*\s*[:\-–—]?\s*(.*)$/);
  if (!match) return null;
  const [, title, body] = match;
  if (!body || body.trim().length < 12) return null;
  return { title: title.trim(), body: body.trim() };
};

function parseMarkdownTable(lines: string[]): { headers: string[]; rows: string[][] } | null {
  if (lines.length < 2 || !isSeparatorRow(lines[1])) return null;
  const headers = splitTableRow(lines[0]);
  const rows = lines
    .slice(2)
    .map(splitTableRow)
    .filter((row) => row.some((cell) => cell.length > 0));
  if (!headers.length || !rows.length) return null;
  return { headers, rows };
}

/** A table reads as a pricing table when a currency symbol or price-ish
 * label shows up anywhere in the header row or first column. */
function tableToPricingBlock(headers: string[], rows: string[][]): MessageBlock | null {
  const looksLikePricing =
    headers.some((h) => CURRENCY_REGEX.test(h) || PRICE_ROW_LABEL_REGEX.test(h)) ||
    rows.some((row) => CURRENCY_REGEX.test(row[0] ?? ''));
  if (!looksLikePricing) return null;

  // Orientation A: rows are plans, first column is the plan name (a "Price"
  // column exists among the headers).
  const priceColIndex = headers.findIndex((h) => PRICE_ROW_LABEL_REGEX.test(h) || CURRENCY_REGEX.test(h));
  if (priceColIndex > 0) {
    const plans = rows.map((row) => ({
      name: row[0] ?? '',
      price: row[priceColIndex],
      rows: headers
        .map((label, i) => ({ label, value: row[i] ?? '' }))
        .filter((_, i) => i !== 0 && i !== priceColIndex && row[i]),
    }));
    if (plans.every((p) => p.name)) return { type: 'pricing', plans };
  }

  // Orientation B: columns are plans (headers[1:]), rows are attributes —
  // the comparison-table shape ("Feature | Plan A | Plan B").
  if (headers.length > 2) {
    const priceRow = rows.find((row) => PRICE_ROW_LABEL_REGEX.test(row[0] ?? '') || CURRENCY_REGEX.test(row[0] ?? ''));
    const plans = headers.slice(1).map((name, colIdx) => ({
      name,
      price: priceRow ? priceRow[colIdx + 1] : undefined,
      rows: rows
        .filter((row) => row !== priceRow)
        .map((row) => ({ label: row[0] ?? '', value: row[colIdx + 1] ?? '' }))
        .filter((r) => r.value),
    }));
    if (plans.every((p) => p.name)) return { type: 'pricing', plans };
  }

  return null;
}

/** A simple two-column table where the second column reads like prose is
 * really a feature list rendered as Markdown — treat it as one. */
function tableToFeaturesBlock(headers: string[], rows: string[][]): MessageBlock | null {
  if (headers.length !== 2) return null;
  const items = rows
    .map((row) => ({ title: row[0] ?? '', body: row[1] ?? '' }))
    .filter((item) => item.title && item.body.length > 12);
  if (items.length < 2 || items.length !== rows.length) return null;
  return { type: 'features', items };
}

function classifyBulletBlock(items: string[]): MessageBlock {
  const parsed = items.map((item) => splitTitleBody(stripListMarker(item)));
  const withTitles = parsed.filter((p): p is FeatureItem => p !== null);

  if (withTitles.length >= Math.ceil(items.length * 0.6)) {
    return { type: 'features', items: withTitles };
  }

  return { type: 'checklist', items: items.map((item) => stripListMarker(item)) };
}

function classifyOrderedBlock(items: string[]): MessageBlock {
  const stepItems: StepItem[] = items.map((item) => {
    const stripped = stripListMarker(item);
    const titled = splitTitleBody(stripped);
    if (titled) return titled;
    // Fall back to splitting on the first sentence boundary so long,
    // un-bolded numbered items still get a short title line.
    const sentenceSplit = stripped.match(/^(.{0,60}?[.:])\s+(.+)$/);
    if (sentenceSplit) return { title: sentenceSplit[1].replace(/[.:]$/, ''), body: sentenceSplit[2] };
    return { title: stripped, body: '' };
  });
  return { type: 'steps', items: stepItems };
}

export type InlineToken =
  | { kind: 'text'; value: string }
  | { kind: 'bold'; value: string }
  | { kind: 'citation'; value: string }
  | { kind: 'stat'; value: string };

const INLINE_MASTER_REGEX = new RegExp(
  `(\\*\\*[^*]+\\*\\*)|(\\[\\d+\\]|【\\d+】)|(${STAT_INLINE_REGEX.source})`,
  'gi'
);

/** Tokenizes a run of inline text into bold / citation-marker / stat /
 * plain-text pieces so the renderer can style each differently without a
 * full Markdown-inline parser. */
export function tokenizeInline(text: string): InlineToken[] {
  const tokens: InlineToken[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  INLINE_MASTER_REGEX.lastIndex = 0;

  while ((match = INLINE_MASTER_REGEX.exec(text))) {
    if (match.index > lastIndex) {
      tokens.push({ kind: 'text', value: text.slice(lastIndex, match.index) });
    }
    if (match[1]) {
      tokens.push({ kind: 'bold', value: match[1].slice(2, -2) });
    } else if (match[2]) {
      tokens.push({ kind: 'citation', value: match[2] });
    } else {
      tokens.push({ kind: 'stat', value: match[0] });
    }
    lastIndex = INLINE_MASTER_REGEX.lastIndex;
  }
  if (lastIndex < text.length) {
    tokens.push({ kind: 'text', value: text.slice(lastIndex) });
  }
  return tokens;
}

export function parseMessageContent(raw: string): MessageBlock[] {
  const text = (raw ?? '').replace(/\r\n/g, '\n');
  if (!text.trim()) return [];

  const rawBlocks = text.split(/\n\s*\n/).map((b) => b.split('\n').filter((l) => l.trim().length > 0));
  const blocks: MessageBlock[] = [];

  for (const lines of rawBlocks) {
    if (!lines.length) continue;

    // Table
    if (lines.length >= 2 && isTableRow(lines[0]) && isSeparatorRow(lines[1])) {
      const parsed = parseMarkdownTable(lines);
      if (parsed) {
        const pricing = tableToPricingBlock(parsed.headers, parsed.rows);
        if (pricing) {
          blocks.push(pricing);
          continue;
        }
        const features = tableToFeaturesBlock(parsed.headers, parsed.rows);
        if (features) {
          blocks.push(features);
          continue;
        }
        blocks.push({ type: 'table', headers: parsed.headers, rows: parsed.rows });
        continue;
      }
    }

    // Heading (single short bold/markdown-heading line)
    if (lines.length === 1 && isHeadingLine(lines[0])) {
      blocks.push({ type: 'heading', text: stripHeadingMarkup(lines[0]) });
      continue;
    }

    // Ordered list → steps/timeline
    if (lines.every(isOrderedItem)) {
      blocks.push(classifyOrderedBlock(lines));
      continue;
    }

    // Bullet list → features or checklist
    if (lines.every(isBulletItem)) {
      blocks.push(classifyBulletBlock(lines));
      continue;
    }

    // Standalone short stat lines ("500+ Companies", "4.9★ Rating", ...)
    if (
      lines.length >= 2 &&
      lines.length <= 6 &&
      lines.every((line) => line.trim().length <= 40 && STAT_LINE_START.test(line.trim()))
    ) {
      blocks.push({ type: 'stats', items: lines.map((l) => l.trim()) });
      continue;
    }

    // Plain paragraph — join wrapped lines into flowing prose.
    blocks.push({ type: 'paragraph', text: lines.join(' ').trim() });
  }

  // The model often appends its own numbered "Sources" section — the
  // dedicated SourceChips row (built from the API's separate `sources`
  // array, with real domain/title chips) already covers this and reads far
  // better, so drop everything from that heading onward to avoid a
  // duplicate, uglier list of raw citation text + parenthetical URLs.
  const sourcesHeadingIndex = blocks.findIndex(
    (block) => block.type === 'heading' && /^sources?$/i.test(block.text.trim())
  );
  return sourcesHeadingIndex === -1 ? blocks : blocks.slice(0, sourcesHeadingIndex);
}
