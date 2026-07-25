/**
 * The Ha-Shem solution catalog. SPIDIFY and ZivaAIRA are the first two
 * entries with a dedicated product and knowledge base ("live"); everything
 * else is a business area Ha-Shem advises and delivers on today without a
 * standalone product site yet ("advisory"). Adding a new solution — a new
 * product launch, or promoting an advisory category to "live" once it has
 * its own site — is a one-line addition here; nothing else in the app
 * needs to change.
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
  /** External site, for solutions with their own dedicated product. */
  learnMoreUrl?: string;
};

export const solutions: Solution[] = [
  {
    id: 'SPIDIFY',
    name: 'SPIDIFY',
    category: 'Identity Verification',
    description: 'Identity verification, KYC, and secure access — verify users and protect onboarding at scale.',
    status: 'live',
    highlights: ['Secure KYC', 'User authentication', 'Identity validation'],
    learnMoreUrl: 'https://havisspidify.com/',
  },
  {
    id: 'ZivaAIRA',
    name: 'ZivaAIRA',
    category: 'HR & Recruitment',
    description: 'Recruitment, hiring automation, and HR workflow management for growing teams.',
    status: 'live',
    highlights: ['Talent acquisition', 'Hiring automation', 'HR workflow management'],
    learnMoreUrl: 'https://aira.havis360.com/',
  },
  {
    id: 'cybersecurity',
    name: 'Cybersecurity',
    category: 'Cybersecurity',
    description: 'Security assessments, compliance guidance, and protection strategies for your infrastructure.',
    status: 'advisory',
    highlights: ['Risk assessment', 'Compliance guidance', 'Threat protection'],
  },
  {
    id: 'cloud-services',
    name: 'Cloud Services',
    category: 'Cloud Services',
    description: 'Cloud strategy, migration, and managed infrastructure for modern, resilient operations.',
    status: 'advisory',
    highlights: ['Cloud migration', 'Infrastructure strategy', 'Ongoing optimization'],
  },
  {
    id: 'software-development',
    name: 'Software Development',
    category: 'Software Development',
    description: 'Custom software and platform engineering, from architecture through delivery.',
    status: 'advisory',
    highlights: ['Custom builds', 'Platform engineering', 'Technical architecture'],
  },
  {
    id: 'managed-services',
    name: 'Managed Services',
    category: 'Managed Services',
    description: 'Ongoing operational support so your team can focus on the business, not the infrastructure.',
    status: 'advisory',
    highlights: ['24/7 support', 'Proactive monitoring', 'SLA-backed delivery'],
  },
  {
    id: 'training',
    name: 'Training',
    category: 'Training',
    description: 'Hands-on training and certification programs to build capability inside your team.',
    status: 'advisory',
    highlights: ['Certification programs', 'Hands-on workshops', 'Team enablement'],
  },
];
