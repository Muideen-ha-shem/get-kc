import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { resolveConfig } from '../src/config';
import { mountWidget } from '../src/widget';

const mockWorkspace = {
  id: 'w1',
  slug: 'acme',
  name: 'Acme',
  logo: null,
  primaryColor: '#0055CC',
  welcomeMessage: 'Welcome to Acme IQ',
  quickActions: [{ label: 'Pricing', prompt: 'What does it cost?' }],
};

describe('mountWidget', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    sessionStorage.clear();
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => mockWorkspace }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('appends a shadow-root host to the document body', async () => {
    await mountWidget(resolveConfig({ apiKey: 'k' }));

    const host = document.getElementById('havisiq-sdk-root');
    expect(host).not.toBeNull();
    expect(host?.shadowRoot).not.toBeNull();
  });

  it('renders a toggle button inside the shadow root', async () => {
    await mountWidget(resolveConfig({ apiKey: 'k' }));

    const root = document.getElementById('havisiq-sdk-root')!.shadowRoot!;
    expect(root.querySelector('.havisiq-toggle')).not.toBeNull();
  });

  it('shows the welcome message and quick-action chips after opening the panel', async () => {
    await mountWidget(resolveConfig({ apiKey: 'k' }));

    const root = document.getElementById('havisiq-sdk-root')!.shadowRoot!;
    const toggle = root.querySelector('.havisiq-toggle') as HTMLButtonElement;
    toggle.click();

    const panel = root.querySelector('.havisiq-panel');
    expect(panel?.classList.contains('havisiq-open')).toBe(true);
    expect(panel?.textContent).toContain('Welcome to Acme IQ');

    const chips = root.querySelectorAll('.havisiq-chip');
    expect(chips.length).toBe(1);
    expect(chips[0].textContent).toBe('Pricing');
  });

  it('renders an inline error bubble instead of throwing when config fetch fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401 }));

    await expect(mountWidget(resolveConfig({ apiKey: 'bad-key' }))).resolves.not.toThrow();

    const root = document.getElementById('havisiq-sdk-root')!.shadowRoot!;
    expect(root.querySelector('.havisiq-bubble.error')).not.toBeNull();
  });

  it('warns and falls back to floating for an unimplemented mode', async () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    await mountWidget(resolveConfig({ apiKey: 'k', mode: 'inline' }));

    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('inline'));
    const root = document.getElementById('havisiq-sdk-root')!.shadowRoot!;
    expect(root.querySelector('.havisiq-toggle')).not.toBeNull();
    warnSpy.mockRestore();
  });
});
