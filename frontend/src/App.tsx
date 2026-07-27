import { AnimatePresence, motion } from 'framer-motion';
import { FormEvent, MouseEvent as ReactMouseEvent, useEffect, useRef, useState } from 'react';
import {
  CalendarDays,
  CheckCircle2,
  CircleHelp,
  Clock3,
  GitCompare,
  Headphones,
  MessageCircleMore,
  Sparkles,
  Square,
  Ticket,
  SendHorizonal,
  Zap,
} from 'lucide-react';
import { HavisIQMark } from './components/HavisIQMark';
import { DemoRequestModal } from './components/DemoRequestModal';
import { CompareSolutionsModal } from './components/CompareSolutionsModal';
import { MessageContent } from './components/message/MessageContent';
import { SourceChips } from './components/message/SourceChips';
import { solutions, type Solution } from './solutions';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

type Message = {
  id: number;
  sender: 'user' | 'assistant';
  content: string;
  isTyping?: boolean;
  sources?: string[];
};

const navigation = ['Home', 'Solutions', 'Support Center', 'Contact'];

const supportWidgets = [
  { title: 'Submit Ticket', desc: 'Create a new case in minutes', icon: Ticket },
  { title: 'Track Ticket', desc: 'Follow progress in real time', icon: CircleHelp },
  { title: 'Knowledge Base', desc: 'Browse answers and documentation', icon: Sparkles },
  { title: 'Contact Support', desc: 'Speak to a specialist instantly', icon: Headphones },
];

const appointmentSlots = ['09:00', '10:30', '13:00', '15:30'];

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

