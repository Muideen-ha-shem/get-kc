import { describe, expect, it } from 'vitest';
import { resolveConfig } from '../src/config';

describe('resolveConfig', () => {
  it('throws when apiKey is missing', () => {
    // @ts-expect-error intentionally omitting required field
    expect(() => resolveConfig({})).toThrow(/apiKey/);
  });

  it('throws when apiKey is empty', () => {
    expect(() => resolveConfig({ apiKey: '   ' })).toThrow(/apiKey/);
  });

  it('applies defaults when only apiKey is given', () => {
    const resolved = resolveConfig({ apiKey: 'key-1' });

    expect(resolved.apiKey).toBe('key-1');
    expect(resolved.apiBaseUrl).toBe('https://api.havisiq.ai');
    expect(resolved.mode).toBe('floating');
    expect(resolved.theme).toBe('auto');
    expect(resolved.position).toBe('bottom-right');
  });

  it('preserves explicit overrides', () => {
    const resolved = resolveConfig({
      apiKey: 'key-1',
      apiBaseUrl: 'http://localhost:8000',
      theme: 'dark',
      position: 'bottom-left',
    });

    expect(resolved.apiBaseUrl).toBe('http://localhost:8000');
    expect(resolved.theme).toBe('dark');
    expect(resolved.position).toBe('bottom-left');
  });

  it('throws on an unknown mode', () => {
    // @ts-expect-error intentionally invalid mode
    expect(() => resolveConfig({ apiKey: 'key-1', mode: 'sidebar' })).toThrow(/mode/);
  });
});
