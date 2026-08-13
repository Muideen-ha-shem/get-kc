import { AnimatePresence, motion } from 'framer-motion';
import { FormEvent, MouseEvent as ReactMouseEvent, useEffect, useRef, useState } from 'react';
import {
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  CircleHelp,
  Code2,
  Download,
  GitCompare,
  Headphones,
  MessageCircleMore,
  Search,
  Sparkles,
  Square,
  Star,
  Ticket,
  SendHorizonal,
  X,
  Zap,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { HavisIQMark } from './components/HavisIQMark';
import { DemoRequestModal } from './components/DemoRequestModal';
import { CompareSolutionsModal } from './components/CompareSolutionsModal';
import { AuthModal } from './components/auth/AuthModal';
import { AppointmentScheduler } from './components/AppointmentScheduler';
import { MessageContent } from './components/message/MessageContent';
import { MessageActions } from './components/message/MessageActions';
import { SourceChips } from './components/message/SourceChips';
import { isSourceRequest } from './lib/sourceRequest';
import { detectProductHeader } from './lib/detectProduct';
import { type Solution } from './solutions';
import { useSolutions } from './lib/useSolutions';
import { getProductLogo, groupForCategory, sortGroups } from './productCatalogCopy';
import { useAuth } from './lib/authContext';
import { apiFetch } from './lib/apiClient';
import { getSessionId } from './lib/sessionId';
import { downloadMarkdown, messagesToMarkdown } from './lib/exportConversation';

type NextAction = { label: string; action_type: string; target: string | null };

type Message = {
  id: number;
  sender: 'user' | 'assistant';
  content: string;
  isTyping?: boolean;
  sources?: string[];
  question?: string;
  nextActions?: NextAction[];
  savedRecommendation?: boolean;
};

const navigation = ['Home', 'Solutions', 'Support Center', 'Contact'];

const supportWidgets = [
  { title: 'Submit Ticket', desc: 'Create a new case in minutes', icon: Ticket },
  { title: 'Track Ticket', desc: 'Follow progress in real time', icon: CircleHelp },
  { title: 'Knowledge Base', desc: 'Browse answers and documentation', icon: Sparkles },
  { title: 'Contact Support', desc: 'Speak to a specialist instantly', icon: Headphones },
];

const CHAT_PANEL_DEFAULT_WIDTH = 420;
const CHAT_PANEL_DEFAULT_HEIGHT = 640;
const CHAT_PANEL_DEFAULT_LEFT = 16;
const CHAT_PANEL_DEFAULT_BOTTOM = 16;
const CHAT_PANEL_MIN_WIDTH = 320;
const CHAT_PANEL_MAX_WIDTH = 640;
const CHAT_PANEL_MIN_HEIGHT = 380;
const CHAT_PANEL_MAX_HEIGHT = 860;
const CHAT_PANEL_VIEWPORT_MARGIN = 16;

type ChatResizeEdge = 'left' | 'right' | 'top' | 'bottom';

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

// Kept short deliberately — shown only before the user's first message
// (see hasUserMessage below), so it's a quick-start row, not a permanent
// fixture crowding the panel on every turn. The compact hero mock uses a
// short slice of these.
const suggestedPrompts = [
  'Recommend the best solution for my business',
  'Compare SPIDIFY and V-Login',
  'Which solution handles payroll?',
  'I need cybersecurity services',
  'Tell me about Ha-Shem',
];
const heroPrompts = suggestedPrompts.slice(0, 4);

// "What are you trying to solve?" — Business Problem Discovery. Each
// problem is matched against a solution's name/category/description
// client-side (no API call — instant catalog highlighting), reusing
// whatever's already in the fetched Product Registry data rather than a
// second hardcoded product mapping.
const businessProblems: { label: string; match: string[] }[] = [
  { label: 'Identity Verification', match: ['identity', 'kyc', 'verification'] },
  { label: 'Recruitment', match: ['recruit', 'hiring', 'hr recruitment', 'candidate'] },
  { label: 'Visitor Management', match: ['visitor'] },
  { label: 'Attendance Tracking', match: ['attendance'] },
  { label: 'Leave Management', match: ['leave', 'vacation', 'absence'] },
  { label: 'Expense Management', match: ['expense'] },
  { label: 'Payroll', match: ['payroll', 'salary'] },
  { label: 'Reporting', match: ['report'] },
  { label: 'Compliance', match: ['compliance', 'certification', 'learning'] },
  { label: 'Software Licensing', match: ['licens'] },
  { label: 'Custom Software', match: ['software development', 'custom'] },
  { label: 'Cloud Migration', match: ['cloud'] },
  { label: 'Cybersecurity', match: ['cybersecurity', 'security'] },
];

function matchesProblem(solution: Solution, problem: { match: string[] }): boolean {
  const haystack = `${solution.name} ${solution.category} ${solution.description}`.toLowerCase();
  return problem.match.some((term) => haystack.includes(term));
}

const renderFormattedContent = (content: string) => {
  const lines = content.split('\n');

  return lines.map((line, lineIndex) => {
    const parts = line.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);

    return (
      <div key={`${lineIndex}-${line}`} className="whitespace-pre-wrap">
        {parts.map((part, partIndex) => {
          if (part.startsWith('**') && part.endsWith('**')) {
            return (
              <strong key={`${lineIndex}-${partIndex}`} className="font-semibold text-ink">
                {part.slice(2, -2)}
              </strong>
            );
          }

          return <span key={`${lineIndex}-${partIndex}`}>{part}</span>;
        })}
      </div>
    );
  });
};

