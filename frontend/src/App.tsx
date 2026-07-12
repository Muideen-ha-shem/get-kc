import { AnimatePresence, motion } from 'framer-motion';
import { FormEvent, useEffect, useRef, useState } from 'react';
import {
  Bot,
  CalendarDays,
  CheckCircle2,
  CircleHelp,
  Clock3,
  Headphones,
  MessageCircleMore,
  MonitorSmartphone,
  SendHorizonal,
  Sparkles,
  Ticket,
  Zap,
} from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

type Message = {
  id: number;
  sender: 'user' | 'assistant';
  content: string;
  isTyping?: boolean;
};

const navigation = ['Home', 'Products', 'Solutions', 'Support Center', 'Contact'];

const quickActions = [
  {
    title: 'Products',
    description: 'Browse our AI-powered products',
    icon: MonitorSmartphone,
    accent: 'from-cyan-500/20 to-sky-500/10',
  },
  {
    title: 'Solutions',
    description: 'Discover business-ready solutions',
    icon: Sparkles,
    accent: 'from-fuchsia-500/20 to-violet-500/10',
  },
  {
    title: 'Customer Support',
    description: 'Create a secure support ticket',
    icon: Headphones,
    accent: 'from-emerald-500/20 to-lime-500/10',
  },
  {
    title: 'Schedule Meeting',
    description: 'Book a consultation with our team',
    icon: CalendarDays,
    accent: 'from-indigo-500/20 to-blue-500/10',
  },
];

const products = [
  {
    name: 'AI Support Copilot',
    description: 'Secure assistance for customer operations and knowledge answers.',
  },
  {
    name: 'Enterprise Automation',
    description: 'Workflow automations that speed up support and service delivery.',
  },
  {
    name: 'Cloud Advisory',
    description: 'Modern cloud strategy and implementation services for growth teams.',
  },
];

const solutions = [
  'AI Solutions',
  'Cloud Services',
  'Enterprise Software',
  'Business Automation',
  'Managed Services',
];

const supportWidgets = [
  { title: 'Submit Ticket', desc: 'Create a new case in minutes', icon: Ticket },
  { title: 'Track Ticket', desc: 'Follow progress in real time', icon: CircleHelp },
  { title: 'Knowledge Base', desc: 'Browse answers and documentation', icon: Sparkles },
  { title: 'Contact Support', desc: 'Speak to a specialist instantly', icon: Headphones },
];

const appointmentSlots = ['09:00', '10:30', '13:00', '15:30'];

const suggestedPrompts = [
  'Tell me about Ha-Shem Limited',
  'Explore Products',
  'Explore Solutions',
  'Submit a Support Ticket',
  'Book Appointment',
];

