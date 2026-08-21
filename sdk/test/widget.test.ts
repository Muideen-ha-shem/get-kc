import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { resolveConfig } from '../src/config';
import { mountWidget, openPanel } from '../src/widget';

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

  it('renders the panel inside the shadow root, closed by default', async () => {
    await mountWidget(resolveConfig({ apiKey: 'k' }));

    const root = document.getElementById('havisiq-sdk-root')!.shadowRoot!;
    const panel = root.querySelector('.havisiq-panel');
    expect(panel).not.toBeNull();
    expect(panel?.classList.contains('havisiq-open')).toBe(false);
  });

  it('shows the welcome message and quick-action chips once opened via openPanel()', async () => {
    await mountWidget(resolveConfig({ apiKey: 'k' }));

    openPanel();

    const root = document.getElementById('havisiq-sdk-root')!.shadowRoot!;
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
    expect(root.querySelector('.havisiq-panel')).not.toBeNull();
    warnSpy.mockRestore();
  });
});
