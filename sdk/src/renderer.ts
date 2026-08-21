import type { ChatMessage, HavisIQContext, Position, QuickAction, Theme } from './types';

const HOST_ID = 'havisiq-sdk-root';

// ---------------------------------------------------------------------
// Small inline stroke icons (no <title>/<text> children, so they never
// leak into an element's textContent and break exact-match assertions
// like chip[0].textContent === label). Defined before anything that
// references them — a module-level const referencing another const
// declared later in the file throws (temporal dead zone), not just
// renders blank.
// ---------------------------------------------------------------------
function icon(paths: string, size = 16): string {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" aria-hidden="true">${paths}</svg>`;
}
const S = 'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"';
const ICON_SPARK = icon(`<path d="M12 4 L13.3 9 L18 10.5 L13.3 12 L12 17 L10.7 12 L6 10.5 L10.7 9 Z" ${S}/>`, 15);

/** The real HavisIQ brand mark — copied verbatim from
 * `frontend/src/components/HavisIQMark.tsx` (glyph, gradient chip, inset
 * gloss/shadow, gold node) so the SDK's launcher and the rest of the
 * product show the same fixed-identity icon, not a generic AI sparkle.
 * Inline styles on purpose, same reasoning as the source component: this
 * must render correctly with zero build-time CSS, since it ships inside
 * a bundled string, not a Tailwind-processed class. */
function havisiqMark(size: number): string {
  const glyphSize = size * 0.56;
  return `<div style="width:${size}px;height:${size}px;border-radius:22%;display:flex;align-items:center;justify-content:center;flex-shrink:0;background:linear-gradient(150deg,#232833 0%,#171B22 48%,#0F1216 100%);box-shadow:inset 0 1px 0 rgba(255,255,255,0.09), inset 0 -10px 16px rgba(0,0,0,0.4), 0 6px 16px rgba(15,17,22,0.35), 0 0 0 1px rgba(200,154,62,0.14);">
    <svg viewBox="0 0 48 48" width="${glyphSize}" height="${glyphSize}" fill="none" aria-hidden="true">
      <path d="M14 12 L14 36 M34 12 L34 36" stroke="#ECEEF2" stroke-width="4.5" stroke-linecap="round"/>
      <path d="M14 24 L20 24 M28 24 L34 24" stroke="#ECEEF2" stroke-width="4.5" stroke-linecap="round"/>
      <circle cx="24" cy="24" r="4" fill="#C89A3E"/>
    </svg>
  </div>`;
}
const ICON_PIN = icon(`<path d="M12 2 L14 8 L20 9 L15.5 13 L17 20 L12 16.5 L7 20 L8.5 13 L4 9 L10 8 Z" ${S}/>`);
const ICON_HELP = icon(`<circle cx="12" cy="12" r="9" ${S}/><path d="M9.5 9.5 C9.5 7.5 11 6.5 12 6.5 C13.3 6.5 14.5 7.4 14.5 9 C14.5 10.6 12 10.8 12 13" ${S}/><circle cx="12" cy="16.3" r="0.9" fill="currentColor" stroke="none"/>`);
const ICON_CLOSE = icon(`<path d="M6 6 L18 18 M18 6 L6 18" ${S}/>`);
const ICON_BULB = icon(`<path d="M9 18 H15 M10 21 H14 M12 3 A6 6 0 0 0 8.5 14 C9.2 14.6 9.5 15.4 9.5 16 H14.5 C14.5 15.4 14.8 14.6 15.5 14 A6 6 0 0 0 12 3 Z" ${S}/>`);
const ICON_CHEVRON = icon(`<path d="M9 6 L15 12 L9 18" ${S}/>`, 14);
const ICON_INFO = icon(`<circle cx="12" cy="12" r="9" ${S}/><path d="M12 11 V16.5 M12 8 V8.1" ${S}/>`, 13);
const ICON_SEND = icon(`<path d="M4 12 L20 4 L14 20 L11 13 L4 12 Z" ${S}/>`, 17);
const ICON_SHIELD = icon(`<path d="M12 3 L19 6 V11 C19 16 16 19.5 12 21 C8 19.5 5 16 5 11 V6 Z" ${S}/><path d="M9 12 L11 14 L15.5 9.5" ${S}/>`);
const ICON_COMPASS = icon(`<circle cx="12" cy="12" r="9" ${S}/><path d="M15 9 L13 13 L9 15 L11 11 Z" ${S}/>`, 15);
const ICON_TARGET = icon(`<circle cx="12" cy="12" r="8" ${S}/><circle cx="12" cy="12" r="4" ${S}/><circle cx="12" cy="12" r="0.6" fill="currentColor" stroke="none"/>`, 15);
const ICON_BOLT = icon(`<path d="M13 2 L4 14 H11 L10 22 L20 9 H13 Z" ${S}/>`, 15);

