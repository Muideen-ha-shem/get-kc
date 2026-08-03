import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchWorkspaceConfig, getOrCreateSessionId, sendChatMessage } from '../src/client';
import { resolveConfig } from '../src/config';

const config = resolveConfig({ apiKey: 'test-key', apiBaseUrl: 'http://localhost:8000' });

describe('getOrCreateSessionId', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('persists the generated id across calls', () => {
    const first = getOrCreateSessionId();
    const second = getOrCreateSessionId();
    expect(first).toBe(second);
  });

  it('stores it under the sdk-specific key', () => {
    const id = getOrCreateSessionId();
    expect(sessionStorage.getItem('havisiq_sdk_session_id')).toBe(id);
  });
});

describe('fetchWorkspaceConfig', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('GETs /workspace/config with the X-Api-Key header', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 'w1', slug: 'acme', name: 'Acme', logo: null, primaryColor: null, welcomeMessage: null, quickActions: null }),
    });
    vi.stubGlobal('fetch', mockFetch);

    await fetchWorkspaceConfig(config);

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/workspace/config',
      expect.objectContaining({ method: 'GET', headers: { 'X-Api-Key': 'test-key' } }),
    );
  });

  it('throws on a non-2xx response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401 }));

    await expect(fetchWorkspaceConfig(config)).rejects.toThrow(/401/);
  });
});

describe('sendChatMessage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('POSTs exactly {message, session_id} to /chat', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ answer: 'Hi there', sources: [], session_id: 's1' }),
    });
    vi.stubGlobal('fetch', mockFetch);

    await sendChatMessage(config, 'Hello', 's1');

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toBe('http://localhost:8000/chat');
    expect(init.method).toBe('POST');
    expect(init.headers).toEqual({ 'Content-Type': 'application/json', 'X-Api-Key': 'test-key' });
    expect(JSON.parse(init.body)).toEqual({ message: 'Hello', session_id: 's1' });
  });

  it('maps the response to the SDK ChatApiResponse shape', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ answer: 'Hi there', sources: ['https://a.com'], session_id: 's1' }),
      }),
    );

    const result = await sendChatMessage(config, 'Hello', 's1');

    expect(result).toEqual({ answer: 'Hi there', sources: ['https://a.com'], sessionId: 's1' });
  });
});
