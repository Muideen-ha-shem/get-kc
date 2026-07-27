/**
 * The Ha-Shem solution catalog has two sources:
 *
 * 1. "live" solutions — real products with their own knowledge base
 *    (SPIDIFY, ZivaAIRA, and the HAVIS-360 catalog). These come from
 *    `GET /solutions`, which reads directly from the backend's
 *    `PRODUCT_REGISTRY` (see `lib/useSolutions.ts`) — not hardcoded here,
 *    so the frontend catalog can never drift out of sync with it again.
 * 2. "advisory" solutions — business areas Ha-Shem delivers on without a
 *    dedicated product/knowledge base of their own. These have no backend
 *    registry entry (nothing to crawl or retrieve), so they stay a small,
 *    explicitly-separate static list here.
 */
export type SolutionStatus = 'live' | 'advisory';

export type Solution = {
  /** Stable identifier — also sent as `product` on demo requests. */
  id: string;
  name: string;
  category: string;
  description: string;
  status: SolutionStatus;
  highlights: string[];
  /** Short descriptor of who typically uses this solution. */
  typicalUsers?: string;
  /** External site, for solutions with their own dedicated product. */
  learnMoreUrl?: string;
};

export const ADVISORY_SERVICES: Solution[] = [
  {
    id: 'cybersecurity',
    name: 'Cybersecurity',
    category: 'Cybersecurity',
    description: 'Security assessments, compliance guidance, and protection strategies for your infrastructure.',
    status: 'advisory',
    highlights: ['Risk assessment', 'Compliance guidance', 'Threat protection'],
    typicalUsers: 'Security and compliance leaders',
  },
  {
    id: 'cloud-services',
    name: 'Cloud Services',
    category: 'Cloud Services',
    description: 'Cloud strategy, migration, and managed infrastructure for modern, resilient operations.',
    status: 'advisory',
    highlights: ['Cloud migration', 'Infrastructure strategy', 'Ongoing optimization'],
    typicalUsers: 'IT and infrastructure teams',
  },
  {
    id: 'software-development',
    name: 'Software Development',
    category: 'Software Development',
    description: 'Custom software and platform engineering, from architecture through delivery.',
    status: 'advisory',
    highlights: ['Custom builds', 'Platform engineering', 'Technical architecture'],
    typicalUsers: 'Product and engineering leaders',
  },
  {
    id: 'managed-services',
    name: 'Managed Services',
    category: 'Managed Services',
    description: 'Ongoing operational support so your team can focus on the business, not the infrastructure.',
    status: 'advisory',
    highlights: ['24/7 support', 'Proactive monitoring', 'SLA-backed delivery'],
    typicalUsers: 'Operations and IT leaders',
  },
  {
    id: 'training',
    name: 'Training',
    category: 'Training',
    description: 'Hands-on training and certification programs to build capability inside your team.',
    status: 'advisory',
    highlights: ['Certification programs', 'Hands-on workshops', 'Team enablement'],
    typicalUsers: 'L&D and technical teams',
  },
];