// Suggestion-card icons, one per default/first-4 quick actions — cycled,
// purely decorative, never load-bearing for meaning.
const SUGGESTION_ICONS = [
  icon(`<path d="M4 17 L4 5 A2 2 0 0 1 6 3 H14 L20 9 V19 A2 2 0 0 1 18 21 H6 A2 2 0 0 1 4 19 Z" ${S}/><path d="M14 3 V9 H20" ${S}/>`, 16),
  icon(`<circle cx="11" cy="11" r="7" ${S}/><path d="M20 20 L16 16" ${S}/>`, 16),
  icon(`<rect x="4" y="4" width="16" height="16" rx="3" ${S}/><path d="M8 12 H16 M12 8 V16" ${S}/>`, 16),
  icon(`<circle cx="12" cy="8" r="3.5" ${S}/><path d="M5 20 C5 16 8 14 12 14 C16 14 19 16 19 20" ${S}/>`, 16),
];

/** Insight/capability copy is intentionally generic — there is no backend
 * endpoint generating personalized insights yet, so this never pretends
 * to know something real about the current user. See types.ts's
 * HavisIQContext docstring for the same principle applied to context. */
const INTELLIGENCE_INSIGHTS = [
  'A new conversation topic is trending this week',
  'Your last question may need a follow-up',
  'A real person is available if you need one',
];

const CAPABILITIES: { icon: string; title: string; desc: string }[] = [
  { icon: ICON_SPARK, title: 'Understand', desc: 'Reads your question in the context of this page.' },
  { icon: ICON_COMPASS, title: 'Guide', desc: 'Helps you navigate and use the platform.' },
  { icon: ICON_TARGET, title: 'Recommend', desc: 'Suggests next steps based on what you ask.' },
  { icon: ICON_BOLT, title: 'Act', desc: "Can hand you off to a human when it can't finish the job." },
];

/** Domain-agnostic fallback quick actions — used only when the workspace
 * admin hasn't configured any of their own via `GET /workspace/config`,
 * so a freshly-embedded workspace never shows empty Smart Suggestions,
 * and never shows content (like job-search prompts) the connected
 * backend can't actually answer. */
const DEFAULT_QUICK_ACTIONS: QuickAction[] = [
  { label: 'What can you help with?', prompt: 'What can you help me with?' },
  { label: 'Tell me about your products', prompt: 'Tell me about your products.' },
  { label: 'How do I get started?', prompt: 'How do I get started?' },
  { label: 'Talk to a human', prompt: "I'd like to talk to a person." },
];