function App() {
  const [isAssistantOpen, setIsAssistantOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      sender: 'assistant',
      content: 'Hello! I can help you discover products, explore solutions, and guide you to support.',
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

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

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsAssistantOpen(true);
    setIsTyping(true);
    setMessages((prev) => [...prev, { id: assistantMessageId, sender: 'assistant', content: '', isTyping: true }]);

    try {
      const response = await fetch(`${API_BASE_URL || 'http://127.0.0.1:8000'}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: trimmed }),
      });

      const data = await response.json();
      const answer = data.answer || 'I could not generate a response right now.';

      setMessages((prev) =>
        prev.map((message) => (message.id === assistantMessageId ? { ...message, content: answer, isTyping: false } : message))
      );
    } catch (error) {
      setMessages((prev) =>
        prev.map((message) =>
          message.id === assistantMessageId
            ? { ...message, content: 'I’m sorry, I’m having trouble reaching the assistant right now.', isTyping: false }
            : message
        )
      );
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4 lg:px-8">
          <div className="flex items-center gap-3">
            
            {/* To replace the Bot Icon with ha-shem logo in frontend/public/logo */}
            <img src="/logo/Ha-Shem-Logo-dark.png" alt="Ha-Shem Logo" className="h-10 w-10 rounded-full" />
            

            <div>
              <p className="text-lg font-semibold tracking-tight">Ha-Shem Limited</p>
              <p className="text-xs uppercase tracking-[0.32em] text-slate-500">AI Support Platform</p>
            </div>
          </div>

          <nav className="hidden items-center gap-8 text-sm font-medium text-slate-600 lg:flex">
            {navigation.map((item) => (
              <a key={item} href={`#${item.toLowerCase().replace(/ /g, '-')}`} className="transition hover:text-[#0A2540]">
                {item}
              </a>
            ))}
          </nav>

          <a href="#contact" className="rounded-full bg-[#0A2540] px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-slate-200 transition hover:-translate-y-0.5 hover:bg-[#112f4f]">
            Request a demo
          </a>
        </div>
      </header>

      <main>
        <section className="relative overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(6,182,212,0.14),_transparent_40%),linear-gradient(135deg,_#f8fbff_0%,_#f8fafc_100%)]">
          <div className="mx-auto grid max-w-7xl gap-12 px-6 py-20 lg:grid-cols-[1.05fr_0.95fr] lg:px-8 lg:py-28">
            <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="max-w-2xl">
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-cyan-200 bg-cyan-50 px-4 py-2 text-sm font-medium text-cyan-700">
                <Zap size={16} />
                Premium AI Customer Experience
              </div>
              <h1 className="text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl lg:text-6xl">
                Customer Support Reimagined with AI
              </h1>
              <p className="mt-6 text-lg leading-8 text-slate-600">
                Get instant answers, discover products and solutions, submit support tickets, book appointments, and connect with Ha-Shem Limited in one intelligent platform.
              </p>
              <div className="mt-8 flex flex-wrap gap-4">
                <a href="#products" className="rounded-full border border-slate-300 bg-white px-6 py-3.5 font-semibold text-slate-700 transition hover:-translate-y-0.5 hover:border-cyan-300 hover:text-[#0A2540]">
                  Explore Products
                </a>
              </div>
              <div className="mt-10 flex flex-wrap gap-4 text-sm text-slate-600">
                {['Instant answers', 'Tickets', 'Appointments', 'Secure support'].map((item) => (
                  <div key={item} className="flex items-center gap-2 rounded-full bg-white/80 px-3 py-2 shadow-sm ring-1 ring-slate-200">
                    <CheckCircle2 size={16} className="text-emerald-500" />
                    {item}
                  </div>
                ))}
              </div>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.1 }} className="relative">
              <div className="absolute inset-0 rounded-[2rem] bg-gradient-to-br from-cyan-400/20 via-transparent to-fuchsia-400/20 blur-3xl" />
              <div className="relative overflow-hidden rounded-[2rem] border border-slate-200 bg-white/90 p-4 shadow-[0_25px_80px_rgba(15,23,42,0.12)] backdrop-blur">
                <div className="rounded-[1.5rem] border border-slate-200 bg-[#0A2540] p-4 text-white">
                  <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/10 px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-cyan-400/20">
                        <Bot size={18} className="text-cyan-300" />
                      </div>
                      <div>
                        <p className="font-semibold">Ha-Shem Assistant</p>
                        <p className="text-xs text-slate-300">Online • Ready to help</p>
                      </div>
                    </div>
                    <div className="rounded-full border border-emerald-400/30 bg-emerald-500/15 px-3 py-1 text-xs font-medium text-emerald-300">
                      Secure & Live
                    </div>
                  </div>

                  <div className="mt-4 space-y-3 rounded-2xl border border-white/10 bg-slate-950/30 p-4">
                    <div className="rounded-2xl border border-white/10 bg-white/10 p-3 text-sm text-slate-200">
                      Hello! I can help you discover products, explore solutions, and guide you to support.
                    </div>
                    <div className="flex justify-end">
                      <div className="max-w-[80%] rounded-2xl bg-cyan-500/20 p-3 text-sm text-cyan-100">
                        Tell me about Ha-Shem Limited
                      </div>
                    </div>
                    <div className="rounded-2xl border border-cyan-400/20 bg-gradient-to-r from-cyan-500/10 to-fuchsia-500/10 p-3">
                      <div className="flex items-center gap-2 text-sm font-medium text-cyan-200">
                        <Sparkles size={16} />
                        Suggested actions
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {suggestedPrompts.map((prompt) => (
                          <button key={prompt} onClick={() => handlePrompt(prompt)} className="rounded-full border border-white/10 bg-white/10 px-3 py-1 text-xs text-slate-200 transition hover:bg-white/20">
                            {prompt}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-slate-300">
                      <div className="flex gap-1">
                        <span className="h-2 w-2 rounded-full bg-cyan-400" />
                        <span className="h-2 w-2 rounded-full bg-cyan-400/70" />
                        <span className="h-2 w-2 rounded-full bg-cyan-400/40" />
                      </div>
                      {isTyping ? 'Ha-Shem AI is thinking...' : 'Ready to assist'}
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </section>

        <section id="chat" className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
          <div className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-[0_20px_70px_rgba(15,23,42,0.08)]">
            <div className="grid gap-0 lg:grid-cols-[1.05fr_0.95fr]">
              <div className="border-b border-slate-200 bg-gradient-to-br from-slate-50 to-white p-8 lg:border-b-0 lg:border-r">
                <div className="mb-8 inline-flex items-center gap-2 rounded-full bg-cyan-50 px-3 py-2 text-sm font-medium text-cyan-700">
                  <MessageCircleMore size={16} />
                  AI Chat Experience
                </div>
                <h2 className="text-3xl font-semibold tracking-tight text-slate-900">A support experience that feels premium, fast, and intelligent.</h2>
                <p className="mt-4 max-w-xl text-lg leading-8 text-slate-600">
                  The conversation layer is designed to feel productive and personal, with rich cards, proactive suggestions, and a polished enterprise-grade flow.
                </p>
                <div className="mt-8 space-y-4">
                  {[
                    'Live conversational guidance',
                    'Context-rich product and solution discovery',
                    'Instant ticket submission and appointment booking',
                  ].map((item) => (
                    <div key={item} className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
                      <CheckCircle2 className="text-emerald-500" size={18} />
                      <span className="text-slate-700">{item}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-[#0A2540] p-6 text-white sm:p-8">
                <div className="rounded-[1.5rem] border border-white/10 bg-white/10 p-4 backdrop-blur">
                  <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-slate-950/30 px-4 py-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-cyan-400/20">
                      <Bot size={18} className="text-cyan-300" />
                    </div>
                    <div>
                      <p className="font-semibold">Ha-Shem Assistant</p>
                      <p className="text-xs text-slate-300">AI support • solutions • tickets</p>
                    </div>
                  </div>

                  <div className="mt-4 space-y-3">
                    <div className="rounded-2xl border border-white/10 bg-white/10 p-3 text-sm text-slate-200">
                      I can help you find the right product, understand a solution, or start a support request.
                    </div>
                    <div className="flex justify-end">
                      <div className="max-w-[85%] rounded-2xl bg-cyan-500/20 p-3 text-sm text-cyan-100">
                        Explore Solutions for my business
                      </div>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {solutions.slice(0, 2).map((solution) => (
                        <div key={solution} className="rounded-2xl border border-white/10 bg-slate-950/30 p-3 text-sm text-slate-200">
                          {solution}
                        </div>
                      ))}
                    </div>
                    <div className="rounded-2xl border border-emerald-400/20 bg-emerald-500/10 p-3 text-sm text-emerald-100">
                      Support ticket created. Our team will reach out shortly.
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
                <motion.div whileHover={{ y: -4, scale: 1.01 }} key={action.title} className="rounded-[1.5rem] border border-slate-200 bg-white p-6 shadow-sm">
                  <div className={`inline-flex rounded-2xl bg-gradient-to-br ${action.accent} p-3`}>
                    <Icon className="text-[#0A2540]" size={20} />
                  </div>
                  <h3 className="mt-4 text-lg font-semibold text-slate-900">{action.title}</h3>
                  <p className="mt-2 text-sm leading-7 text-slate-600">{action.description}</p>
                </motion.div>
              );
            })}
          </div>
        </section>

        <section id="products" className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
          <div className="mb-10 flex items-end justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.3em] text-cyan-700">Products</p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Enterprise-ready solutions for modern support teams</h2>
            </div>
          </div>
          <div className="grid gap-6 lg:grid-cols-3">
            {products.map((product) => (
              <div key={product.name} className="rounded-[1.75rem] border border-slate-200 bg-white p-8 shadow-sm">
                <div className="h-32 rounded-[1.25rem] bg-gradient-to-br from-slate-100 via-cyan-50 to-slate-200" />
                <h3 className="mt-6 text-xl font-semibold text-slate-900">{product.name}</h3>
                <p className="mt-3 text-sm leading-7 text-slate-600">{product.description}</p>
                <button className="mt-6 rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-cyan-300 hover:text-[#0A2540]">
                  Learn More
                </button>
              </div>
            ))}
          </div>
        </section>

        <section id="solutions" className="mx-auto max-w-7xl px-6 py-4 lg:px-8">
          <div className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-cyan-700">Solutions</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Built for growth, resilience, and smarter service delivery</h2>
            <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
              {solutions.map((solution) => (
                <div key={solution} className="rounded-[1.25rem] border border-slate-200 bg-slate-50 p-5 text-sm font-medium text-slate-700">
                  {solution}
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="support-center" className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
          <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
            <div className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-sm">
              <p className="text-sm font-semibold uppercase tracking-[0.3em] text-cyan-700">Support Center</p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Everything your customers need to get help fast</h2>
              <div className="mt-8 grid gap-4">
                {supportWidgets.map((widget) => {
                  const Icon = widget.icon;
                  return (
                    <div key={widget.title} className="flex items-start gap-3 rounded-[1.25rem] border border-slate-200 bg-slate-50 p-4">
                      <div className="rounded-2xl bg-[#0A2540] p-2 text-white">
                        <Icon size={16} />
                      </div>
                      <div>
                        <p className="font-semibold text-slate-900">{widget.title}</p>
                        <p className="mt-1 text-sm text-slate-600">{widget.desc}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="rounded-[2rem] border border-slate-200 bg-gradient-to-br from-[#0A2540] to-[#1E40AF] p-8 text-white shadow-sm">
              <div className="rounded-[1.5rem] border border-white/10 bg-white/10 p-6 backdrop-blur">
                <p className="text-sm font-semibold uppercase tracking-[0.3em] text-cyan-300">Appointment Scheduling</p>
                <h3 className="mt-3 text-2xl font-semibold">Book a strategy session</h3>
                <div className="mt-6 grid gap-4 md:grid-cols-[1.1fr_0.9fr]">
                  <div className="rounded-[1.25rem] border border-white/10 bg-slate-950/20 p-4">
                    <div className="flex items-center gap-2 text-sm font-medium text-cyan-100">
                      <CalendarDays size={16} />
                      Available dates
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {['Mon', 'Tue', 'Wed', 'Thu'].map((day) => (
                        <div key={day} className="rounded-full border border-white/10 px-3 py-2 text-sm text-slate-200">
                          {day}
                        </div>
                      ))}
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {appointmentSlots.map((slot) => (
                        <div key={slot} className="rounded-full bg-cyan-400/15 px-3 py-2 text-sm text-cyan-100">
                          {slot}
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="rounded-[1.25rem] border border-white/10 bg-white/10 p-4">
                    <div className="flex items-center gap-2 text-sm font-medium text-cyan-100">
                      <Clock3 size={16} />
                      Confirmation
                    </div>
                    <div className="mt-4 rounded-2xl bg-white p-4 text-slate-900">
                      <p className="font-semibold">Thursday • 13:00</p>
                      <p className="mt-2 text-sm text-slate-600">A senior specialist will confirm your slot.</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="contact" className="mx-auto max-w-7xl px-6 pb-20 lg:px-8">
          <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
            <div className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-sm">
              <p className="text-sm font-semibold uppercase tracking-[0.3em] text-cyan-700">Contact</p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Let’s build better support experiences together</h2>
              <div className="mt-8 space-y-4 text-slate-600">
                <div className="rounded-[1.25rem] border border-slate-200 bg-slate-50 p-4">Phone: +234 800 000 0000</div>
                <div className="rounded-[1.25rem] border border-slate-200 bg-slate-50 p-4">Email: support@ha-shem.com</div>
                <div className="rounded-[1.25rem] border border-slate-200 bg-slate-50 p-4">Address: Lagos, Nigeria</div>
              </div>
            </div>
            <div className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-sm">
              <div className="grid gap-4">
                <input className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 outline-none ring-0" placeholder="Your name" />
                <input className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 outline-none ring-0" placeholder="Work email" />
                <textarea className="min-h-32 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 outline-none ring-0" placeholder="How can we help?" />
                <button className="rounded-full bg-[#0A2540] px-5 py-3 font-semibold text-white transition hover:bg-[#112f4f]">Send Message</button>
              </div>
            </div>
          </div>
        </section>
      </main>

      <AnimatePresence>
        {isAssistantOpen ? (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }} className="fixed bottom-4 left-4 z-[60] w-[min(92vw,420px)] overflow-hidden rounded-[1.75rem] border border-slate-200 bg-white shadow-[0_20px_80px_rgba(15,23,42,0.2)]">
            <div className="bg-[#0A2540] px-4 py-4 text-white">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-cyan-400/20">
                    <Bot size={18} className="text-cyan-300" />
                  </div>
                  <div>
                    <p className="font-semibold">Ha-Shem Assistant</p>
                    <p className="text-xs text-slate-300">Online • Ready to help</p>
                  </div>
                </div>
                <button type="button" onClick={() => setIsAssistantOpen(false)} className="rounded-full border border-white/10 bg-white/10 px-2.5 py-2 text-sm text-white transition hover:bg-white/20">
                  ×
                </button>
              </div>
              <div className="mt-3 inline-flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-500/15 px-3 py-1 text-xs font-medium text-emerald-300">
                <CheckCircle2 size={12} />
                Secure & Live
              </div>
            </div>

            <div ref={scrollRef} className="max-h-[420px] overflow-y-auto bg-slate-50 p-4">
              <div className="space-y-3">
                {messages.map((message) => (
                  <div key={message.id} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-7 ${message.sender === 'user' ? 'bg-[#0A2540] text-white' : 'bg-white text-slate-700 shadow-sm ring-1 ring-slate-200'}`}>
                      {message.content}
                      {message.isTyping ? <span className="ml-1 animate-pulse">█</span> : null}
                    </div>
                  </div>
                ))}
                {isTyping ? (
                  <div className="flex justify-start">
                    <div className="rounded-2xl bg-white px-3 py-2 text-sm text-slate-600 shadow-sm ring-1 ring-slate-200">
                      Ha-Shem AI is thinking...
                    </div>
                  </div>
                ) : null}
              </div>
            </div>

            <div className="border-t border-slate-200 bg-white p-3">
              <div className="mb-3 flex flex-wrap gap-2">
                {suggestedPrompts.map((prompt) => (
                  <button key={prompt} type="button" onClick={() => handlePrompt(prompt)} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-cyan-300 hover:text-[#0A2540]">
                    {prompt}
                  </button>
                ))}
              </div>
              <form onSubmit={handleSubmit} className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-2">
                <input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask Ha-Shem Assistant..." className="flex-1 bg-transparent text-sm outline-none" />
                <button type="submit" disabled={isTyping} className="rounded-full bg-[#0A2540] p-2 text-white transition hover:bg-[#112f4f] disabled:cursor-not-allowed disabled:opacity-60">
                  <SendHorizonal size={16} />
                </button>
              </form>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>

      <motion.button initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} onClick={() => setIsAssistantOpen(true)} className="fixed bottom-4 left-4 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-[#0A2540] via-[#1E40AF] to-[#06B6D4] text-white shadow-[0_16px_45px_rgba(6,182,212,0.3)]">
        <Bot size={24} />
      </motion.button>

      <footer className="border-t border-slate-200 bg-white/80 px-6 py-8 text-sm text-slate-500 lg:px-8">
        <div className="mx-auto flex max-w-7xl flex-col justify-between gap-3 sm:flex-row">
          <p>© 2026 Ha-Shem Limited. Premium AI support experience.</p>
          <div className="flex gap-4">
            <a href="#" className="hover:text-[#0A2540]">Privacy</a>
            <a href="#" className="hover:text-[#0A2540]">Terms</a>
            <a href="#" className="hover:text-[#0A2540]">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