const suggestedPrompts = [
  'What does SPIDIFY do?',
  'Tell me about ZivaAIRA',
  'Do you offer cybersecurity services?',
  'Help with cloud migration',
];

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
  const [isAssistantOpen, setIsAssistantOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      sender: 'assistant',
      content:
        "Hello! I'm HavisIQ, the AI advisor for Ha-Shem's solutions. Tell me what you're trying to solve — identity verification, recruitment, cybersecurity, cloud, and more — and I'll point you the right way.",
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

  const openDemoModal = (solution?: Solution) => setDemoModal({ open: true, solution });
  const closeDemoModal = () => setDemoModal((prev) => ({ ...prev, open: false }));

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

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isTyping) return;

    const userMessage: Message = { id: Date.now(), sender: 'user', content: trimmed };
    const assistantMessageId = Date.now() + 1;
    activeAssistantIdRef.current = assistantMessageId;

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsAssistantOpen(true);
    setIsTyping(true);
    setMessages((prev) => [...prev, { id: assistantMessageId, sender: 'assistant', content: '', isTyping: true }]);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const response = await fetch(`${API_BASE_URL || 'http://localhost:8000'}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: trimmed }),
        signal: controller.signal,
      });

      const data = await response.json();
      const answer = data.answer || 'I could not generate a response right now.';
      const sources = Array.isArray(data.sources) ? data.sources : [];

      let streamedIndex = 0;
      const streamSpeed = 18;

      const streamInterval = window.setInterval(() => {
        streamedIndex += 1;
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
            prev.map((message) => (message.id === assistantMessageId ? { ...message, isTyping: false, sources } : message))
          );
          setIsTyping(false);
        }
      }, streamSpeed);
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

          <button
            type="button"
            onClick={() => openDemoModal()}
            className="rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-paper shadow-lg shadow-ink/10 transition hover:-translate-y-0.5 hover:bg-ink-soft"
          >
            Request a demo
          </button>
        </div>
      </header>

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
                Describe a business need — identity verification, recruitment, cybersecurity, cloud, software
                development, managed services, or training — and HavisIQ matches it to the right Ha-Shem solution,
                with sources, in seconds. SPIDIFY and ZivaAIRA are the first two in a growing catalog.
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
                        What cybersecurity support do you offer?
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
                        Recommended: Cybersecurity
                      </div>
                      <div className="relative mt-3 flex flex-wrap gap-2">
                        {suggestedPrompts.map((prompt, index) => (
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

        <section id="solutions" className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
          <div className="mb-10 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.3em] text-gold-600">Solution catalog</p>
              <h2 className="mt-2 font-display text-3xl tracking-tight text-ink">One advisor, a growing catalog of Ha-Shem expertise</h2>
              <p className="mt-3 max-w-2xl text-ink/65">
                SPIDIFY and ZivaAIRA are live today, each with their own knowledge base. The rest are business areas
                Ha-Shem already delivers on — ask HavisIQ, or talk to a specialist directly.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setIsCompareOpen(true)}
              className="inline-flex items-center gap-2 rounded-full border border-ink/15 px-5 py-2.5 text-sm font-semibold text-ink transition hover:border-gold-400 hover:text-gold-700"
            >
              <GitCompare size={16} />
              Compare Solutions
            </button>
          </div>
          <div className="grid gap-6 lg:grid-cols-3">
            {solutions.map((solution) => (
              <div key={solution.id} className="flex flex-col rounded-[1.75rem] border border-ink/10 bg-white p-8 shadow-sm">
                <div className="flex h-32 items-center justify-center rounded-[1.25rem] bg-gradient-to-br from-paper via-gold-50 to-paper">
                  <span className="font-display text-2xl text-ink/70">{solution.name}</span>
                </div>
                <div className="mt-6 flex items-center justify-between gap-2">
                  <h3 className="text-xl font-semibold text-ink">{solution.name}</h3>
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
                    onClick={() => openDemoModal(solution)}
                    className="rounded-full bg-ink px-4 py-2 text-sm font-medium text-paper transition hover:bg-ink-soft"
                  >
                    Request Demo
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section id="support-center" className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
          <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
            <div className="rounded-[2rem] border border-ink/10 bg-white p-8 shadow-sm">
              <p className="text-sm font-semibold uppercase tracking-[0.3em] text-gold-600">Support Center</p>
              <h2 className="mt-2 font-display text-3xl tracking-tight text-ink">Everything your customers need to get help fast</h2>
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
              <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
                <p className="text-sm font-semibold uppercase tracking-[0.3em] text-gold-300">Appointment Scheduling</p>
                <h3 className="mt-3 font-display text-2xl">Book a strategy session</h3>
                <div className="mt-6 grid gap-4 md:grid-cols-[1.1fr_0.9fr]">
                  <div className="rounded-[1.25rem] border border-white/10 bg-black/20 p-4">
                    <div className="flex items-center gap-2 text-sm font-medium text-gold-100">
                      <CalendarDays size={16} />
                      Available dates
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {['Mon', 'Tue', 'Wed', 'Thu'].map((day) => (
                        <div key={day} className="rounded-full border border-white/10 px-3 py-2 text-sm text-paper/80">
                          {day}
                        </div>
                      ))}
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {appointmentSlots.map((slot) => (
                        <div key={slot} className="rounded-full bg-gold-400/15 px-3 py-2 text-sm text-gold-100">
                          {slot}
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="rounded-[1.25rem] border border-white/10 bg-white/5 p-4">
                    <div className="flex items-center gap-2 text-sm font-medium text-gold-100">
                      <Clock3 size={16} />
                      Confirmation
                    </div>
                    <div className="mt-4 rounded-2xl bg-white p-4 text-ink">
                      <p className="font-semibold">Thursday • 13:00</p>
                      <p className="mt-2 text-sm text-ink/65">A senior specialist will confirm your slot.</p>
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => openDemoModal()}
                  className="mt-6 w-full rounded-full bg-gold-400 px-5 py-3 text-sm font-semibold text-ink transition hover:bg-gold-300"
                >
                  Contact Sales
                </button>
              </div>
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
              <div className="mt-3 inline-flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-500/15 px-3 py-1 text-xs font-medium text-emerald-300">
                <CheckCircle2 size={12} />
                Secure & Live
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
                          <MessageContent content={message.content} />
                        )
                      ) : (
                        message.content
                      )}
                      {message.isTyping ? <span className="ml-1 animate-pulse">█</span> : null}
                      {message.sender === 'assistant' && !message.isTyping && message.sources && message.sources.length > 0 ? (
                        <SourceChips sources={message.sources} />
                      ) : null}
                    </div>
                  </div>
                ))}
                {isTyping ? (
                  <div className="flex justify-start">
                    <div className="rounded-2xl bg-white px-3 py-2 text-sm text-ink/70 shadow-sm ring-1 ring-ink/10">
                      HavisIQ is thinking...
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
              ) : (
                <div className="mb-3 flex flex-wrap gap-2">
                  {suggestedPrompts.map((prompt) => (
                    <button key={prompt} type="button" onClick={() => handlePrompt(prompt)} className="rounded-full border border-ink/10 bg-paper px-3 py-1.5 text-xs font-medium text-ink/70 transition hover:border-gold-400 hover:text-gold-700">
                      {prompt}
                    </button>
                  ))}
                </div>
              )}
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
        onClose={() => setIsCompareOpen(false)}
        solutions={solutions}
        onRequestDemo={(solution) => {
          setIsCompareOpen(false);
          openDemoModal(solution);
        }}
      />
    </div>
  );
}

export default App;