const WIDGET_CSS = `
  :host, .havisiq-root { all: initial; }
  .havisiq-root {
    position: fixed;
    inset: 0;
    z-index: 2147483000;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    pointer-events: none;
    --havisiq-accent: #C89A3E;
    --havisiq-accent-soft: #FBF5E7;
    --havisiq-bg: #ffffff;
    --havisiq-panel-2: #F6F7FB;
    --havisiq-fg: #12141c;
    --havisiq-fg-dim: #6b7280;
    --havisiq-border: #e5e7eb;
  }
  .havisiq-root[data-theme='dark'] {
    --havisiq-accent-soft: rgba(200,154,62,0.16);
    --havisiq-bg: #14151c;
    --havisiq-panel-2: #191b24;
    --havisiq-fg: #f3f4f6;
    --havisiq-fg-dim: #9aa0ab;
    --havisiq-border: #2a2d38;
  }

  /* ---- panel: fills everything right of the host's own nav, not a
     full-page takeover and not an arbitrarily-capped drawer leaving a
     dead gap of host content showing through (the .havisiq-root wrapper
     is pointer-events:none; only the drawer itself opts back in).
     --havisiq-reserve-left is how much the host's own nav/sidebar
     needs — set from HavisIQConfig.reserveLeft, 0 by default. */
  .havisiq-panel {
    display: none;
    position: absolute; top: 0; right: 0; bottom: 0; pointer-events: auto;
    left: min(var(--havisiq-reserve-left, 0px), calc(100% - 480px));
    flex-direction: column;
    background: var(--havisiq-bg); color: var(--havisiq-fg);
    font-size: 14px; line-height: 1.5;
    border-left: 1px solid var(--havisiq-border);
    box-shadow: -24px 0 60px rgba(20,23,29,0.22);
  }
  .havisiq-panel.havisiq-open { display: flex; }

  .havisiq-topbar {
    flex-shrink: 0; display: flex; align-items: center; gap: 18px;
    padding: 14px 22px; background: var(--havisiq-bg); color: var(--havisiq-fg);
    border-bottom: 1px solid var(--havisiq-border);
  }
  .havisiq-brand { display: flex; align-items: center; gap: 10px; }
  .havisiq-brand-mark { flex-shrink: 0; display: flex; }
  .havisiq-brand-text { display: flex; flex-direction: column; line-height: 1.15; }
  .havisiq-brand-name { font-weight: 700; font-size: 14.5px; display: flex; align-items: center; gap: 7px; }
  .havisiq-ai-pill {
    font-size: 10px; font-weight: 700; letter-spacing: 0.04em;
    background: var(--havisiq-accent); color: #fff; padding: 1px 6px; border-radius: 6px;
  }
  .havisiq-brand-sub { font-size: 11px; color: var(--havisiq-fg-dim); }

  .havisiq-platform-pill {
    display: flex; align-items: center; gap: 6px;
    font-size: 12.5px; color: var(--havisiq-fg-dim);
    background: var(--havisiq-panel-2); border: 1px solid var(--havisiq-border);
    padding: 7px 12px; border-radius: 999px;
  }
  .havisiq-platform-pill b { color: var(--havisiq-fg); font-weight: 700; }

  .havisiq-topbar-spacer { flex: 1; }
  .havisiq-topbar-actions { display: flex; align-items: center; gap: 6px; }
  .havisiq-icon-btn {
    width: 32px; height: 32px; border-radius: 9px; border: none; cursor: pointer;
    background: transparent; color: var(--havisiq-fg-dim);
    display: flex; align-items: center; justify-content: center;
    transition: background 0.15s ease, color 0.15s ease;
  }
  .havisiq-icon-btn:hover { background: var(--havisiq-panel-2); color: var(--havisiq-fg); }
  .havisiq-intel-chip {
    display: flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600;
    color: var(--havisiq-fg-dim); padding: 0 4px;
  }

  /* ---- body: three columns ---- */
  .havisiq-body { flex: 1; display: flex; overflow: hidden; }

  .havisiq-col-left, .havisiq-col-right {
    flex-shrink: 0; overflow-y: auto; padding: 20px 16px;
  }
  .havisiq-col-left { width: 272px; background: var(--havisiq-panel-2); color: var(--havisiq-fg); border-right: 1px solid var(--havisiq-border); }
  .havisiq-col-right { width: 296px; background: var(--havisiq-panel-2); border-left: 1px solid var(--havisiq-border); }
  .havisiq-col-center { flex: 1; min-width: 0; display: flex; flex-direction: column; overflow: hidden; background: var(--havisiq-bg); }
  .havisiq-scroll {
    flex: 1; overflow-y: auto; display: flex; flex-direction: column; align-items: center;
    padding: 32px 28px 12px;
  }

  .havisiq-label {
    font-size: 10.5px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
    display: flex; align-items: center; gap: 6px;
    margin: 18px 4px 10px;
    color: var(--havisiq-fg-dim);
  }
  .havisiq-col-left .havisiq-label:first-child { margin-top: 2px; }

  .havisiq-insight-card {
    background: var(--havisiq-bg); border: 1px solid var(--havisiq-border);
    border-radius: 14px; padding: 14px;
  }
  .havisiq-insight-head { display: flex; align-items: center; gap: 10px; }
  .havisiq-insight-icon {
    width: 30px; height: 30px; border-radius: 9px; flex-shrink: 0;
    background: var(--havisiq-accent-soft); color: var(--havisiq-accent);
    display: flex; align-items: center; justify-content: center;
  }
  .havisiq-insight-title { font-size: 13px; font-weight: 700; color: var(--havisiq-fg); }
  .havisiq-insight-sub { font-size: 11.5px; color: var(--havisiq-fg-dim); }
  .havisiq-insight-list { list-style: none; margin: 12px 0 0; padding: 10px 0 0; border-top: 1px solid var(--havisiq-border); display: flex; flex-direction: column; gap: 9px; }
  .havisiq-insight-list li { display: flex; align-items: flex-start; gap: 8px; font-size: 12px; color: var(--havisiq-fg-dim); }
  .havisiq-insight-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--havisiq-accent); margin-top: 5px; flex-shrink: 0; }

  .havisiq-suggestion {
    display: flex; align-items: center; gap: 11px; width: 100%; text-align: left;
    border: 1px solid var(--havisiq-border); background: var(--havisiq-bg);
    border-radius: 12px; padding: 10px 11px; margin-bottom: 7px; cursor: pointer;
    font-family: inherit; color: inherit;
    transition: background 0.15s ease, border-color 0.15s ease;
  }
  .havisiq-suggestion:hover { background: var(--havisiq-accent-soft); border-color: var(--havisiq-accent); }
  .havisiq-suggestion-icon {
    width: 30px; height: 30px; border-radius: 9px; flex-shrink: 0;
    background: var(--havisiq-panel-2); color: var(--havisiq-accent);
    display: flex; align-items: center; justify-content: center;
  }
  .havisiq-suggestion-label { font-size: 12.5px; font-weight: 600; color: var(--havisiq-fg); flex: 1; }

  .havisiq-help-link {
    display: flex; align-items: center; gap: 9px; width: 100%; text-align: left;
    border: 1px solid var(--havisiq-border); background: transparent;
    border-radius: 12px; padding: 10px 11px; margin-top: 6px; cursor: pointer;
    font-family: inherit; color: var(--havisiq-fg-dim); font-size: 12px;
  }
  .havisiq-help-link:hover { color: var(--havisiq-fg); border-color: var(--havisiq-accent); }

  /* ---- center column ---- */
  /* Before the first message, .havisiq-hero + .havisiq-suggested-row
     show inside the scroll area and .havisiq-transcript is empty. Once
     a conversation starts, .havisiq-active hides both — the transcript
     becomes the only content, growing from the top like an ordinary
     chat thread, with the composer pinned below it (outside the
     scrolling area) rather than getting buried above a growing
     conversation. */
  .havisiq-hero { text-align: center; max-width: 520px; }
  .havisiq-hero-mark { display: flex; justify-content: center; margin: 0 auto 14px; }
  .havisiq-hero h2 { margin: 0; font-size: 24px; font-weight: 700; }
  .havisiq-hero p { margin: 6px 0 0; font-size: 14px; color: var(--havisiq-fg-dim); }

  .havisiq-suggested-row { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 20px; max-width: 640px; }
  .havisiq-chip {
    border: 1px solid var(--havisiq-border); background: var(--havisiq-bg); color: var(--havisiq-fg);
    border-radius: 999px; padding: 8px 14px; font-size: 12.5px; font-weight: 600; cursor: pointer;
    font-family: inherit; transition: border-color 0.15s ease, background 0.15s ease;
  }
  .havisiq-chip:hover { border-color: var(--havisiq-accent); background: var(--havisiq-accent-soft); }

  .havisiq-col-center.havisiq-active .havisiq-hero,
  .havisiq-col-center.havisiq-active .havisiq-suggested-row { display: none; }
  .havisiq-col-center.havisiq-active .havisiq-transcript { margin-top: 0; }

  .havisiq-composer {
    flex-shrink: 0; width: 100%; display: flex; flex-direction: column; align-items: center;
    padding: 14px 28px 20px; border-top: 1px solid var(--havisiq-border);
  }
  .havisiq-form { width: 100%; max-width: 640px; display: flex; align-items: center; gap: 8px; border: 1.5px solid var(--havisiq-border); border-radius: 999px; padding: 6px 6px 6px 18px; background: var(--havisiq-bg); }
  .havisiq-form:focus-within { border-color: var(--havisiq-accent); }
  .havisiq-input { flex: 1; border: none; outline: none; background: transparent; color: var(--havisiq-fg); font-size: 14px; font-family: inherit; }
  .havisiq-input::placeholder { color: var(--havisiq-fg-dim); }
  .havisiq-send {
    width: 36px; height: 36px; border-radius: 50%; border: none; cursor: pointer; flex-shrink: 0;
    background: var(--havisiq-accent); color: #fff; display: flex; align-items: center; justify-content: center;
    transition: filter 0.15s ease;
  }
  .havisiq-send:hover { filter: brightness(1.08); }
  .havisiq-send:disabled { opacity: 0.5; cursor: default; }
  .havisiq-disclaimer { width: 100%; max-width: 640px; font-size: 11px; color: var(--havisiq-fg-dim); margin-top: 10px; text-align: center; }

  .havisiq-transcript { width: 100%; max-width: 640px; margin-top: 26px; }
  .havisiq-transcript-label { font-size: 11px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--havisiq-fg-dim); margin-bottom: 10px; }
  .havisiq-messages { display: flex; flex-direction: column; gap: 10px; width: 100%; }
  .havisiq-empty-hint { font-size: 12.5px; color: var(--havisiq-fg-dim); border: 1px dashed var(--havisiq-border); border-radius: 12px; padding: 12px 14px; }
  .havisiq-bubble { padding: 9px 13px; border-radius: 14px; max-width: 90%; font-size: 13.5px; line-height: 1.5; }
  .havisiq-bubble.user { align-self: flex-end; background: var(--havisiq-accent); color: #fff; }
  .havisiq-bubble.assistant { align-self: flex-start; background: var(--havisiq-panel-2); border: 1px solid var(--havisiq-border); }
  .havisiq-bubble.error { align-self: stretch; background: #fee2e2; color: #991b1b; }

  /* ---- right column ---- */
  .havisiq-context-card, .havisiq-connection-card {
    background: var(--havisiq-bg); border: 1px solid var(--havisiq-border);
    border-radius: 14px; padding: 14px;
  }
  .havisiq-context-row + .havisiq-context-row { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--havisiq-border); }
  .havisiq-context-row .k { font-size: 11px; color: var(--havisiq-fg-dim); }
  .havisiq-context-row .v { font-size: 13px; font-weight: 700; margin-top: 2px; }
  .havisiq-context-row .v.havisiq-live { display: flex; align-items: center; gap: 6px; }
  .havisiq-live-dot { width: 6px; height: 6px; border-radius: 50%; background: #22c55e; flex-shrink: 0; }

  .havisiq-capability { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 12px; }
  .havisiq-capability-icon {
    width: 28px; height: 28px; border-radius: 8px; flex-shrink: 0;
    background: var(--havisiq-bg); border: 1px solid var(--havisiq-border); color: var(--havisiq-accent);
    display: flex; align-items: center; justify-content: center;
  }
  .havisiq-capability-title { font-size: 12.5px; font-weight: 700; }
  .havisiq-capability-desc { font-size: 11.5px; color: var(--havisiq-fg-dim); margin-top: 1px; line-height: 1.4; }

  .havisiq-connection-card { margin-top: 18px; }
  .havisiq-connection-top { display: flex; align-items: center; gap: 9px; }
  .havisiq-connection-icon {
    width: 30px; height: 30px; border-radius: 9px; flex-shrink: 0;
    background: var(--havisiq-accent-soft); color: var(--havisiq-accent);
    display: flex; align-items: center; justify-content: center;
  }
  .havisiq-connection-name { font-size: 13px; font-weight: 700; }
  .havisiq-secure-badge {
    margin-left: auto; font-size: 10px; font-weight: 700; color: #15803d;
    background: #dcfce7; padding: 3px 8px; border-radius: 999px;
  }
  .havisiq-connection-card p { font-size: 11.5px; color: var(--havisiq-fg-dim); margin: 10px 0 0; }
`;