function App() {
  const { solutions, isLoading: solutionsLoading, error: solutionsError } = useSolutions();
  const [selectedProblem, setSelectedProblem] = useState<string | null>(null);
  const [compareInitialId, setCompareInitialId] = useState<string | undefined>(undefined);

  const [isAssistantOpen, setIsAssistantOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      sender: 'assistant',
      content: "Hi! What are you trying to solve?",
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const streamIntervalRef = useRef<number | null>(null);
  const activeAssistantIdRef = useRef<number | null>(null);

  const [demoModal, setDemoModal] = useState<{ open: boolean; solution?: Solution }>({ open: false });
  const [isCompareOpen, setIsCompareOpen] = useState(false);
  const { user } = useAuth();
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  const openDemoModal = (solution?: Solution) => setDemoModal({ open: true, solution });
  const closeDemoModal = () => setDemoModal((prev) => ({ ...prev, open: false }));

  const openCompareModal = (preselectId?: string) => {
    setCompareInitialId(preselectId);
    setIsCompareOpen(true);
  };

  const activeProblem = businessProblems.find((p) => p.label === selectedProblem) ?? null;
  const matchedSolutionIds = activeProblem
    ? new Set(solutions.filter((s) => matchesProblem(s, activeProblem)).map((s) => s.id))
    : null;

  const groupedSolutions = sortGroups(
    Array.from(new Set(solutions.map((s) => groupForCategory(s.category))))
  ).map((group) => ({
    group,
    items: solutions.filter((s) => groupForCategory(s.category) === group),
  }));

  const [chatWidth, setChatWidth] = useState(CHAT_PANEL_DEFAULT_WIDTH);
  const [chatHeight, setChatHeight] = useState(CHAT_PANEL_DEFAULT_HEIGHT);
  const [chatLeft, setChatLeft] = useState(CHAT_PANEL_DEFAULT_LEFT);
  const [chatBottom, setChatBottom] = useState(CHAT_PANEL_DEFAULT_BOTTOM);
  const [isResizing, setIsResizing] = useState(false);
  const resizeStateRef = useRef<{
    edge: ChatResizeEdge;
    startX: number;
    startY: number;
    startWidth: number;
    startHeight: number;
    startLeft: number;
    startBottom: number;
  } | null>(null);

  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      const state = resizeStateRef.current;
      if (!state) return;

      const dx = event.clientX - state.startX;
      const dy = event.clientY - state.startY;

      if (state.edge === 'left') {
        const rightEdge = state.startLeft + state.startWidth;
        const maxWidth = Math.min(CHAT_PANEL_MAX_WIDTH, window.innerWidth - 2 * CHAT_PANEL_VIEWPORT_MARGIN);
        const nextWidth = clamp(state.startWidth - dx, CHAT_PANEL_MIN_WIDTH, maxWidth);
        const nextLeft = Math.max(CHAT_PANEL_VIEWPORT_MARGIN, rightEdge - nextWidth);
        setChatWidth(nextWidth);
        setChatLeft(nextLeft);
      } else if (state.edge === 'right') {
        const maxWidth = Math.min(
          CHAT_PANEL_MAX_WIDTH,
          window.innerWidth - state.startLeft - CHAT_PANEL_VIEWPORT_MARGIN
        );
        const nextWidth = clamp(state.startWidth + dx, CHAT_PANEL_MIN_WIDTH, maxWidth);
        setChatWidth(nextWidth);
      } else if (state.edge === 'top') {
        // Dragging the top border up grows the panel while the bottom edge
        // (its anchor point) stays put.
        const maxHeight = Math.min(
          CHAT_PANEL_MAX_HEIGHT,
          window.innerHeight - state.startBottom - CHAT_PANEL_VIEWPORT_MARGIN
        );
        const nextHeight = clamp(state.startHeight - dy, CHAT_PANEL_MIN_HEIGHT, maxHeight);
        setChatHeight(nextHeight);
      } else if (state.edge === 'bottom') {
        // Dragging the bottom border down grows the panel while the top
        // edge stays put — recompute `bottom` so the top position holds.
        const topPx = window.innerHeight - state.startBottom - state.startHeight;
        const maxHeight = Math.min(CHAT_PANEL_MAX_HEIGHT, window.innerHeight - topPx - CHAT_PANEL_VIEWPORT_MARGIN);
        const nextHeight = clamp(state.startHeight + dy, CHAT_PANEL_MIN_HEIGHT, maxHeight);
        const nextBottom = Math.max(CHAT_PANEL_VIEWPORT_MARGIN, window.innerHeight - topPx - nextHeight);
        setChatHeight(nextHeight);
        setChatBottom(nextBottom);
      }
    };

    const handleMouseUp = () => {
      if (!resizeStateRef.current) return;
      resizeStateRef.current = null;
      setIsResizing(false);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  const handleResizeStart = (edge: ChatResizeEdge) => (event: ReactMouseEvent) => {
    event.preventDefault();
    resizeStateRef.current = {
      edge,
      startX: event.clientX,
      startY: event.clientY,
      startWidth: chatWidth,
      startHeight: chatHeight,
      startLeft: chatLeft,
      startBottom: chatBottom,
    };
    setIsResizing(true);
    document.body.style.userSelect = 'none';
    document.body.style.cursor = edge === 'left' || edge === 'right' ? 'col-resize' : 'row-resize';
  };

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, isAssistantOpen]);

  const handlePrompt = (prompt: string) => {
    if (!prompt.trim()) return;
    setIsAssistantOpen(true);
    setInput(prompt);
  };

  const streamAssistantReply = async (question: string, assistantMessageId: number) => {
    activeAssistantIdRef.current = assistantMessageId;
    setIsTyping(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const response = await apiFetch('/chat', {
        method: 'POST',
        body: JSON.stringify({ message: question, session_id: getSessionId() }),
        signal: controller.signal,
      });

      const data = await response.json();
      const answer = data.answer || 'I could not generate a response right now.';
      const sources = Array.isArray(data.sources) ? data.sources : [];
      const nextActions: NextAction[] = Array.isArray(data.next_actions) ? data.next_actions : [];

      // Reveal in chunks sized so the whole answer streams in roughly
      // TARGET_STREAM_DURATION_MS regardless of length — a 3-line answer
      // and a 20-line answer both feel similarly snappy, instead of long
      // answers dragging on for many extra seconds at a fixed 1-char/tick
      // pace.
      let streamedIndex = 0;
      const streamTickMs = 16;
      const targetStreamDurationMs = 700;
      const charsPerTick = Math.max(1, Math.ceil(answer.length / (targetStreamDurationMs / streamTickMs)));

      const streamInterval = window.setInterval(() => {
        streamedIndex = Math.min(streamedIndex + charsPerTick, answer.length);
        const nextContent = answer.slice(0, streamedIndex);

        setMessages((prev) =>
          prev.map((message) => (message.id === assistantMessageId ? { ...message, content: nextContent } : message))
        );

        if (streamedIndex >= answer.length) {
          window.clearInterval(streamInterval);
          streamIntervalRef.current = null;
          abortControllerRef.current = null;
          activeAssistantIdRef.current = null;
          setMessages((prev) =>
            prev.map((message) =>
              message.id === assistantMessageId
                ? { ...message, isTyping: false, sources, question, nextActions, savedRecommendation: false }
                : message
            )
          );
          setIsTyping(false);
        }
      }, streamTickMs);
      streamIntervalRef.current = streamInterval;
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }
      setMessages((prev) =>
        prev.map((message) =>
          message.id === assistantMessageId
            ? { ...message, content: 'I’m sorry, I’m having trouble reaching HavisIQ right now.', isTyping: false }
            : message
        )
      );
      setIsTyping(false);
      abortControllerRef.current = null;
      activeAssistantIdRef.current = null;
    }
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isTyping) return;

    const userMessage: Message = { id: Date.now(), sender: 'user', content: trimmed };
    const assistantMessageId = Date.now() + 1;

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsAssistantOpen(true);
    setMessages((prev) => [...prev, { id: assistantMessageId, sender: 'assistant', content: '', isTyping: true }]);

    await streamAssistantReply(trimmed, assistantMessageId);
  };

  const handleRegenerate = async (message: Message) => {
    if (isTyping || !message.question) return;
    setMessages((prev) =>
      prev.map((m) => (m.id === message.id ? { ...m, content: '', isTyping: true, sources: undefined } : m))
    );
    await streamAssistantReply(message.question, message.id);
  };

  const handleStopGenerating = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    if (streamIntervalRef.current !== null) {
      window.clearInterval(streamIntervalRef.current);
      streamIntervalRef.current = null;
    }
    const targetId = activeAssistantIdRef.current;
    if (targetId !== null) {
      setMessages((prev) =>
        prev
          .map((message) => (message.id === targetId ? { ...message, isTyping: false } : message))
          // Nothing had streamed in yet (stopped while still awaiting the
          // response) — drop the empty bubble rather than leaving it stranded.
          .filter((message) => message.id !== targetId || message.content.trim().length > 0)
      );
    }
    activeAssistantIdRef.current = null;
    setIsTyping(false);
  };

  const recommendedProductsFor = (message: Message): string[] => {
    const header = detectProductHeader(message.content, solutions);
    const fromActions = (message.nextActions ?? [])
      .filter((a) => a.action_type === 'learn_more' || a.action_type === 'request_demo' || a.action_type === 'compare')
      .map((a) => a.target)
      .filter((t): t is string => Boolean(t));
    const products = new Set<string>(fromActions);
    if (header) products.add(header.solution.name);
    return Array.from(products);
  };

  const handleSaveRecommendation = async (message: Message) => {
    const products = recommendedProductsFor(message);
    if (products.length === 0) return;
    try {
      const response = await apiFetch('/saved-recommendations', {
        method: 'POST',
        body: JSON.stringify({
          products,
          question: message.question || '',
          recommendation: message.content,
        }),
      });
      if (!response.ok) return;
      setMessages((prev) => prev.map((m) => (m.id === message.id ? { ...m, savedRecommendation: true } : m)));
    } catch {
      // Non-critical enrichment — a failed save just leaves the button clickable again.
    }
  };

  const handleExportConversation = () => {
    const exportable = messages
      .filter((m) => !m.isTyping)
      .map((m) => ({ role: m.sender, content: m.content, sources: m.sources }));
    if (exportable.length === 0) return;
    const markdown = messagesToMarkdown('HavisIQ Conversation', exportable);
    downloadMarkdown(`havisiq-conversation-${new Date().toISOString().slice(0, 10)}.md`, markdown);
  };

  const quickActions = [
    {
      title: 'Explore Solutions',
      description: 'Browse the full Ha-Shem solution catalog',
      icon: Sparkles,
      onClick: () => document.getElementById('solutions')?.scrollIntoView({ behavior: 'smooth' }),
    },
    {
      title: 'Compare Solutions',
      description: 'See how our solutions stack up side by side',
      icon: GitCompare,
      onClick: () => setIsCompareOpen(true),
    },
    {
      title: 'Talk to an Expert',
      description: 'Get a personal recommendation from our team',
      icon: Headphones,
      onClick: () => openDemoModal(),
    },
    {
      title: 'Schedule Meeting',
      description: 'Book a consultation with our team',
      icon: CalendarDays,
      onClick: () => openDemoModal(),
    },
  ];

  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="sticky top-0 z-50 border-b border-ink/10 bg-white/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4 lg:px-8">
          <div className="flex items-center gap-3">
            <HavisIQMark size={40} />
            <div>
              <p className="font-display text-lg tracking-tight">HavisIQ</p>
              <p className="text-[11px] uppercase tracking-[0.32em] text-ink/50">AI Solutions Advisor</p>
            </div>
          </div>

          <nav className="hidden items-center gap-8 text-sm font-medium text-ink/70 lg:flex">
            {navigation.map((item) => (
              <a key={item} href={`#${item.toLowerCase().replace(/ /g, '-')}`} className="transition hover:text-ink">
                {item}
              </a>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            {user ? (
              <Link
                to="/dashboard"
                className="rounded-full border border-ink/15 px-4 py-2.5 text-sm font-semibold text-ink transition hover:bg-paper"
              >
                Dashboard
              </Link>
            ) : (
              <button
                type="button"
                onClick={() => setIsAuthModalOpen(true)}
                className="rounded-full border border-ink/15 px-4 py-2.5 text-sm font-semibold text-ink transition hover:bg-paper"
              >
                Sign In
              </button>
            )}
            <button
              type="button"
              onClick={() => openDemoModal()}
              className="rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-paper shadow-lg shadow-ink/10 transition hover:-translate-y-0.5 hover:bg-ink-soft"
            >
              Request a demo
            </button>
          </div>
        </div>
      </header>
      <AuthModal isOpen={isAuthModalOpen} onClose={() => setIsAuthModalOpen(false)} />

      <main>
        <section className="relative overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(200,154,62,0.14),_transparent_40%),linear-gradient(135deg,_#f7f8fa_0%,_#eceef2_100%)]">
          <div className="mx-auto grid max-w-7xl gap-12 px-6 py-20 lg:grid-cols-[1.05fr_0.95fr] lg:px-8 lg:py-28">
            <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="max-w-2xl">
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-gold-300 bg-gold-50 px-4 py-2 text-sm font-medium text-gold-700">
                <Zap size={16} />
                AI Solutions Advisor for the Ha-Shem ecosystem
              </div>
              <h1 className="font-display text-4xl tracking-tight text-ink sm:text-5xl lg:text-6xl">
                One assistant. The right solution, every time.
              </h1>
              <p className="mt-6 text-lg leading-8 text-ink/65">
                Describe a business need — identity verification, recruitment, attendance, payroll, expenses,
                cybersecurity, cloud, or custom software — and HavisIQ matches it to the right Ha-Shem solution,
                with sources, in seconds, across a growing catalog of {solutionsLoading ? '13+' : solutions.length}{' '}
                business solutions.
              </p>
              <div className="mt-8 flex flex-wrap gap-4">
                <a href="#solutions" className="rounded-full border border-ink/15 bg-white px-6 py-3.5 font-semibold text-ink transition hover:-translate-y-0.5 hover:border-gold-400 hover:text-gold-700">
                  Explore Solutions
                </a>
                <button
                  type="button"
                  onClick={() => setIsCompareOpen(true)}
                  className="rounded-full px-6 py-3.5 font-semibold text-ink/70 transition hover:text-gold-700"
                >
                  Compare Solutions →
                </button>
              </div>
              <div className="mt-10 flex flex-wrap gap-4 text-sm text-ink/65">
                {['Instant answers', 'Solution matching', 'Tickets & appointments', 'Secure support'].map((item) => (
                  <div key={item} className="flex items-center gap-2 rounded-full bg-white/80 px-3 py-2 shadow-sm ring-1 ring-ink/10">
                    <CheckCircle2 size={16} className="text-emerald-500" />
                    {item}
                  </div>
                ))}
              </div>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.1 }} className="relative">
              <div className="absolute inset-0 rounded-[2rem] bg-gradient-to-br from-gold-300/25 via-transparent to-ink/10 blur-3xl" />
              <div className="relative overflow-hidden rounded-[2rem] border border-ink/10 bg-white/90 p-4 shadow-[0_25px_80px_rgba(20,23,29,0.12)] backdrop-blur">
                <div className="rounded-[1.5rem] border border-white/10 bg-ink p-4 text-paper">
                  <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                    <div className="flex items-center gap-3">
                      <HavisIQMark size={40} />
                      <div>
                        <p className="font-display font-semibold">HavisIQ</p>
                        <p className="text-xs text-paper/60">Online • Ready to help</p>
                      </div>
                    </div>
                    <div className="rounded-full border border-emerald-400/30 bg-emerald-500/15 px-3 py-1 text-xs font-medium text-emerald-300">
                      Secure & Live
                    </div>
                  </div>

                  <div className="relative mt-4 space-y-3 overflow-hidden rounded-2xl border border-white/10 bg-black/20 p-4">
                    <motion.div
                      aria-hidden
                      className="pointer-events-none absolute -left-10 -top-12 h-32 w-32 rounded-full bg-gold-400/20 blur-3xl"
                      animate={{ x: [0, 16, 0], y: [0, 12, 0], opacity: [0.45, 0.75, 0.45] }}
                      transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }}
                    />
                    <motion.div
                      aria-hidden
                      className="pointer-events-none absolute -bottom-14 -right-10 h-36 w-36 rounded-full bg-emerald-400/10 blur-3xl"
                      animate={{ x: [0, -14, 0], y: [0, -10, 0], opacity: [0.35, 0.65, 0.35] }}
                      transition={{ duration: 9, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
                    />

                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.5, delay: 0.2 }}
                      className="relative rounded-2xl border border-white/10 bg-white/5 p-3 text-sm text-paper/85"
                    >
                      Hello! Tell me what you're trying to solve and I'll match you to the right Ha-Shem solution.
                    </motion.div>

                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.5, delay: 0.5 }}
                      className="relative flex justify-end"
                    >
                      <div className="max-w-[80%] rounded-2xl bg-gold-500/20 p-3 text-sm text-gold-100">
                        What compliance focused identity verification platform do you offer?
                      </div>
                    </motion.div>

                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.5, delay: 0.8 }}
                      className="relative overflow-hidden rounded-2xl border border-gold-400/25 bg-gold-500/10 p-3"
                    >
                      <motion.div
                        aria-hidden
                        className="pointer-events-none absolute inset-0 rounded-2xl"
                        animate={{
                          boxShadow: [
                            '0 0 0 0 rgba(200,154,62,0)',
                            '0 0 0 3px rgba(200,154,62,0.18)',
                            '0 0 0 0 rgba(200,154,62,0)',
                          ],
                        }}
                        transition={{ duration: 2.6, repeat: Infinity, ease: 'easeInOut' }}
                      />
                      <div className="relative flex items-center gap-2 text-sm font-medium text-gold-200">
                        <Sparkles size={16} />
                        Recommended: Spidify
                      </div>
                      <div className="relative mt-3 flex flex-wrap gap-2">
                        {heroPrompts.map((prompt, index) => (
                          <motion.button
                            key={prompt}
                            initial={{ opacity: 0, y: 6 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.4, delay: 1 + index * 0.08 }}
                            onClick={() => handlePrompt(prompt)}
                            className="rounded-full border border-white/10 bg-white/10 px-3 py-1 text-xs text-paper/85 transition hover:bg-white/20"
                          >
                            {prompt}
                          </motion.button>
                        ))}
                      </div>
                    </motion.div>

                    <div className="relative flex items-center gap-2 text-sm text-paper/60">
                      <div className="flex gap-1">
                        {[0, 1, 2].map((dot) => (
                          <motion.span
                            key={dot}
                            className="h-2 w-2 rounded-full bg-gold-400"
                            animate={{ opacity: [0.3, 1, 0.3], scale: [0.85, 1, 0.85] }}
                            transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut', delay: dot * 0.2 }}
                          />
                        ))}
                      </div>
                      {isTyping ? 'HavisIQ is thinking...' : 'Ready to assist'}
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </section>

        <section id="chat" className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
          <div className="overflow-hidden rounded-[2rem] border border-ink/10 bg-white shadow-[0_20px_70px_rgba(20,23,29,0.08)]">
            <div className="grid gap-0 lg:grid-cols-[1.05fr_0.95fr]">
              <div className="border-b border-ink/10 bg-gradient-to-br from-paper to-white p-8 lg:border-b-0 lg:border-r">
                <div className="mb-8 inline-flex items-center gap-2 rounded-full bg-gold-50 px-3 py-2 text-sm font-medium text-gold-700">
                  <MessageCircleMore size={16} />
                  AI Chat Experience
                </div>
                <h2 className="font-display text-3xl tracking-tight text-ink">A consultant that feels premium, fast, and intelligent.</h2>
                <p className="mt-4 max-w-xl text-lg leading-8 text-ink/65">
                  The conversation layer understands your business need and matches it against Ha-Shem's full
                  solution catalog — not just two products — with cited sources and a polished enterprise-grade flow.
                </p>
                <div className="mt-8 space-y-4">
                  {[
                    'Live conversational guidance',
                    'Solution-aware matching across the whole catalog',
                    'Instant ticket submission and appointment booking',
                  ].map((item) => (
                    <div key={item} className="flex items-center gap-3 rounded-2xl border border-ink/10 bg-white px-4 py-3 shadow-sm">
                      <CheckCircle2 className="text-emerald-500" size={18} />
                      <span className="text-ink/80">{item}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-ink p-6 text-paper sm:p-8">
                <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4 backdrop-blur">
                  <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                    <HavisIQMark size={40} />
                    <div>
                      <p className="font-display font-semibold">HavisIQ</p>
                      <p className="text-xs text-paper/60">AI advisor • solutions • support</p>
                    </div>
                  </div>

                  <div className="mt-4 space-y-3">
                    <div className="rounded-2xl border border-white/10 bg-white/5 p-3 text-sm text-paper/85">
                      I can help you find the right solution, understand what it does, or start a support request.
                    </div>
                    <div className="flex justify-end">
                      <div className="max-w-[85%] rounded-2xl bg-gold-500/20 p-3 text-sm text-gold-100">
                        We hire over 500 employees every year
                      </div>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {['ZivaAIRA — Talent Acquisition', 'ZivaAIRA — Hiring Automation'].map((item) => (
                        <div key={item} className="rounded-2xl border border-white/10 bg-black/20 p-3 text-sm text-paper/85">
                          {item}
                        </div>
                      ))}
                    </div>
                    <div className="rounded-2xl border border-emerald-400/20 bg-emerald-500/10 p-3 text-sm text-emerald-100">
                      Demo request started. Our team will reach out shortly.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-6 py-4 lg:px-8">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {quickActions.map((action) => {
              const Icon = action.icon;
              return (
                <motion.button
                  type="button"
                  onClick={action.onClick}
                  whileHover={{ y: -4, scale: 1.01 }}
                  key={action.title}
                  className="rounded-[1.5rem] border border-ink/10 bg-white p-6 text-left shadow-sm"
                >
                  <div className="inline-flex rounded-2xl bg-gold-50 p-3">
                    <Icon className="text-gold-600" size={20} />
                  </div>
                  <h3 className="mt-4 text-lg font-semibold text-ink">{action.title}</h3>
                  <p className="mt-2 text-sm leading-7 text-ink/65">{action.description}</p>
                </motion.button>
              );
            })}
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-6 pt-20 lg:px-8">
          <div className="rounded-[2rem] border border-ink/10 bg-white p-8 shadow-sm sm:p-10">
            <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.3em] text-gold-600">
              <Search size={16} />
              Business problem discovery
            </div>
            <h2 className="mt-2 font-display text-2xl tracking-tight text-ink sm:text-3xl">What are you trying to solve?</h2>
            <p className="mt-2 max-w-2xl text-ink/65">
              Pick the challenge closest to yours and we'll highlight the Ha-Shem solutions built for it.
            </p>
            <div className="mt-6 flex flex-wrap gap-2.5">
              {businessProblems.map((problem) => {
                const active = selectedProblem === problem.label;
                return (
                  <button
                    key={problem.label}
                    type="button"
                    onClick={() => setSelectedProblem(active ? null : problem.label)}
                    className={`rounded-full border px-4 py-2 text-sm font-medium transition ${
                      active
                        ? 'border-ink bg-ink text-paper'
                        : 'border-ink/15 bg-paper text-ink/70 hover:border-gold-400 hover:text-gold-700'
                    }`}
                  >
                    {problem.label}
                  </button>
                );
              })}
            </div>
            {activeProblem ? (
              <div className="mt-5 flex flex-wrap items-center gap-3 rounded-2xl bg-gold-50 px-4 py-3 text-sm text-gold-800">
                <Sparkles size={16} />
                <span>
                  Showing solutions for <strong>{activeProblem.label}</strong> — {matchedSolutionIds?.size ?? 0} match
                  {matchedSolutionIds?.size === 1 ? '' : 'es'} highlighted below.
                </span>
                <a
                  href="#solutions"
                  className="inline-flex items-center gap-1 rounded-full bg-ink px-3 py-1 text-xs font-semibold text-paper shadow-sm transition hover:bg-ink-soft"
                >
                  Explore
                  <ArrowRight size={12} />
                </a>
                <button
                  type="button"
                  onClick={() => setSelectedProblem(null)}
                  className="ml-auto inline-flex items-center gap-1 rounded-full bg-white px-3 py-1 text-xs font-semibold text-ink/70 shadow-sm transition hover:text-ink"
                >
                  <X size={12} />
                  Clear
                </button>
              </div>
            ) : null}

            <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-ink/10 pt-5">
              <div className="flex items-center gap-3 rounded-2xl border border-dashed border-ink/15 bg-paper px-4 py-3 text-sm text-ink/60">
                <span className="rounded-full bg-ink/5 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-ink/50">
                  Coming Soon
                </span>
                <span>
                  <strong className="text-ink/80">ZivaFarm360</strong> — farm &amp; livestock management, agri
                  supply-chain visibility.
                </span>
              </div>
              <a
                href="#custom-solution"
                className="ml-auto inline-flex items-center gap-2 rounded-full border border-ink/15 px-4 py-2 text-sm font-semibold text-ink/70 transition hover:border-gold-400 hover:text-gold-700"
              >
                Don't see your challenge? Build a custom solution
                <ArrowRight size={14} />
              </a>
            </div>
          </div>
        </section>

        <section id="solutions" className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
          <div className="mb-10 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.3em] text-gold-600">Solution catalog</p>
              <h2 className="mt-2 font-display text-3xl tracking-tight text-ink">One advisor, a growing catalog of Ha-Shem expertise</h2>
              <p className="mt-3 max-w-2xl text-ink/65">
                SPIDIFY, ZivaAIRA, and the full HAVIS-360 suite are live today, each with their own knowledge base.
                Advisory services are business areas Ha-Shem already delivers on — ask HavisIQ, or talk to a
                specialist directly.
              </p>
            </div>
            <button
              type="button"
              onClick={() => openCompareModal()}
              className="inline-flex items-center gap-2 rounded-full border border-ink/15 px-5 py-2.5 text-sm font-semibold text-ink transition hover:border-gold-400 hover:text-gold-700"
            >
              <GitCompare size={16} />
              Compare Solutions
            </button>
          </div>

          {solutionsLoading ? (
            <div className="grid gap-6 lg:grid-cols-3">
              {[0, 1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-72 animate-pulse rounded-[1.75rem] border border-ink/10 bg-paper" />
              ))}
            </div>
          ) : (
            <>
              {solutionsError ? (
                <div className="mb-8 rounded-2xl border border-gold-300 bg-gold-50 px-4 py-3 text-sm text-gold-800">
                  We couldn't reach the live solution catalog just now, so advisory services are shown below —
                  everything else still works, including chat.
                </div>
              ) : null}
              <div className="space-y-14">
                {groupedSolutions.map(({ group, items }) => (
                  <div key={group}>
                    <h3 className="font-display text-lg tracking-tight text-ink/80">{group}</h3>
                    <div className="mt-5 grid gap-6 lg:grid-cols-3">
                      {items.map((solution) => {
                        const dimmed = matchedSolutionIds !== null && !matchedSolutionIds.has(solution.id);
                        const highlighted = matchedSolutionIds !== null && matchedSolutionIds.has(solution.id);
                        return (
                          <motion.div
                            key={solution.id}
                            animate={{ opacity: dimmed ? 0.4 : 1 }}
                            transition={{ duration: 0.25 }}
                            className={`flex flex-col rounded-[1.75rem] border bg-white p-8 shadow-sm transition-colors ${
                              highlighted ? 'border-gold-400 ring-2 ring-gold-300/50' : 'border-ink/10'
                            }`}
                          >
                            <div className="flex h-28 items-center justify-center rounded-[1.25rem] bg-gradient-to-br from-paper via-gold-50 to-paper p-6">
                              <img
                                src={getProductLogo(solution.id)}
                                alt={`${solution.name} logo`}
                                className="max-h-full max-w-full object-contain"
                              />
                            </div>
                            <div className="mt-6 flex items-center justify-between gap-2">
                              <h4 className="text-xl font-semibold text-ink">{solution.name}</h4>
                              <span
                                className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${
                                  solution.status === 'live' ? 'bg-emerald-100 text-emerald-700' : 'bg-gold-100 text-gold-700'
                                }`}
                              >
                                {solution.status === 'live' ? 'Live solution' : 'Ha-Shem Advisory'}
                              </span>
                            </div>
                            <p className="mt-1 text-xs font-medium uppercase tracking-wide text-ink/40">{solution.category}</p>
                            <p className="mt-3 flex-1 text-sm leading-7 text-ink/65">{solution.description}</p>
                            {solution.highlights.length > 0 ? (
                              <ul className="mt-3 flex flex-wrap gap-1.5">
                                {solution.highlights.slice(0, 3).map((highlight) => (
                                  <li key={highlight} className="rounded-full bg-paper px-2.5 py-1 text-xs text-ink/60 ring-1 ring-ink/10">
                                    {highlight}
                                  </li>
                                ))}
                              </ul>
                            ) : null}
                            <div className="mt-6 flex flex-wrap gap-2">
                              {solution.learnMoreUrl ? (
                                <a
                                  href={solution.learnMoreUrl}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="rounded-full border border-ink/15 px-4 py-2 text-sm font-medium text-ink/80 transition hover:border-gold-400 hover:text-gold-700"
                                >
                                  Learn More
                                </a>
                              ) : (
                                <button
                                  type="button"
                                  onClick={() => openDemoModal(solution)}
                                  className="rounded-full border border-ink/15 px-4 py-2 text-sm font-medium text-ink/80 transition hover:border-gold-400 hover:text-gold-700"
                                >
                                  Learn More
                                </button>
                              )}
                              <button
                                type="button"
                                onClick={() => openCompareModal(solution.id)}
                                className="rounded-full border border-ink/15 px-4 py-2 text-sm font-medium text-ink/80 transition hover:border-gold-400 hover:text-gold-700"
                              >
                                Compare
                              </button>
                              <button
                                type="button"
                                onClick={() => openDemoModal(solution)}
                                className="rounded-full bg-ink px-4 py-2 text-sm font-medium text-paper transition hover:bg-ink-soft"
                              >
                                Request Demo
                              </button>
                            </div>
                          </motion.div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </section>

        <section id="custom-solution" className="mx-auto max-w-7xl px-6 pb-4 lg:px-8">
          <div className="relative overflow-hidden rounded-[2rem] border border-ink/10 bg-gradient-to-br from-ink to-ink-soft p-8 text-paper shadow-sm sm:p-12">
            <div className="absolute -right-16 -top-16 h-56 w-56 rounded-full bg-gold-400/10 blur-3xl" />
            <div className="relative flex flex-col items-start gap-6 sm:flex-row sm:items-center sm:justify-between">
              <div className="max-w-xl">
                <div className="inline-flex items-center gap-2 rounded-full border border-gold-400/30 bg-gold-500/15 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-gold-200">
                  <Code2 size={14} />
                  Build a custom solution
                </div>
                <h2 className="mt-4 font-display text-2xl tracking-tight sm:text-3xl">Nothing in the catalog quite fits?</h2>
                <p className="mt-3 text-paper/70">
                  Tell us about your enterprise problem and our solution architects will design something custom —
                  built on the same Ha-Shem platform standards as everything else in the catalog.
                </p>
              </div>
              <button
                type="button"
                onClick={() => openDemoModal({ id: 'custom-software', name: 'Custom Software', category: 'Advisory', description: '', status: 'advisory', highlights: [] })}
                className="inline-flex shrink-0 items-center gap-2 rounded-full bg-gold-400 px-6 py-3.5 text-sm font-semibold text-ink transition hover:-translate-y-0.5 hover:bg-gold-300"
              >
                Request Custom Software
                <Code2 size={16} />
              </button>
            </div>
          </div>
        </section>

        <section id="support-center" className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
          <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
            <div className="rounded-[2rem] border border-ink/10 bg-white p-8 shadow-sm">
              <p className="text-sm font-semibold uppercase tracking-[0.3em] text-gold-600">Support Center</p>
              <h2 className="mt-2 font-display text-3xl tracking-tight text-ink">Everything you need to get help.</h2>
              <div className="mt-8 grid gap-4">
                {supportWidgets.map((widget) => {
                  const Icon = widget.icon;
                  return (
                    <div key={widget.title} className="flex items-start gap-3 rounded-[1.25rem] border border-ink/10 bg-paper p-4">
                      <div className="rounded-2xl bg-ink p-2 text-paper">
                        <Icon size={16} />
                      </div>
                      <div>
                        <p className="font-semibold text-ink">{widget.title}</p>
                        <p className="mt-1 text-sm text-ink/65">{widget.desc}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
              <button
                type="button"
                onClick={() => openDemoModal()}
                className="mt-6 rounded-full border border-ink/15 px-5 py-2.5 text-sm font-semibold text-ink transition hover:border-gold-400 hover:text-gold-700"
              >
                Talk to an Expert
              </button>
            </div>

            <div className="rounded-[2rem] border border-ink/10 bg-gradient-to-br from-ink to-ink-soft p-8 text-paper shadow-sm">
              <AppointmentScheduler />
            </div>
          </div>
        </section>

        <section id="contact" className="mx-auto max-w-7xl px-6 pb-20 lg:px-8">
          <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
            <div className="rounded-[2rem] border border-ink/10 bg-white p-8 shadow-sm">
              <p className="text-sm font-semibold uppercase tracking-[0.3em] text-gold-600">Contact</p>
              <h2 className="mt-2 font-display text-3xl tracking-tight text-ink">Let’s find the right solution for your business</h2>
              <div className="mt-8 space-y-4 text-ink/70">
                <div className="rounded-[1.25rem] border border-ink/10 bg-paper p-4">Phone: +234 800 000 0000</div>
                <div className="rounded-[1.25rem] border border-ink/10 bg-paper p-4">Email: support@ha-shem.com</div>
                <div className="rounded-[1.25rem] border border-ink/10 bg-paper p-4">Address: Lagos, Nigeria</div>
              </div>
            </div>
            <div className="rounded-[2rem] border border-ink/10 bg-white p-8 shadow-sm">
              <p className="mb-4 text-sm text-ink/65">
                Prefer a form to a chat? Send us a message and a specialist will follow up — this uses the same
                request pipeline as the chat widget's "Request a demo".
              </p>
              <button
                type="button"
                onClick={() => openDemoModal()}
                className="w-full rounded-full bg-ink px-5 py-3 font-semibold text-paper transition hover:bg-ink-soft"
              >
                Contact Sales
              </button>
            </div>
          </div>
        </section>
      </main>

      <AnimatePresence>
        {isAssistantOpen ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            style={{ left: chatLeft, bottom: chatBottom, width: chatWidth, height: chatHeight, maxWidth: '92vw', maxHeight: '90vh' }}
            className={`fixed z-[60] flex flex-col overflow-hidden rounded-[1.75rem] border border-ink/10 bg-white shadow-[0_20px_80px_rgba(20,23,29,0.2)] ${
              isResizing ? '' : 'transition-[left,bottom,width,height] duration-150 ease-out'
            }`}
          >
            {/* Resize handles — one per edge, each keeps the opposite edge anchored. */}
            <div
              onMouseDown={handleResizeStart('left')}
              className="group absolute inset-y-0 left-0 z-[70] flex w-3 cursor-col-resize items-center justify-center touch-none"
            >
              <span className="h-12 w-1 rounded-full bg-ink/15 transition-colors group-hover:bg-gold-400/70" />
            </div>
            <div
              onMouseDown={handleResizeStart('right')}
              className="group absolute inset-y-0 right-0 z-[70] flex w-3 cursor-col-resize items-center justify-center touch-none"
            >
              <span className="h-12 w-1 rounded-full bg-ink/15 transition-colors group-hover:bg-gold-400/70" />
            </div>
            <div
              onMouseDown={handleResizeStart('top')}
              className="group absolute inset-x-0 top-0 z-[70] flex h-3 cursor-row-resize items-center justify-center touch-none"
            >
              <span className="h-1 w-12 rounded-full bg-ink/15 transition-colors group-hover:bg-gold-400/70" />
            </div>
            <div
              onMouseDown={handleResizeStart('bottom')}
              className="group absolute inset-x-0 bottom-0 z-[70] flex h-3 cursor-row-resize items-center justify-center touch-none"
            >
              <span className="h-1 w-12 rounded-full bg-ink/15 transition-colors group-hover:bg-gold-400/70" />
            </div>

            <div className="shrink-0 bg-ink px-4 py-4 text-paper">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <HavisIQMark size={40} />
                  <div>
                    <p className="font-display font-semibold">HavisIQ</p>
                    <p className="text-xs text-paper/60">Online • Ready to help</p>
                  </div>
                </div>
                <button type="button" onClick={() => setIsAssistantOpen(false)} className="rounded-full border border-white/10 bg-white/10 px-2.5 py-2 text-sm text-paper transition hover:bg-white/20">
                  ×
                </button>
              </div>
              <div className="mt-3 flex items-center justify-between gap-2">
                <div className="inline-flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-500/15 px-3 py-1 text-xs font-medium text-emerald-300">
                  <CheckCircle2 size={12} />
                  Secure & Live
                </div>
                {messages.some((m) => m.sender === 'assistant' && !m.isTyping) ? (
                  <button
                    type="button"
                    onClick={handleExportConversation}
                    className="flex items-center gap-1.5 rounded-full border border-white/15 px-3 py-1 text-xs font-medium text-paper/80 transition hover:bg-white/10 hover:text-paper"
                    aria-label="Export conversation as Markdown"
                  >
                    <Download size={12} />
                    Export
                  </button>
                ) : null}
              </div>
            </div>

            <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto bg-paper p-4">
              <div className="space-y-3">
                {messages.map((message) => (
                  <div key={message.id} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div
                      className={`rounded-2xl px-3 py-2 text-sm leading-7 ${
                        message.sender === 'user'
                          ? 'max-w-[85%] bg-ink text-paper'
                          : 'max-w-[95%] bg-white text-ink/85 shadow-sm ring-1 ring-ink/10'
                      }`}
                    >
                      {message.sender === 'assistant' ? (
                        message.isTyping ? (
                          renderFormattedContent(message.content)
                        ) : (
                          <MessageContent content={message.content} solutions={solutions} />
                        )
                      ) : (
                        message.content
                      )}
                      {message.isTyping ? <span className="ml-1 animate-pulse">█</span> : null}
                      {message.sender === 'assistant' && !message.isTyping && message.sources && message.sources.length > 0 && isSourceRequest(message.question) ? (
                        <SourceChips sources={message.sources} />
                      ) : null}
                      {message.sender === 'assistant' && !message.isTyping && message.question ? (
                        <div className="flex flex-wrap items-center gap-1.5">
                          <MessageActions
                            question={message.question}
                            answer={message.content}
                            sessionId={getSessionId()}
                            onRegenerate={() => handleRegenerate(message)}
                          />
                          {user && recommendedProductsFor(message).length > 0 ? (
                            <button
                              type="button"
                              onClick={() => handleSaveRecommendation(message)}
                              disabled={message.savedRecommendation}
                              className={`mt-2 flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                                message.savedRecommendation
                                  ? 'cursor-default border-emerald-300 bg-emerald-50 text-emerald-700'
                                  : 'border-ink/10 text-ink/60 hover:border-gold-400 hover:text-gold-700'
                              }`}
                            >
                              <Star size={12} className={message.savedRecommendation ? 'fill-current' : ''} />
                              {message.savedRecommendation ? 'Saved' : 'Save Recommendation'}
                            </button>
                          ) : null}
                        </div>
                      ) : null}
                    </div>
                  </div>
                ))}
                {isTyping && !messages.some((m) => m.sender === 'assistant' && m.isTyping && m.content) ? (
                  <div className="flex justify-start">
                    <div className="flex items-center gap-1.5 rounded-2xl bg-white px-4 py-3 shadow-sm ring-1 ring-ink/10">
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink/40 [animation-delay:-0.3s]" />
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink/40 [animation-delay:-0.15s]" />
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink/40" />
                    </div>
                  </div>
                ) : null}
              </div>
            </div>

            <div className="shrink-0 border-t border-ink/10 bg-white p-3">
              {isTyping ? (
                <div className="mb-3 flex justify-center">
                  <button
                    type="button"
                    onClick={handleStopGenerating}
                    className="flex items-center gap-1.5 rounded-full border border-ink/15 bg-white px-3.5 py-1.5 text-xs font-semibold text-ink/70 shadow-sm transition hover:border-ink/30 hover:text-ink"
                  >
                    <Square size={11} fill="currentColor" />
                    Stop generating
                  </button>
                </div>
              ) : messages.every((message) => message.sender !== 'user') ? (
                // Quick-start row — only before the first user message, so
                // it doesn't keep crowding the panel on every later turn.
                <div className="mb-3 flex flex-wrap gap-2">
                  {suggestedPrompts.map((prompt) => (
                    <button key={prompt} type="button" onClick={() => handlePrompt(prompt)} className="rounded-full border border-ink/10 bg-paper px-3 py-1.5 text-xs font-medium text-ink/70 transition hover:border-gold-400 hover:text-gold-700">
                      {prompt}
                    </button>
                  ))}
                </div>
              ) : null}
              <form onSubmit={handleSubmit} className="flex items-center gap-2 rounded-full border border-ink/10 bg-paper px-3 py-2">
                <input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask HavisIQ..." className="flex-1 bg-transparent text-sm outline-none" />
                <button
                  type={isTyping ? 'button' : 'submit'}
                  onClick={isTyping ? handleStopGenerating : undefined}
                  aria-label={isTyping ? 'Stop generating' : 'Send message'}
                  className="rounded-full bg-ink p-2 text-paper transition hover:bg-ink-soft disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isTyping ? <Square size={14} fill="currentColor" /> : <SendHorizonal size={16} />}
                </button>
              </form>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>

      <motion.button
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setIsAssistantOpen(true)}
        className="fixed bottom-4 left-4 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-ink text-paper shadow-[0_16px_45px_rgba(20,23,29,0.35)]"
      >
        <HavisIQMark size={40} />
      </motion.button>

      <footer className="border-t border-ink/10 bg-white/80 px-6 py-8 text-sm text-ink/55 lg:px-8">
        <div className="mx-auto flex max-w-7xl flex-col justify-between gap-3 sm:flex-row">
          <p>© 2026 Ha-Shem Limited. HavisIQ is the AI solutions advisor for the Ha-Shem ecosystem.</p>
          <div className="flex gap-4">
            <a href="#" className="hover:text-ink">Privacy</a>
            <a href="#" className="hover:text-ink">Terms</a>
            <a href="#" className="hover:text-ink">Contact</a>
          </div>
        </div>
      </footer>

      <DemoRequestModal
        isOpen={demoModal.open}
        onClose={closeDemoModal}
        product={demoModal.solution?.id}
        productLabel={demoModal.solution?.name}
      />
      <CompareSolutionsModal
        isOpen={isCompareOpen}
        onClose={() => {
          setIsCompareOpen(false);
          setCompareInitialId(undefined);
        }}
        solutions={solutions}
        initialSelectedId={compareInitialId}
        onRequestDemo={(solution) => {
          setIsCompareOpen(false);
          openDemoModal(solution);
        }}
      />
    </div>
  );
}

export default App;
