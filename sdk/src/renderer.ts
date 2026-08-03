import type { ChatMessage, Position, QuickAction, Theme } from './types';

const HOST_ID = 'havisiq-sdk-root';

const WIDGET_CSS = `
  :host, .havisiq-root { all: initial; }
  .havisiq-root {
    position: fixed;
    bottom: 20px;
    z-index: 2147483000;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    --havisiq-accent: #2563eb;
    --havisiq-bg: #ffffff;
    --havisiq-fg: #111827;
    --havisiq-border: #e5e7eb;
  }
  .havisiq-root[data-theme='dark'] {
    --havisiq-bg: #1f2937;
    --havisiq-fg: #f9fafb;
    --havisiq-border: #374151;
  }
  .havisiq-root.havisiq-left { left: 20px; }
  .havisiq-root.havisiq-right { right: 20px; }
  .havisiq-toggle {
    width: 56px; height: 56px; border-radius: 999px; border: none; cursor: pointer;
    background: var(--havisiq-accent); color: #fff; font-size: 24px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.2);
  }
  .havisiq-panel {
    display: none; flex-direction: column; width: 360px; height: 520px;
    position: absolute; bottom: 68px; background: var(--havisiq-bg); color: var(--havisiq-fg);
    border: 1px solid var(--havisiq-border); border-radius: 16px; overflow: hidden;
    box-shadow: 0 16px 48px rgba(0,0,0,0.25);
  }
  .havisiq-root.havisiq-right .havisiq-panel { right: 0; }
  .havisiq-root.havisiq-left .havisiq-panel { left: 0; }
  .havisiq-panel.havisiq-open { display: flex; }
  .havisiq-header {
    display: flex; align-items: center; gap: 8px; padding: 12px 16px;
    border-bottom: 1px solid var(--havisiq-border); font-weight: 600;
  }
  .havisiq-logo { width: 24px; height: 24px; border-radius: 6px; }
  .havisiq-messages { flex: 1; overflow-y: auto; padding: 12px 16px; display: flex; flex-direction: column; gap: 8px; }
  .havisiq-bubble { padding: 8px 12px; border-radius: 12px; max-width: 85%; font-size: 14px; line-height: 1.4; }
  .havisiq-bubble.user { align-self: flex-end; background: var(--havisiq-accent); color: #fff; }
  .havisiq-bubble.assistant { align-self: flex-start; background: var(--havisiq-border); }
  .havisiq-bubble.error { align-self: stretch; background: #fee2e2; color: #991b1b; }
  .havisiq-chips { display: flex; flex-wrap: wrap; gap: 6px; padding: 0 16px 8px; }
  .havisiq-chip {
    border: 1px solid var(--havisiq-border); background: transparent; color: var(--havisiq-fg);
    border-radius: 999px; padding: 4px 10px; font-size: 12px; cursor: pointer;
  }
  .havisiq-form { display: flex; gap: 8px; padding: 12px 16px; border-top: 1px solid var(--havisiq-border); }
  .havisiq-input {
    flex: 1; border: 1px solid var(--havisiq-border); border-radius: 999px; padding: 8px 12px;
    font-size: 14px; background: var(--havisiq-bg); color: var(--havisiq-fg);
  }
  .havisiq-send { border: none; background: var(--havisiq-accent); color: #fff; border-radius: 999px; padding: 8px 16px; cursor: pointer; }
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

export function buildToggleButton(root: ShadowRoot, primaryColor?: string | null): HTMLButtonElement {
  const wrapper = root.querySelector('.havisiq-root') as HTMLElement;
  const button = document.createElement('button');
  button.className = 'havisiq-toggle';
  button.setAttribute('aria-label', 'Open chat');
  button.textContent = '💬';
  if (primaryColor) {
    wrapper.style.setProperty('--havisiq-accent', primaryColor);
  }
  wrapper.appendChild(button);
  return button;
}

export function buildPanel(
  root: ShadowRoot,
  branding: { logo?: string | null; name?: string; welcomeMessage?: string | null },
): { panel: HTMLElement; messageList: HTMLElement; input: HTMLInputElement; sendButton: HTMLButtonElement } {
  const wrapper = root.querySelector('.havisiq-root') as HTMLElement;

  const panel = document.createElement('div');
  panel.className = 'havisiq-panel';

  const header = document.createElement('div');
  header.className = 'havisiq-header';
  if (branding.logo) {
    const img = document.createElement('img');
    img.className = 'havisiq-logo';
    img.src = branding.logo;
    img.alt = '';
    header.appendChild(img);
  }
  const title = document.createElement('span');
  title.textContent = branding.name ?? 'HavisIQ';
  header.appendChild(title);
  panel.appendChild(header);

  const messageList = document.createElement('div');
  messageList.className = 'havisiq-messages';
  panel.appendChild(messageList);

  if (branding.welcomeMessage) {
    appendMessage(messageList, { role: 'assistant', text: branding.welcomeMessage });
  }

  const form = document.createElement('form');
  form.className = 'havisiq-form';
  const input = document.createElement('input');
  input.className = 'havisiq-input';
  input.type = 'text';
  input.placeholder = 'Ask a question…';
  const sendButton = document.createElement('button');
  sendButton.className = 'havisiq-send';
  sendButton.type = 'submit';
  sendButton.textContent = 'Send';
  form.appendChild(input);
  form.appendChild(sendButton);
  panel.appendChild(form);

  wrapper.appendChild(panel);
  return { panel, messageList, input, sendButton };
}

export function appendMessage(messageList: HTMLElement, message: ChatMessage): void {
  const bubble = document.createElement('div');
  bubble.className = `havisiq-bubble ${message.role}`;
  bubble.textContent = message.text;
  messageList.appendChild(bubble);
  messageList.scrollTop = messageList.scrollHeight;
}

export function appendErrorMessage(messageList: HTMLElement, text: string): void {
  const bubble = document.createElement('div');
  bubble.className = 'havisiq-bubble error';
  bubble.textContent = text;
  messageList.appendChild(bubble);
}

export function appendQuickActionChips(
  panel: HTMLElement,
  actions: QuickAction[],
  onSelect: (prompt: string) => void,
): void {
  if (!actions.length) return;
  const chipRow = document.createElement('div');
  chipRow.className = 'havisiq-chips';
  for (const action of actions) {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'havisiq-chip';
    chip.textContent = action.label;
    chip.addEventListener('click', () => onSelect(action.prompt));
    chipRow.appendChild(chip);
  }
  const form = panel.querySelector('.havisiq-form');
  panel.insertBefore(chipRow, form);
}