export function createShadowHost(position: Position): { host: HTMLElement; root: ShadowRoot } {
  let host = document.getElementById(HOST_ID);
  if (!host) {
    host = document.createElement('div');
    host.id = HOST_ID;
    document.body.appendChild(host);
  }
  const root = host.shadowRoot ?? host.attachShadow({ mode: 'open' });
  root.innerHTML = '';

  const style = document.createElement('style');
  style.textContent = WIDGET_CSS;
  root.appendChild(style);

  const wrapper = document.createElement('div');
  wrapper.className = `havisiq-root ${position === 'bottom-left' ? 'havisiq-left' : 'havisiq-right'}`;
  root.appendChild(wrapper);

  return { host, root };
}

export function applyTheme(root: ShadowRoot, theme: Theme): 'light' | 'dark' {
  const wrapper = root.querySelector('.havisiq-root') as HTMLElement | null;
  const resolved =
    theme === 'auto'
      ? window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light'
      : theme;
  wrapper?.setAttribute('data-theme', resolved);
  return resolved;
}

/** No internal floating launcher — the host page's own UI (e.g. myAIRA's
 * "Intelligence Layer" sidebar button) is the only entry point, opened
 * via `HavisIQ.open()`. This still sets the workspace's primary color as
 * the panel's accent when the host hasn't asked for the HavisIQ ink/gold
 * identity to be overridden. */
