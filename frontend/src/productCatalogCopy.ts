/**
 * Presentation-only copy layered on top of the live `/solutions` API data.
 *
 * `GET /solutions` (backed by `PRODUCT_REGISTRY`) is the source of truth for
 * what a product *is* — its name, category, business problem, and URL. It
 * doesn't carry marketing bullet points or "who's this for" labels, so
 * those are curated here, the same way the original catalog already
 * hand-wrote `highlights` for every entry. Falls back gracefully (empty
 * highlights, generic "Business and operations teams" label) for any
 * product added to the registry that doesn't have an entry here yet — a
 * new product works immediately, this is purely cosmetic enrichment.
 */

export const HIGHLIGHTS_BY_PRODUCT: Record<string, string[]> = {
  SPIDIFY: ['Secure KYC', 'User authentication', 'Identity validation'],
  ZivaAIRA: ['Talent acquisition', 'Hiring automation', 'HR workflow management'],
  'V-Login': ['Visitor check-in', 'Badge generation', 'Pre-registration'],
  STAAS: ['Real-time attendance monitoring', 'Mobile & desktop sign-in', 'Active Directory integration'],
  WeCare: ['Ticket tracking', 'Escalation management', 'Systematic documentation'],
  'Havis Xpend': ['Expense tracking', 'Procurement & travel spend', 'Petty cash management'],
  'Havis Vacay': ['One-click leave requests', 'Balance tracking', 'Automated approvals'],
  'Havis iReport': ['Task & activity tracking', 'Daily/weekly/monthly reports', 'Performance accountability'],
  'Havis REMA': ['Digital receipt submission', 'Paperless record-keeping', 'Expense documentation'],
  'Havis eCertify': ['Certification management', 'Exam & training requests', 'Curated learning content'],
  KwikAlert: ['Real-time alerts', 'Desktop notifications', 'Company-wide broadcasts'],
  AppManage: ['License activation', 'Renewal tracking', 'Customer license management'],
  PayCheq: ['Staff payroll self-service', 'Admin payroll control', 'Tax & compliance management'],
};

/**
 * Per-product logo image, shown in place of the plain text-on-gradient
 * tile the catalog card used before. Only SPIDIFY and ZivaAIRA have their
 * own brand mark today — every other product (and any future one added
 * to PRODUCT_REGISTRY that isn't listed here yet) falls back to the
 * Ha-Shem company mark via getProductLogo() below, rather than showing
 * nothing.
 */
export const LOGO_BY_PRODUCT: Record<string, string> = {
  SPIDIFY: '/logo/spidify-logo.png',
  ZivaAIRA: '/logo/ziva-aira-logo.svg',
};

const DEFAULT_LOGO = '/logo/Ha-Shem-Logo-dark.png';

export function getProductLogo(productId: string): string {
  return LOGO_BY_PRODUCT[productId] ?? DEFAULT_LOGO;
}

export const TYPICAL_USERS_BY_PRODUCT: Record<string, string> = {
  SPIDIFY: 'Compliance, security, and onboarding teams',
  ZivaAIRA: 'Recruiters and HR teams',
  'V-Login': 'Front-desk and facilities teams',
  STAAS: 'HR and workforce management teams',
  WeCare: 'Support and service teams',
  'Havis Xpend': 'Finance and procurement teams',
  'Havis Vacay': 'HR teams and employees',
  'Havis iReport': 'Managers and team leads',
  'Havis REMA': 'Finance and admin teams',
  'Havis eCertify': 'L&D teams and employees',
  KwikAlert: 'Facilities and operations teams',
  AppManage: 'IT and license administrators',
  PayCheq: 'Payroll and finance teams',
};

/**
 * Maps a raw PRODUCT_REGISTRY category (specific, one-per-product) to the
 * broader logical group the Solution Catalog section organizes cards
 * under. Unmapped categories fall back to "Other Solutions" rather than
 * being dropped, so a newly-registered product always shows up somewhere.
 */
const CATEGORY_TO_GROUP: Record<string, string> = {
  'Identity Verification': 'Identity & Security',
  'Visitor & Access Management': 'Identity & Security',
  'HR Recruitment': 'Human Resources',
  'Workforce Attendance': 'Human Resources',
  'Leave Management': 'Human Resources',
  Payroll: 'Human Resources',
  'Customer & Employee Support': 'Operations & Support',
  'Emergency Communication': 'Operations & Support',
  'Software Licensing': 'Operations & Support',
  'Expense Management': 'Finance',
  'Receipt & Document Management': 'Finance',
  Reporting: 'Business Intelligence',
  'Learning & Certification': 'Learning & Compliance',
  Cybersecurity: 'Advisory Services',
  'Cloud Services': 'Advisory Services',
  'Software Development': 'Advisory Services',
  'Managed Services': 'Advisory Services',
  Training: 'Advisory Services',
};

const GROUP_ORDER = [
  'Identity & Security',
  'Human Resources',
  'Operations & Support',
  'Finance',
  'Business Intelligence',
  'Learning & Compliance',
  'Advisory Services',
  'Other Solutions',
];

export function groupForCategory(category: string): string {
  return CATEGORY_TO_GROUP[category] ?? 'Other Solutions';
}

export function sortGroups(groups: string[]): string[] {
  return [...groups].sort((a, b) => {
    const ai = GROUP_ORDER.indexOf(a);
    const bi = GROUP_ORDER.indexOf(b);
    if (ai === -1 && bi === -1) return a.localeCompare(b);
    if (ai === -1) return 1;
    if (bi === -1) return -1;
    return ai - bi;
  });
}
