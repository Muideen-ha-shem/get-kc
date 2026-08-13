/** Sources are hidden by default (see App.tsx/DashboardPage.tsx) so a chat
 * answer never hands the customer an outbound link off the platform. This
 * detects the one case they should reappear: the customer explicitly asked
 * where the information came from. Shared by both chat surfaces so the
 * definition of "asked for the source" can't drift between them. */
const SOURCE_REQUEST_KEYWORDS = [
  'where did you get this',
  'where did that come from',
  'show me the source',
  'show me your source',
  'what is your source',
  "what's your source",
  'cite your source',
  'cite your sources',
  'source please',
  'what are your sources',
];

export function isSourceRequest(question: string | undefined | null): boolean {
  if (!question) return false;
  const lowered = question.toLowerCase();
  return SOURCE_REQUEST_KEYWORDS.some((keyword) => lowered.includes(keyword));
}