export function applyPrimaryColor(root: ShadowRoot, primaryColor?: string | null): void {
  if (!primaryColor) return;
  const wrapper = root.querySelector('.havisiq-root') as HTMLElement;
  wrapper.style.setProperty('--havisiq-accent', primaryColor);
}

/** How much of the host's own nav/sidebar (in px) the panel must leave
 * uncovered — see `ResolvedConfig.reserveLeft`. */
export function applyReserveLeft(root: ShadowRoot, reserveLeft: number): void {
  const wrapper = root.querySelector('.havisiq-root') as HTMLElement;
  wrapper.style.setProperty('--havisiq-reserve-left', `${reserveLeft}px`);
}

function greeting(userName?: string): string {
  const hour = new Date().getHours();
  const time = hour < 12 ? 'morning' : hour < 18 ? 'afternoon' : 'evening';
  return userName ? `Good ${time}, ${userName}` : `Good ${time}`;
}

function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

export function buildPanel(
  root: ShadowRoot,
  branding: { name?: string; welcomeMessage?: string | null },
  context: HavisIQContext,
): {
  panel: HTMLElement;
  messageList: HTMLElement;
  input: HTMLInputElement;
  sendButton: HTMLButtonElement;
  suggestedRow: HTMLElement;
  suggestionList: HTMLElement;
  colCenter: HTMLElement;
  scrollArea: HTMLElement;
} {
  const wrapper = root.querySelector('.havisiq-root') as HTMLElement;
  const platformName = context.platform ?? branding.name ?? 'this platform';
  const roleName = context.role ?? 'Visitor';
  const pageName = context.currentPage ?? 'this page';

  const panel = document.createElement('div');
  panel.className = 'havisiq-panel';
  panel.innerHTML = `
    <div class="havisiq-topbar">
      <div class="havisiq-brand">
        <div class="havisiq-brand-mark">${havisiqMark(30)}</div>
        <div class="havisiq-brand-text">
          <span class="havisiq-brand-name">HavisIQ <span class="havisiq-ai-pill">AI</span></span>
          <span class="havisiq-brand-sub">Intelligence Layer</span>
        </div>
      </div>
      <div class="havisiq-platform-pill">You are in:&nbsp;<b class="havisiq-platform-name"></b></div>
      <div class="havisiq-topbar-spacer"></div>
      <div class="havisiq-topbar-actions">
        <button type="button" class="havisiq-icon-btn" aria-label="Pinned" title="Pinned">${ICON_PIN}</button>
        <span class="havisiq-intel-chip">${ICON_SPARK} Intelligence</span>
        <button type="button" class="havisiq-icon-btn" aria-label="Help" title="Help">${ICON_HELP}</button>
        <button type="button" class="havisiq-icon-btn havisiq-close" aria-label="Close">${ICON_CLOSE}</button>
      </div>
    </div>
    <div class="havisiq-body">
      <div class="havisiq-col-left">
        <div class="havisiq-label">Intelligence Overview</div>
        <div class="havisiq-insight-card">
          <div class="havisiq-insight-head">
            <div class="havisiq-insight-icon">${ICON_BULB}</div>
            <div>
              <div class="havisiq-insight-title">${INTELLIGENCE_INSIGHTS.length} Insights</div>
              <div class="havisiq-insight-sub">Worth a look</div>
            </div>
          </div>
          <ul class="havisiq-insight-list">
            ${INTELLIGENCE_INSIGHTS.map((text) => `<li><span class="havisiq-insight-dot"></span>${escapeHtml(text)}</li>`).join('')}
          </ul>
        </div>
        <div class="havisiq-label">Smart Suggestions</div>
        <div class="havisiq-suggestion-list"></div>
        <button type="button" class="havisiq-help-link">${ICON_HELP} Need help using the platform? Ask HavisIQ.</button>
      </div>
      <div class="havisiq-col-center">
        <div class="havisiq-scroll">
          <div class="havisiq-hero">
            <div class="havisiq-hero-mark">${havisiqMark(56)}</div>
            <h2 class="havisiq-greeting"></h2>
            <p>How can I help you today?</p>
          </div>
          <div class="havisiq-suggested-row"></div>
          <div class="havisiq-transcript">
            <div class="havisiq-transcript-label">Conversation</div>
            <div class="havisiq-messages"></div>
          </div>
        </div>
        <div class="havisiq-composer">
          <form class="havisiq-form">
            <input class="havisiq-input" type="text" placeholder="Ask HavisIQ anything…" autocomplete="off" />
            <button type="submit" class="havisiq-send" aria-label="Send">${ICON_SEND}</button>
          </form>
          <p class="havisiq-disclaimer">HavisIQ can make mistakes. Verify important information.</p>
        </div>
      </div>
      <div class="havisiq-col-right">
        <div class="havisiq-label">${ICON_INFO} Current Context</div>
        <div class="havisiq-context-card">
          <div class="havisiq-context-row"><div class="k">Platform</div><div class="v havisiq-platform-name-2"></div></div>
          <div class="havisiq-context-row"><div class="k">You are viewing</div><div class="v"></div></div>
          <div class="havisiq-context-row"><div class="k">User role</div><div class="v"></div></div>
          <div class="havisiq-context-row"><div class="k">Last updated</div><div class="v havisiq-live"><span class="havisiq-live-dot"></span>Just now</div></div>
        </div>
        <div class="havisiq-label">Available Capabilities</div>
        <div class="havisiq-capabilities"></div>
        <div class="havisiq-connection-card">
          <div class="havisiq-connection-top">
            <div class="havisiq-connection-icon">${ICON_SHIELD}</div>
            <span class="havisiq-connection-name">HavisIQ is connected to</span>
          </div>
          <div class="havisiq-context-row" style="margin-top:8px;padding-top:8px;">
            <div class="v havisiq-connection-workspace"></div>
            <span class="havisiq-secure-badge">Secure</span>
          </div>
          <p>All data is encrypted in transit.</p>
        </div>
      </div>
    </div>
  `;

  // Text that could come from workspace/host config is set via
  // textContent below, never through the innerHTML template above, so
  // nothing admin- or host-supplied can inject markup.
  panel.querySelectorAll('.havisiq-platform-name, .havisiq-platform-name-2').forEach((el) => {
    el.textContent = platformName;
  });
  (panel.querySelector('.havisiq-context-card .havisiq-context-row:nth-child(2) .v') as HTMLElement).textContent = pageName;
  (panel.querySelector('.havisiq-context-card .havisiq-context-row:nth-child(3) .v') as HTMLElement).textContent = roleName;
  (panel.querySelector('.havisiq-greeting') as HTMLElement).textContent = greeting(context.userName);
  (panel.querySelector('.havisiq-connection-workspace') as HTMLElement).textContent = branding.name ?? platformName;

  const capabilities = panel.querySelector('.havisiq-capabilities') as HTMLElement;
  for (const cap of CAPABILITIES) {
    const row = document.createElement('div');
    row.className = 'havisiq-capability';
    row.innerHTML = `<div class="havisiq-capability-icon">${cap.icon}</div><div><div class="havisiq-capability-title">${cap.title}</div><div class="havisiq-capability-desc"></div></div>`;
    (row.querySelector('.havisiq-capability-desc') as HTMLElement).textContent = cap.desc;
    capabilities.appendChild(row);
  }

  const messageList = panel.querySelector('.havisiq-messages') as HTMLElement;
  if (branding.welcomeMessage) {
    appendMessage(messageList, { role: 'assistant', text: branding.welcomeMessage });
  } else {
    const hint = document.createElement('div');
    hint.className = 'havisiq-empty-hint';
    hint.textContent = 'Ask a question below to get started.';
    messageList.appendChild(hint);
  }

  const input = panel.querySelector('.havisiq-input') as HTMLInputElement;
  const sendButton = panel.querySelector('.havisiq-send') as HTMLButtonElement;
  const suggestedRow = panel.querySelector('.havisiq-suggested-row') as HTMLElement;
  const suggestionList = panel.querySelector('.havisiq-suggestion-list') as HTMLElement;
  const colCenter = panel.querySelector('.havisiq-col-center') as HTMLElement;
  const scrollArea = panel.querySelector('.havisiq-scroll') as HTMLElement;

  const closeButton = panel.querySelector('.havisiq-close') as HTMLButtonElement;
  closeButton.addEventListener('click', () => panel.classList.remove('havisiq-open'));

  wrapper.appendChild(panel);
  return { panel, messageList, input, sendButton, suggestedRow, suggestionList, colCenter, scrollArea };
}

/** Appends one message bubble. Doesn't scroll itself — `.havisiq-messages`
 * isn't the scrolling element once inside `.havisiq-scroll` (see
 * `buildPanel`); callers scroll `scrollArea` after appending. */
export function appendMessage(messageList: HTMLElement, message: ChatMessage): void {
  const hint = messageList.querySelector('.havisiq-empty-hint');
  hint?.remove();
  const bubble = document.createElement('div');
  bubble.className = `havisiq-bubble ${message.role}`;
  bubble.textContent = message.text;
  messageList.appendChild(bubble);
}

export function appendErrorMessage(messageList: HTMLElement, text: string): void {
  messageList.querySelector('.havisiq-empty-hint')?.remove();
  const bubble = document.createElement('div');
  bubble.className = 'havisiq-bubble error';
  bubble.textContent = text;
  messageList.appendChild(bubble);
}

/** Populates the center column's pill row — kept as `.havisiq-chip`
 * elements with label-only textContent, one per action, matching the
 * SDK's existing test contract. */
export function appendQuickActionChips(
  row: HTMLElement,
  actions: QuickAction[],
  onSelect: (prompt: string) => void,
): void {
  const list = actions.length ? actions : DEFAULT_QUICK_ACTIONS;
  for (const action of list.slice(0, 4)) {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'havisiq-chip';
    chip.textContent = action.label;
    chip.addEventListener('click', () => onSelect(action.prompt));
    row.appendChild(chip);
  }
}

/** Populates the left column's richer "Smart Suggestions" cards — the
 * same underlying actions as the center chips, in the fuller card
 * treatment the Intelligence Layer's left rail uses. */
export function appendSuggestionCards(
  list: HTMLElement,
  actions: QuickAction[],
  onSelect: (prompt: string) => void,
): void {
  const items = actions.length ? actions : DEFAULT_QUICK_ACTIONS;
  items.slice(0, 4).forEach((action, index) => {
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'havisiq-suggestion';
    card.innerHTML = `<div class="havisiq-suggestion-icon">${SUGGESTION_ICONS[index % SUGGESTION_ICONS.length]}</div><span class="havisiq-suggestion-label"></span>${ICON_CHEVRON}`;
    (card.querySelector('.havisiq-suggestion-label') as HTMLElement).textContent = action.label;
    card.addEventListener('click', () => onSelect(action.prompt));
    list.appendChild(card);
  });
}
